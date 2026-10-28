// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Test double for the Automata entrypoint: returns a configured (success, output) pair,
/// or reverts when told to.
contract AutomataMock_Test {
    bool public success;
    bytes public output;
    bool public shouldRevert;

    function set(bool success_, bytes calldata output_, bool shouldRevert_) external {
        success = success_;
        output = output_;
        shouldRevert = shouldRevert_;
    }

    function verifyAndAttestOnChain(bytes calldata) external payable returns (bool, bytes memory) {
        require(!shouldRevert, "mock revert");
        return (success, output);
    }
}
