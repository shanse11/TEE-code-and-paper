// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./MerkleVerifier.sol";
import "./MockDARegistry.sol";
import "./MockTEEVerifier.sol";

contract HybridTEERollup {
    using MerkleVerifier for bytes32;

    enum TxStatus {
        NONE,
        PENDING,
        FINALIZED,
        SLASHED
    }

    enum ChallengeStatus {
        NONE,
        OPEN,
        RESPONDED,
        NARROWING,
        READY_FOR_REPLAY,
        REPLAYED,
        RECOVERED,
        RESOLVED
    }

    struct Commit {
        bytes32 stateRoot;
        bytes32 outputHash;
        bytes32 proofHash;
        bytes32 daPointer;
        bytes32 daMerkleRoot;
    }

    struct RollupTransaction {
        bool exists;
        TxStatus status;
        address submitter;
        bytes32 inputHash;
        bytes32 mrenclave;
        uint256 createdAt;
        uint256 challengeDeadline;
        bytes32 attestationNonce;
        Commit commit;
    }

    struct ChallengeEvidence {
        bool daAvailable;
        bool daProofValid;
        uint256 mismatchBits;
        uint256 targetStep;
        bytes32 expectedHash;
        bytes32 claimedHash;
    }

    struct DisputeState {
        uint256 left;
        uint256 right;
        uint256 round;
        uint256 traceLength;
        bool lengthMismatch;
        bool narrowingComplete;
        uint256 targetStep;
        bool replayExecuted;
        bool replayPassed;
    }

    struct RecoveryState {
        uint256 count;
        uint256 lastRecoveredAt;
        uint256 lastPriorRound;
        ChallengeStatus lastPriorStatus;
    }

    struct ChallengeSession {
        bool exists;
        address challenger;
        address responder;
        address operator;
        address arbitrator;
        ChallengeStatus status;
        uint256 openedAt;
        uint256 lastUpdatedAt;
        uint256 timeoutAt;
        uint256 resolvedAt;
        bool challengeSuccess;
        uint256 resolutionBits;
        ChallengeEvidence evidence;
        DisputeState dispute;
        RecoveryState recovery;
    }

    MockTEEVerifier public immutable teeVerifier;
    MockDARegistry public immutable daRegistry;
    uint256 public immutable defaultDisputeWindowSeconds;
    uint256 public immutable defaultChallengeTimeoutSeconds;
    uint256 public immutable defaultMaxBisectionRounds;

    mapping(bytes32 => RollupTransaction) private transactions;
    mapping(bytes32 => ChallengeSession) private sessions;

    event TransactionSubmitted(bytes32 indexed txId, address indexed submitter, bytes32 daPointer);
    event ChallengeOpened(bytes32 indexed txId, address indexed challenger, uint256 traceLength);
    event ChallengeResponded(bytes32 indexed txId, address indexed responder, uint256 mismatchBits);
    event ChallengeStepped(bytes32 indexed txId, uint256 round, uint256 left, uint256 right, bool complete);
    event ChallengeRecovered(bytes32 indexed txId, address indexed operator, ChallengeStatus restoredStatus);
    event ChallengeReplayed(bytes32 indexed txId, uint256 targetStep, bool passed);
    event ChallengeResolved(bytes32 indexed txId, bool challengeSuccess, TxStatus txStatus);
    event TransactionFinalized(bytes32 indexed txId);

    constructor(
        address teeVerifier_,
        address daRegistry_,
        uint256 disputeWindowSeconds_,
        uint256 challengeTimeoutSeconds_,
        uint256 maxBisectionRounds_
    ) {
        require(teeVerifier_ != address(0), "invalid verifier");
        require(daRegistry_ != address(0), "invalid da registry");
        teeVerifier = MockTEEVerifier(teeVerifier_);
        daRegistry = MockDARegistry(daRegistry_);
        defaultDisputeWindowSeconds = disputeWindowSeconds_;
        defaultChallengeTimeoutSeconds = challengeTimeoutSeconds_;
        defaultMaxBisectionRounds = maxBisectionRounds_;
    }

    function submitRollup(
        bytes32 txId,
        bytes32 inputHash,
        bytes32 mrenclave,
        bytes32 attestationNonce,
        bytes calldata attestationSignature,
        Commit calldata commit
    ) external {
        require(txId != bytes32(0), "invalid tx id");
        require(!transactions[txId].exists, "tx exists");

        MockDARegistry.DARecord memory daRecord = daRegistry.getRecord(commit.daPointer);
        require(daRecord.available, "da unavailable");
        require(daRecord.merkleRoot == commit.daMerkleRoot, "da root mismatch");
        require(
            teeVerifier.verifyAttestation(
                inputHash,
                commit.outputHash,
                attestationNonce,
                mrenclave,
                attestationSignature
            ),
            "attestation invalid"
        );
        require(
            teeVerifier.computeProofHash(attestationNonce, attestationSignature) == commit.proofHash,
            "proof hash mismatch"
        );

        transactions[txId] = RollupTransaction({
            exists: true,
            status: TxStatus.PENDING,
            submitter: msg.sender,
            inputHash: inputHash,
            mrenclave: mrenclave,
            createdAt: block.timestamp,
            challengeDeadline: block.timestamp + defaultDisputeWindowSeconds,
            attestationNonce: attestationNonce,
            commit: commit
        });

        emit TransactionSubmitted(txId, msg.sender, commit.daPointer);
    }

    function openChallenge(
        bytes32 txId,
        uint256 mismatchBits,
        uint256 traceLength,
        bool lengthMismatch,
        bytes32 fieldKeyHash,
        bytes32 fieldValueHash,
        bytes32[] calldata siblingHashes,
        bool[] calldata siblingOnLeft
    ) external {
        RollupTransaction storage transaction = transactions[txId];
        require(transaction.exists, "tx missing");
        require(transaction.status == TxStatus.PENDING, "tx not pending");
        require(block.timestamp <= transaction.challengeDeadline, "challenge window closed");
        require(!_isActiveSession(txId), "challenge already active");

        bool daAvailable = daRegistry.isAvailable(transaction.commit.daPointer);
        bool daProofValid = daAvailable
            && MerkleVerifier.verify(
                transaction.commit.daMerkleRoot,
                fieldKeyHash,
                fieldValueHash,
                siblingHashes,
                siblingOnLeft
            );

        ChallengeSession storage session = sessions[txId];
        delete sessions[txId];
        session.exists = true;
        session.challenger = msg.sender;
        session.status = ChallengeStatus.OPEN;
        session.openedAt = block.timestamp;
        session.lastUpdatedAt = block.timestamp;
        session.timeoutAt = block.timestamp + defaultChallengeTimeoutSeconds;
        session.evidence.daAvailable = daAvailable;
        session.evidence.daProofValid = daProofValid;
        session.evidence.mismatchBits = mismatchBits;

        if (traceLength == 0) {
            session.dispute.left = 0;
            session.dispute.right = 0;
            session.dispute.traceLength = 0;
            session.dispute.lengthMismatch = lengthMismatch;
            session.dispute.narrowingComplete = true;
            session.dispute.targetStep = 0;
            session.status = ChallengeStatus.READY_FOR_REPLAY;
        } else {
            session.dispute.left = 0;
            session.dispute.right = lengthMismatch ? traceLength : traceLength - 1;
            session.dispute.traceLength = traceLength;
            session.dispute.lengthMismatch = lengthMismatch;
            session.dispute.narrowingComplete = traceLength <= 1;
            if (session.dispute.narrowingComplete) {
                session.dispute.targetStep = 0;
                session.status = ChallengeStatus.READY_FOR_REPLAY;
            }
        }

        emit ChallengeOpened(txId, msg.sender, traceLength);
    }

    function respondChallenge(bytes32 txId, uint256 previewMismatchBits) external {
        ChallengeSession storage session = sessions[txId];
        require(session.exists && session.status == ChallengeStatus.OPEN, "no open challenge");
        require(!_isTimedOut(session), "challenge timed out");

        session.responder = msg.sender;
        session.status = ChallengeStatus.RESPONDED;
        session.evidence.mismatchBits |= previewMismatchBits;
        _touchSession(session);

        emit ChallengeResponded(txId, msg.sender, session.evidence.mismatchBits);
    }

    function stepChallenge(bytes32 txId, uint256 observedMismatchIndex) external {
        ChallengeSession storage session = sessions[txId];
        require(session.exists && _isActiveStatus(session.status), "no active challenge");
        require(!_isTimedOut(session), "challenge timed out");

        DisputeState storage dispute = session.dispute;
        require(dispute.round < defaultMaxBisectionRounds, "max rounds reached");

        if (dispute.traceLength == 0) {
            dispute.narrowingComplete = true;
            dispute.targetStep = 0;
            session.status = ChallengeStatus.READY_FOR_REPLAY;
            _touchSession(session);
            emit ChallengeStepped(txId, dispute.round, dispute.left, dispute.right, true);
            return;
        }

        if (dispute.narrowingComplete) {
            session.status = ChallengeStatus.READY_FOR_REPLAY;
            _touchSession(session);
            emit ChallengeStepped(txId, dispute.round, dispute.left, dispute.right, true);
            return;
        }

        uint256 mid = (dispute.left + dispute.right) / 2;
        if (observedMismatchIndex <= mid) {
            dispute.right = mid;
        } else {
            dispute.left = mid + 1;
        }
        dispute.round += 1;

        if (dispute.left >= dispute.right) {
            dispute.narrowingComplete = true;
            dispute.targetStep = dispute.left;
            session.status = ChallengeStatus.READY_FOR_REPLAY;
        } else {
            session.status = ChallengeStatus.NARROWING;
        }

        _touchSession(session);
        emit ChallengeStepped(txId, dispute.round, dispute.left, dispute.right, dispute.narrowingComplete);
    }

    function recoverChallenge(bytes32 txId) external {
        ChallengeSession storage session = sessions[txId];
        require(session.exists && session.status != ChallengeStatus.RESOLVED, "no recoverable challenge");
        require(_isTimedOut(session), "challenge still active");

        session.recovery.count += 1;
        session.recovery.lastRecoveredAt = block.timestamp;
        session.recovery.lastPriorRound = session.dispute.round;
        session.recovery.lastPriorStatus = session.status;
        session.operator = msg.sender;

        if (session.dispute.narrowingComplete) {
            session.status = ChallengeStatus.READY_FOR_REPLAY;
        } else if (session.dispute.round > 0) {
            session.status = ChallengeStatus.RECOVERED;
        } else if (session.responder != address(0)) {
            session.status = ChallengeStatus.RESPONDED;
        } else {
            session.status = ChallengeStatus.OPEN;
        }

        _touchSession(session);
        emit ChallengeRecovered(txId, msg.sender, session.status);
    }

    function replayChallenge(
        bytes32 txId,
        uint256 targetStep,
        bytes32 expectedHash,
        bytes32 claimedHash,
        bool lengthMismatch
    ) external {
        ChallengeSession storage session = sessions[txId];
        require(session.exists && _isActiveStatus(session.status), "no active challenge");
        require(!_isTimedOut(session), "challenge timed out");
        require(session.dispute.narrowingComplete, "dispute not narrowed");
        require(targetStep == session.dispute.targetStep, "target step mismatch");

        bool passed = !lengthMismatch && expectedHash == claimedHash;
        session.dispute.replayExecuted = true;
        session.dispute.replayPassed = passed;
        session.evidence.targetStep = targetStep;
        session.evidence.expectedHash = expectedHash;
        session.evidence.claimedHash = claimedHash;
        session.status = ChallengeStatus.REPLAYED;
        _touchSession(session);

        emit ChallengeReplayed(txId, targetStep, passed);
    }

    function resolveChallenge(bytes32 txId, uint256 resolutionBits) external {
        RollupTransaction storage transaction = transactions[txId];
        ChallengeSession storage session = sessions[txId];
        require(transaction.exists, "tx missing");
        require(session.exists && _isActiveStatus(session.status), "no resolvable challenge");

        bool challengeSuccess = resolutionBits != 0 || (session.dispute.replayExecuted && !session.dispute.replayPassed);
        session.arbitrator = msg.sender;
        session.status = ChallengeStatus.RESOLVED;
        session.resolvedAt = block.timestamp;
        session.lastUpdatedAt = block.timestamp;
        session.challengeSuccess = challengeSuccess;
        session.resolutionBits = resolutionBits;
        session.evidence.mismatchBits |= resolutionBits;

        if (challengeSuccess) {
            transaction.status = TxStatus.SLASHED;
        }

        emit ChallengeResolved(txId, challengeSuccess, transaction.status);
    }

    function finalizeExpired(bytes32[] calldata txIds) external {
        for (uint256 index = 0; index < txIds.length; index++) {
            bytes32 txId = txIds[index];
            RollupTransaction storage transaction = transactions[txId];
            if (
                transaction.exists &&
                transaction.status == TxStatus.PENDING &&
                block.timestamp >= transaction.challengeDeadline &&
                !_isActiveSession(txId)
            ) {
                transaction.status = TxStatus.FINALIZED;
                emit TransactionFinalized(txId);
            }
        }
    }

    function verifyDAField(
        bytes32 txId,
        bytes32 fieldKeyHash,
        bytes32 valueHash,
        bytes32[] calldata siblingHashes,
        bool[] calldata siblingOnLeft
    ) external view returns (bool available, bool valid) {
        RollupTransaction storage transaction = transactions[txId];
        require(transaction.exists, "tx missing");
        available = daRegistry.isAvailable(transaction.commit.daPointer);
        valid = available
            && MerkleVerifier.verify(
                transaction.commit.daMerkleRoot,
                fieldKeyHash,
                valueHash,
                siblingHashes,
                siblingOnLeft
            );
    }

    function getTransaction(bytes32 txId) external view returns (RollupTransaction memory) {
        require(transactions[txId].exists, "tx missing");
        return transactions[txId];
    }

    function getChallengeSession(bytes32 txId) external view returns (ChallengeSession memory) {
        require(sessions[txId].exists, "session missing");
        return sessions[txId];
    }

    function isChallengeTimedOut(bytes32 txId) external view returns (bool) {
        require(sessions[txId].exists, "session missing");
        return _isTimedOut(sessions[txId]);
    }

    function _touchSession(ChallengeSession storage session) internal {
        session.lastUpdatedAt = block.timestamp;
        session.timeoutAt = block.timestamp + defaultChallengeTimeoutSeconds;
    }

    function _isTimedOut(ChallengeSession storage session) internal view returns (bool) {
        return block.timestamp > session.timeoutAt;
    }

    function _isActiveSession(bytes32 txId) internal view returns (bool) {
        ChallengeSession storage session = sessions[txId];
        return session.exists && session.status != ChallengeStatus.RESOLVED;
    }

    function _isActiveStatus(ChallengeStatus status) internal pure returns (bool) {
        return
            status == ChallengeStatus.OPEN ||
            status == ChallengeStatus.RESPONDED ||
            status == ChallengeStatus.NARROWING ||
            status == ChallengeStatus.READY_FOR_REPLAY ||
            status == ChallengeStatus.REPLAYED ||
            status == ChallengeStatus.RECOVERED;
    }
}
