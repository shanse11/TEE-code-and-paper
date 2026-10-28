// Link an SGX-produced trace to a local BoundedTaskRollup settlement.
// The quote is checked off-chain. The contract does not verify DCAP.

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { ethers } = require("hardhat");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN must be absolute");

function abiEncode(types, values) {
  return ethers.AbiCoder.defaultAbiCoder().encode(types, values);
}
function jsCompute(initial, steps) {
  const trace = [initial];
  let cur = initial;
  for (let i = 0; i < steps; i++) {
    cur = ethers.keccak256(abiEncode(["uint256", "bytes32"], [BigInt(i), cur]));
    trace.push(cur);
  }
  return { output: trace[steps], root: ethers.keccak256(abiEncode(["bytes32[]"], [trace])), trace };
}

function reportDigest(output, root, nonce) {
  return ethers.keccak256(ethers.concat([output, root, nonce]));
}

function quoteReport(file) {
  const b = fs.readFileSync(file);
  return "0x" + b.subarray(48 + 320, 48 + 352).toString("hex");
}

async function main() {
  const initial = "0x" + "11".repeat(32);
  const nonce = "0x" + "22".repeat(32);
  const cases = [
    { steps: 4, quote: path.join(REVISION_RUN, "quote_steps4.dat") },
    { steps: 128, quote: path.join(REVISION_RUN, "quote_steps128.dat") },
  ];
  const [submitter, challenger] = await ethers.getSigners();
  const Factory = await ethers.getContractFactory("BoundedTaskRollup");
  const bond = ethers.parseEther("1");
  const rollup = await Factory.deploy(bond, 100, 10, 2);
  await rollup.waitForDeployment();
  const domain = await rollup.DOMAIN();
  const chainId = (await ethers.provider.getNetwork()).chainId;
  const addr = await rollup.getAddress();
  const out = [];
  for (const c of cases) {
    const comp = jsCompute(initial, c.steps);
    const bound = reportDigest(comp.output, comp.root, nonce);
    const fromQuote = quoteReport(c.quote);
    assert.equal(fromQuote, bound, `quote report_data mismatch for steps=${c.steps}`);
    const taskId = ethers.keccak256(ethers.toUtf8Bytes("sgx-link:" + c.steps));
    const input = {
      taskId, initial, steps: c.steps, version: 1,
      output: comp.output, traceRoot: comp.root,
      dataHash: ethers.keccak256(ethers.toUtf8Bytes("sgx")),
    };
    const digest = ethers.keccak256(abiEncode(
      ["bytes32", "uint256", "address", "bytes32", "bytes32", "uint16", "uint32", "bytes32", "bytes32", "bytes32"],
      [domain, chainId, addr, input.taskId, input.initial, input.steps, input.version, input.output, input.traceRoot, input.dataHash]
    ));
    const sig = await submitter.signMessage(ethers.getBytes(digest));
    const submitRc = await (await rollup.connect(submitter).submit(input, sig, { value: bond })).wait();
    const chalRc = await (await rollup.connect(challenger).openChallenge(taskId, { value: bond })).wait();
    const adjRc = await (await rollup.adjudicate(taskId)).wait();
    const task = await rollup.getTask(taskId);
    assert.equal(Number(task.phase), 7);
    assert.equal(Number(task.verdict), 0);
    const wdRc = await (await rollup.connect(submitter).withdraw(submitter.address)).wait();
    out.push({
      steps: c.steps,
      output: comp.output,
      traceRoot: comp.root,
      reportData: bound,
      quoteFile: path.basename(c.quote),
      verdict: Number(task.verdict),
      phase: "SETTLED",
      gas: {
        submit: submitRc.gasUsed.toString(),
        openChallenge: chalRc.gasUsed.toString(),
        adjudicate: adjRc.gasUsed.toString(),
        withdraw: wdRc.gasUsed.toString(),
      },
      note: "real SGX execution produced this trace; DCAP result remains 0xA003 so the quote was not accepted as UpToDate. Settlement is local EVM and does not verify the quote on-chain.",
    });
  }
  const dest = path.join(REVISION_RUN, "tee_link.json");
  fs.writeFileSync(dest, JSON.stringify({ schemaVersion: "hybrid-tee-rollup.stageH.tee-link.v1", cases: out }, null, 2));
  console.log(JSON.stringify(out, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
