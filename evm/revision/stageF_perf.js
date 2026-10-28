// SPDX-License-Identifier: MIT
//
// evm/revision/stageF_perf.js
//
// 阶段 F 本地测量 runner（F-local）。不依赖 D/E 真实公网资源，不部署主网、不广播、不付费。
//
// 设计要点（阶段 F 提示词）：
//   §F1  A 每样本一逻辑批：batch record 的 taskCount = batchSize；吞吐 numerator 不超过该样本 taskCount。
//        跨批次汇总另设**独立版本化** window record（hybrid-tee-rollup.stageF.window.v1），
//        不用 A experiment_record 冒充窗口记录或单样本。
//   §F2  设计先冻结再执行：design.frozen.json 落盘后才跑；不观察结果后删格子。
//        warmup 预热也记录但按预先规则不参与稳态统计；失败/重试/删失全部保留。
//   §F3  默认矩阵 batchSize 1/8/32、payloadKiBPerTask 1/8/32、configuredConcurrency 1/4/16、
//        steps 选 1 / 64(中间) / 128(MAX)，并含 steps=0/129 超上限拒绝边界。
//        **先单变量筛查再预设交叉**，不无限展开笛卡尔积。
//        batchSize=1 × concurrency=1/4/16 三组必须保留差异并解释。
//   §F4  端点时间戳分离：提交确认 / 应用可用 / 协议终局 / 可提现 / 实际提现。
//   §F5  gas/wei 全部 BigInt + 十进制字符串；本地 gas 与真实货币费用分开，
//        feeSource="local-gas-only"，不填 0 不填估算。押金/退款/罚没作为价值转移单列。
//   §F6  raw 落盘后由 stageF_aggregate.js 单独聚合；本文件不做统计。
//
// 诚实边界（必须随结果一起报告）：
//   1. 有界模型 dataHash 固定 32 字节，payloadKiBPerTask **不改变链上数据大小**；
//      计算只处理 hash 链。故 payload 维名义参数，标 payloadIsNominal=true，不伪造差异，
//      不把吞吐称为高频 DApp 通用业务 TPS。
//   2. Hardhat in-process automining：适合 gas 与客户端开销，**不能证明共识吞吐**。
//   3. 负载模型为**闭环模型**（closed-loop，固定批数、批完成才补新批），
//      不能宣称无限到达压力下的容量。
//
// 运行：
//   cd evm
//   REVISION_RUN=<abs> node ./node_modules/hardhat/internal/cli/cli.js \
//     run --config revision/hardhat.config.js revision/stageF_perf.js
// 冒烟（小规模，与足量测量分开）：STAGEF_SMOKE=1

"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { ethers, network } = require("hardhat");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径的独立输出目录");
const OUT = path.join(REVISION_RUN, "stageF");
const RAW = path.join(OUT, "raw");
fs.mkdirSync(RAW, { recursive: true });

const BATCH_SCHEMA = "hybrid-tee-rollup.stageF.batch.v1";
const WINDOW_SCHEMA = "hybrid-tee-rollup.stageF.window.v1";
const TASK_SCHEMA = "hybrid-tee-rollup.stageF.task.v1";

const SMOKE = process.env.STAGEF_SMOKE === "1";

// 仪器旋钮（默认值即主矩阵冻结值；改动必须重新冻结 source/config 哈希后再测）
//   F_CHALLENGE_WINDOW：部署参数 challengeWindow（链上秒）。默认 100。
//   F_ONLY_CELLS：逗号分隔的 cellId 白名单，仅用于**归因验证**等定向复测。
//   F_WARMUP / F_MEASURE / F_RUNS：仅用于定向复测的样本计划覆盖。
const CHALLENGE_WINDOW = Number(process.env.F_CHALLENGE_WINDOW || 100);
const ONLY_CELLS = process.env.F_ONLY_CELLS ? process.env.F_ONLY_CELLS.split(",").map((s) => s.trim()) : null;

// ---------------- 实验设计（先冻结再执行） ----------------
const BASELINE = { batchSize: 8, payloadKiBPerTask: 8, configuredConcurrency: 4, steps: 64 };

// 单变量筛查：除被测维度外固定为 baseline
const SCREENING = [
  { axis: "batchSize", values: [1, 8, 32] },
  { axis: "configuredConcurrency", values: [1, 4, 16] },
  { axis: "payloadKiBPerTask", values: [1, 8, 32] },
  { axis: "steps", values: [1, 64, 128] },
];

// F3 强制：batchSize=1 时 concurrency=1/4/16 三组保留差异
const FORCED_CONCURRENCY_CELLS = [
  { batchSize: 1, payloadKiBPerTask: 8, configuredConcurrency: 1, steps: 64 },
  { batchSize: 1, payloadKiBPerTask: 8, configuredConcurrency: 4, steps: 64 },
  { batchSize: 1, payloadKiBPerTask: 8, configuredConcurrency: 16, steps: 64 },
];

