// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockTEEVerifier {
    address public immutable authorizedSigner;

    constructor(address signer_) {
        require(signer_ != address(0), "invalid signer");
        authorizedSigner = signer_;
    }

    function attestationDigest(
        bytes32 inputHash,
        bytes32 outputHash,
        bytes32 nonce,
        bytes32 mrenclave
    ) public pure returns (bytes32) {
        return sha256(abi.encode(inputHash, outputHash, nonce, mrenclave));
    }

    function computeProofHash(bytes32 nonce, bytes memory signature) public pure returns (bytes32) {
        bytes32 schemeHash = sha256(bytes("ecdsa-secp256k1"));
        return sha256(abi.encode(nonce, sha256(signature), schemeHash));
    }

    function verifyAttestation(
        bytes32 inputHash,
        bytes32 outputHash,
        bytes32 nonce,
        bytes32 mrenclave,
        bytes calldata signature
    ) external view returns (bool) {
        bytes32 digest = attestationDigest(inputHash, outputHash, nonce, mrenclave);
        bytes32 ethHash = _toEthSignedMessageHash(digest);
        return _recover(ethHash, signature) == authorizedSigner;
    }

    function _toEthSignedMessageHash(bytes32 digest) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
    }

    function _recover(bytes32 digest, bytes calldata signature) internal pure returns (address) {
        if (signature.length != 65) {
            return address(0);
        }

        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (v < 27) {
            v += 27;
        }
        if (v != 27 && v != 28) {
            return address(0);
        }
        return ecrecover(digest, v, r, s);
    }
}
