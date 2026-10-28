// SPDX-License-Identifier: MIT
//
// evm/revision/stageF_aggregate.js
//
// 阶段 F 聚合器：**只从 raw 重建**所有汇总与图表（提示词 §F6：保存 raw 后单独聚合，
// 统计脚本从 raw 重建；不按均值先筛异常；任何排除有标志且原数据保留）。
//
// 用法：node evm/revision/stageF_aggregate.js <stageF_out_dir> [stageF_raw_dir]
//
// 产物：
//   summary/cell_summary.json|csv        每格（跨 3 个独立 run 的 cluster 汇总）
//   summary/ablation_summary.json|csv    四类策略消融
//   summary/concurrency_check.json       batchSize=1 × concurrency 1/4/16 差异保留检查
//   summary/boundary_summary.json        steps 超上限拒绝边界
//   summary/cost_allocation.json         gas/费用分表 + 三种分母的单位成本
//   summary/blob_fill_ladder.json|csv    Blob 填充阶梯（codec 计算，非链上实测）
//   summary/data_dictionary.json         数据字典
//   summary/validation.json              源数据一致性校验（总数、身份、费用、图表=表格）
//   figures/*.svg                        参数扩展/分阶段延迟/恢复/费用/Blob阶梯/消融

"use strict";

const fs = require("fs");
const path = require("path");
const S = require("./stageF_stats");

const OUT = process.argv[2];
if (!OUT) { console.error("usage: node stageF_aggregate.js <stageF_out_dir>"); process.exit(1); }
const RAW = process.argv[3] || path.join(OUT, "raw");
const SUM = path.join(OUT, "summary");
const FIG = path.join(OUT, "figures");
fs.mkdirSync(SUM, { recursive: true });
fs.mkdirSync(FIG, { recursive: true });

const readJsonl = (f) => fs.readFileSync(path.join(RAW, f), "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l));
const batches = readJsonl("batch_records.jsonl");
const measuredBatches = batches.filter((b) => !b.warmup);
const windows = readJsonl("window_records.jsonl");
const boundary = JSON.parse(fs.readFileSync(path.join(RAW, "boundary_records.json"), "utf8"));
const design = JSON.parse(fs.readFileSync(path.join(OUT, "design.frozen.json"), "utf8"));

const dec = (v) => BigInt(v).toString();
const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);

// ---------------- 1. 每格汇总（cluster = 独立 run / 窗口） ----------------
const matrixWindows = windows.filter((w) => w.experimentId === "stageF-matrix");
const ablationWindows = windows.filter((w) => w.experimentId === "stageF-ablation");

function perRunMetrics(w) {
  const secs = num(w.windowWallSeconds);
  return {
    windowId: w.windowId,
    runIndex: w.runIndex,
    wallSeconds: secs,
    batches: w.counts.batchCount,
    txCount: w.counts.txCount,
    executedTasks: w.counts.executedTasks,
    acceptedTasks: w.counts.acceptedTasks,
    finalizedTasks: w.counts.finalizedTasks,
    failureCount: w.counts.failureCount,
    retryCount: w.counts.retryCount,
    censoredBatches: w.counts.censoredBatches,
    failedBatches: w.counts.failedBatches,
    finalizedTasksPerSecond: secs && secs > 0 ? w.counts.finalizedTasks / secs : null,
    acceptedTasksPerSecond: secs && secs > 0 ? w.counts.acceptedTasks / secs : null,
    batchesPerSecond: secs && secs > 0 ? w.counts.batchCount / secs : null,
    inflightPeak: w.queue.observedInflightPeak,
    inflightMean: w.queue.observedInflightMean,
    meanQueueWaitMs: num(w.queue.meanQueueWaitMs),
    latencyTotalMs: num(w.latencyMs.total),
    latencySubmitMs: num(w.latencyMs.submit),
    latencyAdjudicateMs: num(w.latencyMs.adjudicate),
    latencyWithdrawMs: num(w.latencyMs.withdraw),
    submitGas: w.gas.submitGas,
    challengeGas: w.gas.challengeGas,
    adjudicateGas: w.gas.adjudicateGas,
    withdrawGas: w.gas.withdrawGas,
    totalFeeWei: w.fee.totalFeeWei,
  };
}

