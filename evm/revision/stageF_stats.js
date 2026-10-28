// SPDX-License-Identifier: MIT
//
// evm/revision/stageF_stats.js
//
// 阶段 F 统计模块（**纯函数，无 IO、无副作用**），供 stageF_aggregate.js 与 fixture 测试共用。
//
// 设计约束（阶段 F 提示词 §4 / §6）：
//   - gas / wei 一律 BigInt 运算 + 十进制字符串序列化；绝不先转 JS Number 再保存，
//     绝不用字符串比较大小（比较一律先 BigInt()）。
//   - 分母 0 或未测 → { value: null, reason }，不填 0、不填估算。
//   - 样本量不足时不报 p99、不输出无法计算的置信区间。
//   - 不按均值先筛异常；故障排除策略必须是预设的，且排除有标志、原数据保留。
//   - 批内任务不是独立样本：以独立 run / 批为 cluster，不以批内任务数伪造大样本。

"use strict";

// ---------------- 分位数 ----------------

/**
 * nearest-rank 分位数（与提示词 design.quantileMethod 一致）。
 * @param {number[]} sorted 已升序排列的有限数值数组
 * @param {number} p 分位点，0<p<=1
 * @returns {number|null}
 */
function nearestRankQuantile(sorted, p) {
  if (!Array.isArray(sorted) || sorted.length === 0) return null;
  if (!(p > 0 && p <= 1)) return null;
  const n = sorted.length;
  // nearest-rank: ceil(p * n)，最小为 1
  const rank = Math.max(1, Math.ceil(p * n));
  return sorted[Math.min(n - 1, rank - 1)];
}

/** 数值是否可用于统计（排除 NaN/Infinity/null/undefined）。 */
function isFiniteNumber(v) {
  return typeof v === "number" && Number.isFinite(v);
}

// 分位数所需最小样本量（经验规则：p95 至少 20 个独立样本；p99 至少 100）。
const MIN_N_FOR_QUANTILE = { 0.5: 1, 0.9: 10, 0.95: 20, 0.99: 100 };

/**
 * 汇总一组样本。
 * @param {Array<number|null|undefined>} values
 * @param {object} opts
 *   - quantiles: 需要报告的分位点数组，默认 [0.5, 0.95]
 *   - enforceMinN: 是否强制执行最小样本量规则（默认 true）
 * @returns {object} n / mean / min / max / quantiles{p->value|null} / omitted{}
 */
function summarizeSamples(values, opts = {}) {
  const quantiles = opts.quantiles || [0.5, 0.95];
  const enforceMinN = opts.enforceMinN !== false;
  const clean = (values || []).filter(isFiniteNumber).slice().sort((a, b) => a - b);
  const n = clean.length;
  const out = {
    n,
    inputCount: (values || []).length,
    droppedNonFinite: (values || []).length - n,
    mean: null,
    min: null,
    max: null,
    quantiles: {},
    method: "nearest-rank on sorted samples",
    omitted: {},
  };
  if (n === 0) {
    out.reason = "no_finite_samples";
    for (const p of quantiles) out.quantiles[p] = null;
    return out;
  }
  out.mean = clean.reduce((a, b) => a + b, 0) / n;
  out.min = clean[0];
  out.max = clean[n - 1];
  for (const p of quantiles) {
    const need = enforceMinN ? (MIN_N_FOR_QUANTILE[p] || 1) : 1;
    if (n < need) {
      out.quantiles[p] = null;
      out.omitted[p] = `insufficient_n_for_p${Math.round(p * 100)}: n=${n} < ${need}`;
    } else {
      out.quantiles[p] = nearestRankQuantile(clean, p);
    }
  }
  return out;
}

// ---------------- 比率 / 分母保护 ----------------

/**
 * 计算比率，分母 0 或未测时返回 null + reason（不填 0、不填估算）。
 */
function rate(numerator, denominator, opts = {}) {
  const unit = opts.unit || "per_unit";
  if (denominator === null || denominator === undefined) {
    return { value: null, unit, denominator: null, reason: "denominator_not_measured" };
  }
  if (!isFiniteNumber(denominator) || denominator <= 0) {
    return { value: null, unit, denominator, reason: "zero_or_invalid_denominator" };
  }
  if (!isFiniteNumber(numerator)) {
    return { value: null, unit, denominator, reason: "invalid_numerator" };
  }
  return { value: numerator / denominator, unit, denominator, reason: null };
}

/**
 * 按不同分母分别计算成本/吞吐（提示词 §F5：分母 0 或未测为 null+reason）。
 * 分母必须互斥归因，不重复计入总额。
 */
function costPerDenominator(totalCostWeiStr, denominators) {
  const out = {};
  let total;
  try {
    total = BigInt(totalCostWeiStr);
  } catch (e) {
    for (const k of Object.keys(denominators)) {
      out[k] = { valueWei: null, reason: "invalid_total_cost" };
    }
    return out;
  }
  for (const [k, den] of Object.entries(denominators)) {
    if (den === null || den === undefined || den <= 0) {
      out[k] = { valueWei: null, reason: "denominator_zero_or_not_measured" };
      continue;
    }
    out[k] = { valueWei: (total / BigInt(den)).toString(), reason: null };
  }
  return out;
}

// ---------------- BigInt 金额累加 ----------------

/**
 * 累加十进制字符串形式的 wei / gas。
 * 缺失字段单独计数，不静默按 0 处理。
 */
function sumBigIntStrings(values) {
  let total = 0n;
  let missing = 0;
  let invalid = 0;
  for (const v of values || []) {
    if (v === null || v === undefined || v === "") { missing++; continue; }
    try { total += BigInt(v); } catch (e) { invalid++; }
  }
  return { total: total.toString(), count: (values || []).length, missing, invalid };
}

