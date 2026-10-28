// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./IQuoteVerifier.sol";

/// @notice Local-only verifier that returns results recorded beforehand, either from the
/// Sepolia Automata call or from a fault-injection script. It performs no cryptography and
/// must never be deployed outside a test chain.
contract ReplayQuoteVerifier is IQuoteVerifier {
    struct Result {
        bool known;
        bool ok;
        uint8 tcbStatus;
        bytes32 mrEnclave;
        bytes32 reportData;
    }

    address public immutable owner;
    mapping(bytes32 => Result) private results;

    constructor() {
        owner = msg.sender;
    }

    function record(bytes calldata quote, bool ok, uint8 tcbStatus, bytes32 mrEnclave, bytes32 reportData) external {
        require(msg.sender == owner, "owner");
        results[keccak256(quote)] = Result(true, ok, tcbStatus, mrEnclave, reportData);
    }

    function verifyQuote(bytes calldata quote)
        external
        payable
        returns (bool ok, uint8 tcbStatus, bytes32 mrEnclave, bytes32 reportData)
    {
        Result memory r = results[keccak256(quote)];
        if (!r.known) return (false, 255, bytes32(0), bytes32(0));
        return (r.ok, r.tcbStatus, r.mrEnclave, r.reportData);
    }
}