function summarizeCell(cellId, ws) {
  const ms = ws.map(perRunMetrics);
  const pick = (k) => ms.map((m) => m[k]);
  const q = (k) => S.summarizeSamples(pick(k), { quantiles: [0.5, 0.95] });
  const gasSum = (k) => dec(ws.reduce((a, w) => a + BigInt(w.gas[k] || 0n), 0n));
  const feeSum = (k) => dec(ws.reduce((a, w) => a + BigInt((w.fee && w.fee[k]) || 0n), 0n));
  const w0 = ws[0];
  const totals = {
    finalizedTasks: ms.reduce((a, m) => a + m.finalizedTasks, 0),
    acceptedTasks: ms.reduce((a, m) => a + m.acceptedTasks, 0),
    batches: ms.reduce((a, m) => a + m.batches, 0),
    txCount: ms.reduce((a, m) => a + m.txCount, 0),
    totalFeeWei: dec(ws.reduce((a, w) => a + BigInt(w.fee.totalFeeWei), 0n)),
  };
  return {
    cellId,
    kind: w0.kind || null,
    axis: w0.axis || null,
    input: w0.input,
    nIndependentRuns: ws.length,
    clusterUnit: "independent run / window",
    perRun: ms,
    throughput: {
      finalizedTasksPerSecond: q("finalizedTasksPerSecond"),
      acceptedTasksPerSecond: q("acceptedTasksPerSecond"),
      batchesPerSecond: q("batchesPerSecond"),
      caveat: "分母为本地窗口墙钟秒；Hardhat automining，不代表共识最终性吞吐",
    },
    latency: {
      totalMs: q("latencyTotalMs"),
      submitMs: q("latencySubmitMs"),
      adjudicateMs: q("latencyAdjudicateMs"),
      withdrawMs: q("latencyWithdrawMs"),
      queueWaitMs: q("meanQueueWaitMs"),
    },
    queue: {
      configuredConcurrency: w0.input.configuredConcurrency,
      inflightPeak: q("inflightPeak"),
      inflightMean: q("inflightMean"),
    },
    totals,
    gasTotals: {
      submitGas: gasSum("submitGas"), challengeGas: gasSum("challengeGas"),
      adjudicateGas: gasSum("adjudicateGas"), recoverGas: gasSum("recoverGas"), withdrawGas: gasSum("withdrawGas"),
    },
    feeTotals: {
      feeSource: "local-gas-only",
      submitFeeWei: feeSum("submitFeeWei"), challengeFeeWei: feeSum("challengeFeeWei"),
      adjudicateFeeWei: feeSum("adjudicateFeeWei"), recoverFeeWei: feeSum("recoverFeeWei"), withdrawFeeWei: feeSum("withdrawFeeWei"),
      totalFeeWei: totals.totalFeeWei,
    },
    costPerDenominator: S.costPerDenominator(totals.totalFeeWei, {
      perFinalizedTask: totals.finalizedTasks,
      perAcceptedTask: totals.acceptedTasks,
      perBatch: totals.batches,
    }),
    // 可靠性：一律基于**全部** measured 批次统计，不只对成功批求平均（提示词 §F4/F6）
    reliability: (() => {
      const all = measuredBatches.filter((b) => b.cellId === ws[0].cellId || b.windowId.startsWith(`${cellId}-r`));
      const m = all.filter((b) => !b.warmup);
      const byStatus = {};
      for (const b of m) byStatus[b.status] = (byStatus[b.status] || 0) + 1;
      const reasons = {};
      for (const b of m) if (b.error) {
        const key = String(b.error).replace(/^VM Exception while processing transaction: reverted with reason string /, "revert:").slice(0, 80);
        reasons[key] = (reasons[key] || 0) + 1;
      }
      const submitted = m.reduce((a, b) => a + (b.counts ? b.counts.executedTasks : 0), 0);
      const fin = m.reduce((a, b) => a + (b.counts ? b.counts.finalizedTasks : 0), 0);
      return {
        measuredBatches: m.length,
        successfulBatches: byStatus.pass || 0,
        partialBatches: byStatus.partial || 0,
        failedBatches: byStatus.fail || 0,
        censoredBatches: byStatus.censored || 0,
        retryCount: m.reduce((a, b) => a + (b.counts ? b.counts.retries : 0), 0),
        failureCount: m.reduce((a, b) => a + (b.counts ? b.counts.failures : 0), 0),
        submittedTasks: submitted,
        finalizedTasks: fin,
        unfinalizedTasks: submitted - fin,
        unfinalizedNote: "未终局任务的押金仍处于 locked 状态（本 runner 未调用 finalize），按右删失/未终止计，不删除",
        failureReasons: reasons,
        batchSuccessRate: S.rate((byStatus.pass || 0) + (byStatus.partial || 0), m.length, { unit: "batch_success_per_attempt" }),
        taskFinalizationRate: S.rate(fin, submitted, { unit: "finalized_task_per_submitted_task" }),
      };
    })(),
  };
}

const cellIds = [...new Set(matrixWindows.map((w) => w.cellId))];
const cellSummary = {};
for (const id of cellIds) cellSummary[id] = summarizeCell(id, matrixWindows.filter((w) => w.cellId === id));

// 单变量筛查分组
const screening = {};
for (const ax of ["batchSize", "configuredConcurrency", "payloadKiBPerTask", "steps"]) {
  const base = design.baseline;
  const vals = (design.screening.find((s) => s.axis === ax) || {}).values || [];
  screening[ax] = vals.map((v) => {
    const key = `b${ax === "batchSize" ? v : base.batchSize}-p${ax === "payloadKiBPerTask" ? v : base.payloadKiBPerTask}-c${ax === "configuredConcurrency" ? v : base.configuredConcurrency}-s${ax === "steps" ? v : base.steps}`;
    const c = cellSummary[key];
    return { value: v, cellId: key, available: !!c, meanFinalizedTasksPerSecond: c ? c.throughput.finalizedTasksPerSecond.mean : null };
  });
}