/** BigInt 十进制字符串比较：-1/0/1。禁止字符串字典序比较。 */
function compareWei(a, b) {
  const x = BigInt(a);
  const y = BigInt(b);
  return x < y ? -1 : x > y ? 1 : 0;
}

// ---------------- 去重 / 身份 ----------------

/**
 * 按 id 去重（重复 task / tx 只计一次），返回唯一集合与重复计数。
 */
function dedupeById(records, idOf) {
  const seen = new Set();
  const unique = [];
  let duplicates = 0;
  for (const r of records || []) {
    const id = idOf(r);
    if (id === null || id === undefined) continue;
    if (seen.has(id)) { duplicates++; continue; }
    seen.add(id);
    unique.push(r);
  }
  return { unique, duplicates, uniqueCount: unique.length };
}

// ---------------- 删失 / 失败感知汇总 ----------------

/**
 * 成功率 + 条件于成功的延迟，同时报告分母与删失数。
 * 提示词：超时未完成属于右删失/失败，不能删除后仅对成功计算"总平均恢复时间"。
 *
 * @param {Array<{ok:boolean, censored?:boolean, latencyMs?:number|null}>} samples
 */
function censorAwareSummary(samples) {
  const all = samples || [];
  const okList = all.filter((s) => s && s.ok === true);
  const censoredList = all.filter((s) => s && s.censored === true);
  const failedList = all.filter((s) => s && s.ok !== true && s.censored !== true);
  const successLatencies = okList.map((s) => s.latencyMs).filter(isFiniteNumber);
  return {
    attemptCount: all.length,
    successCount: okList.length,
    failureCount: failedList.length,
    censoredCount: censoredList.length,
    successRate: rate(okList.length, all.length, { unit: "success_per_attempt" }),
    censoredRate: rate(censoredList.length, all.length, { unit: "censored_per_attempt" }),
    // 条件于成功的延迟：必须与成功率/分母/删失一起报告
    latencyConditionalOnSuccessMs: summarizeSamples(successLatencies, { quantiles: [0.5, 0.95] }),
    warning:
      okList.length < all.length
        ? "conditional_on_success_latency_excludes_failures_and_censored; not comparable across cells with different failure rates"
        : null,
  };
}

// ---------------- cluster bootstrap（固定 seed） ----------------

/** mulberry32：固定 seed 的可复现 PRNG。 */
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * 以 cluster（独立 run / 批）为单位的配对差 bootstrap。
 * 样本量过小时返回 null + reason，不输出无法计算的置信区间。
 *
 * @param {number[]} diff 每个 cluster 的配对差（b - a）
 * @param {object} opts { seed, iterations }
 */
function clusterBootstrapPairedDiff(diff, opts = {}) {
  const iterations = opts.iterations || 2000;
  const seed = opts.seed === undefined ? 20260917 : opts.seed;
  const clean = (diff || []).filter(isFiniteNumber);
  if (clean.length < 3) {
    return {
      nClusters: clean.length,
      meanDiff: clean.length ? clean.reduce((a, b) => a + b, 0) / clean.length : null,
      ci: null,
      reason: "insufficient_clusters_for_bootstrap_ci: need >= 3 independent clusters",
    };
  }
  if (clean.length < 10) {
    // 只有 3 个独立 run：CI 极不稳定，如实标注
    return {
      nClusters: clean.length,
      meanDiff: clean.reduce((a, b) => a + b, 0) / clean.length,
      ci: null,
      reason: "only_3_independent_runs: CI unstable, reported as descriptive only",
    };
  }
  const rnd = mulberry32(seed);
  const n = clean.length;
  const means = [];
  for (let i = 0; i < iterations; ++i) {
    let s = 0;
    for (let j = 0; j < n; ++j) s += clean[Math.floor(rnd() * n)];
    means.push(s / n);
  }
  means.sort((a, b) => a - b);
  const lo = nearestRankQuantile(means, 0.025);
  const hi = nearestRankQuantile(means, 0.975);
  return {
    nClusters: n,
    meanDiff: clean.reduce((a, b) => a + b, 0) / clean.length,
    ci: { level: 0.95, low: lo, high: hi, method: "cluster bootstrap percentile (seed=" + seed + ", iters=" + iterations + ")" },
    reason: null,
  };
}

// ---------------- 窗口归属 ----------------

/**
 * 跨窗口任务归属规则：任务归属其**提交**所在窗口；若提交时间在窗口开始之前
 * 或结束之后则标记为 out_of_window 并单独计数，不静默丢弃。
 * drain 期（窗口结束后仍在途的批次）单独标记，不只统计完成最快的一部分。
 */
function assignTaskToWindow(task, windows) {
  for (const w of windows || []) {
    if (task.windowId && task.windowId === w.windowId) {
      return { windowId: w.windowId, status: "assigned_by_window_id" };
    }
  }
  for (const w of windows || []) {
    if (task.monotonicStartNs && w.monotonicStartNs && w.monotonicEndNs) {
      const t = BigInt(task.monotonicStartNs);
      if (t >= BigInt(w.monotonicStartNs) && t <= BigInt(w.monotonicEndNs)) {
        return { windowId: w.windowId, status: "assigned_by_time_range" };
      }
    }
  }
  return { windowId: null, status: "out_of_window_or_drain" };
}

module.exports = {
  nearestRankQuantile,
  summarizeSamples,
  isFiniteNumber,
  rate,
  costPerDenominator,
  sumBigIntStrings,
  compareWei,
  dedupeById,
  censorAwareSummary,
  mulberry32,
  clusterBootstrapPairedDiff,
  assignTaskToWindow,
  MIN_N_FOR_QUANTILE,
};
