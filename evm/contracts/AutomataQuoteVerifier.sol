// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./IQuoteVerifier.sol";

interface IAutomataDcapAttestation {
    function verifyAndAttestOnChain(bytes calldata rawQuote)
        external
        payable
        returns (bool success, bytes memory output);
}

/// @notice Adapter over Automata DCAP attestation (v1.1.0).
/// Output layout: quoteVersion(2) | quoteBodyType(2) | tcbStatus(1) | fmspc(6) | quoteBody | advisories.
/// For an SGX enclave report body, MRENCLAVE is at body[64:96] and report_data at body[320:384].
/// Revoked or unrecognised TCB makes Automata return success=false; out-of-date TCB returns
/// success=true with the status, which this adapter passes through for the caller's policy.
/// A malformed or tampered quote can make Automata revert; that is reported as a failed quote.
/// Debug enclaves (attributes.flags bit 1, body[48]) expose their memory to the host and are
/// also reported as failed quotes.
contract AutomataQuoteVerifier is IQuoteVerifier {
    uint256 private constant HEADER = 11;
    uint256 private constant SGX_BODY = 384;
    IAutomataDcapAttestation public immutable attestation;

    constructor(address attestation_) {
        attestation = IAutomataDcapAttestation(attestation_);
    }

    function verifyQuote(bytes calldata quote)
        external
        payable
        returns (bool ok, uint8 tcbStatus, bytes32 mrEnclave, bytes32 reportData)
    {
        bool success;
        bytes memory output;
        try attestation.verifyAndAttestOnChain{value: msg.value}(quote) returns (bool s, bytes memory o) {
            (success, output) = (s, o);
        } catch {
            return (false, 255, bytes32(0), bytes32(0));
        }
        if (!success || output.length < HEADER + SGX_BODY) return (false, 255, bytes32(0), bytes32(0));
        if (uint8(output[HEADER + 48]) & 0x02 != 0) return (false, 255, bytes32(0), bytes32(0));
        tcbStatus = uint8(output[4]);
        assembly {
            let body := add(add(output, 32), 11)
            mrEnclave := mload(add(body, 64))
            reportData := mload(add(body, 320))
        }
        ok = true;
    }
}