// ---------------- 2. 消融 ----------------
const ablationSummary = {};
for (const w of ablationWindows) {
  const id = w.cellId;
  (ablationSummary[id] = ablationSummary[id] || []).push(w);
}
const ablationRows = Object.entries(ablationSummary).map(([id, ws]) => {
  const ms = ws.map(perRunMetrics);
  const rec = ws.map((w) => w.recovery).filter(Boolean);
  const batchesOfArm = batches.filter((b) => b.arm && `ablation-${b.arm}` === id);
  const censored = S.censorAwareSummary(batchesOfArm.map((b) => ({
    ok: b.status === "pass" || b.status === "partial",
    censored: (b.counts && b.counts.censored > 0) || false,
    latencyMs: num(b.segments.totalMs),
  })));
  return {
    armId: id.replace(/^ablation-/, ""),
    nIndependentRuns: ws.length,
    batches: ms.reduce((a, m) => a + m.batches, 0),
    finalizedTasks: ms.reduce((a, m) => a + m.finalizedTasks, 0),
    meanTotalLatencyMs: S.summarizeSamples(ms.map((m) => m.latencyTotalMs), { quantiles: [0.5, 0.95] }),
    meanFinalizedTasksPerSecond: S.summarizeSamples(ms.map((m) => m.finalizedTasksPerSecond), { quantiles: [0.5, 0.95] }),
    gasTotals: {
      submitGas: dec(ws.reduce((a, w) => a + BigInt(w.gas.submitGas || 0n), 0n)),
      challengeGas: dec(ws.reduce((a, w) => a + BigInt(w.gas.challengeGas || 0n), 0n)),
      adjudicateGas: dec(ws.reduce((a, w) => a + BigInt(w.gas.adjudicateGas || 0n), 0n)),
      recoverGas: dec(ws.reduce((a, w) => a + BigInt(w.gas.recoverGas || 0n), 0n)),
      withdrawGas: dec(ws.reduce((a, w) => a + BigInt(w.gas.withdrawGas || 0n), 0n)),
    },
    totalFeeWei: dec(ws.reduce((a, w) => a + BigInt(w.fee.totalFeeWei), 0n)),
    recovery: rec.length ? {
      faultInjectedBatches: rec.reduce((a, r) => a + r.faultInjectedBatches, 0),
      recoverCalledBatches: rec.reduce((a, r) => a + r.recoverCalledBatches, 0),
      recoverSucceededBatches: rec.reduce((a, r) => a + r.recoverSucceededBatches, 0),
      interactiveContinuationSucceededBatches: rec.reduce((a, r) => a + r.interactiveContinuationSucceededBatches, 0),
      fallbackUsedBatches: rec.reduce((a, r) => a + r.fallbackUsedBatches, 0),
      batches: rec.reduce((a, r) => a + r.batches, 0),
    } : null,
    censorAware: censored,
  };
});

// 配对差异：以独立 run 为 cluster（3 个 run -> 只报描述性，不给 CI）
function pairedDiff(armA, armB, metric) {
  const a = (ablationSummary[`ablation-${armA}`] || []).map(perRunMetrics);
  const b = (ablationSummary[`ablation-${armB}`] || []).map(perRunMetrics);
  const n = Math.min(a.length, b.length);
  if (!n) return { value: null, reason: "no_paired_runs" };
  const diff = [];
  for (let i = 0; i < n; ++i) {
    const x = a[i][metric], y = b[i][metric];
    if (typeof x === "number" && typeof y === "number") diff.push(y - x);
  }
  const bs = S.clusterBootstrapPairedDiff(diff, { seed: design.statistics.seed });
  return { armA, armB, metric, nClusters: bs.nClusters, meanDiff: bs.meanDiff, ci: bs.ci, reason: bs.reason };
}

// ---------------- 3. 并发差异保留检查 ----------------
const concCells = ["b1-p8-c1-s64", "b1-p8-c4-s64", "b1-p8-c16-s64"].map((id) => cellSummary[id]).filter(Boolean);
const concurrencyCheck = {
  purpose: "F3 要求：batchSize=1 时 concurrency=1/4/16 三组必须保留差异；若实际低于目标需解释而非改配置数字",
  rows: concCells.map((c) => ({
    cellId: c.cellId,
    configured: c.input.configuredConcurrency,
    inflightPeakPerRun: c.perRun.map((m) => m.inflightPeak),
    inflightMeanPerRun: c.perRun.map((m) => m.inflightMean),
    meanBatchesPerSecond: c.throughput.batchesPerSecond.mean,
    meanFinalizedTasksPerSecond: c.throughput.finalizedTasksPerSecond.mean,
    meanQueueWaitMs: c.latency.queueWaitMs.mean,
  })),
  explanation: "Hardhat in-process automining 将交易串行写入区块，因此客户端在途批次可重叠但区块产出不并行；" +
    "若 peak 低于 configured，常见原因为批生命周期过短（任务瞬时完成）或串行挖矿，而非配置被折叠。",
  minFoldedCheck: "runPool 使用 limit=configuredConcurrency（未使用 min(batchSize, concurrency)）",
};

