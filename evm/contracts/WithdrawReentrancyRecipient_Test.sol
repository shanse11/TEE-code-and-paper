// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice TEST-ONLY helper contract for evm/revision/security.test.js.
///         It is NOT part of the production system. On receiving ETH it tries to
///         re-enter `rollup.withdraw(address(this))` to prove the rollup's
///         reentrancy guard prevents a malicious recipient from extracting more
///         than the single owed amount. The re-entered call must revert.
interface IBoundedTaskRollup_Test {
    function withdraw(address payable recipient) external;
}

contract WithdrawReentrancyRecipient_Test {
    IBoundedTaskRollup_Test public rollup;
    uint256 public calls;
    uint256 public receivedTotal;

    receive() external payable {
        calls += 1;
        receivedTotal += msg.value;
        if (calls == 1) {
            // Attempt reentrancy: re-invoke withdraw targeting self.
            // The rollup must block this (withdrawing guard / zeroed claimable).
            try rollup.withdraw(payable(address(this))) {
                // Should not happen: guard must prevent double payout.
            } catch {
                // Expected: reentrancy blocked.
            }
        }
    }

    fallback() external payable {
        calls += 1;
        receivedTotal += msg.value;
    }

    constructor(address _rollup) {
        rollup = IBoundedTaskRollup_Test(_rollup);
    }
}