// 预设交叉（不无限展开笛卡尔积）：支撑主结论的两个极端角点
const CROSS_CELLS = [
  { batchSize: 32, payloadKiBPerTask: 32, configuredConcurrency: 16, steps: 128, tag: "heavy-corner" },
  { batchSize: 1, payloadKiBPerTask: 1, configuredConcurrency: 1, steps: 1, tag: "light-corner" },
];

const DESIGN = {
  schemaVersion: "hybrid-tee-rollup.stageF.design.v1",
  createdAtUtc: new Date().toISOString(),
  smoke: SMOKE,
  plan: "先冻结设计再执行；单变量筛查 -> 预设交叉；不观察初步结果后删格子",
  baseline: BASELINE,
  screening: SCREENING,
  forcedCells: FORCED_CONCURRENCY_CELLS,
  crossCells: CROSS_CELLS,
  matrixProtocol: {
    warmupBatches: process.env.F_WARMUP ? Number(process.env.F_WARMUP) : (SMOKE ? 1 : 5),
    measureBatches: process.env.F_MEASURE ? Number(process.env.F_MEASURE) : (SMOKE ? 2 : 30),
    independentRuns: process.env.F_RUNS ? Number(process.env.F_RUNS) : (SMOKE ? 1 : 3),
    note: "每格每 run 固定预热 5 批 + 稳态 30 批；预热记录但不参与稳态统计（推荐起点，非尾部充分）",
  },
  loadModel: {
    model: "closed-loop",
    note: "固定批数、批完成才补新批；不能宣称无限到达压力下的容量，不忽略排队等待",
  },
  challengeWindow: CHALLENGE_WINDOW,
  challengeWindowNote: "部署参数（链上秒）。主矩阵冻结值 100；Hardhat 每块 +1s 链钟且 automining 串行，高负载下 openChallenge 可能越过该窗口（见 attribution 运行）",
  onlyCells: ONLY_CELLS,
  boundary: {
    stepsReject: [0, 129],
    note: "MAX_STEPS=128；steps=0 与 steps=129 必须被 submit 拒绝（不缩小 payload、不截断）",
  },
  ablation: {
    protocol: { warmupBatches: SMOKE ? 1 : 2, measureBatches: SMOKE ? 2 : 10, independentRuns: SMOKE ? 1 : 3 },
    reason: "故障注入需全局时间推进（evm_increaseTime），强制串行；故每臂 3×(2 预热+10 稳态) 批",
    arms: [
      { id: "recovery-interactive", faultInjected: false, useRecover: false, note: "提交方在线，交互定位 respond->advance*->replay->settle" },
      { id: "no-recovery-with-fault-fallback", faultInjected: true, useRecover: false, note: "提交方超时离线，不调用 recover，第三方只能走 adjudicate 兜底（不关闭兜底）" },
      { id: "direct-fallback", faultInjected: false, useRecover: false, direct: true, note: "不 respond，直接 adjudicate 重算兜底" },
      { id: "recovery-under-fault", faultInjected: true, useRecover: true, note: "提交方超时离线，观察者 recover 后第三方续推 advance*->replay->settle" },
    ],
    workload: { batchSize: 1, payloadKiBPerTask: 1, configuredConcurrency: 1, steps: 64 },
  },
  nonceAndSigners: {
    availableAccounts: 40,
    poolStart: 1,
    poolSize: 39,
    allocation: "第 i 批使用 signers[(slot+2i) % poolSize] 作为 submitter、下一个作为 challenger",
    recovererRole: "由 challenger 承担（合约未限制 recover/advance/replay/settle 调用者）；引入第三个独立 EOA 会在 concurrency=16 时需要 48 个无冲突账户 > 可用 39 个，从而改变系统条件",
    note: "使用多个 EOA 会改变系统条件，故显式报告：nonce 分配策略固定、signer 数量固定（每批 2 个）、重试规则固定",
  },
  retry: { maxAttempts: 3, backoffMs: 20, note: "重试次数固定；失败与重试均保留，重试成本计入总额子集" },
  timeouts: { batchTimeoutMs: 120000, note: "单批超时记右删失(censored)，不删除、不只对成功求平均" },
  application: {
    name: "bounded-keccak-chain-accumulator",
    deterministic: true,
    maxSteps: 128,
    note: "落在实际有界模型内的可复现确定性应用样例；属合成微基准，不是真实 DApp 业务负载",
  },
  payloadIsNominal: true,
  payloadIsNominalReason:
    "有界模型 dataHash 固定 32 字节，计算只处理 hash 链；payloadKiBPerTask 不改变链上数据大小，属名义/DA 填充参数",
  environment: "hardhat in-process automining, cancun, blockGasLimit=60000000, initialBaseFeePerGas=1 gwei；不能证明共识吞吐",
  statistics: {
    note: "raw 落盘后由 stageF_aggregate.js 单独聚合；3 个独立 run 时 CI 不稳，不报 p99、不伪造大样本",
    clusterUnit: "independent run / batch（批内任务不是独立样本）",
    quantiles: [0.5, 0.95],
    quantileMethod: "nearest-rank on sorted samples",
    seed: 20260917,
  },
};

