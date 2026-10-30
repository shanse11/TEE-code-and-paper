// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;
/// @notice SUPP-20261030 experimental variant (NOT the paper's BoundedTaskRollup).
/// DA duty whose fulfilment is checked by the EIP-4844 point-evaluation precompile (0x0a)
/// instead of a keccak256 preimage. bind -> fulfill(point-eval) | slash after deadline.
contract PointEvalDaDuty {
    address constant POINT_EVAL = address(0x0a);
    uint256 constant BLS_MODULUS = 52435875175126190479447740508185965837690552500527637822603658699938581184513;
    struct Duty { address responder; bytes32 versionedHash; bytes32 z; uint64 deadline; uint256 bond; uint8 state; } // 1 bound 2 fulfilled 3 slashed
    mapping(bytes32 => Duty) public duties;
    mapping(address => uint256) public claimable;
    uint256 public totalBurned;
    event Bound(bytes32 indexed id, bytes32 versionedHash, bytes32 z, uint64 deadline);
    event Fulfilled(bytes32 indexed id, bytes32 y);
    event Slashed(bytes32 indexed id, uint256 amount);

    function bind(bytes32 id, bytes32 versionedHash, bytes32 z, uint64 window) external payable {
        require(duties[id].state == 0 && msg.value > 0 && uint256(z) < BLS_MODULUS, "bind");
        require(versionedHash[0] == 0x01, "vh version");
        duties[id] = Duty(msg.sender, versionedHash, z, uint64(block.timestamp + window), msg.value, 1);
        emit Bound(id, versionedHash, z, uint64(block.timestamp + window));
    }
    function verifyPoint(bytes32 vh, bytes32 z, bytes32 y, bytes calldata commitment, bytes calldata proof) public view returns (bool) {
        if (commitment.length != 48 || proof.length != 48) return false;
        (bool ok, bytes memory out) = POINT_EVAL.staticcall(abi.encodePacked(vh, z, y, commitment, proof));
        return ok && out.length == 64 && uint256(bytes32(_slice32(out, 32))) == BLS_MODULUS;
    }
    function fulfill(bytes32 id, bytes32 y, bytes calldata commitment, bytes calldata proof) external {
        Duty storage d = duties[id];
        require(d.state == 1 && msg.sender == d.responder && block.timestamp <= d.deadline, "state");
        require(verifyPoint(d.versionedHash, d.z, y, commitment, proof), "point-eval");
        d.state = 2; claimable[d.responder] += d.bond; emit Fulfilled(id, y);
    }
    function slash(bytes32 id) external {
        Duty storage d = duties[id];
        require(d.state == 1 && block.timestamp > d.deadline, "state");
        d.state = 3; totalBurned += d.bond;
        (bool ok,) = payable(address(0)).call{value: d.bond}(""); require(ok, "burn"); emit Slashed(id, d.bond);
    }
    function _slice32(bytes memory b, uint256 off) private pure returns (bytes32 r) { assembly { r := mload(add(add(b, 32), off)) } }
}
