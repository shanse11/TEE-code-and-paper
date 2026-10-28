// SPDX-License-Identifier: MIT
//
// evm/contracts/MechanismBaseline.sol
//
// 阶段 G 的 **机制基线（mechanism baseline）**，仅用于同计算模型微基准对照。
//
// 这不是 Arbitrum / Optimism / TeeRollup 的任何官方实现，也**不是**本项目生产协议的一部分；
// 它是一个最小化的「二分定位 + 单步证明 + 无兜底重算」争议机制，用来在**与
// BoundedTaskRollup 完全相同的有界 hash 链计算模型**下做同口径对照：
//
//   - 与 BoundedTaskRollup 相同：submit / openChallenge / respond / advance 二分定位 / settle。
//   - 与 BoundedTaskRollup 不同：
//       1. **没有** adjudicate 直接重算兜底；
//       2. 定位完成后用 **单步证明** step() 验证 trace[idx-1] -> trace[idx]；
//       3. 超时后只能 terminate()，由挑战方获胜（提交方被罚没），
//          即使提交方的 trace 本来是**正确的**。
//
// 这样可以在同一模型内量化「去掉兜底重算」的代价，而不是靠断言。

pragma solidity 0.8.26;

contract MechanismBaseline {
    enum Phase { NONE, SUBMITTED, OPEN, RESPONDED, LOCATING, READY, SETTLED }

    struct Input {
        bytes32 taskId;
        bytes32 initial;
        uint16 steps;
        uint32 version;
        bytes32 output;
        bytes32 traceRoot;
        bytes32 dataHash;
    }

    bytes32 public constant DOMAIN = keccak256("MECHANISM_BASELINE_V1");
    uint32 public constant TASK_VERSION = 1;
    uint16 public constant MAX_STEPS = 128;

    uint256 public immutable bond;
    uint64 public immutable challengeWindow;
    uint64 public immutable stepTimeout;

    struct Task {
        Input input;
        address submitter;
        address challenger;
        uint16 left;
        uint16 right;
        uint16 round;
        uint16 firstMismatch;
        uint64 timeoutAt;
        uint64 absoluteDeadline;
        uint8 phase;
    }

    mapping(bytes32 => Task) private tasks;
    mapping(address => uint256) public claimable;

    event Submitted(bytes32 indexed taskId, address indexed submitter);
    event Challenged(bytes32 indexed taskId, address indexed challenger);
    event Responded(bytes32 indexed taskId, uint16 firstMismatch);
    event Advanced(bytes32 indexed taskId, uint16 left, uint16 right);
    event Stepped(bytes32 indexed taskId, uint16 index, bool ok);
    event Settled(bytes32 indexed taskId, address winner, uint256 amount);

    constructor(uint256 bond_, uint64 challengeWindow_, uint64 stepTimeout_) {
        require(bond_ > 0 && challengeWindow_ > 0 && stepTimeout_ >= 2, "config");
        bond = bond_; challengeWindow = challengeWindow_; stepTimeout = stepTimeout_;
    }

    function getTask(bytes32 id) external view returns (Task memory) { return tasks[id]; }

    function taskDigest(Input memory t) public view returns (bytes32) {
        return keccak256(abi.encode(DOMAIN, block.chainid, address(this), t));
    }

    function submit(Input calldata input, bytes calldata signature) external payable {
        require(msg.value == bond, "bond");
        require(input.taskId != bytes32(0) && tasks[input.taskId].phase == uint8(Phase.NONE), "task id");
        require(input.steps >= 1 && input.steps <= MAX_STEPS && input.version == TASK_VERSION, "task bounds");
        require(_signer(taskDigest(input), signature) == msg.sender, "signature");
        Task storage t = tasks[input.taskId];
        t.input = input;
        t.submitter = msg.sender;
        t.phase = uint8(Phase.SUBMITTED);
        emit Submitted(input.taskId, msg.sender);
    }

    function openChallenge(bytes32 id) external payable {
        Task storage t = tasks[id];
        require(t.phase == uint8(Phase.SUBMITTED), "phase");
        require(msg.sender != t.submitter && msg.value == bond, "challenger bond");
        t.challenger = msg.sender;
        t.phase = uint8(Phase.OPEN);
        t.right = t.input.steps;
        t.timeoutAt = uint64(block.timestamp + stepTimeout);
        t.absoluteDeadline =
            uint64(block.timestamp + uint256(normalTransitions(t.input.steps)) * stepTimeout);
        emit Challenged(id, msg.sender);
    }

    function normalTransitions(uint16 steps) public pure returns (uint16) {
        require(steps >= 1 && steps <= MAX_STEPS, "steps");
        uint16 rounds;
        uint16 width = steps + 1;
        while (width > 1) { width = (width + 1) / 2; ++rounds; }
        return rounds + 3;
    }

    function respond(bytes32 id, bytes32[] calldata trace) external {
        Task storage t = tasks[id];
        require(t.phase == uint8(Phase.OPEN), "phase");
        require(msg.sender == t.submitter, "submitter only");
        _live(t);
        require(trace.length == uint256(t.input.steps) + 1, "trace length");
        require(keccak256(abi.encode(trace)) == t.input.traceRoot, "trace binding");
        bytes32 expected = t.input.initial;
        uint16 first = t.input.steps;
        bool found;
        for (uint16 i = 0; i <= t.input.steps; ++i) {
            if (!found && trace[i] != expected) { first = i; found = true; }
            if (i < t.input.steps) expected = keccak256(abi.encode(uint256(i), expected));
        }
        t.firstMismatch = first;
        t.left = 0;
        t.right = t.input.steps;
        t.phase = uint8(Phase.RESPONDED);
        _touch(t);
        emit Responded(id, first);
    }

    function advance(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase == uint8(Phase.RESPONDED) || t.phase == uint8(Phase.LOCATING), "phase");
        _live(t);
        require(t.left < t.right, "already located");
        uint16 mid = (t.left + t.right) / 2;
        if (t.firstMismatch <= mid) t.right = mid; else t.left = mid + 1;
        ++t.round;
        t.phase = t.left == t.right ? uint8(Phase.READY) : uint8(Phase.LOCATING);
        _touch(t);
        emit Advanced(id, t.left, t.right);
    }

    /// @notice 单步证明：在已定位的下标 idx 处验证 trace[idx-1] -> trace[idx]
    function step(bytes32 id, uint16 idx, bytes32 pre, bytes32 post) external {
        Task storage t = tasks[id];
        require(t.phase == uint8(Phase.READY), "phase");
        _live(t);
        require(idx == t.left && idx >= 1 && idx <= t.input.steps, "index");
        // 单步正确性：idx==1 时前状态必须等于 initial；后状态必须等于 keccak(i-1, pre)
        bool ok = (idx == 1 ? pre == t.input.initial : true) &&
                  post == keccak256(abi.encode(uint256(idx - 1), pre));
        emit Stepped(id, idx, ok);
        _settle(t, id, ok ? t.submitter : t.challenger);
    }

    /// @notice 超时终止：无兜底重算，超时一律判挑战方获胜（提交方被罚没）
    function terminate(bytes32 id) external {
        Task storage t = tasks[id];
        require(t.phase >= uint8(Phase.OPEN) && t.phase < uint8(Phase.SETTLED), "phase");
        require(block.timestamp > t.timeoutAt || block.timestamp >= t.absoluteDeadline, "not timed out");
        _settle(t, id, t.challenger);
    }

    function withdraw(address payable recipient) external {
        uint256 amount = claimable[msg.sender];
        require(amount > 0, "no balance");
        claimable[msg.sender] = 0;
        (bool ok,) = recipient.call{value: amount}("");
        require(ok, "transfer failed");
    }

    function _settle(Task storage t, bytes32 id, address winner) private {
        t.phase = uint8(Phase.SETTLED);
        claimable[winner] += 2 * bond;
        emit Settled(id, winner, 2 * bond);
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
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        if ((v != 27 && v != 28) ||
            uint256(s) > 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0) {
            return address(0);
        }
        return ecrecover(keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest)), v, r, s);
    }
}