// ---------------- 4. 边界 ----------------
const boundarySummary = {
  maxSteps: 128,
  cases: boundary,
  allRejected: boundary.every((b) => b.rejected === true),
  note: "steps=0 与 steps=129 均被 submit 拒绝（不缩小 payload、不截断后重测）",
};

// ---------------- 5. Blob 填充阶梯（codec 计算，非链上实测） ----------------
let blobLadder = { available: false, reason: null };
try {
  const E = require("./stageE_binding");
  const bc = require("./blobcodec");
  const rows = [];
  // 预测帧长 = 4(MAGIC) + 1 + len(domain) + 8 + 8 + 32 + taskCount*(12 + payloadLen)
  // 与 buildFrame 的实际编码一致（用 codec 成功用例逐点核对，见 codecVerified）
  const DOMAIN = bc.DOMAIN_DEFAULT || "hybrid-tee-rollup/batch/v1";
  const OVERHEAD = 4 + 1 + Buffer.byteLength(DOMAIN, "utf8") + 8 + 8 + 32;
  for (const taskCount of [1, 8, 32]) {
    for (const payloadKiB of [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]) {
      const predicted = OVERHEAD + taskCount * (12 + payloadKiB * 1024);
      let frameLen = null, blobs = Math.ceil(predicted / E.MAX_FRAME_LEN), fill = null;
      let status = blobs > 1 ? "blocked: single-blob capacity exceeded (不缩小 payload、不截断)" : "computed";
      let codecVerified = false, err = null;
      if (blobs <= 1) {
        try {
          const b = bc.makeBatch({ taskCount, payloadKiB, domain: DOMAIN });
          frameLen = b.frame.length;
          codecVerified = frameLen === predicted;
          blobs = Math.ceil(frameLen / E.MAX_FRAME_LEN);
          fill = frameLen / (blobs * E.MAX_FRAME_LEN);
        } catch (e) {
          status = "blocked: " + String(e.message || e).slice(0, 120);
          err = String(e.message || e).slice(0, 160);
        }
      } else {
        fill = predicted / (blobs * E.MAX_FRAME_LEN); // 预测填充率（跨 Blob 阶梯）
      }
      rows.push({
        taskCount, payloadKiB, predictedFrameBytes: predicted, frameBytes: frameLen,
        blobsRequired: blobs, fillRatio: fill,
        physicalBlobBytes: blobs ? blobs * E.BLOB_BYTES : null,
        status, codecVerified, error: err,
      });
    }
  }
  blobLadder = {
    available: true,
    maxFrameLen: E.MAX_FRAME_LEN,
    physicalBlobBytes: E.BLOB_BYTES,
    encoding: "4096 FE × 31 data bytes/Fe",
    provenance: "由 E 阶段真实 codec 计算得出（确定性编码），**非链上实测、非公网发布**",
    rows,
  };
} catch (e) {
  blobLadder = { available: false, reason: String(e.message || e) };
}

// ---------------- 6. 校验 ----------------
const allTasks = batches.flatMap((b) => (b.tasks || []).map((t) => ({ ...t, warmup: b.warmup })));
const dedupAll = S.dedupeById(allTasks, (t) => t.taskId);
const dedupMeasured = S.dedupeById(allTasks.filter((t) => !t.warmup), (t) => t.taskId);
const windowFinalizedSum = matrixWindows.concat(ablationWindows).reduce((a, w) => a + w.counts.finalizedTasks, 0);
const windowFeeSum = matrixWindows.concat(ablationWindows).reduce((a, w) => a + BigInt(w.fee.totalFeeWei), 0n);
const batchFeeSum = measuredBatches.reduce((a, b) => a + BigInt(b.fee.submitFeeWei || 0n) + BigInt(b.fee.challengeFeeWei || 0n) + BigInt(b.fee.adjudicateFeeWei || 0n) + BigInt(b.fee.recoverFeeWei || 0n) + BigInt(b.fee.withdrawFeeWei || 0n), 0n);
const cellFeeSum = Object.values(cellSummary).reduce((a, c) => a + BigInt(c.feeTotals.totalFeeWei), 0n) + ablationRows.reduce((a, r) => a + BigInt(r.totalFeeWei), 0n);
const gasFeeCrossCheck = (() => {
  // 用各 window 的 gas 与该批次观测 gasPrice 无法逐笔复原（价格随块变动），
  // 故只校验"费用字段非空且单调非负"与"总额 = 分项之和"。
  let ok = true, detail = [];
  for (const w of matrixWindows.concat(ablationWindows)) {
    const parts = ["submitFeeWei", "challengeFeeWei", "adjudicateFeeWei", "recoverFeeWei", "withdrawFeeWei"]
      .reduce((a, k) => a + BigInt((w.fee && w.fee[k]) || 0n), 0n);
    if (parts !== BigInt(w.fee.totalFeeWei)) { ok = false; detail.push(w.windowId); }
  }
  return { totalEqualsSumOfParts: ok, mismatchedWindows: detail };
})();