// ---------------- 工具 ----------------
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function increaseTime(sec) {
  await network.provider.send("evm_increaseTime", [sec]);
  await network.provider.send("evm_mine", []);
}

// 并发池：以 inflight_batches 为单位，**禁用 min(batchSize, concurrency)** 折叠
async function runPool(total, limit, worker, windowStartMs) {
  const inflightSeries = [];
  let inflight = 0, peak = 0, sum = 0, samples = 0, next = 0, completed = 0;
  const results = new Array(total);
  async function launch() {
    for (;;) {
      const my = next++;
      if (my >= total) return;
      const queueWaitMs = nowMs() - windowStartMs;
      inflight++;
      sum += inflight; samples++;
      if (inflight > peak) peak = inflight;
      inflightSeries.push({ t: nowMs() - windowStartMs, inflight, queued: Math.max(0, total - 1 - my), completed });
      try {
        results[my] = await worker(my, queueWaitMs);
      } catch (e) {
        results[my] = { fatal: true, error: String((e && (e.shortMessage || e.message)) || e).slice(0, 300) };
      } finally {
        inflight--; completed++;
      }
    }
  }
  const runners = [];
  for (let i = 0; i < Math.min(limit, total); ++i) runners.push(launch());
  await Promise.all(runners);
  return { results, peak, mean: samples ? sum / samples : 0, series: inflightSeries };
}

