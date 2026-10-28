// SPDX-License-Identifier: MIT
//
// evm/revision/stageG_mechanism.js
//
// 阶段 G · L1 同计算模型机制微基准（mechanism microbenchmark）。
//
// 目的：在**完全相同的有界 hash 链计算模型**下，把本项目 BoundedTaskRollup 与一个
// **机制基线（mechanism baseline）** MechanismBaseline 做同口径对照。
// 基线**不是** Arbitrum / Optimism / TeeRollup 的官方实现，也不属于本项目生产协议；
// 命名为 mechanism baseline，用于量化「去掉兜底重算」的代价。
//
// 与 F 阶段的关系：
//   - 复用 F 的统计口径与统计模块 stageF_stats.js（同 cluster 单位、同删失规则）；
//   - 不复用 F 的历史样本充当新实验 —— 本脚本在同进程内对两套系统做**配对**测量；
//   - F 的消融结果作为独立交叉核对引用，不合并为本表数值。
//
// 运行：cd evm; REVISION_RUN=<abs> node ./node_modules/hardhat/internal/cli/cli.js \
//   run --config revision/hardhat.config.js revision/stageG_mechanism.js

"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { ethers, network } = require("hardhat");
const S = require("./stageF_stats");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径");
const OUT = path.join(REVISION_RUN, "stageG");
const RAW = path.join(OUT, "raw", "mechanism");
fs.mkdirSync(RAW, { recursive: true });

const SCHEMA = "hybrid-tee-rollup.stageG.mechanism.v1";

const DESIGN = {
  schemaVersion: "hybrid-tee-rollup.stageG.mechanism-design.v1",
  createdAtUtc: new Date().toISOString(),
  purpose: "L1 同计算模型机制微基准：本项目 BoundedTaskRollup vs MechanismBaseline",
  systems: {
    "bounded-task-rollup": { contract: "BoundedTaskRollup", role: "本方案（有界重算兜底 + recover）" },
    "mechanism-baseline": { contract: "MechanismBaseline", role: "机制基线（二分 + 单步证明 + 无兜底重算）" },
  },
  workload: { batchSize: 1, steps: 64, payloadKiBPerTask: 1, configuredConcurrency: 1 },
  deploy: {
    bondWei: "1000000000000000",
    challengeWindow: 100000,
    stepTimeout: 10,
    maxRecoveries: 2,
    note: "两套系统使用相同部署参数；challengeWindow 取 100000 以消除 F 已归因的链钟窗口假象",
  },
  protocol: { warmupBatches: 2, measureBatches: 10, independentRuns: 3 },
  arms: [
    { id: "interactive", faultInjected: false, note: "双方在线：本方案 respond→advance*→replay→settle；基线 respond→advance*→step" },
    { id: "fault-no-recovery", faultInjected: true, note: "提交方 respond 后超时离线；本方案走 adjudicate 兜底，基线只能 terminate" },
    { id: "fault-with-recovery", faultInjected: true, note: "提交方超时离线 + recover 后续推（基线无恢复机制，标 not_applicable）" },
    { id: "direct-no-response", faultInjected: false, note: "不 respond：本方案直接 adjudicate；基线只能 terminate" },
  ],
  correctnessDefinition: {
    correct: "任务已 SETTLED 且胜者为提交方（本微基准始终提交正确 trace，故提交方获胜=正确终局）",
    incorrect: "任务已 SETTLED 但胜者为挑战方（正确提交方被罚没）",
    unresolved: "批结束时未 SETTLED（右删失）",
  },
  statistics: {
    clusterUnit: "independent run / batch",
    note: "3 个独立 run 不给 CI，只报描述性；成功率与分母同时报告，不只对成功求平均",
    seed: 20260917,
  },
};

const nowMs = () => Number(process.hrtime.bigint() / 1000000n);
const monoNs = () => process.hrtime.bigint().toString();
const utc = () => new Date().toISOString();
const dec = (v) => BigInt(v).toString();

