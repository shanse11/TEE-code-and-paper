// Shared helpers for the attested fast-path experiments (stage I).

const { ethers } = require("hardhat");

const TCB = {
  OK: 0,
  SW_HARDENING_NEEDED: 1,
  CONFIGURATION_AND_SW_HARDENING_NEEDED: 2,
  CONFIGURATION_NEEDED: 3,
  OUT_OF_DATE: 4,
  OUT_OF_DATE_CONFIGURATION_NEEDED: 5,
  REVOKED: 6,
  UNRECOGNIZED: 7,
};
const ACTION = { REJECT: 0, LONG: 1, SHORT: 2 };
const PHASE = { NONE: 0, SUBMITTED: 1, OPEN: 2, SETTLED: 3 };
const MRENCLAVE = "0x1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37";

// Index 0..7 by TCB status, index 8 for failed or mismatched quotes.
// Strict policy: only OK is short; out-of-date and configuration statuses fall back to the long
// window; revoked, unrecognised and failed quotes also fall back instead of blocking submission.
const STRICT_POLICY = [
  ACTION.SHORT, ACTION.LONG, ACTION.LONG, ACTION.LONG, ACTION.LONG,
  ACTION.LONG, ACTION.LONG, ACTION.LONG, ACTION.LONG,
];

function abiEncode(t, v) {
  return ethers.AbiCoder.defaultAbiCoder().encode(t, v);
}

function jsCompute(initial, steps) {
  const trace = [initial];
  let cur = initial;
  for (let i = 0; i < steps; ++i) {
    cur = ethers.keccak256(abiEncode(["uint256", "bytes32"], [BigInt(i), cur]));
    trace.push(cur);
  }
  return { output: trace[steps], root: ethers.keccak256(abiEncode(["bytes32[]"], [trace])) };
}

function makeInput(label, steps, { forge = false, initial } = {}) {
  const init = initial || ethers.keccak256(ethers.toUtf8Bytes("init:" + label));
  const c = jsCompute(init, steps);
  return {
    taskId: ethers.keccak256(ethers.toUtf8Bytes("task:" + label)),
    initial: init,
    steps,
    version: 1,
    output: forge ? ethers.keccak256(ethers.toUtf8Bytes("forged:" + label)) : c.output,
    traceRoot: c.root,
    dataHash: ethers.keccak256(ethers.toUtf8Bytes("data:" + label)),
  };
}

// A fake quote blob is only a lookup key for ReplayQuoteVerifier; it carries no cryptography.
function fakeQuote(label) {
  return ethers.toUtf8Bytes("replay-quote:" + label);
}

function reportDataFor(address) {
  return ethers.zeroPadBytes(address, 32);
}

async function deployAttested({
  verifier,
  bond = ethers.parseEther("1"),
  shortWindow = 600,
  longWindow = 7 * 24 * 3600,
  instanceTtl = 30 * 24 * 3600,
  teeOnly = false,
  policy = STRICT_POLICY,
  mrEnclave = MRENCLAVE,
}) {
  const F = await ethers.getContractFactory("AttestedTaskRollup");
  const c = await F.deploy(await verifier.getAddress(), mrEnclave, bond, shortWindow, longWindow, instanceTtl, teeOnly, policy);
  await c.waitForDeployment();
  return c;
}

async function deployReplay() {
  const F = await ethers.getContractFactory("ReplayQuoteVerifier");
  const v = await F.deploy();
  await v.waitForDeployment();
  return v;
}

async function registerInstance(rollup, verifier, instanceWallet, { tcbStatus = TCB.OK, ok = true, mrEnclave = MRENCLAVE, label } = {}) {
  const quote = fakeQuote(label || instanceWallet.address);
  await (await verifier.record(quote, ok, tcbStatus, mrEnclave, reportDataFor(instanceWallet.address))).wait();
  return (await rollup.registerInstance(quote)).wait();
}

async function sign(wallet, rollup, input) {
  const digest = await rollup.taskDigest(input);
  return wallet.signMessage(ethers.getBytes(digest));
}

async function now() {
  return (await ethers.provider.getBlock("latest")).timestamp;
}

async function advance(seconds) {
  await ethers.provider.send("evm_increaseTime", [seconds]);
  await ethers.provider.send("evm_mine", []);
}

module.exports = {
  TCB,
  ACTION,
  PHASE,
  MRENCLAVE,
  STRICT_POLICY,
  jsCompute,
  makeInput,
  fakeQuote,
  reportDataFor,
  deployAttested,
  deployReplay,
  registerInstance,
  sign,
  now,
  advance,
};