// ---------------- 单批测量 ----------------
async function runBatch(ctx, { batchIndex, signerSlot, queueWaitMs }) {
  const {
    runId, cellId, experimentId, runIndex, rollup, signers,
    batchSize, payloadKiB, steps, concurrency, warmup, arm,
  } = ctx;
  const rec = {
    schemaVersion: BATCH_SCHEMA,
    runId, cellId, experimentId, runIndex, batchIndex,
    sampleId: `${runId}-${cellId}-r${runIndex}-b${batchIndex}`,
    windowId: `${cellId}-r${runIndex}`,
    warmup: !!warmup,
    arm: arm || null,
    status: "pass",
    error: null,
    startedAtUtc: utc(),
    monotonicStartNs: monoNs(),
    queueWaitMs,
    workload: {
      batchSize, taskCount: batchSize,
      payloadKiBPerTask: payloadKiB,
      payloadBytesPerTask: payloadKiB * 1024,
      batchPayloadBytes: batchSize * payloadKiB * 1024,
      nominalPayload: true,
      steps, configuredConcurrency: concurrency,
      concurrencyUnit: "inflight_batches",
      application: DESIGN.application.name,
    },
    endpoints: {},
    segments: {},
    gas: {},
    fee: { feeSource: "local-gas-only", feeStatus: "local_measured_not_monetary", note: "Hardhat 本地 gas×effectiveGasPrice，不是真实公网货币费用" },
    valueTransfer: { bondPaidWei: "0", refundedWei: "0", slashedWei: "0", burnedWei: "0", withdrawnWei: "0" },
    counts: { attempts: 0, retries: 0, failures: 0, censored: 0, acceptedTasks: 0, executedTasks: 0, finalizedTasks: 0, withdrawableTasks: 0, withdrawnTasks: 0 },
    recovery: null,
    tasks: [],
    signerRoles: { submitter: null, challenger: null, recoverer: null },
  };

  const rollupAddr = ctx.rollupAddr;
  const bond = ctx.bond;
  const domain = ctx.domain;
  const chainId = ctx.chainId;
  const version = ctx.version;

  const submitter = signers[signerSlot % signers.length];
  const challenger = signers[(signerSlot + 1) % signers.length];
  // 观察者/续推角色由 challenger 承担：合约未限制 recover/advance/replay/settle 的调用者。
  // 若再引入第三个独立 EOA，concurrency=16 时需 48 个无冲突账户 > 可用 39 个，会改变系统条件。
  const observer = challenger;
  rec.signerRoles = { submitter: submitter.address, challenger: challenger.address, recoverer: observer.address };

  const t0 = nowMs();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; }, DESIGN.timeouts.batchTimeoutMs);

  const addGas = (key, r) => {
    const g = BigInt(r.gasUsed);
    const p = BigInt(r.gasPrice || r.effectiveGasPrice || 0n);
    rec.gas[key] = dec(BigInt(rec.gas[key] || 0n) + g);
    // submitGas -> submitFeeWei（与 window 聚合的 fee 键保持一致）
    const feeKey = key.replace(/Gas$/, "") + "FeeWei";
    rec.fee[feeKey] = dec(BigInt(rec.fee[feeKey] || 0n) + g * p);
    rec.fee.observedGasPriceWei = dec(p);
    rec.fee.gasPriceSource = "receipt.gasPrice (Hardhat EIP-1559 effective price)";
    return g;
  };
  const txCount = { n: 0 };
  const track = (key, r) => { addGas(key, r); txCount.n++; };

  try {
    // ---- 编码（客户端） ----
    const tEncode = nowMs();
    const tasks = [];
    for (let k = 0; k < batchSize; ++k) {
      const label = `${rec.sampleId}-t${k}`;
      const initial = ethers.keccak256(ethers.toUtf8Bytes("init:" + label));
      const taskId = ethers.keccak256(ethers.toUtf8Bytes("task:" + label));
      const comp = jsCompute(initial, steps);
      const dataHash = ethers.keccak256(ethers.toUtf8Bytes(`payload:${label}:${payloadKiB}KiB`));
      tasks.push({ taskId, input: { taskId, initial, steps, version, output: comp.output, traceRoot: comp.root, dataHash }, comp });
    }
    rec.segments.encodeMs = nowMs() - tEncode;

    // ---- 签名 ----
    const tSign = nowMs();
    const sigs = [];
    for (const { input } of tasks) {
      const digest = jsTaskDigest(domain, chainId, rollupAddr, input);
      sigs.push(await submitter.signMessage(ethers.getBytes(digest)));
    }
    rec.segments.signMs = nowMs() - tSign;

    // ---- submit（含 nonce 重试规则固定为 maxAttempts） ----
    const tSubmit = nowMs();
    for (let k = 0; k < tasks.length; ++k) {
      const { input, taskId } = tasks[k];
      let ok = false, lastErr = null;
      for (let attempt = 1; attempt <= DESIGN.retry.maxAttempts; ++attempt) {
        rec.counts.attempts += 1;
        try {
          const tx = await rollup.connect(submitter).submit(input, sigs[k], { value: bond });
          const r = await tx.wait();
          track("submitGas", r);
          rec.valueTransfer.bondPaidWei = dec(BigInt(rec.valueTransfer.bondPaidWei) + bond);
          rec.counts.acceptedTasks += 1;
          rec.counts.executedTasks += 1;
          rec.tasks.push({ schemaVersion: TASK_SCHEMA, taskId, windowId: rec.windowId, sampleId: rec.sampleId, monotonicStartNs: rec.monotonicStartNs, phase: "submitted" });
          ok = true;
          break;
        } catch (e) {
          lastErr = e;
          if (attempt < DESIGN.retry.maxAttempts) { rec.counts.retries += 1; await sleep(DESIGN.retry.backoffMs); }
        }
      }
      if (!ok) { rec.counts.failures += 1; rec.counts.censored += 1; rec.error = String((lastErr && (lastErr.shortMessage || lastErr.message)) || lastErr).slice(0, 200); }
    }
    rec.segments.submitMs = nowMs() - tSubmit;
    rec.endpoints.submittedConfirmedAtUtc = utc();
    rec.endpoints.submittedConfirmedMonoNs = monoNs();
    // 乐观可用（optimistic availability）：提交确认即可用，不等终局
    rec.endpoints.optimisticAvailableAtUtc = rec.endpoints.submittedConfirmedAtUtc;

    // ---- openChallenge ----
    const tCh = nowMs();
    for (const { taskId } of tasks) {
      try {
        const tx = await rollup.connect(challenger).openChallenge(taskId, { value: bond });
        const r = await tx.wait();
        track("challengeGas", r);
        rec.valueTransfer.bondPaidWei = dec(BigInt(rec.valueTransfer.bondPaidWei) + bond);
      } catch (e) {
        rec.counts.failures += 1;
        rec.error = rec.error || String((e && (e.shortMessage || e.message)) || e).slice(0, 200);
      }
    }
    rec.segments.challengeMs = nowMs() - tCh;
    rec.endpoints.challengedAtUtc = utc();

    // ---- 裁决路径 ----
    const tAdj = nowMs();
    const armId = arm || "direct-fallback";
    const recovery = { armId, faultInjected: false, recoverCalled: false, recoverSucceeded: false, interactiveContinuationSucceeded: false, fallbackUsed: false, firstEffectiveAdvanceMonoNs: null };
    for (const { taskId, input, comp } of tasks) {
      if (armId === "direct-fallback") {
        try {
          const tx = await rollup.connect(challenger).adjudicate(taskId);
          const r = await tx.wait();
          track("adjudicateGas", r);
          recovery.fallbackUsed = true;
          rec.counts.finalizedTasks += 1;
          rec.counts.withdrawableTasks += 1;
        } catch (e) { rec.counts.failures += 1; rec.error = rec.error || String((e && (e.shortMessage || e.message)) || e).slice(0, 200); }
        continue;
      }
      // 交互路径：respond -> advance* -> replay -> settle
      const actor = armId === "recovery-interactive" ? submitter : observer; // 故障臂由第三方续推
      try {
        let r = await (await rollup.connect(submitter).respond(taskId, comp.trace)).wait();
        track("adjudicateGas", r);
      } catch (e) { rec.counts.failures += 1; rec.error = rec.error || String((e && (e.shortMessage || e.message)) || e).slice(0, 200); continue; }

      if (armId !== "recovery-interactive") {
        // 故障注入：提交方离线，推进链上时间越过 timeoutAt（不缩 payload、不改配置）
        recovery.faultInjected = true;
        await increaseTime(11);
        if (armId === "recovery-under-fault") {
          try {
            const rt = await (await rollup.connect(observer).recover(taskId)).wait();
            track("recoverGas", rt);
            recovery.recoverCalled = true;
            recovery.recoverSucceeded = true;
          } catch (e) { recovery.recoverFailedReason = String((e && (e.shortMessage || e.message)) || e).slice(0, 200); }
        } else {
          recovery.recoverCalled = false;
        }
      }

      // 续推：advance*（首次有效推进单独记端点）
      let guard = 0, advOk = true, advErr = null;
      while (guard++ < steps + 5) {
        let phase;
        try { phase = Number((await rollup.getTask(taskId)).phase); } catch (e) { advErr = e; break; }
        if (phase === 5 || phase >= 6 || phase < 3) break; // READY=5, VERIFIED=6, SETTLED=7
        try {
          const r = await (await rollup.connect(actor).advance(taskId)).wait();
          track("adjudicateGas", r);
          if (!recovery.firstEffectiveAdvanceMonoNs) recovery.firstEffectiveAdvanceMonoNs = monoNs();
        } catch (e) { advOk = false; advErr = e; break; }
      }
      if (advOk) {
        recovery.interactiveContinuationSucceeded = true;
        try {
          let r = await (await rollup.connect(actor).replay(taskId)).wait();
          track("adjudicateGas", r);
          r = await (await rollup.connect(actor).settle(taskId)).wait();
          track("adjudicateGas", r);
          recovery.fallbackUsed = false;
          rec.counts.finalizedTasks += 1;
          rec.counts.withdrawableTasks += 1;
        } catch (e) { rec.counts.failures += 1; rec.error = rec.error || String((e && (e.shortMessage || e.message)) || e).slice(0, 200); }
      } else {
        // 交互续推失败 -> 兜底（不关闭兜底伪造"无恢复必失败"）
        recovery.interactiveContinuationFailedReason = String((advErr && (advErr.shortMessage || advErr.message)) || advErr).slice(0, 200);
        try {
          const r = await (await rollup.connect(challenger).adjudicate(taskId)).wait();
          track("adjudicateGas", r);
          recovery.fallbackUsed = true;
          rec.counts.finalizedTasks += 1;
          rec.counts.withdrawableTasks += 1;
        } catch (e) { rec.counts.failures += 1; rec.counts.censored += 1; rec.error = rec.error || String((e && (e.shortMessage || e.message)) || e).slice(0, 200); }
      }
    }
    rec.segments.adjudicateMs = nowMs() - tAdj;
    rec.recovery = recovery;
    rec.endpoints.protocolFinalAtUtc = utc();
    rec.endpoints.protocolFinalMonoNs = monoNs();
    rec.endpoints.withdrawableAtUtc = rec.endpoints.protocolFinalAtUtc;

    // ---- 实际 withdraw ----
    const tW = nowMs();
    for (const who of [submitter, challenger]) {
      try {
        const claimable = await rollup.claimable(who.address);
        if (claimable > 0n) {
          const r = await (await rollup.connect(who).withdraw(who.address)).wait();
          track("withdrawGas", r);
          rec.valueTransfer.withdrawnWei = dec(BigInt(rec.valueTransfer.withdrawnWei) + claimable);
          rec.counts.withdrawnTasks += 1;
        }
      } catch (e) { rec.counts.failures += 1; rec.error = rec.error || String((e && (e.shortMessage || e.message)) || e).slice(0, 200); }
    }
    rec.segments.withdrawMs = nowMs() - tW;
    rec.endpoints.withdrawnAtUtc = utc();
    rec.endpoints.withdrawnMonoNs = monoNs();

    // 价值转移归因（不重复加到费用总额）
    rec.valueTransfer.refundedWei = rec.valueTransfer.withdrawnWei;
    rec.valueTransfer.slashedWei = "0";
    rec.valueTransfer.burnedWei = "0";
    rec.valueTransfer.note = "押金/退款为价值转移，单列；不计入 gas 费用总额";

    rec.segments.totalMs = nowMs() - t0;
    rec.txCount = txCount.n;
    if (timedOut) { rec.counts.censored += 1; rec.status = "censored"; }
    if (rec.counts.failures > 0 && rec.counts.finalizedTasks === 0) rec.status = "fail";
    else if (rec.counts.failures > 0) rec.status = "partial";
    // 吞吐：numerator 不超过该样本 taskCount；分母为本批次本地耗时秒（非共识最终性）
    const secs = rec.segments.totalMs / 1000;
    rec.throughput = {
      executedTasksPerSecond: secs > 0 ? rec.counts.executedTasks / secs : null,
      acceptedTasksPerSecond: secs > 0 ? rec.counts.acceptedTasks / secs : null,
      finalizedTasksPerSecond: secs > 0 ? rec.counts.finalizedTasks / secs : null,
      numeratorTasks: rec.counts.finalizedTasks,
      denominatorSeconds: secs,
      caveat: "分母为本地客户端分段耗时秒数，非共识最终性吞吐；Hardhat automining 不可外推为公网 TPS",
    };
  } catch (e) {
    rec.status = "fail";
    rec.error = String((e && (e.shortMessage || e.message)) || e).slice(0, 300);
    rec.counts.failures += 1;
    rec.segments.totalMs = nowMs() - t0;
  } finally {
    clearTimeout(timer);
  }
  rec.monotonicEndNs = monoNs();
  rec.endedAtUtc = utc();
  return rec;
}