function abiEncode(t, v) { return ethers.AbiCoder.defaultAbiCoder().encode(t, v); }
function jsCompute(initial, steps) {
  const trace = [initial];
  let cur = initial;
  for (let i = 0; i < steps; ++i) {
    cur = ethers.keccak256(abiEncode(["uint256", "bytes32"], [BigInt(i), cur]));
    trace.push(cur);
  }
  return { output: trace[steps], root: ethers.keccak256(abiEncode(["bytes32[]"], [trace])), trace };
}
function jsTaskDigest(domain, chainId, addr, i) {
  return ethers.keccak256(abiEncode(
    ["bytes32", "uint256", "address", "bytes32", "bytes32", "uint16", "uint32", "bytes32", "bytes32", "bytes32"],
    [domain, BigInt(chainId), addr, i.taskId, i.initial, i.steps, i.version, i.output, i.traceRoot, i.dataHash]));
}
async function increaseTime(sec) {
  await network.provider.send("evm_increaseTime", [sec]);
  await network.provider.send("evm_mine", []);
}

// ---------------- 单批测量 ----------------
async function runBatch(ctx, batchIndex) {
  const { systemKey, contract, domain, addr, chainId, version, signers, runIndex, arm, warmup, steps, challengeWindow } = ctx;
  const t0 = nowMs();
  const rec = {
    schemaVersion: SCHEMA,
    runId: ctx.runId,
    system: systemKey,
    arm,
    runIndex,
    batchIndex,
    sampleId: `stageG-${systemKey}-${arm}-r${runIndex}-b${batchIndex}`,
    warmup,
    startedAtUtc: utc(),
    monotonicStartNs: monoNs(),
    workload: { batchSize: 1, taskCount: 1, steps, configuredConcurrency: 1, payloadKiBPerTask: 1 },
    outcome: "unresolved",
    outcomeReason: null,
    correctFinality: false,
    segments: {},
    gas: { submitGas: "0", challengeGas: "0", resolveGas: "0", withdrawGas: "0" },
    fee: { feeSource: "local-gas-only", feeStatus: "local_measured_not_monetary", submitFeeWei: "0", challengeFeeWei: "0", resolveFeeWei: "0", withdrawFeeWei: "0" },
    counts: { attempts: 0, retries: 0, failures: 0, censored: 0, txCount: 0, interactiveMoves: 0 },
    recovery: { recoverCalled: false, recoverSucceeded: false, continuationSucceeded: false, fallbackUsed: false },
    endpoints: {},
  };
  const slot = (runIndex * 100 + batchIndex) * 2;
  const submitter = signers[slot % signers.length];
  const challenger = signers[(slot + 1) % signers.length];
  const bond = ctx.bond;

  const track = (key, r) => {
    const g = BigInt(r.gasUsed);
    const p = BigInt(r.gasPrice || 0n);
    rec.gas[key] = dec(BigInt(rec.gas[key]) + g);
    const fk = key.replace(/Gas$/, "") + "FeeWei";
    rec.fee[fk] = dec(BigInt(rec.fee[fk]) + g * p);
    rec.counts.txCount += 1;
  };

  const label = rec.sampleId;
  const initial = ethers.keccak256(ethers.toUtf8Bytes("init:" + label));
  const taskId = ethers.keccak256(ethers.toUtf8Bytes("task:" + label));
  const comp = jsCompute(initial, steps);
  const input = {
    taskId, initial, steps, version,
    output: comp.output, traceRoot: comp.root,
    dataHash: ethers.keccak256(ethers.toUtf8Bytes("payload:" + label)),
  };
  const digest = jsTaskDigest(domain, chainId, addr, input);
  const sig = await submitter.signMessage(ethers.getBytes(digest));

  try {
    rec.counts.attempts += 1;
    let r = await (await contract.connect(submitter).submit(input, sig, { value: bond })).wait();
    track("submitGas", r);
    rec.endpoints.submittedAtUtc = utc();

    r = await (await contract.connect(challenger).openChallenge(taskId, { value: bond })).wait();
    track("challengeGas", r);
    rec.endpoints.challengedAtUtc = utc();

    if (systemKey === "bounded-task-rollup") {
      if (arm === "direct-no-response") {
        r = await (await contract.connect(challenger).adjudicate(taskId)).wait();
        track("resolveGas", r);
        rec.recovery.fallbackUsed = true;
        rec.outcome = "correct";
      } else {
        r = await (await contract.connect(submitter).respond(taskId, comp.trace)).wait();
        track("resolveGas", r);
        if (arm !== "interactive") {
          await increaseTime(11);
          if (arm === "fault-with-recovery") {
            try {
              const rt = await (await contract.connect(challenger).recover(taskId)).wait();
              track("resolveGas", rt);
              rec.recovery.recoverCalled = true; rec.recovery.recoverSucceeded = true;
            } catch (e) { rec.outcomeReason = "recover failed: " + String(e.message || e).slice(0, 120); }
          }
        }
        let guard = 0, ok = true, err = null;
        while (guard++ < steps + 5) {
          const ph = Number((await contract.getTask(taskId)).phase);
          if (ph === 5 || ph >= 6 || ph < 3) break;
          try {
            r = await (await contract.connect(challenger).advance(taskId)).wait();
            track("resolveGas", r);
            rec.counts.interactiveMoves += 1;
          } catch (e) { ok = false; err = e; break; }
        }
        if (ok) {
          rec.recovery.continuationSucceeded = true;
          r = await (await contract.connect(challenger).replay(taskId)).wait();
          track("resolveGas", r);
          r = await (await contract.connect(challenger).settle(taskId)).wait();
          track("resolveGas", r);
          rec.outcome = "correct";
        } else {
          rec.outcomeReason = "continuation failed: " + String((err && err.message) || err).slice(0, 120);
          r = await (await contract.connect(challenger).adjudicate(taskId)).wait();
          track("resolveGas", r);
          rec.recovery.fallbackUsed = true;
          rec.outcome = "correct";
        }
      }
    } else {
      // ---- MechanismBaseline ----
      if (arm === "direct-no-response") {
        await increaseTime(11);
        r = await (await contract.connect(challenger).terminate(taskId)).wait();
        track("resolveGas", r);
        rec.outcome = "incorrect";
        rec.outcomeReason = "基线无兜底重算：未 respond 时只能 terminate，正确提交方被罚没";
      } else if (arm === "fault-with-recovery") {
        rec.outcome = "not_applicable";
        rec.outcomeReason = "MechanismBaseline 无恢复机制；本臂对基线不适用";
      } else {
        r = await (await contract.connect(submitter).respond(taskId, comp.trace)).wait();
        track("resolveGas", r);
        if (arm !== "interactive") await increaseTime(11);
        let guard = 0, ok = true, err = null;
        while (guard++ < steps + 5) {
          const t = await contract.getTask(taskId);
          if (Number(t.phase) === 5 || Number(t.phase) >= 6 || Number(t.phase) < 3) break;
          try {
            r = await (await contract.connect(challenger).advance(taskId)).wait();
            track("resolveGas", r);
            rec.counts.interactiveMoves += 1;
          } catch (e) { ok = false; err = e; break; }
        }
        if (ok) {
          rec.recovery.continuationSucceeded = true;
          const t = await contract.getTask(taskId);
          const idx = Number(t.left);
          const pre = comp.trace[idx - 1];
          const post = comp.trace[idx];
          r = await (await contract.connect(challenger).step(taskId, idx, pre, post)).wait();
          track("resolveGas", r);
          rec.outcome = "correct";
        } else {
          rec.outcomeReason = "continuation failed: " + String((err && err.message) || err).slice(0, 120);
          await increaseTime(11);
          r = await (await contract.connect(challenger).terminate(taskId)).wait();
          track("resolveGas", r);
          rec.outcome = "incorrect";
        }
      }
    }

    rec.endpoints.protocolFinalAtUtc = utc();
    rec.endpoints.protocolFinalMonoNs = monoNs();
    for (const who of [submitter, challenger]) {
      const c = await contract.claimable(who.address);
      if (c > 0n) {
        try {
          r = await (await contract.connect(who).withdraw(await who.getAddress())).wait();
          track("withdrawGas", r);
        } catch (e) { rec.counts.failures += 1; }
      }
    }
    rec.endpoints.withdrawnAtUtc = utc();
  } catch (e) {
    rec.counts.failures += 1;
    rec.outcome = "unresolved";
    rec.outcomeReason = String((e && (e.shortMessage || e.message)) || e).slice(0, 200);
    rec.counts.censored += 1;
  }
  rec.correctFinality = rec.outcome === "correct";
  rec.segments.totalMs = nowMs() - t0;
  rec.monotonicEndNs = monoNs();
  return rec;
}

