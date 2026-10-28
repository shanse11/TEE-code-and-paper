// Stage I: attestation-gated windows with recomputation fallback.
//
// Run:
//   cd evm; REVISION_RUN=<abs> node node_modules/hardhat/internal/cli/cli.js \
//     test --config revision/hardhat.config.js revision/stageI_attested.test.js

const assert = require("assert");
const { ethers } = require("hardhat");
const {
  TCB, ACTION, PHASE, MRENCLAVE, STRICT_POLICY,
  makeInput, fakeQuote, reportDataFor, deployAttested, deployReplay,
  registerInstance, sign, advance,
} = require("./attested_common");

const BOND = ethers.parseEther("1");
const SHORT = 600;
const LONG = 7 * 24 * 3600;

async function expectRevert(promise, reason) {
  await assert.rejects(promise, (err) => {
    assert.ok(String(err.message).includes(reason), `expected "${reason}", got: ${err.message}`);
    return true;
  });
}

describe("AttestedTaskRollup", function () {
  let submitter, challenger, observer, instance;

  beforeEach(async function () {
    [submitter, challenger, observer] = await ethers.getSigners();
    instance = ethers.Wallet.createRandom();
  });

  async function fixture(opts = {}) {
    const verifier = await deployReplay();
    const rollup = await deployAttested({ verifier, shortWindow: SHORT, longWindow: LONG, ...opts });
    return { verifier, rollup };
  }

  async function submitWith(rollup, input, { withInstance = true } = {}) {
    const subSig = await sign(submitter, rollup, input);
    const instSig = withInstance ? await sign(instance, rollup, input) : "0x";
    return (await rollup.connect(submitter).submit(input, subSig, instSig, { value: BOND })).wait();
  }

  it("I01 OK quote registers a short-window instance", async function () {
    const { verifier, rollup } = await fixture();
    await registerInstance(rollup, verifier, instance, { tcbStatus: TCB.OK });
    const inst = await rollup.instances(instance.address);
    assert.equal(Number(inst.action), ACTION.SHORT);
    const input = makeInput("i01", 16);
    await submitWith(rollup, input);
    const t = await rollup.getTask(input.taskId);
    assert.equal(t.fastPath, true);
    assert.equal(Number(t.challengeDeadline - t.submittedAt), SHORT);
  });

  it("I02 out-of-date-configuration-needed (0xA003) falls back to the long window", async function () {
    const { verifier, rollup } = await fixture();
    await registerInstance(rollup, verifier, instance, { tcbStatus: TCB.OUT_OF_DATE_CONFIGURATION_NEEDED });
    const input = makeInput("i02", 16);
    await submitWith(rollup, input);
    const t = await rollup.getTask(input.taskId);
    assert.equal(t.fastPath, false);
    assert.equal(Number(t.challengeDeadline - t.submittedAt), LONG);
  });

  it("I03 a reject policy blocks registration of a revoked status", async function () {
    const policy = [...STRICT_POLICY];
    policy[TCB.REVOKED] = ACTION.REJECT;
    const { verifier, rollup } = await fixture({ policy });
    await expectRevert(registerInstance(rollup, verifier, instance, { tcbStatus: TCB.REVOKED }), "quote rejected");
  });

  it("I04 failed verification and wrong MRENCLAVE never get the short window", async function () {
    const { verifier, rollup } = await fixture();
    await registerInstance(rollup, verifier, instance, { ok: false, label: "failed" });
    assert.equal(Number((await rollup.instances(instance.address)).action), ACTION.LONG);
    const other = ethers.Wallet.createRandom();
    await registerInstance(rollup, verifier, other, { mrEnclave: ethers.ZeroHash, label: "wrong-mr" });
    assert.equal(Number((await rollup.instances(other.address)).action), ACTION.LONG);
  });

  it("I05 a failed quote cannot be configured as short", async function () {
    const verifier = await deployReplay();
    const policy = [...STRICT_POLICY];
    policy[8] = ACTION.SHORT;
    await expectRevert(deployAttested({ verifier, policy }), "failed quote cannot be short");
  });

  it("I06 no instance signature means the long window", async function () {
    const { rollup } = await fixture();
    const input = makeInput("i06", 8);
    await submitWith(rollup, input, { withInstance: false });
    const t = await rollup.getTask(input.taskId);
    assert.equal(t.fastPath, false);
    assert.equal(Number(t.challengeDeadline - t.submittedAt), LONG);
  });

  it("I07 an expired instance loses the short window", async function () {
    const { verifier, rollup } = await fixture({ instanceTtl: 3600 });
    await registerInstance(rollup, verifier, instance);
    await advance(3601);
    const input = makeInput("i07", 8);
    await submitWith(rollup, input);
    assert.equal((await rollup.getTask(input.taskId)).fastPath, false);
  });

  it("I08 forged result from a compromised instance is slashed when challenged inside the short window", async function () {
    const { verifier, rollup } = await fixture();
    await registerInstance(rollup, verifier, instance);
    const input = makeInput("i08", 64, { forge: true });
    await submitWith(rollup, input);
    await advance(SHORT - 10);
    await (await rollup.connect(challenger).openChallenge(input.taskId, { value: BOND })).wait();
    await (await rollup.connect(observer).adjudicate(input.taskId)).wait();
    const t = await rollup.getTask(input.taskId);
    assert.equal(Number(t.phase), PHASE.SETTLED);
    assert.equal(Number(t.verdict), 1);
    assert.equal(t.recomputed, true);
    assert.equal(await rollup.claimable(challenger.address), 2n * BOND);
  });

  it("I09 forged result settles wrongly when nobody challenges inside the short window", async function () {
    const { verifier, rollup } = await fixture();
    await registerInstance(rollup, verifier, instance);
    const input = makeInput("i09", 64, { forge: true });
    await submitWith(rollup, input);
    await advance(SHORT + 1);
    await expectRevert(rollup.connect(challenger).openChallenge(input.taskId, { value: BOND }), "window");
    await (await rollup.finalize(input.taskId)).wait();
    const t = await rollup.getTask(input.taskId);
    assert.equal(Number(t.verdict), 0);
    assert.equal(t.recomputed, false);
    assert.equal(await rollup.claimable(submitter.address), BOND);
  });

  it("I10 teeOnly baseline settles a forged result at submission", async function () {
    const { verifier, rollup } = await fixture({ teeOnly: true });
    await registerInstance(rollup, verifier, instance);
    const input = makeInput("i10", 64, { forge: true });
    await submitWith(rollup, input);
    const t = await rollup.getTask(input.taskId);
    assert.equal(Number(t.phase), PHASE.SETTLED);
    assert.equal(t.recomputed, false);
    await expectRevert(rollup.connect(challenger).openChallenge(input.taskId, { value: BOND }), "phase");
  });

  it("I11 honest task survives a griefing challenge and the challenger loses its bond", async function () {
    const { verifier, rollup } = await fixture();
    await registerInstance(rollup, verifier, instance);
    const input = makeInput("i11", 32);
    await submitWith(rollup, input);
    await (await rollup.connect(challenger).openChallenge(input.taskId, { value: BOND })).wait();
    await (await rollup.adjudicate(input.taskId)).wait();
    assert.equal(Number((await rollup.getTask(input.taskId)).verdict), 0);
    assert.equal(await rollup.claimable(submitter.address), 2n * BOND);
  });

  it("I12 finalize before the deadline is rejected and balances stay conserved", async function () {
    const { verifier, rollup } = await fixture();
    await registerInstance(rollup, verifier, instance);
    const input = makeInput("i12", 4);
    await submitWith(rollup, input);
    await expectRevert(rollup.finalize(input.taskId), "window");
    await advance(SHORT + 1);
    await (await rollup.finalize(input.taskId)).wait();
    const bal = await ethers.provider.getBalance(await rollup.getAddress());
    assert.equal(bal, (await rollup.locked()) + (await rollup.totalClaimable()));
    await (await rollup.connect(submitter).withdraw(submitter.address)).wait();
    assert.equal(await ethers.provider.getBalance(await rollup.getAddress()), 0n);
  });

  it("I13 a signature from an unregistered key is treated as no attestation", async function () {
    const { rollup } = await fixture();
    const input = makeInput("i13", 8);
    await submitWith(rollup, input);
    assert.equal((await rollup.getTask(input.taskId)).fastPath, false);
  });

  it("I14 reportData must carry the instance address", async function () {
    const { verifier, rollup } = await fixture();
    const quote = fakeQuote("zero-rd");
    await (await verifier.record(quote, true, TCB.OK, MRENCLAVE, ethers.ZeroHash)).wait();
    await (await rollup.registerInstance(quote)).wait();
    assert.equal(Number((await rollup.instances(ethers.ZeroAddress)).action), ACTION.LONG);
    assert.equal(reportDataFor(instance.address).length, 66);
  });
});
