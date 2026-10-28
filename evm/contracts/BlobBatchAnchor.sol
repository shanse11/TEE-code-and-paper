// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

/// @title BlobBatchAnchor
/// @notice Independent real-blob anchor for the Hybrid TEE-Rollup revision branch.
///
///         This contract deliberately does NOT modify BoundedTaskRollup or the project's
///         main Hardhat config. It provides a separate, self-contained anchor that records,
///         for a batch carried by a REAL EIP-4844 blob:
///           * the current transaction's blob versioned hash, obtained via the BLOBHASH
///             opcode (EIP-4844) at a NON-ZERO index,
///           * the off-chain-computed payloadHash (keccak256 of the decoded batch content),
///           * the taskCount,
///           * the submitting block and address.
///
///         Business semantics ("does payloadHash/taskCount actually correspond to the blob?")
///         are intentionally NOT verified on-chain: the EVM cannot read blob bytes. They MUST
///         be verified INDEPENDENTLY off-chain by fetching the blob from the beacon chain,
///         decoding it with the revision codec, and recomputing keccak256(content) and
///         taskCount, then comparing to the stored values. The verify script does exactly this.
///
///         A distinct calldata-benchmark branch exists for gas comparison. It emits a
///         DIFFERENT event (CalldataBatchAnchored) and NEVER sets blobVersionedHash, so a
///         calldata payload can never be mistaken for, or impersonate, a real blob anchor.
///
///         Overwrite protection: a given payloadHash may be anchored only once, and a given
///         blob versioned hash may be used by at most one anchor. This prevents replay /
///         collision / overwrite attacks where different content claims the same hash.
contract BlobBatchAnchor {
    ////////////////////////////////////////////////////////////////////////////
    // Types
    ////////////////////////////////////////////////////////////////////////////
    struct Anchor {
        bytes32 payloadHash; // keccak256(decoded batch content)
        uint256 taskCount; // number of tasks in the batch
        bytes32 blobVersionedHash; // 0x01.. KZG versioned hash (zero for calldata branch)
        uint64 blockNumber;
        address submitter;
    }

    ////////////////////////////////////////////////////////////////////////////
    // State
    ////////////////////////////////////////////////////////////////////////////
    // 1-based id counter so that id 0 stays the "unused" sentinel.
    uint256 public nextAnchorId = 1;
    mapping(uint256 => Anchor) private _anchors;
    mapping(bytes32 => bool) private _blobHashUsed; // guards against reusing a blob hash
    mapping(bytes32 => uint256) public payloadHashToAnchor; // 0 == not anchored

    ////////////////////////////////////////////////////////////////////////////
    // Events
    ////////////////////////////////////////////////////////////////////////////
    /// @notice Emitted only for a REAL blob anchor (blobhash opcode, non-zero index).
    event BlobBatchAnchored(
        uint256 indexed id,
        bytes32 payloadHash,
        uint256 taskCount,
        uint256 blobIndex,
        bytes32 blobVersionedHash,
        address submitter
    );

    /// @notice Distinct tag for the calldata benchmark branch. MUST NOT be confused
    ///         with a real blob anchor; blobVersionedHash is left zero.
    event CalldataBatchAnchored(uint256 indexed id, bytes32 payloadHash, uint256 taskCount, address submitter);

    ////////////////////////////////////////////////////////////////////////////
    // Errors
    ////////////////////////////////////////////////////////////////////////////
    error BlobhashEmpty(); // the requested blob slot was not present in this tx
    error BlobHashReused(bytes32 blobVersionedHash); // prevents overwrite/collision
    error PayloadAlreadyAnchored(bytes32 payloadHash); // prevents duplicate/overwrite

    ////////////////////////////////////////////////////////////////////////////
    // Real blob anchor
    ////////////////////////////////////////////////////////////////////////////
    /// @notice Anchor a batch carried by a REAL blob.
    /// @dev The caller attaches `blobIndex + 1` blobs to this type-3 transaction (0-based).
    ///      The contract reads the versioned hash of the blob at `blobIndex` via the
    ///      BLOBHASH opcode (EIP-4844). `blobIndex` is the 0-based slot in this tx's
    ///      blob_versioned_hashes list — the common case is a single blob at index 0.
    /// @param payloadHash keccak256 of the decoded batch content (independently verifiable).
    /// @param taskCount number of tasks in the batch (independently verifiable).
    /// @param blobIndex index of the blob in this tx's blob_versioned_hashes (0-based).
    function anchorBlobBatch(bytes32 payloadHash, uint256 taskCount, uint256 blobIndex)
        external
        returns (uint256 id)
    {
        bytes32 bh = blobhash(blobIndex);
        if (bh == bytes32(0)) revert BlobhashEmpty();
        if (_blobHashUsed[bh]) revert BlobHashReused(bh);
        if (payloadHashToAnchor[payloadHash] != 0) revert PayloadAlreadyAnchored(payloadHash);

        id = nextAnchorId++;
        _anchors[id] = Anchor({
            payloadHash: payloadHash,
            taskCount: taskCount,
            blobVersionedHash: bh,
            blockNumber: uint64(block.number),
            submitter: msg.sender
        });
        _blobHashUsed[bh] = true;
        payloadHashToAnchor[payloadHash] = id;

        emit BlobBatchAnchored(id, payloadHash, taskCount, blobIndex, bh, msg.sender);
        return id;
    }

    ////////////////////////////////////////////////////////////////////////////
    // Calldata benchmark branch (distinct event, never impersonates a blob)
    ////////////////////////////////////////////////////////////////////////////
    /// @notice Benchmark branch: records the same commitment shape via calldata only.
    ///         Emits CalldataBatchAnchored (different tag) and leaves blobVersionedHash zero.
    function anchorCalldataPayload(bytes calldata payload, uint256 taskCount) external returns (uint256 id) {
        return anchorCalldataBatch(keccak256(payload), taskCount);
    }

    function anchorCalldataBatch(bytes32 payloadHash, uint256 taskCount) public returns (uint256 id) {
        if (payloadHashToAnchor[payloadHash] != 0) revert PayloadAlreadyAnchored(payloadHash);
        id = nextAnchorId++;
        _anchors[id] = Anchor({
            payloadHash: payloadHash,
            taskCount: taskCount,
            blobVersionedHash: bytes32(0),
            blockNumber: uint64(block.number),
            submitter: msg.sender
        });
        payloadHashToAnchor[payloadHash] = id;
        emit CalldataBatchAnchored(id, payloadHash, taskCount, msg.sender);
        return id;
    }

    ////////////////////////////////////////////////////////////////////////////
    // Views
    ////////////////////////////////////////////////////////////////////////////
    function getAnchor(uint256 id) external view returns (Anchor memory) {
        return _anchors[id];
    }

    function isBlobHashUsed(bytes32 bh) external view returns (bool) {
        return _blobHashUsed[bh];
    }
}
