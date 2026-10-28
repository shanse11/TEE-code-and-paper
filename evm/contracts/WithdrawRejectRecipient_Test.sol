// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice TEST-ONLY helper contract for evm/revision/security.test.js.
///         It is NOT part of the production system. It intentionally reverts on
///         any inbound ETH transfer so the `withdraw` failure path (recipient
///         that rejects payment) can be exercised by the security suite.
contract WithdrawRejectRecipient_Test {
    uint256 public received;

    receive() external payable {
        revert("WithdrawRejectRecipient_Test: reject ETH");
    }

    fallback() external payable {
        revert("WithdrawRejectRecipient_Test: reject ETH");
    }
}