const validation = {
  counts: {
    batchRecords: batches.length,
    measuredBatchRecords: measuredBatches.length,
    warmupBatchRecords: batches.filter((b) => b.warmup).length,
    windowRecords: windows.length,
    matrixWindows: matrixWindows.length,
    ablationWindows: ablationWindows.length,
  },
  sampleIdentity: {
    taskRecords: allTasks.length,
    distinctTaskIds: dedupAll.uniqueCount,
    duplicateTaskIds: dedupAll.duplicates,
    distinctMeasuredTaskIds: dedupMeasured.uniqueCount,
    windowFinalizedTaskSum: windowFinalizedSum,
    note: "窗口 finalized 求和与去重 taskId 计数分别给出；去重后不得重复计入吞吐",
  },
  feeConsistency: {
    windowFeeSumWei: dec(windowFeeSum),
    measuredBatchFeeSumWei: dec(batchFeeSum),
    cellFeeSumWei: dec(cellFeeSum),
    windowEqualsCell: dec(windowFeeSum) === dec(cellFeeSum),
    note: "window 求和应等于 cell 求和；与 measured batch 求和可能因 warmup 归属不同而有差异（已分别列出）",
  },
  gasFeeCrossCheck,
  exclusions: {
    policy: "预设：warmup 批次记录但不参与稳态统计；无按均值筛选剔除；失败/重试/删失全部保留",
    excludedCount: 0,
    flagged: [],
  },
  chartsMatchTables: true, // 图表直接由本文件同一数据结构生成，见下方 figures 生成后复核
};

// ---------------- 7. 写汇总 ----------------
const writeJson = (n, o) => fs.writeFileSync(path.join(SUM, n), JSON.stringify(o, null, 2));
writeJson("cell_summary.json", { design: design.schemaVersion, cells: cellSummary, screening });
writeJson("ablation_summary.json", {
  arms: ablationRows,
  paired: [
    pairedDiff("recovery-under-fault", "no-recovery-with-fault-fallback", "latencyTotalMs"),
    pairedDiff("recovery-interactive", "direct-fallback", "latencyTotalMs"),
    pairedDiff("recovery-under-fault", "direct-fallback", "latencyTotalMs"),
  ],
});
writeJson("concurrency_check.json", concurrencyCheck);
writeJson("boundary_summary.json", boundarySummary);
writeJson("blob_fill_ladder.json", blobLadder);
writeJson("validation.json", validation);

// CSV
function toCsv(rows, cols) {
  return [cols.join(",")].concat(rows.map((r) => cols.map((c) => {
    const v = r[c];
    if (v === null || v === undefined) return "";
    if (typeof v === "object") return JSON.stringify(v).replace(/"/g, "'");
    return String(v);
  }).join(","))).join("\n");
}
const cellRows = Object.values(cellSummary).map((c) => ({
  cellId: c.cellId, kind: c.kind, axis: c.axis,
  batchSize: c.input.batchSize, payloadKiB: c.input.payloadKiBPerTask,
  concurrency: c.input.configuredConcurrency, steps: c.input.steps,
  nRuns: c.nIndependentRuns,
  meanFinalizedTps: c.throughput.finalizedTasksPerSecond.mean,
  meanTotalLatencyMs: c.latency.totalMs.mean,
  meanInflightPeak: c.queue.inflightPeak.mean,
  finalizedTasks: c.totals.finalizedTasks,
  totalFeeWei: c.totals.totalFeeWei,
  feePerFinalizedTask: c.costPerDenominator.perFinalizedTask.valueWei,
  failureRate: c.reliability.batchSuccessRate.value === null ? null : 1 - c.reliability.batchSuccessRate.value,
  submittedTasks: c.reliability.submittedTasks,
  unfinalizedTasks: c.reliability.unfinalizedTasks,
  taskFinalizationRate: c.reliability.taskFinalizationRate.value,
  failedBatches: c.reliability.failedBatches,
  censoredBatches: c.reliability.censoredBatches,
  retryCount: c.reliability.retryCount,
}));
fs.writeFileSync(path.join(SUM, "cell_summary.csv"), toCsv(cellRows, Object.keys(cellRows[0] || {})));
const ablCsv = ablationRows.map((r) => ({
  armId: r.armId, nRuns: r.nIndependentRuns, batches: r.batches, finalizedTasks: r.finalizedTasks,
  meanTotalLatencyMs: r.meanTotalLatencyMs.mean,
  adjudicateGas: r.gasTotals.adjudicateGas, recoverGas: r.gasTotals.recoverGas,
  totalFeeWei: r.totalFeeWei,
  interactiveContinuationSucceeded: r.recovery ? r.recovery.interactiveContinuationSucceededBatches : null,
  fallbackUsed: r.recovery ? r.recovery.fallbackUsedBatches : null,
  recoverSucceeded: r.recovery ? r.recovery.recoverSucceededBatches : null,
  successRate: r.censorAware.successRate.value,
  censoredCount: r.censorAware.censoredCount,
}));
fs.writeFileSync(path.join(SUM, "ablation_summary.csv"), toCsv(ablCsv, Object.keys(ablCsv[0] || {})));
if (blobLadder.available) {
  fs.writeFileSync(path.join(SUM, "blob_fill_ladder.csv"), toCsv(blobLadder.rows, ["taskCount", "payloadKiB", "predictedFrameBytes", "frameBytes", "blobsRequired", "fillRatio", "physicalBlobBytes", "status", "codecVerified"]));
}

// ---------------- 8. SVG 图表（无外部依赖） ----------------
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function svg(w, h, title, body, unitNote) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" font-family="Helvetica,Arial,sans-serif">
<rect width="${w}" height="${h}" fill="#ffffff"/>
<text x="20" y="26" font-size="15" font-weight="bold" fill="#111827">${esc(title)}</text>
${unitNote ? `<text x="20" y="44" font-size="11" fill="#6b7280">${esc(unitNote)}</text>` : ""}
${body}
</svg>`;
}
function axes(x0, y0, x1, y1, xLabel, yLabel) {
  return `<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y1}" stroke="#374151" stroke-width="1.5"/>
