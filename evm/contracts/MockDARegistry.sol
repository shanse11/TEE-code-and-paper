// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockDARegistry {
    struct DARecord {
        bool exists;
        bool available;
        bytes32 payloadHash;
        bytes32 merkleRoot;
        uint256 updatedAt;
    }

    mapping(bytes32 => DARecord) private records;

    event DARecordRegistered(bytes32 indexed pointer, bytes32 payloadHash, bytes32 merkleRoot);
    event DAAvailabilityUpdated(bytes32 indexed pointer, bool available);
    event DAMerkleRootUpdated(bytes32 indexed pointer, bytes32 merkleRoot);

    function registerRecord(bytes32 pointer, bytes32 payloadHash, bytes32 merkleRoot) external {
        require(pointer != bytes32(0), "invalid pointer");
        require(!records[pointer].exists, "record exists");
        records[pointer] = DARecord({
            exists: true,
            available: true,
            payloadHash: payloadHash,
            merkleRoot: merkleRoot,
            updatedAt: block.timestamp
        });
        emit DARecordRegistered(pointer, payloadHash, merkleRoot);
    }

    function setAvailability(bytes32 pointer, bool available) external {
        require(records[pointer].exists, "record missing");
        records[pointer].available = available;
        records[pointer].updatedAt = block.timestamp;
        emit DAAvailabilityUpdated(pointer, available);
    }

    function updateMerkleRoot(bytes32 pointer, bytes32 merkleRoot) external {
        require(records[pointer].exists, "record missing");
        records[pointer].merkleRoot = merkleRoot;
        records[pointer].updatedAt = block.timestamp;
        emit DAMerkleRootUpdated(pointer, merkleRoot);
    }

    function getRecord(bytes32 pointer) external view returns (DARecord memory) {
        require(records[pointer].exists, "record missing");
        return records[pointer];
    }

    function isAvailable(bytes32 pointer) external view returns (bool) {
        return records[pointer].exists && records[pointer].available;
    }
}
