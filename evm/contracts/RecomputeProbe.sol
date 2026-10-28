// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Measurement-only contract: the same hash chain and ordered vector commitment as
/// BoundedTaskRollup.compute, without the 128-step cap, so recomputation gas can be measured
/// up to the block gas limit. It holds no funds and settles nothing.
contract RecomputeProbe {
    bytes32 public last;

    function recompute(bytes32 initial, uint32 steps) external returns (bytes32 output, bytes32 root) {
        bytes32[] memory trace = new bytes32[](uint256(steps) + 1);
        trace[0] = initial;
        for (uint256 i = 0; i < steps; ++i) trace[i + 1] = keccak256(abi.encode(i, trace[i]));
        output = trace[steps];
        root = keccak256(abi.encode(trace));
        last = output;
    }
}