// ---------------- 窗口聚合（独立版本化） ----------------
function buildWindow(ctx, allBatches, measured, { peak, mean, series }, windowStartNs, windowStartMs) {
  const ok = measured.filter((r) => r && !r.fatal && (r.status === "pass" || r.status === "partial"));
  const failed = measured.filter((r) => r && (r.fatal || r.status === "fail"));
  const censored = measured.filter((r) => r && r.counts && r.counts.censored > 0);
  const g = (k) => dec(ok.reduce((a, r) => a + BigInt((r.gas && r.gas[k]) || 0n), 0n));
  const f = (k) => dec(ok.reduce((a, r) => a + BigInt((r.fee && r.fee[k]) || 0n), 0n));
  const meanOf = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null);
  const seg = (k) => ok.map((r) => r.segments && r.segments[k]).filter((v) => typeof v === "number");
  const wallSec = (nowMs() - windowStartMs) / 1000;
  const distinctTasks = ok.reduce((a, r) => a + (r.counts ? r.counts.executedTasks : 0), 0);
  return {
    schemaVersion: WINDOW_SCHEMA,
    runId: ctx.runId,
    windowId: `${ctx.cellId}-r${ctx.runIndex}`,
    cellId: ctx.cellId,
    experimentId: ctx.experimentId,
    runIndex: ctx.runIndex,
    arm: ctx.arm || null,
    createdAtUtc: utc(),
    monotonicStartNs: windowStartNs,
    monotonicEndNs: monoNs(),
    windowWallSeconds: wallSec,
    sampleIds: allBatches.map((r) => (r && r.sampleId) || null),
    input: {
      batchSize: ctx.batchSize, payloadKiBPerTask: ctx.payloadKiB,
      configuredConcurrency: ctx.concurrency, concurrencyUnit: "inflight_batches",
      steps: ctx.steps, warmupBatches: ctx.warmupBatches, measureBatches: ctx.measureBatches,
      strategy: ctx.arm || "direct-fallback",
    },
    counts: {
      batchCount: measured.length,
      warmupBatchCount: allBatches.filter((r) => r && r.warmup).length,
      successfulBatches: ok.length,
      failedBatches: failed.length,
      censoredBatches: censored.length,
      attemptCount: ok.reduce((a, r) => a + (r.counts ? r.counts.attempts : 0), 0),
      retryCount: ok.reduce((a, r) => a + (r.counts ? r.counts.retries : 0), 0),
      txCount: ok.reduce((a, r) => a + (r.txCount || 0), 0),
      distinctTaskCount: distinctTasks,
      executedTasks: ok.reduce((a, r) => a + (r.counts ? r.counts.executedTasks : 0), 0),
      acceptedTasks: ok.reduce((a, r) => a + (r.counts ? r.counts.acceptedTasks : 0), 0),
      finalizedTasks: ok.reduce((a, r) => a + (r.counts ? r.counts.finalizedTasks : 0), 0),
      withdrawableTasks: ok.reduce((a, r) => a + (r.counts ? r.counts.withdrawableTasks : 0), 0),
      withdrawnTasks: ok.reduce((a, r) => a + (r.counts ? r.counts.withdrawnTasks : 0), 0),
      failureCount: ok.reduce((a, r) => a + (r.counts ? r.counts.failures : 0), 0),
    },
    queue: {
      configuredConcurrency: ctx.concurrency,
      observedInflightPeak: peak,
      observedInflightMean: mean,
      inflightSeriesSamples: series.length,
      meanQueueWaitMs: meanOf(allBatches.map((r) => (r && typeof r.queueWaitMs === "number" ? r.queueWaitMs : null)).filter((v) => v !== null)),
      note: "inflight 为批次在途观测（非 Promise 数量）；closed-loop 负载模型",
    },
    gas: {
      submitGas: g("submitGas"), challengeGas: g("challengeGas"),
      adjudicateGas: g("adjudicateGas"), recoverGas: g("recoverGas"), withdrawGas: g("withdrawGas"),
    },
    fee: {
      feeSource: "local-gas-only",
      feeStatus: "local_measured_not_monetary",
      submitFeeWei: f("submitFeeWei"), challengeFeeWei: f("challengeFeeWei"),
      adjudicateFeeWei: f("adjudicateFeeWei"), recoverFeeWei: f("recoverFeeWei"), withdrawFeeWei: f("withdrawFeeWei"),
      totalFeeWei: dec(["submitFeeWei", "challengeFeeWei", "adjudicateFeeWei", "recoverFeeWei", "withdrawFeeWei"]
        .reduce((a, k) => a + BigInt(f(k)), 0n)),
      note: "本地 Hardhat gas×effectiveGasPrice；不是真实公网货币费用，无真实 blobGas 字段",
    },
    valueTransferWei: {
      bondPaid: dec(ok.reduce((a, r) => a + BigInt(r.valueTransfer.bondPaidWei), 0n)),
      withdrawn: dec(ok.reduce((a, r) => a + BigInt(r.valueTransfer.withdrawnWei), 0n)),
      slashed: dec(ok.reduce((a, r) => a + BigInt(r.valueTransfer.slashedWei), 0n)),
      burned: dec(ok.reduce((a, r) => a + BigInt(r.valueTransfer.burnedWei), 0n)),
      note: "价值转移单列，不与 gas 费用总额相加",
    },
    latencyMs: {
      encode: meanOf(seg("encodeMs")), sign: meanOf(seg("signMs")), submit: meanOf(seg("submitMs")),
      challenge: meanOf(seg("challengeMs")), adjudicate: meanOf(seg("adjudicateMs")),
      withdraw: meanOf(seg("withdrawMs")), total: meanOf(seg("totalMs")),
      note: "批级均值；并行阶段不可直接相加，仅报告各段均值",
    },
    recovery: (() => {
      const rs = ok.map((r) => r.recovery).filter(Boolean);
      if (!rs.length) return null;
      return {
        armId: rs[0].armId,
        batches: rs.length,
        faultInjectedBatches: rs.filter((r) => r.faultInjected).length,
        recoverCalledBatches: rs.filter((r) => r.recoverCalled).length,
        recoverSucceededBatches: rs.filter((r) => r.recoverSucceeded).length,
        interactiveContinuationSucceededBatches: rs.filter((r) => r.interactiveContinuationSucceeded).length,
        fallbackUsedBatches: rs.filter((r) => r.fallbackUsed).length,
        note: "recover 交易成功 ≠ 恢复完成；交互续推成功比例与兜底比例分别计数",
      };
    })(),
  };
}