// ---------------- 主流程 ----------------
async function main() {
  const signers = (await ethers.getSigners()).slice(1);
  const bond = BigInt(DESIGN.deploy.bondWei);
  const chainId = (await ethers.provider.getNetwork()).chainId;

  const ours = await (await ethers.getContractFactory("BoundedTaskRollup")).deploy(
    bond, DESIGN.deploy.challengeWindow, DESIGN.deploy.stepTimeout, DESIGN.deploy.maxRecoveries);
  await ours.waitForDeployment();
  const base = await (await ethers.getContractFactory("MechanismBaseline")).deploy(
    bond, DESIGN.deploy.challengeWindow, DESIGN.deploy.stepTimeout);
  await base.waitForDeployment();

  const systems = {
    "bounded-task-rollup": { contract: ours, domain: await ours.DOMAIN(), version: Number(await ours.TASK_VERSION()), addr: await ours.getAddress() },
    "mechanism-baseline": { contract: base, domain: await base.DOMAIN(), version: Number(await base.TASK_VERSION()), addr: await base.getAddress() },
  };

  fs.writeFileSync(path.join(OUT, "mechanism_design.frozen.json"), JSON.stringify(DESIGN, null, 2));
  const log = fs.openSync(path.join(RAW, "mechanism_records.jsonl"), "w");
  const write = (o) => fs.writeSync(log, JSON.stringify(o) + "\n");

  const runId = "stageG-mechanism";
  const { warmupBatches, measureBatches, independentRuns } = DESIGN.protocol;
  for (const [systemKey, sys] of Object.entries(systems)) {
    for (const armDef of DESIGN.arms) {
      if (systemKey === "mechanism-baseline" && armDef.id === "fault-with-recovery") continue;
      for (let runIndex = 0; runIndex < independentRuns; ++runIndex) {
        const total = warmupBatches + measureBatches;
        const recs = [];
        for (let i = 0; i < total; ++i) {
          const r = await runBatch({
            runId, systemKey, contract: sys.contract, domain: sys.domain, addr: sys.addr,
            chainId, version: sys.version, signers, runIndex, arm: armDef.id,
            warmup: i < warmupBatches, steps: DESIGN.workload.steps,
            challengeWindow: DESIGN.deploy.challengeWindow, bond,
          }, i);
          recs.push(r);
          write(r);
        }
        const m = recs.filter((r) => !r.warmup);
        const correct = m.filter((r) => r.outcome === "correct").length;
        console.log(`[G] ${systemKey} ${armDef.id} r${runIndex}: n=${m.length} correct=${correct} incorrect=${m.filter(r=>r.outcome==='incorrect').length} unresolved=${m.filter(r=>r.outcome==='unresolved').length}`);
      }
    }
  }
  fs.closeSync(log);
  console.log(`[G] mechanism raw: ${RAW}`);
}

main().catch((e) => { console.error(e); process.exitCode = 1; });
