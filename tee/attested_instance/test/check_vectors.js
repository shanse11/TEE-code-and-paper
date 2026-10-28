// Compares the native C vectors with ethers: hash chain, ordered vector commitment, task
// digest (same encoding as AttestedTaskRollup.taskDigest), and the recovered signer address.
// Usage: NODE_PATH=../../evm/node_modules node test/check_vectors.js build/vectors.json

const fs = require("fs");
const assert = require("assert");
const { ethers } = require("ethers");

const v = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const coder = ethers.AbiCoder.defaultAbiCoder();

assert.equal(v.domain, ethers.keccak256(ethers.toUtf8Bytes("HYBRID_ATTESTED_TASK_V1")), "domain");
assert.equal(ethers.computeAddress(new ethers.SigningKey(v.seed).publicKey).toLowerCase(), v.address, "address");

for (const c of v.cases) {
  const trace = [c.initial];
  for (let i = 0; i < c.steps; ++i) trace.push(ethers.keccak256(coder.encode(["uint256", "bytes32"], [i, trace[i]])));
  assert.equal(c.output, trace[c.steps], `output steps=${c.steps}`);
  assert.equal(c.traceRoot, ethers.keccak256(coder.encode(["bytes32[]"], [trace])), `root steps=${c.steps}`);
  const digest = ethers.keccak256(coder.encode(
    ["bytes32", "uint256", "address", "tuple(bytes32,bytes32,uint16,uint32,bytes32,bytes32,bytes32)"],
    [v.domain, 31337, "0x" + "cc".repeat(20), [c.taskId, c.initial, c.steps, 1, c.output, c.traceRoot, c.dataHash]]));
  assert.equal(c.digest, digest, `digest steps=${c.steps}`);
  const signer = ethers.verifyMessage(ethers.getBytes(c.digest), c.signature).toLowerCase();
  assert.equal(signer, v.address, `signer steps=${c.steps}`);
  const s = BigInt("0x" + c.signature.slice(66, 130));
  assert.ok(s <= 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0n, "low-s");
}
console.log(`ok: ${v.cases.length} cases, address ${v.address}`);