// ---------------- 主流程 ----------------
function buildCells() {
  const cells = [];
  const push = (c, kind, axis) => {
    const key = `b${c.batchSize}-p${c.payloadKiBPerTask}-c${c.configuredConcurrency}-s${c.steps}`;
    if (!cells.some((x) => x.key === key)) cells.push({ key, ...c, kind, axis: axis || null });
  };
  for (const s of SCREENING) {
    for (const v of s.values) push({ ...BASELINE, [s.axis]: v }, "screening", s.axis);
  }
  for (const c of FORCED_CONCURRENCY_CELLS) push(c, "forced", "batchSize=1×concurrency");
  for (const c of CROSS_CELLS) push(c, "cross", c.tag);
  return cells;
}

async function main() {
  const signers = (await ethers.getSigners()).slice(1); // 39 个（accounts count=40）
  const rollup = await (await ethers.getContractFactory("BoundedTaskRollup")).deploy(
    ethers.parseEther("0.001"), CHALLENGE_WINDOW, 10, 2);
  await rollup.waitForDeployment();
  const rollupAddr = await rollup.getAddress();
  const net = await ethers.provider.getNetwork();

  const shared = {
    bond: await rollup.bond(),
    domain: await rollup.DOMAIN(),
    chainId: net.chainId,
    version: Number(await rollup.TASK_VERSION()),
    rollup, rollupAddr, signers,
  };

  const runId = process.env.F_RUN_ID || (SMOKE ? "stageF-smoke" : "stageF-local");
  const batchLog = fs.openSync(path.join(RAW, "batch_records.jsonl"), "w");
  const windowLog = fs.openSync(path.join(RAW, "window_records.jsonl"), "w");
  const write = (fd, obj) => fs.writeSync(fd, JSON.stringify(obj) + "\n");
  fs.writeFileSync(path.join(OUT, "design.frozen.json"), JSON.stringify(DESIGN, null, 2));

  // ---- 超上限拒绝边界（不缩小 payload、不截断） ----
  const boundaryLog = [];
  for (const stepsRej of DESIGN.boundary.stepsReject) {
    const s = signers[0];
    const initial = ethers.keccak256(ethers.toUtf8Bytes("boundary:" + stepsRej));
    const taskId = ethers.keccak256(ethers.toUtf8Bytes("boundary-task:" + stepsRej));
    const comp = jsCompute(initial, Math.max(1, Math.min(stepsRej, 128)));
    const input = {
      taskId, initial, steps: stepsRej, version: shared.version,
      output: comp.output, traceRoot: comp.root,
      dataHash: ethers.keccak256(ethers.toUtf8Bytes("boundary-payload")),
    };
    const digest = jsTaskDigest(shared.domain, shared.chainId, rollupAddr, input);
    const sig = await s.signMessage(ethers.getBytes(digest));
    let rejected = false, reason = null;
    try {
      await rollup.connect(s).submit(input, sig, { value: shared.bond });
    } catch (e) {
      rejected = true;
      reason = String((e && (e.shortMessage || e.message)) || e).slice(0, 200);
    }
    boundaryLog.push({ steps: stepsRej, maxSteps: 128, rejected, reason, expected: "reject" });
    console.log(`[F] boundary steps=${stepsRej}: rejected=${rejected}`);
  }
  fs.writeFileSync(path.join(RAW, "boundary_records.json"), JSON.stringify(boundaryLog, null, 2));

  // ---- 主矩阵 ----
  const cells = buildCells();
  const { warmupBatches, measureBatches, independentRuns } = DESIGN.matrixProtocol;
  for (const cell of cells) {
    if (ONLY_CELLS && !ONLY_CELLS.includes(cell.key)) continue;
    for (let runIndex = 0; runIndex < independentRuns; ++runIndex) {
      const ctx = {
        ...shared, runId, cellId: cell.key, experimentId: "stageF-matrix", runIndex,
        batchSize: cell.batchSize, payloadKiB: cell.payloadKiBPerTask,
        concurrency: cell.configuredConcurrency, steps: cell.steps, arm: null,
        warmupBatches, measureBatches,
      };
      const total = warmupBatches + measureBatches;
      const slotBase = runIndex * 1000 + cells.indexOf(cell) * 100;
      const windowStartMs = nowMs();
      const windowStartNs = monoNs();
      const { results, peak, mean, series } = await runPool(total, cell.configuredConcurrency, (i, qw) =>
        runBatch({ ...ctx, warmup: i < warmupBatches }, {
          batchIndex: i, signerSlot: slotBase + i * 2, queueWaitMs: qw,
        }), windowStartMs);
      for (const r of results) write(batchLog, r);
      const measured = results.filter((_, i) => i >= warmupBatches);
      const win = buildWindow(ctx, results, measured, { peak, mean, series }, windowStartNs, windowStartMs);
      win.kind = cell.kind; win.axis = cell.axis;
      write(windowLog, win);
      console.log(`[F] ${cell.key} r${runIndex}: batches=${measured.length} peak=${peak} mean=${mean.toFixed(2)} finalized=${win.counts.finalizedTasks} totalFeeWei=${win.fee.totalFeeWei}`);
    }
  }

  // ---- 消融（四类策略，不关闭兜底伪造优势） ----
  const ap = DESIGN.ablation.protocol;
  for (const arm of DESIGN.ablation.arms) {
    for (let runIndex = 0; runIndex < ap.independentRuns; ++runIndex) {
      const w = DESIGN.ablation.workload;
      const ctx = {
        ...shared, runId, cellId: `ablation-${arm.id}`, experimentId: "stageF-ablation", runIndex,
        batchSize: w.batchSize, payloadKiB: w.payloadKiBPerTask,
        concurrency: w.configuredConcurrency, steps: w.steps, arm: arm.id,
        warmupBatches: ap.warmupBatches, measureBatches: ap.measureBatches,
      };
      const total = ap.warmupBatches + ap.measureBatches;
      const slotBase = runIndex * 1000 + 500;
      const windowStartMs = nowMs();
      const windowStartNs = monoNs();
      const { results, peak, mean, series } = await runPool(total, 1, (i, qw) =>
        runBatch({ ...ctx, warmup: i < ap.warmupBatches }, {
          batchIndex: i, signerSlot: slotBase + i * 2, queueWaitMs: qw,
        }), windowStartMs);
      for (const r of results) write(batchLog, r);
      const measured = results.filter((_, i) => i >= ap.warmupBatches);
      write(windowLog, buildWindow(ctx, results, measured, { peak, mean, series }, windowStartNs, windowStartMs));
      console.log(`[F] ablation ${arm.id} r${runIndex}: batches=${measured.length}`);
    }
  }

  fs.closeSync(batchLog);
  fs.closeSync(windowLog);
  console.log(`[F] 完成，raw: ${RAW}`);
}

main().catch((e) => { console.error(e); process.exitCode = 1; });
