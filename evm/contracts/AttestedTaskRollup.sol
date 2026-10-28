// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./IQuoteVerifier.sol";

/// @notice Bounded deterministic tasks with an attestation-gated challenge window.
/// An attested enclave instance only shortens the window; it never settles a task by itself
/// unless the contract is deployed in teeOnly mode, which exists as an experimental baseline.
/// Any challenge is resolved by on-chain recomputation that anyone may trigger.
contract AttestedTaskRollup {
    enum Phase { NONE, SUBMITTED, OPEN, SETTLED }
    uint8 public constant REJECT = 0;
    uint8 public constant LONG = 1;
    uint8 public constant SHORT = 2;
    uint8 public constant VERIFY_FAILED = 8;

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
        address instance;
        Phase phase;
        bool fastPath;
        bool recomputed;
        uint8 verdict;
        uint64 submittedAt;
        uint64 challengeDeadline;
        uint64 settledAt;
    }
    struct Instance {
        uint8 action;
        uint8 tcbStatus;
        uint64 expiresAt;
    }

    uint32 public constant TASK_VERSION = 1;
    uint16 public constant MAX_STEPS = 128;
    bytes32 public constant DOMAIN = keccak256("HYBRID_ATTESTED_TASK_V1");

    IQuoteVerifier public immutable verifier;
    bytes32 public immutable mrEnclave;
    uint256 public immutable bond;
    uint64 public immutable shortWindow;
    uint64 public immutable longWindow;
    uint64 public immutable instanceTtl;
    bool public immutable teeOnly;
    // 2 bits per index: indices 0..7 are TCB statuses, index 8 is a failed or mismatched quote.
    uint256 public immutable policy;

    mapping(bytes32 => Task) private tasks;
    mapping(address => Instance) public instances;
    mapping(address => uint256) public claimable;
    uint256 public locked;
    uint256 public totalClaimable;
    bool private withdrawing;

    event InstanceRegistered(address indexed instance, uint8 tcbStatus, uint8 action, uint64 expiresAt);
    event Submitted(bytes32 indexed taskId, address indexed submitter, address indexed instance, bool fastPath, uint64 challengeDeadline);
    event Challenged(bytes32 indexed taskId, address indexed challenger);
    event Settled(bytes32 indexed taskId, uint8 verdict, address indexed winner, uint256 amount, bool recomputed);

    constructor(
        address verifier_,
        bytes32 mrEnclave_,
        uint256 bond_,
        uint64 shortWindow_,
        uint64 longWindow_,
        uint64 instanceTtl_,
        bool teeOnly_,
        uint8[9] memory actions
    ) {
        require(bond_ > 0 && shortWindow_ > 0 && longWindow_ >= shortWindow_ && instanceTtl_ > 0, "config");
        uint256 packed;
        for (uint256 i = 0; i < 9; ++i) {
            require(actions[i] <= SHORT, "action");
            packed |= uint256(actions[i]) << (2 * i);
        }
        require(actions[VERIFY_FAILED] != SHORT, "failed quote cannot be short");
        verifier = IQuoteVerifier(verifier_);
        mrEnclave = mrEnclave_;
        bond = bond_;
        shortWindow = shortWindow_;
        longWindow = longWindow_;
        instanceTtl = instanceTtl_;
        teeOnly = teeOnly_;
        policy = packed;
    }

    function actionFor(uint8 index) public view returns (uint8) {
        return uint8((policy >> (2 * uint256(index))) & 3);
    }

    function getTask(bytes32 id) external view returns (Task memory) { return tasks[id]; }

    function taskDigest(TaskInput memory t) public view returns (bytes32) {
        return keccak256(abi.encode(DOMAIN, block.chainid, address(this), t));
    }

    // Ordered vector commitment over x_0..x_n, not a Merkle root.
    function compute(bytes32 initial, uint16 steps) public pure returns (bytes32 output, bytes32 root) {
        require(steps >= 1 && steps <= MAX_STEPS, "steps");
        bytes32[] memory trace = new bytes32[](uint256(steps) + 1);
        trace[0] = initial;
        for (uint256 i = 0; i < steps; ++i) trace[i + 1] = keccak256(abi.encode(i, trace[i]));
        return (trace[steps], keccak256(abi.encode(trace)));
    }

    /// @notice The quote's report_data must start with the 20-byte enclave instance address.
    function registerInstance(bytes calldata quote) external payable returns (address instance, uint8 action) {
        (bool ok, uint8 status, bytes32 mr, bytes32 rd) = verifier.verifyQuote{value: msg.value}(quote);
        instance = address(bytes20(rd));
        uint8 index = (!ok || mr != mrEnclave || status > 7 || instance == address(0)) ? VERIFY_FAILED : status;
        action = actionFor(index);
        require(action != REJECT, "quote rejected");
        uint64 expiresAt = uint64(block.timestamp + instanceTtl);
        instances[instance] = Instance(action, ok ? status : 255, expiresAt);
        emit InstanceRegistered(instance, ok ? status : 255, action, expiresAt);
    }

    function submit(TaskInput calldata input, bytes calldata submitterSig, bytes calldata instanceSig) external payable {
        require(msg.value == bond, "bond");
        require(input.taskId != bytes32(0) && tasks[input.taskId].phase == Phase.NONE, "task id");
        require(input.steps >= 1 && input.steps <= MAX_STEPS && input.version == TASK_VERSION, "task bounds");
        bytes32 digest = taskDigest(input);
        require(_signer(digest, submitterSig) == msg.sender, "signature");
        address instance;
        bool fast;
        if (instanceSig.length != 0) {
            instance = _signer(digest, instanceSig);
            Instance memory inst = instances[instance];
            fast = inst.action == SHORT && block.timestamp <= inst.expiresAt;
        }
        Task storage t = tasks[input.taskId];
        t.input = input;
        t.submitter = msg.sender;
        t.instance = instance;
        t.fastPath = fast;
        t.submittedAt = uint64(block.timestamp);
        locked += msg.value;
        if (teeOnly && fast) {
            t.phase = Phase.SUBMITTED;
            emit Submitted(input.taskId, msg.sender, instance, true, uint64(block.timestamp));
            _settle(t, input.taskId, false);
            return;
        }
        t.phase = Phase.SUBMITTED;
        t.challengeDeadline = uint64(block.timestamp + (fast ? shortWindow : longWindow));
        emit Submitted(input.taskId, msg.sender, instance, fast, t.challengeDeadline);
    }

    function openChallenge(bytes32 id) external payable {
        Task storage t = tasks[id];
        require(t.phase == Phase.SUBMITTED, "phase");
        require(block.timestamp <= t.challengeDeadline, "window");
        require(msg.sender != t.submitter && msg.value == bond, "challenger bond");
        t.challenger = msg.sender;
        t.phase = Phase.OPEN;
        locked += msg.value;
        emit Challenged(id, msg.sender);
    }

    /// @notice Terminating recomputation. Anyone may call it once a challenge is open.
    function adjudicate(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase == Phase.OPEN, "phase");
        _settle(t, id, true);
    }

    /// @notice Unchallenged settlement after the window. No recomputation on this path.
    function finalize(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase == Phase.SUBMITTED, "phase");
        require(block.timestamp > t.challengeDeadline, "window");
        _settle(t, id, false);
    }

    function withdraw(address payable recipient) external {
        require(!withdrawing && recipient != address(0), "withdraw guard");
        uint256 amount = claimable[msg.sender];
        require(amount > 0, "no balance");
        withdrawing = true;
        claimable[msg.sender] = 0;
        totalClaimable -= amount;
        (bool ok,) = recipient.call{value: amount}("");
        require(ok, "transfer failed");
        withdrawing = false;
    }

    function _settle(Task storage t, bytes32 id, bool recompute) private {
        if (recompute) {
            (bytes32 output, bytes32 root) = compute(t.input.initial, t.input.steps);
            t.verdict = (output != t.input.output ? 1 : 0) | (root != t.input.traceRoot ? 2 : 0);
            t.recomputed = true;
        }
        uint256 amount = t.challenger == address(0) ? bond : 2 * bond;
        address winner = t.verdict == 0 ? t.submitter : t.challenger;
        t.phase = Phase.SETTLED;
        t.settledAt = uint64(block.timestamp);
        locked -= amount;
        claimable[winner] += amount;
        totalClaimable += amount;
        emit Settled(id, t.verdict, winner, amount, recompute);
    }

    function _signer(bytes32 digest, bytes calldata sig) private pure returns (address) {
        if (sig.length != 65) return address(0);
        bytes32 r; bytes32 s; uint8 v;
        assembly { r := calldataload(sig.offset) s := calldataload(add(sig.offset, 32)) v := byte(0, calldataload(add(sig.offset, 64))) }
        if ((v != 27 && v != 28) || uint256(s) > 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0) return address(0);
        return ecrecover(keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest)), v, r, s);
    }
}