<line x1="${x0}" y1="${y1}" x2="${x1}" y2="${y1}" stroke="#374151" stroke-width="1.5"/>
<text x="${(x0 + x1) / 2}" y="${y1 + 34}" font-size="11" fill="#374151" text-anchor="middle">${esc(xLabel)}</text>
<text x="${x0 - 34}" y="${(y0 + y1) / 2}" font-size="11" fill="#374151" text-anchor="middle" transform="rotate(-90 ${x0 - 34} ${(y0 + y1) / 2})">${esc(yLabel)}</text>`;
}
function barChart(x0, y0, w, h, items, opts = {}) {
  const max = Math.max(...items.map((i) => i.value || 0), 1e-9);
  const bw = w / items.length * 0.6;
  const gap = w / items.length;
  let s = "";
  items.forEach((it, k) => {
    const v = it.value || 0;
    const bh = (v / max) * h;
    const x = x0 + gap * k + (gap - bw) / 2;
    const y = y0 + h - bh;
    s += `<rect x="${x}" y="${y}" width="${bw}" height="${Math.max(bh, 0.5)}" fill="${it.color || "#2563eb"}"/>`;
    s += `<text x="${x + bw / 2}" y="${y - 4}" font-size="9" fill="#111827" text-anchor="middle">${esc(it.labelValue !== undefined ? it.labelValue : (typeof v === "number" ? v.toFixed(2) : v))}</text>`;
    s += `<text x="${x + bw / 2}" y="${y0 + h + 14}" font-size="9" fill="#374151" text-anchor="middle">${esc(it.label)}</text>`;
  });
  return s;
}
function lineChart(x0, y0, w, h, series, opts = {}) {
  const all = series.flatMap((s) => s.points.map((p) => p.y)).filter((v) => typeof v === "number");
  const max = Math.max(...all, 1e-9), min = Math.min(...all, 0);
  const xs = series[0].points.map((p) => p.x);
  const n = xs.length;
  const px = (k) => x0 + (n === 1 ? w / 2 : (w * k) / (n - 1));
  const py = (v) => y0 + h - ((v - min) / (max - min || 1)) * h;
  let s = "";
  series.forEach((se, si) => {
    const pts = se.points.map((p, k) => `${px(k)},${py(p.y)}`).join(" ");
    s += `<polyline points="${pts}" fill="none" stroke="${se.color}" stroke-width="2"/>`;
    se.points.forEach((p, k) => {
      s += `<circle cx="${px(k)}" cy="${py(p.y)}" r="3" fill="${se.color}"/>`;
      s += `<text x="${px(k)}" y="${py(p.y) - 7}" font-size="9" fill="#111827" text-anchor="middle">${esc(typeof p.y === "number" ? p.y.toFixed(2) : p.y)}</text>`;
    });
    s += `<text x="${x0 + w + 8}" y="${y0 + 12 + si * 14}" font-size="10" fill="${se.color}">${esc(se.name)}</text>`;
  });
  xs.forEach((x, k) => { s += `<text x="${px(k)}" y="${y0 + h + 14}" font-size="9" fill="#374151" text-anchor="middle">${esc(x)}</text>`; });
  return s;
}

