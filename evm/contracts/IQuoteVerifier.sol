// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Normalised result of verifying an SGX DCAP quote.
/// tcbStatus follows the Automata on-chain PCCS enum:
/// 0 OK, 1 SW_HARDENING_NEEDED, 2 CONFIGURATION_AND_SW_HARDENING_NEEDED, 3 CONFIGURATION_NEEDED,
/// 4 OUT_OF_DATE, 5 OUT_OF_DATE_CONFIGURATION_NEEDED, 6 REVOKED, 7 UNRECOGNIZED.
interface IQuoteVerifier {
    function verifyQuote(bytes calldata quote)
        external
        payable
        returns (bool ok, uint8 tcbStatus, bytes32 mrEnclave, bytes32 reportData);
}
