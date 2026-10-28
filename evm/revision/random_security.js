"use strict";
const fs = require("fs");
const path = require("path");
const assert = require("assert/strict");
const { ethers, network } = require("hardhat");
const out = path.join(process.env.REVISION_RUN, "security");
fs.mkdirSync(out, { recursive: true });
const stringify = x => JSON.stringify(x, (_, v) => typeof v === "bigint" ? v.toString() : v);
const hash = x => ethers.keccak256(ethers.toUtf8Bytes(x));
const abi = ethers.AbiCoder.defaultAbiCoder();
// 阶段 C 扩展：seed 可配置，默认保持原有固定基线 0x5eed2026（不删除旧回归）。
// 额外 seed 通过 RANDOM_SEED 环境变量注入；输出按 seed 命名，避免多 seed 互相覆盖原始证据。
const SEED = (Number(process.env.RANDOM_SEED ?? 0x5eed2026)) >>> 0;
const SEED_LABEL = "0x" + SEED.toString(16);
let rng = SEED;
function rand(n) { rng ^= rng << 13; rng ^= rng >>> 17; rng ^= rng << 5; return (rng >>> 0) % n; }
function traceFor(initial, steps) {
  const trace = [initial];
  for (let i = 0; i < steps; i++) trace.push(ethers.keccak256(abi.encode(["uint256", "bytes32"], [i, trace[i]])));
  return trace;
}
async function main() {
  const signers = (await ethers.getSigners()).slice(0, 4);
  const addresses = await Promise.all(signers.map(s => s.getAddress()));
  const contracts = [];
  for (let mr = 0; mr < 3; mr++) {
    const c = await (await ethers.getContractFactory("BoundedTaskRollup")).deploy(1000n, 80, 8, mr);
    await c.waitForDeployment(); contracts.push(c);
  }
  const count = Number(process.env.RANDOM_SEQUENCES || 1000);
  assert(count >= 1000, "At least 1000 sequences required");
  const log = fs.openSync(path.join(out, `random_sequences_${SEED_LABEL}.jsonl`), "w");
  const report = { seed: SEED, requested: count, completed: 0, operations: 0, successes: 0, reverts: 0, revertStateChecks: 0, pass: false, maxRecoveries: [0, 1, 2], steps: [4, 16, 64, 128], operationCounts: {}, startedAt: new Date().toISOString(), evidenceLayer: "local_evm", model: "independent acceptance predicate, transition and escrow accounting after every operation" };
  let active;
  try {
    for (let seq = 0; seq < count; seq++) {
      const snapshot = await network.provider.send("evm_snapshot");
      const mr = seq % 3, c = contracts[mr], addr = await c.getAddress();
      const steps = report.steps[Math.floor(seq / 3) % 4];
      const initial = hash(`random:${seq}`), id = hash(`id:${seq}`);
      const trace = traceFor(initial, steps), root = ethers.keccak256(abi.encode(["bytes32[]"], [trace]));
      const fault = rand(4);
      const input = [id, initial, steps, 1, fault & 1 ? hash("bad-output") : trace[steps], fault & 2 ? hash("bad-root") : root, hash(`data:${seq}`)];
      const digest = ethers.keccak256(abi.encode(["bytes32", "uint256", "address", "tuple(bytes32,bytes32,uint16,uint32,bytes32,bytes32,bytes32)"], [hash("HYBRID_BOUNDED_TASK_V1"), 31337, addr, input]));
      const signature = await signers[0].signMessage(ethers.getBytes(digest));
      const m = { phase: 0, rec: 0, left: 0, right: 0, round: 0, verdict: 0, locked: 0n, deposited: 0n, withdrawn: 0n, burned: 0n, claims: [0n, 0n, 0n, 0n], challenger: -1, abs: 0, timeout: 0, window: 0 };
      const history = [];
      async function state() {
        return { task: await c.getTask(id), locked: await c.locked(), claims: await Promise.all(addresses.map(a => c.claimable(a))), tc: await c.totalClaimable(), td: await c.totalDeposited(), tw: await c.totalWithdrawn(), burned: await c.totalBurned(), balance: await ethers.provider.getBalance(addr) };
      }
      async function check() {
        const s = await state();
        assert.equal(Number(s.task.phase), m.phase); assert.equal(Number(s.task.recoveries), m.rec);
        assert.equal(Number(s.task.absoluteDeadline), m.abs); assert.equal(Number(s.task.timeoutAt), m.timeout);
        assert.equal(Number(s.task.left), m.left); assert.equal(Number(s.task.right), m.right);
        assert.equal(Number(s.task.round), m.round); assert.equal(Number(s.task.verdict), m.verdict);
        assert.equal(s.locked, m.locked); assert.deepEqual(s.claims, m.claims);
        assert.equal(s.tc, m.claims.reduce((a, b) => a + b, 0n));
        assert.equal(s.td, m.deposited); assert.equal(s.tw, m.withdrawn); assert.equal(s.burned, m.burned);
        assert.equal(s.balance, s.locked + s.tc); assert.equal(s.balance, s.td - s.tw - s.burned);
        assert(m.rec <= mr); assert(m.timeout <= m.abs);
        if (m.phase >= 2) assert.equal(s.task.submitter, addresses[0]);
      }
      async function op(name, actor = rand(4), malformed = false) {
        const before = await state();
        const now = (await ethers.provider.getBlock("latest")).timestamp + 1;
        await network.provider.send("evm_setNextBlockTimestamp", [now]);
        const live = now <= m.timeout && now < m.abs;
        let allowed = false, fn;
        const conn = c.connect(signers[actor]), opts = { gasLimit: 3000000 };
        switch (name) {
          case "submit": allowed = m.phase === 0 && actor === 0 && !malformed; fn = () => conn.submit(input, malformed ? "0x1234" : signature, { ...opts, value: 1000n }); break;
          case "challenge": allowed = m.phase === 1 && actor !== 0 && now <= m.window && !malformed; fn = () => conn.openChallenge(id, { ...opts, value: malformed ? 999n : 1000n }); break;
          case "respond": allowed = m.phase === 2 && actor === 0 && live && !(fault & 2) && !malformed; fn = () => conn.respond(id, malformed ? trace.slice(1) : trace, opts); break;
          case "advance": allowed = (m.phase === 3 || m.phase === 4) && live && m.left < m.right; fn = () => conn.advance(id, opts); break;
          case "recover": allowed = m.phase >= 2 && m.phase <= 5 && now > m.timeout && now < m.abs && m.rec < mr; fn = () => conn.recover(id, opts); break;
          case "replay": allowed = m.phase === 5 && live; fn = () => conn.replay(id, opts); break;
          case "settle": allowed = m.phase === 6; fn = () => conn.settle(id, opts); break;
          case "adjudicate": allowed = m.phase >= 2 && m.phase < 7; fn = () => conn.adjudicate(id, opts); break;
          case "terminate": allowed = m.phase >= 2 && m.phase < 7 && (now > m.timeout || now >= m.abs); fn = () => conn.terminate(id, opts); break;
          case "finalize": allowed = m.phase === 1 && now > m.window; fn = () => conn.finalize(id, opts); break;
          case "withdraw": allowed = m.claims[actor] > 0n && !malformed; fn = () => conn.withdraw(malformed ? ethers.ZeroAddress : addresses[actor], opts); break;
          default: throw Error("Unknown operation");
        }
        let receipt, error;
        try { receipt = await (await fn()).wait(); } catch (e) { error = e; }
        active = { seq, name, actor, malformed, now, expectedAllowed: allowed, actualAllowed: !error, model: stringify(m) };
        assert.equal(!error, allowed, stringify(active));
        report.operations++; report.operationCounts[name] = (report.operationCounts[name] || 0) + 1;
        if (!allowed) {
          assert.equal(stringify(await state()), stringify(before), "Revert changed contract state or escrow");
          report.reverts++; report.revertStateChecks++;
        } else {
          report.successes++;
          const touch = () => { m.timeout = Math.min(now + 8, m.abs); };
          const settle = () => { m.verdict = fault; m.phase = 7; const amount = m.challenger < 0 ? 1000n : 2000n; m.locked -= amount;
            if (fault && m.challenger < 0) m.burned += amount;
            else m.claims[fault ? m.challenger : 0] += amount; };
          if (name === "submit") { m.phase = 1; m.window = now + 80; m.locked += 1000n; m.deposited += 1000n; }
          if (name === "challenge") { m.phase = 2; m.challenger = actor; m.right = steps; m.abs = now + (Math.ceil(Math.log2(steps + 1)) + 3 + mr) * 8; m.locked += 1000n; m.deposited += 1000n; touch(); }
          if (name === "respond") { m.phase = 3; touch(); }
          if (name === "advance") { const mid = Math.floor((m.left + m.right) / 2); if (steps <= mid) m.right = mid; else m.left = mid + 1; m.round++; m.phase = m.left === m.right ? 5 : 4; touch(); }
          if (name === "recover") { m.rec++; touch(); }
          if (name === "replay") { m.phase = 6; m.verdict = fault; }
          if (["settle", "adjudicate", "terminate", "finalize"].includes(name)) settle();
          if (name === "withdraw") { m.withdrawn += m.claims[actor]; m.claims[actor] = 0n; }
          await check();
        }
        history.push({ name, actor, malformed, timestamp: now, allowed, phase: m.phase, recoveries: m.rec, txHash: receipt ? receipt.hash : (error.transactionHash || null), error: error ? (error.shortMessage || error.message).slice(0, 200) : null });
      }
      async function jump(n) { await network.provider.send("evm_increaseTime", [n]); await network.provider.send("evm_mine"); history.push({ name: "timeJump", seconds: n }); }
      // Prefixes reach deeper phases; the remaining operations are unfiltered and adversarial.
      await op("submit", 0);
      if (seq % 5 !== 0) await op("challenge", 1);
      if (seq % 5 === 1) { await jump(9); await op("recover", 2); }
      if (seq % 5 === 2 && !(fault & 2)) { await op("respond", 0); while (m.phase === 3 || m.phase === 4) await op("advance", 2); await op("replay", 3); }
      const names = ["submit", "challenge", "respond", "advance", "recover", "replay", "settle", "adjudicate", "terminate", "finalize", "withdraw"];
      for (let i = 0; i < 24; i++) { if (rand(6) === 0) await jump(rand(90) + 1); await op(names[rand(names.length)], rand(4), rand(5) === 0); }
      if (m.phase === 1) { await jump(100); await op("finalize", seq % 4); }
      else if (m.phase < 7) await op("adjudicate", 2);
      for (let a = 0; a < 4; a++) if (m.claims[a]) await op("withdraw", a);
      await check(); assert.equal(m.phase, 7); assert.equal(m.locked, 0n);
      fs.writeSync(log, stringify({ sequence: seq, steps, maxRecoveries: mr, fault, history, final: m }) + "\n");
      report.completed++;
      await network.provider.send("evm_revert", [snapshot]);
      if ((seq + 1) % 100 === 0) console.log(`[random] ${seq + 1}/${count} sequences, ${report.operations} calls, ${report.reverts} unchanged-state reverts`);
    }
    report.pass = report.completed === count;
  } catch (e) { report.failure = { message: e.message, active }; throw e; }
  finally { fs.closeSync(log); report.seedLabel = SEED_LABEL; report.finishedAt = new Date().toISOString(); fs.writeFileSync(path.join(out, `random_report_${SEED_LABEL}.json`), JSON.stringify(report, null, 2)); }
  console.log(JSON.stringify(report));
}
main().catch(e => { console.error(e); process.exitCode = 1; });