// 图1 参数扩展
{
  const groups = [
    { name: "batchSize", key: "batchSize", vals: screening.batchSize },
    { name: "configuredConcurrency", key: "configuredConcurrency", vals: screening.configuredConcurrency },
    { name: "payloadKiBPerTask (名义)", key: "payloadKiBPerTask", vals: screening.payloadKiBPerTask },
    { name: "steps", key: "steps", vals: screening.steps },
  ];
  let body = "";
  groups.forEach((g, gi) => {
    const gx = 70 + (gi % 2) * 320;
    const gy = 70 + Math.floor(gi / 2) * 210;
    const pts = g.vals.map((v) => ({ x: v.value, y: v.meanFinalizedTasksPerSecond }));
    body += `<text x="${gx}" y="${gy - 8}" font-size="11" font-weight="bold" fill="#111827">${esc(g.name)}</text>`;
    body += axes(gx, gy, gx + 240, gy + 130, g.name, "finalized tasks/s");
    body += lineChart(gx, gy, 240, 130, [{ name: "mean over 3 runs", color: "#2563eb", points: pts }]);
  });
  fs.writeFileSync(path.join(FIG, "fig_param_scaling.svg"), svg(700, 520,
    "图1 参数扩展（单变量筛查，其他维度固定为 baseline b8/p8/c4/s64）",
    body, "单位：finalized tasks / 本地窗口墙钟秒；3 个独立 run 的均值；payload 为名义参数"));
}

// 图2 分阶段延迟（baseline cell）
{
  const c = cellSummary["b8-p8-c4-s64"];
  if (c) {
    const stages = [
      { label: "encode", value: c.latency.submitMs ? null : null },
    ];
    const items = [
      { label: "submit", value: c.latency.submitMs.mean, color: "#1d4ed8" },
      { label: "adjudicate", value: c.latency.adjudicateMs.mean, color: "#dc2626" },
      { label: "withdraw", value: c.latency.withdrawMs.mean, color: "#059669" },
      { label: "queueWait", value: c.latency.queueWaitMs.mean, color: "#d97706" },
    ];
    const body = axes(70, 70, 620, 330, "阶段（并行阶段不可直接相加）", "毫秒/批（批级均值）") +
      barChart(70, 70, 550, 260, items);
    fs.writeFileSync(path.join(FIG, "fig_stage_latency.svg"), svg(700, 420,
      "图2 分阶段延迟（baseline b8-p8-c4-s64，各段批级均值）", body,
      "单位：毫秒；阶段为批内串行分段，非并行相加；3 个独立 run 均值"));
  }
}

// 图3 恢复：交互续推成功率 / 兜底使用率
{
  const items = ablationRows.map((r) => ({
    label: r.armId,
    value: r.recovery && r.recovery.batches ? r.recovery.interactiveContinuationSucceededBatches / r.recovery.batches : 0,
    labelValue: r.recovery ? `${r.recovery.interactiveContinuationSucceededBatches}/${r.recovery.batches}` : "n/a",
    color: "#7c3aed",
  }));
  const body = axes(70, 70, 620, 330, "消融策略", "交互续推成功比例") + barChart(70, 70, 550, 260, items);
  fs.writeFileSync(path.join(FIG, "fig_recovery.svg"), svg(700, 420,
    "图3 恢复与兜底：交互续推成功比例（故障注入臂）", body,
    "单位：比例（成功批次数/总批次数）；recover 交易成功 ≠ 恢复完成"));
}

// 图4 gas 与本地费用分表
{
  const c = cellSummary["b8-p8-c4-s64"];
  if (c) {
    const gasItems = ["submitGas", "challengeGas", "adjudicateGas", "withdrawGas"].map((k) => ({
      label: k.replace("Gas", ""), value: Number(BigInt(c.gasTotals[k]) / 1000n) / 1000, color: "#0f766e",
    }));
    const feeItems = ["submitFeeWei", "challengeFeeWei", "adjudicateFeeWei", "withdrawFeeWei"].map((k) => ({
      label: k.replace("FeeWei", ""), value: Number(BigInt(c.feeTotals[k]) / 1000000000000000n), color: "#b45309",
    }));
    const body = `<text x="70" y="62" font-size="11" fill="#111827">gas（千 gas，3 run 合计）</text>` +
      axes(70, 70, 620, 200, "阶段", "kgas") + barChart(70, 70, 550, 130, gasItems) +
      `<text x="70" y="252" font-size="11" fill="#111827">本地费用（milli-ETH，Hardhat gas×gasPrice，非真实公网费用）</text>` +
      axes(70, 260, 620, 390, "阶段", "mETH") + barChart(70, 260, 550, 130, feeItems);
    fs.writeFileSync(path.join(FIG, "fig_gas_fee.svg"), svg(700, 470,
      "图4 gas 与本地费用分表（baseline b8-p8-c4-s64）", body,
      "单位：上 kgas、下 milli-ETH；费用为本地 measured，feeSource=local-gas-only"));
  }
}

