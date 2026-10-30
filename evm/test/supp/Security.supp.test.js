// 专2-2/2-3 security experiments (LOCAL Hardhat). Records outcomes to
// outputs/experiments_supp_20261030/A_security/raw_results.json
const { expect } = require("chai");
const { ethers, network } = require("hardhat");
const fs = require("fs"); const path = require("path");
const R = [];
function rec(scenario, contract, attack, outcome, note) { R.push({ scenario, contract, attack, outcome, note }); }
const s8 = (v) => ethers.sha256(ethers.toUtf8Bytes(v));
const enc = (t, v) => ethers.AbiCoder.defaultAbiCoder().encode(t, v);
const inc = async (s) => { await network.provider.send("evm_increaseTime", [s]); await network.provider.send("evm_mine"); };
const BOND = ethers.parseEther("1");

async function deployB() {
  const F = await ethers.getContractFactory("BoundedTaskRollup");
  return F.deploy(BOND, 60, 10, 2);
}
async function mkTask(c, signer, id, wrong = false, steps = 8) {
  const init = s8("init-" + id);
  const [out, root] = await c.compute(init, steps);
  const input = { taskId: s8(id), initial: init, steps, version: 1, output: wrong ? s8("bad") : out, traceRoot: root, dataHash: ethers.keccak256("0x1234") };
  const d = await c.taskDigest(input);
  const sig = await signer.signMessage(ethers.getBytes(d));
  return { input, sig };
}
async function deployH(teeSigner) {
  const v = await (await ethers.getContractFactory("MockTEEVerifier")).deploy(teeSigner.address);
  const da = await (await ethers.getContractFactory("MockDARegistry")).deploy();
  const r = await (await ethers.getContractFactory("HybridTEERollup")).deploy(await v.getAddress(), await da.getAddress(), 60, 2, 16);
  return { v, da, r };
}
let ctr = 0;
async function submitH(env, from, tee, opt = {}) {
  const inputHash = s8("in"), outputHash = opt.outputHash || s8("out"), mr = opt.mr || s8("mr-release");
  const nonce = opt.nonce || s8("nonce-1");
  const digest = ethers.sha256(enc(["bytes32","bytes32","bytes32","bytes32"], [inputHash, outputHash, nonce, mr]));
  const sig = opt.sig || await tee.signMessage(ethers.getBytes(digest));
  const root = s8("root"); const ptr = s8("ptr" + (ctr++));
  await env.da.registerRecord(ptr, s8("payload"), root);
  const commit = { stateRoot: s8("sr"), outputHash, proofHash: await env.v.computeProofHash(nonce, sig), daPointer: ptr, daMerkleRoot: root };
  const txId = opt.txId || s8("tx" + (ctr++));
  await (opt.rollup || env.r).connect(from).submitRollup(txId, inputHash, mr, nonce, sig, commit);
  return { txId, sig, nonce, inputHash, outputHash, mr, commit };
}
const tryTx = async (p) => { try { await p; return "accepted"; } catch (e) { return "reverted:" + (e.shortMessage || e.message).split("reverted with reason string ")[1]?.replace(/'/g, "") ; } };

describe("SUPP-A security (专2-2/2-3)", function () {
  after(() => {
    const dir = path.join(__dirname, "../../../outputs/experiments_supp_20261030/A_security");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "raw_results.json"), JSON.stringify(R, null, 2));
  });

  describe("S1 recovery-permission abuse", () => {
    it("Bounded: stranger recover() only within timeout window, capped, does not move funds/roles", async () => {
      const [sub, ch, str] = await ethers.getSigners(); const c = await deployB();
      const { input, sig } = await mkTask(c, sub, "r1"); await c.connect(sub).submit(input, sig, { value: BOND });
      await c.connect(ch).openChallenge(input.taskId, { value: BOND });
      const early = await tryTx(c.connect(str).recover(input.taskId));
      expect(early).to.match(/recovery time/);
      await inc(11); await c.connect(str).recover(input.taskId);
      await inc(11); await c.connect(str).recover(input.taskId);
      await inc(11); const third = await tryTx(c.connect(str).recover(input.taskId));
      expect(third).to.not.equal("accepted");
      const t = await c.getTask(input.taskId);
      expect(t.submitter).to.equal(sub.address); expect(t.challenger).to.equal(ch.address);
      expect(await c.claimable(str.address)).to.equal(0n);
      const resp = await tryTx(c.connect(str).respond(input.taskId, []));
      expect(resp).to.not.equal("accepted");
      rec("S1", "BoundedTaskRollup", "stranger calls recover() early / >maxRecoveries / respond()", "DEFENDED",
        `early=${early}; 3rd=${third}; respond=${resp}; roles & claimable unchanged`);
    });
    it("Bounded: stranger cannot bindDa/fulfillDa for someone else's task", async () => {
      const [sub, , str] = await ethers.getSigners(); const c = await deployB();
      const { input, sig } = await mkTask(c, sub, "r2"); await c.connect(sub).submit(input, sig, { value: BOND });
      const b = await tryTx(c.connect(str).bindDa(input.taskId, s8("ref"), { value: BOND }));
      await c.connect(sub).bindDa(input.taskId, s8("ref"), { value: BOND });
      const f = await tryTx(c.connect(str).fulfillDa(input.taskId, "0x1234"));
      expect(b).to.match(/submitter only/); expect(f).to.match(/responder only/);
      rec("S1", "BoundedTaskRollup", "stranger bindDa/fulfillDa", "DEFENDED", `bindDa=${b}; fulfillDa=${f}`);
    });
    it("Hybrid(legacy prototype): ANY address can resolveChallenge with arbitrary bits => slash honest tx (FINDING)", async () => {
      const [sub, tee, att] = await ethers.getSigners(); const env = await deployH(tee);
      const s = await submitH(env, sub, tee);
      await env.r.connect(att).openChallenge(s.txId, 0, 0, false, ethers.ZeroHash, ethers.ZeroHash, [], []);
      const res = await tryTx(env.r.connect(att).resolveChallenge(s.txId, 1));
      const st = (await env.r.getTransaction(s.txId)).status;
      expect(res).to.equal("accepted"); expect(st).to.equal(3n);
      rec("S1", "HybridTEERollup", "stranger opens+resolves challenge with resolutionBits=1 on honest tx", "NOT DEFENDED (FINDING-H1)", `resolve=${res}; tx status=${st} (3=SLASHED)`);
    });
    it("Hybrid: stranger recoverChallenge overwrites session.operator; MockDARegistry.setAvailability unrestricted (FINDING)", async () => {
      const [sub, tee, ch, str] = await ethers.getSigners(); const env = await deployH(tee);
      const s = await submitH(env, sub, tee);
      await env.r.connect(ch).openChallenge(s.txId, 0, 4, false, ethers.ZeroHash, ethers.ZeroHash, [], []);
      await inc(3); await env.r.connect(str).recoverChallenge(s.txId);
      const op = (await env.r.getChallengeSession(s.txId)).operator;
      const da = await tryTx(env.da.connect(str).setAvailability(s.commit.daPointer, false));
      expect(op).to.equal(str.address); expect(da).to.equal("accepted");
      rec("S1", "HybridTEERollup+MockDARegistry", "stranger recoverChallenge; stranger toggles DA availability", "NOT DEFENDED (FINDING-H2/H3)", `operator:=stranger; setAvailability=${da}`);
    });
  });

  describe("S2 replay", () => {
    it("Bounded: same task+sig resubmit, sig moved to new taskId, sig replayed to another contract instance", async () => {
      const [sub] = await ethers.getSigners(); const c = await deployB(); const c2 = await deployB();
      const { input, sig } = await mkTask(c, sub, "p1"); await c.connect(sub).submit(input, sig, { value: BOND });
      const same = await tryTx(c.connect(sub).submit(input, sig, { value: BOND }));
      const moved = await tryTx(c.connect(sub).submit({ ...input, taskId: s8("p1b") }, sig, { value: BOND }));
      const cross = await tryTx(c2.connect(sub).submit(input, sig, { value: BOND }));
      // cross-chain: off-chain digest with chainId=11155111 differs from on-chain (31337)
      const D = await c.DOMAIN();
      const tup = "tuple(bytes32,bytes32,uint16,uint32,bytes32,bytes32,bytes32)";
      const tv = [input.taskId, input.initial, input.steps, input.version, input.output, input.traceRoot, input.dataHash];
      const dOther = ethers.keccak256(enc(["bytes32","uint256","address",tup], [D, 11155111, await c.getAddress(), tv]));
      const dHere = ethers.keccak256(enc(["bytes32","uint256","address",tup], [D, 31337, await c.getAddress(), tv]));
      expect(dHere).to.equal(await c.taskDigest(input)); expect(dOther).to.not.equal(dHere);
      expect(same).to.match(/task id/); expect(moved).to.match(/signature/); expect(cross).to.match(/signature/);
      rec("S2", "BoundedTaskRollup", "resubmit / move sig to new taskId / cross-contract / cross-chain", "DEFENDED",
        `same=${same}; newId=${moved}; otherContract=${cross}; digest binds chainid (31337 vs 11155111 digests differ, on-chain digest reproduced)`);
    });
    it("Hybrid: same TEE attestation (nonce,sig) replayed under new txId and into a 2nd rollup instance (FINDING)", async () => {
      const [sub, tee, att] = await ethers.getSigners(); const env = await deployH(tee);
      const s = await submitH(env, sub, tee);
      const r2 = await (await ethers.getContractFactory("HybridTEERollup")).deploy(await env.v.getAddress(), await env.da.getAddress(), 60, 2, 16);
      const a = await tryTx(submitH(env, att, tee, { sig: s.sig, nonce: s.nonce, txId: s8("replayed") }));
      const b = await tryTx(submitH(env, att, tee, { sig: s.sig, nonce: s.nonce, rollup: r2 }));
      expect(a).to.equal("accepted"); expect(b).to.equal("accepted");
      rec("S2", "HybridTEERollup", "replay attestation by 3rd party under new txId / other contract", "NOT DEFENDED (FINDING-H4)", `newTxId=${a}; otherInstance=${b}; digest lacks chainid/address/txId, nonce not consumed`);
    });
    it("Hybrid: ECDSA malleable (s->n-s) signature accepted by MockTEEVerifier (FINDING)", async () => {
      const [sub, tee] = await ethers.getSigners(); const env = await deployH(tee);
      const s = await submitH(env, sub, tee);
      const sg = ethers.Signature.from(s.sig);
      const n = BigInt("0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141");
      const mal = ethers.concat([sg.r, ethers.toBeHex(n - BigInt(sg.s), 32), sg.v === 27 ? "0x1c" : "0x1b"]);
      const ok = await env.v.verifyAttestation(s.inputHash, s.outputHash, s.nonce, s.mr, mal);
      expect(ok).to.equal(true);
      rec("S2", "MockTEEVerifier", "malleated signature", "NOT DEFENDED (FINDING-H5)", `verifyAttestation(malleated)=${ok}; proofHash differs so 'unique proof' is not unique`);
    });
  });

  describe("S3 collusion", () => {
    it("Bounded: submitter self-challenge blocked; sybil challenger on WRONG output cannot get it accepted", async () => {
      const [sub, sybil] = await ethers.getSigners(); const c = await deployB();
      const { input, sig } = await mkTask(c, sub, "c1", true); await c.connect(sub).submit(input, sig, { value: BOND });
      const self = await tryTx(c.connect(sub).openChallenge(input.taskId, { value: BOND }));
      await c.connect(sybil).openChallenge(input.taskId, { value: BOND });
      await c.adjudicate(input.taskId);
      const t = await c.getTask(input.taskId);
      expect(self).to.match(/challenger bond/); expect(t.verdict).to.not.equal(0n);
      rec("S3", "BoundedTaskRollup", "submitter+sybil challenger collude on wrong output", "CORRECTNESS DEFENDED; ECONOMIC NOT",
        `selfChallenge=${self}; verdict=${t.verdict} (wrong output flagged by on-chain recompute); sybil claimable=${ethers.formatEther(await c.claimable(sybil.address))} ETH => colluders net 0 loss (bond returns to sybil). Contract cannot detect sybil identity.`);
    });
    it("Bounded: colluders stay silent on wrong output -> finalize recomputes and burns bond", async () => {
      const [sub] = await ethers.getSigners(); const c = await deployB();
      const { input, sig } = await mkTask(c, sub, "c2", true); await c.connect(sub).submit(input, sig, { value: BOND });
      await inc(61); await c.finalize(input.taskId);
      const burned = await c.totalBurned(); expect(burned).to.equal(BOND);
      rec("S3", "BoundedTaskRollup", "no-challenge collusion on wrong output", "DEFENDED", `totalBurned=${ethers.formatEther(burned)} ETH`);
    });
    it("Bounded: delay griefing bounded by absoluteDeadline", async () => {
      const [sub, ch] = await ethers.getSigners(); const c = await deployB();
      const { input, sig } = await mkTask(c, sub, "c3", false, 128); await c.connect(sub).submit(input, sig, { value: BOND });
      await c.connect(ch).openChallenge(input.taskId, { value: BOND });
      const t = await c.getTask(input.taskId); const blk = await ethers.provider.getBlock("latest");
      const maxDelay = Number(t.absoluteDeadline) - blk.timestamp;
      await inc(maxDelay + 1); const term = await tryTx(c.terminate(input.taskId));
      expect(term).to.equal("accepted");
      rec("S3", "BoundedTaskRollup", "colluding parties stall dispute (steps=128, stepTimeout=10s, maxRecoveries=2)", "BOUNDED",
        `max stall=${maxDelay}s = (normalTransitions(128)=${await c.normalTransitions(128)}+2)*10s; terminate after = ${term}`);
    });
    it("Hybrid: operator+challenger collusion can slash or clear arbitrarily (resolveChallenge unguarded)", async () => {
      const [sub, tee, ch] = await ethers.getSigners(); const env = await deployH(tee);
      const bad = await submitH(env, sub, tee, { outputHash: s8("wrong") });
      await env.r.connect(ch).openChallenge(bad.txId, 1, 0, false, ethers.ZeroHash, ethers.ZeroHash, [], []);
      await env.r.connect(ch).resolveChallenge(bad.txId, 0); // "clear" a disputed tx
      const st = (await env.r.getTransaction(bad.txId)).status;
      rec("S3", "HybridTEERollup", "colluding challenger resolves own challenge with bits=0", "NOT DEFENDED (FINDING-H1)", `status after=${st} (1=PENDING, challenge consumed as failure; tx later finalizable)`);
    });
  });

  describe("S4 TEE rollback / stale attestation", () => {
    it("Bounded: stale task (old id) and old TASK_VERSION rejected", async () => {
      const [sub] = await ethers.getSigners(); const c = await deployB();
      const { input, sig } = await mkTask(c, sub, "o1"); await c.connect(sub).submit(input, sig, { value: BOND });
      const old = { ...input, taskId: s8("o2"), version: 0 }; const os = await sub.signMessage(ethers.getBytes(await c.taskDigest(old)));
      const v = await tryTx(c.connect(sub).submit(old, os, { value: BOND }));
      expect(v).to.match(/task bounds/);
      rec("S4", "BoundedTaskRollup", "stale version / re-used id", "DEFENDED (no TEE state in this contract)", `version0=${v}; no cross-task state chain => rollback of an enclave's sealed state is out of scope`);
    });
    it("Hybrid: old nonce + old (e.g. debug) MRENCLAVE accepted; no nonce registry, no MRENCLAVE allowlist (FINDING)", async () => {
      const [sub, tee] = await ethers.getSigners(); const env = await deployH(tee);
      await submitH(env, sub, tee, { nonce: s8("n-old") });
      const again = await tryTx(submitH(env, sub, tee, { nonce: s8("n-old") }));
      const dbg = await tryTx(submitH(env, sub, tee, { mr: s8("mr-DEBUG-old") }));
      expect(again).to.equal("accepted"); expect(dbg).to.equal("accepted");
      rec("S4", "HybridTEERollup", "re-use old nonce; old/debug MRENCLAVE", "NOT DEFENDED (FINDING-H6)", `oldNonce=${again}; foreignMrenclave=${dbg}`);
    });
  });

  describe("S5 key leakage", () => {
    it("Hybrid: leaked TEE key forges arbitrary outputs; signer immutable, no revocation", async () => {
      const [sub, tee, att] = await ethers.getSigners(); const env = await deployH(tee);
      const leaked = new ethers.Wallet(ethers.Wallet.createRandom().privateKey); // stand-in
      // attacker holds tee key => use tee signer object as the leaked key
      const forged = await tryTx(submitH(env, att, tee, { outputHash: s8("attacker-chosen"), mr: s8("any") }));
      const hasRevoke = env.v.interface.fragments.some((f) => /revoke|setSigner|rotate/i.test(f.name || ""));
      expect(forged).to.equal("accepted"); expect(hasRevoke).to.equal(false);
      rec("S5", "HybridTEERollup+MockTEEVerifier", "leaked TEE signing key", "NOT DEFENDED (FINDING-H7)", `forgedSubmit=${forged}; revocation API present=${hasRevoke}; no bond => no slashing bound`);
    });
    it("Bounded: leaked submitter key -> can withdraw claimable, but cannot make wrong output pass", async () => {
      const [victim, , thief] = await ethers.getSigners(); const c = await deployB();
      const { input, sig } = await mkTask(c, victim, "k1"); await c.connect(victim).submit(input, sig, { value: BOND });
      await inc(61); await c.finalize(input.taskId);
      const cl = await c.claimable(victim.address);
      // attacker controlling victim's key calls withdraw to own address
      const before = await ethers.provider.getBalance(thief.address);
      await c.connect(victim).withdraw(thief.address);
      const stolen = (await ethers.provider.getBalance(thief.address)) - before;
      const w = await mkTask(c, victim, "k2", true); await c.connect(victim).submit(w.input, w.sig, { value: BOND });
      await inc(61); await c.finalize(w.input.taskId);
      expect(stolen).to.equal(cl);
      rec("S5", "BoundedTaskRollup", "leaked submitter EOA key", "PARTIAL: correctness defended, funds not",
        `stolen=${ethers.formatEther(stolen)} ETH (=claimable); forged wrong output burned (totalBurned=${ethers.formatEther(await c.totalBurned())}); loss bounded by claimable + attacker-posted bonds; no key-rotation API`);
    });
  });
});
