// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Bounded deterministic-task experiment, not a general VM or AI fault proof.
contract BoundedTaskRollup {
    enum Phase { NONE, SUBMITTED, OPEN, RESPONDED, LOCATING, READY, VERIFIED, SETTLED }
    struct TaskInput {
        bytes32 taskId;
        bytes32 initial;
        uint16 steps;
        uint32 version;
        bytes32 output;
        bytes32 traceRoot;
        bytes32 dataHash;
    }
    struct Task {
        TaskInput input;
        address submitter;
        address challenger;
        Phase phase;
        uint64 challengeDeadline;
        uint64 absoluteDeadline;
        uint64 timeoutAt;
        uint8 recoveries;
        uint16 left;
        uint16 right;
        uint16 round;
        uint16 firstMismatch;
        bytes32 evidenceRoot;
        uint8 verdict;
    }
    uint32 public constant TASK_VERSION = 1;
    uint16 public constant MAX_STEPS = 128;
    bytes32 public constant DOMAIN = keccak256("HYBRID_BOUNDED_TASK_V1");
    uint256 public immutable bond;
    uint64 public immutable challengeWindow;
    uint64 public immutable stepTimeout;
    uint8 public immutable maxRecoveries;
    uint256 public totalBurned;
    mapping(bytes32 => Task) private tasks;
    mapping(address => uint256) public claimable;
    uint256 public locked;
    uint256 public totalClaimable;
    uint256 public totalDeposited;
    uint256 public totalWithdrawn;
    bool private withdrawing;
    event Submitted(bytes32 indexed taskId, address indexed submitter, bytes32 digest, uint64 challengeDeadline);
    event Challenged(bytes32 indexed taskId, address indexed challenger, uint64 absoluteDeadline);
    event Responded(bytes32 indexed taskId, bytes32 evidenceRoot, uint16 firstMismatch);
    event Advanced(bytes32 indexed taskId, uint16 left, uint16 right, uint16 round);
    event Recovered(bytes32 indexed taskId, address indexed observer, uint8 count, uint64 timeoutAt);
    event Verified(bytes32 indexed taskId, uint8 verdict);
    event Settled(bytes32 indexed taskId, uint8 verdict, address indexed winner, uint256 amount);
    event Withdrawn(address indexed owner, address indexed recipient, uint256 amount);
    event DaBound(bytes32 indexed taskId, address indexed responder, bytes32 daRef, uint64 deadline);
    event DaFulfilled(bytes32 indexed taskId, bytes32 disclosedHash);
    event DaSlashed(bytes32 indexed taskId, address indexed responder, uint256 amount);
    struct DaDuty {
        bytes32 daRef;
        address responder;
        uint64 deadline;
        bool bound;
        bool fulfilled;
        bool slashed;
        bytes32 disclosedHash;
    }
    mapping(bytes32 => DaDuty) private daDuties;

    constructor(uint256 bond_, uint64 challengeWindow_, uint64 stepTimeout_, uint8 maxRecoveries_) {
        require(bond_ > 0 && stepTimeout_ >= 2 && challengeWindow_ > 0, "config");
        require(maxRecoveries_ <= 2, "recovery config");
        bond = bond_; challengeWindow = challengeWindow_; stepTimeout = stepTimeout_; maxRecoveries = maxRecoveries_;
    }
    function getTask(bytes32 id) external view returns (Task memory) { return tasks[id]; }
    function getDaDuty(bytes32 id) external view returns (DaDuty memory) { return daDuties[id]; }
    function taskDigest(TaskInput memory t) public view returns (bytes32) {
        return keccak256(abi.encode(DOMAIN, block.chainid, address(this), t));
    }
    // x_0 is included; root = keccak256(abi.encode(bytes32[n+1])). This is an ordered
    // vector commitment, deliberately NOT a Merkle root or a single-step proof.
    function compute(bytes32 initial, uint16 steps) public pure returns (bytes32 output, bytes32 root) {
        require(steps >= 1 && steps <= MAX_STEPS, "steps");
        bytes32[] memory trace = new bytes32[](uint256(steps) + 1);
        trace[0] = initial;
        for (uint256 i = 0; i < steps; ++i) trace[i + 1] = keccak256(abi.encode(i, trace[i]));
        return (trace[steps], keccak256(abi.encode(trace)));
    }
    function submit(TaskInput calldata input, bytes calldata signature) external payable {
        require(msg.value == bond, "bond");
        require(input.taskId != bytes32(0) && tasks[input.taskId].phase == Phase.NONE, "task id");
        require(input.steps >= 1 && input.steps <= MAX_STEPS && input.version == TASK_VERSION, "task bounds");
        require(_signer(taskDigest(input), signature) == msg.sender, "signature");
        Task storage t = tasks[input.taskId];
        t.input = input; t.submitter = msg.sender; t.phase = Phase.SUBMITTED;
        t.challengeDeadline = uint64(block.timestamp + challengeWindow);
        locked += msg.value; totalDeposited += msg.value;
        emit Submitted(input.taskId, msg.sender, taskDigest(input), t.challengeDeadline);
    }
    function normalTransitions(uint16 steps) public pure returns (uint16) {
        require(steps >= 1 && steps <= MAX_STEPS, "steps");
        uint16 rounds; uint16 width = steps + 1;
        while (width > 1) { width = (width + 1) / 2; ++rounds; }
        return rounds + 3; // response + bisection rounds + verification + settlement
    }
    function openChallenge(bytes32 id) external payable {
        Task storage t = tasks[id];
        require(t.phase == Phase.SUBMITTED, "phase");
        require(block.timestamp <= t.challengeDeadline, "window");
        require(msg.sender != t.submitter && msg.value == bond, "challenger bond");
        t.challenger = msg.sender; t.phase = Phase.OPEN; t.right = t.input.steps;
        t.absoluteDeadline = uint64(block.timestamp + uint256(normalTransitions(t.input.steps) + maxRecoveries) * stepTimeout);
        _touch(t); locked += msg.value; totalDeposited += msg.value;
        emit Challenged(id, msg.sender, t.absoluteDeadline);
    }
    // Optional diagnostic response, not an obligation punishable by an offline timeout.
    // A third party cannot replace the committed trace. Correctness is checked separately.
    function respond(bytes32 id, bytes32[] calldata trace) external {
        Task storage t = tasks[id];
        require(t.phase == Phase.OPEN, "phase");
        require(msg.sender == t.submitter, "submitter only"); _live(t);
        require(trace.length == uint256(t.input.steps) + 1, "trace length");
        require(keccak256(abi.encode(trace)) == t.input.traceRoot, "trace binding");
        bytes32 expected = t.input.initial;
        uint16 first = t.input.steps; bool found;
        for (uint16 i = 0; i <= t.input.steps; ++i) {
            if (!found && trace[i] != expected) { first = i; found = true; }
            if (i < t.input.steps) expected = keccak256(abi.encode(uint256(i), expected));
        }
        t.firstMismatch = first;
        t.evidenceRoot = keccak256(abi.encode(taskDigest(t.input), t.input.traceRoot));
        t.phase = Phase.RESPONDED; _touch(t);
        emit Responded(id, t.evidenceRoot, first);
    }
    function advance(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase == Phase.RESPONDED || t.phase == Phase.LOCATING, "phase"); _live(t);
        require(t.left < t.right, "already located");
        uint16 mid = (t.left + t.right) / 2;
        if (t.firstMismatch <= mid) t.right = mid; else t.left = mid + 1;
        ++t.round; t.phase = t.left == t.right ? Phase.READY : Phase.LOCATING; _touch(t);
        emit Advanced(id, t.left, t.right, t.round);
    }
    function recover(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase >= Phase.OPEN && t.phase <= Phase.READY, "phase");
        require(block.timestamp > t.timeoutAt && block.timestamp < t.absoluteDeadline, "recovery time");
        require(t.recoveries < maxRecoveries, "recovery limit");
        ++t.recoveries; _touch(t);
        emit Recovered(id, msg.sender, t.recoveries, t.timeoutAt);
    }
    function replay(bytes32 id) external {
        Task storage t = tasks[id]; require(t.phase == Phase.READY, "phase"); _live(t);
        _verify(t, id);
    }
    // Anyone may bypass optional localization: all deterministic inputs are already public.
    // This path remains available at and after every deadline, even with both parties offline.
    function adjudicate(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase >= Phase.OPEN && t.phase < Phase.SETTLED, "phase");
        _daClear(id);
        if (t.phase != Phase.VERIFIED) _verify(t, id);
        _settle(t, id, t.challenger);
    }
    function settle(bytes32 id) external {
        Task storage t = tasks[id]; require(t.phase == Phase.VERIFIED, "phase"); _daClear(id); _settle(t, id, t.challenger);
    }
    function terminate(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase >= Phase.OPEN && t.phase < Phase.SETTLED, "phase");
        require(block.timestamp > t.timeoutAt || block.timestamp >= t.absoluteDeadline, "not timed out");
        _daClear(id);
        if (t.phase != Phase.VERIFIED) _verify(t, id);
        _settle(t, id, t.challenger);
    }
    function finalize(bytes32 id) external {
        Task storage t = tasks[id]; require(t.phase == Phase.SUBMITTED, "phase");
        require(block.timestamp > t.challengeDeadline, "window");
        _daClear(id);
        _verify(t, id);
        if (t.verdict == 0) {
            _settle(t, id, address(0));
        } else {
            // A caller bounty here lets the submitter reclaim its own slash via a Sybil.
            t.phase = Phase.SETTLED; locked -= bond; totalBurned += bond;
            (bool ok,) = payable(address(0)).call{value: bond}("");
            require(ok, "burn failed");
            emit Settled(id, t.verdict, address(0), bond);
        }
    }
    function withdraw(address payable recipient) external {
        require(!withdrawing && recipient != address(0), "withdraw guard");
        uint256 amount = claimable[msg.sender]; require(amount > 0, "no balance");
        withdrawing = true; claimable[msg.sender] = 0; totalClaimable -= amount; totalWithdrawn += amount;
        (bool ok,) = recipient.call{value: amount}(""); require(ok, "transfer failed");
        withdrawing = false; emit Withdrawn(msg.sender, recipient, amount);
    }
    // Optional disclosure duty. Unbound tasks keep the previous settlement path.
    // A bound duty blocks settlement until the preimage of dataHash is posted
    // or the duty is slashed after its deadline. This is a preimage disclosure,
    // not an on-chain EIP-4844 point evaluation.
    function bindDa(bytes32 id, bytes32 daRef) external payable {
        Task storage t = tasks[id];
        require(t.phase == Phase.SUBMITTED, "phase");
        require(msg.sender == t.submitter, "submitter only");
        require(block.timestamp <= t.challengeDeadline, "window");
        require(daRef != bytes32(0) && !daDuties[id].bound, "da ref");
        require(msg.value == bond, "da bond");
        daDuties[id] = DaDuty({
            daRef: daRef,
            responder: msg.sender,
            deadline: t.challengeDeadline,
            bound: true,
            fulfilled: false,
            slashed: false,
            disclosedHash: bytes32(0)
        });
        locked += msg.value; totalDeposited += msg.value;
        emit DaBound(id, msg.sender, daRef, t.challengeDeadline);
    }
    function fulfillDa(bytes32 id, bytes calldata payload) external {
        DaDuty storage d = daDuties[id];
        Task storage t = tasks[id];
        require(d.bound && !d.fulfilled && !d.slashed, "da state");
        require(msg.sender == d.responder, "responder only");
        require(block.timestamp <= d.deadline, "da window");
        bytes32 got = keccak256(payload);
        require(got == t.input.dataHash, "payload hash");
        d.fulfilled = true; d.disclosedHash = got;
        locked -= bond; claimable[d.responder] += bond; totalClaimable += bond;
        emit DaFulfilled(id, got);
    }
    function slashDa(bytes32 id) external {
        DaDuty storage d = daDuties[id];
        require(d.bound && !d.fulfilled && !d.slashed, "da state");
        require(block.timestamp > d.deadline, "da window");
        d.slashed = true; locked -= bond; totalBurned += bond;
        (bool ok,) = payable(address(0)).call{value: bond}("");
        require(ok, "burn failed");
        emit DaSlashed(id, d.responder, bond);
    }
    function _daClear(bytes32 id) private view {
        DaDuty storage d = daDuties[id];
        require(!d.bound || d.fulfilled || d.slashed, "da pending");
    }
    function _verify(Task storage t, bytes32 id) private {
        (bytes32 output, bytes32 root) = compute(t.input.initial, t.input.steps);
        // bit 0: incorrect final output; bit 1: incorrect ordered trace commitment.
        t.verdict = (output != t.input.output ? 1 : 0) | (root != t.input.traceRoot ? 2 : 0);
        t.phase = Phase.VERIFIED; emit Verified(id, t.verdict);
    }
    function _settle(Task storage t, bytes32 id, address errorRecipient) private {
        uint256 amount = t.challenger == address(0) ? bond : 2 * bond;
        address winner = t.verdict == 0 ? t.submitter : errorRecipient;
        t.phase = Phase.SETTLED; locked -= amount; claimable[winner] += amount; totalClaimable += amount;
        emit Settled(id, t.verdict, winner, amount);
    }
    function _live(Task storage t) private view {
        require(block.timestamp <= t.timeoutAt && block.timestamp < t.absoluteDeadline, "timed out");
    }
    function _touch(Task storage t) private {
        uint256 deadline = block.timestamp + stepTimeout;
        t.timeoutAt = uint64(deadline < t.absoluteDeadline ? deadline : t.absoluteDeadline);
    }
    function _signer(bytes32 digest, bytes calldata sig) private pure returns (address) {
        if (sig.length != 65) return address(0);
        bytes32 r; bytes32 s; uint8 v;
        assembly { r := calldataload(sig.offset) s := calldataload(add(sig.offset, 32)) v := byte(0, calldataload(add(sig.offset, 64))) }
        if ((v != 27 && v != 28) || uint256(s) > 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0) return address(0);
        return ecrecover(keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest)), v, r, s);
    }
}