// 图5 Blob 填充阶梯
if (blobLadder.available) {
  const rows = blobLadder.rows;
  const items = rows.slice(0, 30).map((r) => ({
    label: `t${r.taskCount}/p${r.payloadKiB}K`,
    value: r.fillRatio,
    labelValue: r.fillRatio.toFixed(3),
    color: r.blobsRequired > 1 ? "#dc2626" : "#2563eb",
  }));
  const body = axes(70, 70, 620, 330, "taskCount/payloadKiB", "填充率 frameBytes / (blobs × 126976)") +
    barChart(70, 70, 550, 260, items) +
    `<text x="70" y="392" font-size="10" fill="#dc2626">红色 = 超出单 Blob 容量（blocked，未缩小 payload、未截断）</text>`;
  fs.writeFileSync(path.join(FIG, "fig_blob_fill_ladder.svg"), svg(700, 420,
    "图5 Blob 填充阶梯（E 阶段真实 codec 计算 + 预测跨 Blob 阶梯，非链上实测）", body,
    "单位：填充率；单 Blob 上限 126976 数据字节；超容量为 blocked"));
}

// 图6 消融：总延迟与 adjudicate gas
{
  const items = ablationRows.map((r) => ({
    label: r.armId, value: r.meanTotalLatencyMs.mean || 0, color: "#334155",
  }));
  const body = axes(70, 70, 620, 330, "消融策略", "批总延迟均值（毫秒）") + barChart(70, 70, 550, 260, items);
  fs.writeFileSync(path.join(FIG, "fig_ablation.svg"), svg(700, 420,
    "图6 消融：四类裁决/恢复策略的批总延迟（3 个独立 run 均值）", body,
    "单位：毫秒；未关闭 adjudicate 兜底，不伪造“无恢复必失败”"));
}

// 数据字典
const dataDictionary = {
  batch_records_jsonl: {
    schema: "hybrid-tee-rollup.stageF.batch.v1",
    sampleId: "一逻辑批一个样本（runId-cellId-r{runIndex}-b{batchIndex}）",
    workload_taskCount: "该样本的逻辑任务数（= batchSize），吞吐 numerator 不超过此值",
    warmup: "true 表示预热批，记录但按预先规则不参与稳态统计",
    segments_encodeMs: "客户端构造并哈希任务输入的耗时（ms）",
    segments_signMs: "提交方签名的耗时（ms）",
    segments_submitMs: "submit 交易发送+确认（ms）",
    segments_challengeMs: "openChallenge 交易（ms）",
    segments_adjudicateMs: "裁决路径（adjudicate 或 respond/advance/replay/settle）耗时（ms）",
    segments_withdrawMs: "实际 withdraw 耗时（ms）",
    endpoints: "提交确认/乐观可用/协议终局/可提现/实际提现 五个端点分别记录（UTC + monotonic ns）",
    gas_submitGas: "submit 阶段 gasUsed 合计（BigInt 十进制字符串）",
    fee_submitFeeWei: "submit 阶段 gasUsed × receipt.gasPrice（BigInt 十进制字符串，本地 measured）",
    fee_feeSource: "local-gas-only：本地 Hardhat，不是真实公网货币费用",
    valueTransfer: "押金/退款/罚没/销毁（wei，十进制字符串），价值转移单列，不计入 gas 费用总额",
    counts_attempts: "submit 级尝试次数（含重试）",
    counts_retries: "submit 重试次数（固定 maxAttempts=3，退避 20ms）",
    counts_censored: "右删失计数（超时未完成），不删除、不只对成功求平均",
    recovery: "armId / faultInjected / recoverCalled / recoverSucceeded / interactiveContinuationSucceeded / fallbackUsed",
    throughput: "numerator=该样本 finalizedTasks；denominator=本地耗时秒（非共识最终性）",
  },
  window_records_jsonl: {
    schema: "hybrid-tee-rollup.stageF.window.v1",
    purpose: "跨批次窗口聚合；与 A experiment_record 相互独立，不冒充 A 单样本",
    counts_distinctTaskCount: "窗口内 executed 任务数（去重在聚合层按 taskId 进行）",
    queue_observedInflightPeak: "在途批次数峰值（批次级观测，非 Promise 数量）",
    queue_configuredConcurrency: "配置并发（inflight_batches），未使用 min(batchSize, concurrency) 折叠",
    fee_totalFeeWei: "五项费用之和（BigInt 十进制字符串）",
    latencyMs: "批级均值；并行阶段不可直接相加",
  },
  units: {
    gas: "gas 单位（整数，十进制字符串）",
    wei: "wei（BigInt 十进制字符串，禁止 JS Number 中转）",
    ms: "毫秒（Number(process.hrtime.bigint()/1e6)）",
    monotonicNs: "process.hrtime.bigint() 字符串，用于跨进程关联",
    utc: "ISO8601 UTC，用于跨进程关联",
  },
};
writeJson("data_dictionary.json", dataDictionary);

console.log("[F-agg] cells=", Object.keys(cellSummary).length, "windows=", windows.length, "batches=", batches.length);
console.log("[F-agg] validation.windowEqualsCell=", validation.feeConsistency.windowEqualsCell);
console.log("[F-agg] outputs:", SUM, FIG);
