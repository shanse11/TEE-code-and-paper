// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library MerkleVerifier {
    function computeLeaf(bytes32 fieldKeyHash, bytes32 valueHash) internal pure returns (bytes32) {
        return sha256(abi.encode(fieldKeyHash, valueHash));
    }

    function computeParent(bytes32 left, bytes32 right) internal pure returns (bytes32) {
        return sha256(abi.encode(left, right));
    }

    function verify(
        bytes32 root,
        bytes32 fieldKeyHash,
        bytes32 valueHash,
        bytes32[] memory siblingHashes,
        bool[] memory siblingOnLeft
    ) internal pure returns (bool) {
        require(siblingHashes.length == siblingOnLeft.length, "merkle witness length mismatch");
        bytes32 current = computeLeaf(fieldKeyHash, valueHash);
        for (uint256 index = 0; index < siblingHashes.length; index++) {
            current = siblingOnLeft[index]
                ? computeParent(siblingHashes[index], current)
                : computeParent(current, siblingHashes[index]);
        }
        return current == root;
    }
}
