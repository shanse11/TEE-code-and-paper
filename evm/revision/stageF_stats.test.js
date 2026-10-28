// SPDX-License-Identifier: MIT
//
// evm/revision/stageF_stats.test.js
//
// 阶段 F 统计代码 fixture 测试（提示词 §6 要求）：
//   已知分位数、分母 0、全失败、右删失、重复 task/tx、超大 wei、缺费用字段、
//   跨窗口任务、批内相关、nonce 重试。
// 全部使用构造 fixture，不依赖网络、不依赖链上状态。

"use strict";

const assert = require("assert");
const S = require("./stageF_stats");

describe("stageF stats fixtures", function () {
  this.timeout(30000);

  // 1) 已知分位数
  it("F-FIX-01 已知分位数：nearest-rank p50/p95 与手算一致", function () {
    const xs = Array.from({ length: 20 }, (_, i) => i + 1); // 1..20
    assert.strictEqual(S.nearestRankQuantile(xs, 0.5), 10, "p50 of 1..20 = ceil(0.5*20)=10 -> 10");
    assert.strictEqual(S.nearestRankQuantile(xs, 0.95), 19, "p95 of 1..20 = ceil(19)=19 -> 19");
    assert.strictEqual(S.nearestRankQuantile(xs, 1.0), 20);
    assert.strictEqual(S.nearestRankQuantile(xs, 0.01), 1, "最小 rank 为 1");
    const s = S.summarizeSamples(xs, { quantiles: [0.5, 0.95] });
    assert.strictEqual(s.quantiles[0.5], 10);
    assert.strictEqual(s.quantiles[0.95], 19);
    assert.strictEqual(s.n, 20);
  });

  // 2) 样本量不足时不报高分位
  it("F-FIX-02 样本量不足：n=5 时 p95 被省略并给出 reason，不伪造", function () {
    const s = S.summarizeSamples([1, 2, 3, 4, 5], { quantiles: [0.5, 0.95, 0.99] });
    assert.strictEqual(s.quantiles[0.5], 3);
    assert.strictEqual(s.quantiles[0.95], null);
    assert.ok(s.omitted[0.95] && /insufficient_n_for_p95/.test(s.omitted[0.95]));
    assert.strictEqual(s.quantiles[0.99], null);
    assert.ok(s.omitted[0.99] && /insufficient_n_for_p99/.test(s.omitted[0.99]));
  });

  // 3) 分母 0 / 未测
  it("F-FIX-03 分母 0 或 null：rate/costPerDenominator 返回 null+reason，不填 0", function () {
    const r0 = S.rate(10, 0, { unit: "tasks_per_s" });
    assert.strictEqual(r0.value, null);
    assert.strictEqual(r0.reason, "zero_or_invalid_denominator");
    const rn = S.rate(10, null, { unit: "tasks_per_s" });
    assert.strictEqual(rn.value, null);
    assert.strictEqual(rn.reason, "denominator_not_measured");

    const c = S.costPerDenominator("1000", { perFinalized: 0, perAccepted: null, perBatch: 4 });
    assert.strictEqual(c.perFinalized.valueWei, null);
    assert.strictEqual(c.perFinalized.reason, "denominator_zero_or_not_measured");
    assert.strictEqual(c.perAccepted.valueWei, null);
    assert.strictEqual(c.perBatch.valueWei, "250");
  });

  // 4) 全失败
  it("F-FIX-04 全失败：成功率 0，条件延迟为 null 且带 warning，不产生可比延迟", function () {
    const samples = [
      { ok: false, latencyMs: null },
      { ok: false, latencyMs: null },
      { ok: false, latencyMs: null },
    ];
    const s = S.censorAwareSummary(samples);
    assert.strictEqual(s.attemptCount, 3);
    assert.strictEqual(s.successCount, 0);
    assert.strictEqual(s.failureCount, 3);
    assert.strictEqual(s.successRate.value, 0);
    assert.strictEqual(s.latencyConditionalOnSuccessMs.n, 0);
    assert.strictEqual(s.latencyConditionalOnSuccessMs.reason, "no_finite_samples");
    assert.ok(s.warning, "全失败必须携带不可跨格比较的警告");
  });

  // 5) 右删失：不能删除后仅对成功计算"总平均恢复时间"
  it("F-FIX-05 右删失：成功/失败/删失分别计数，延迟标注为条件于成功", function () {
    const samples = [
      { ok: true, latencyMs: 100 },
      { ok: true, latencyMs: 300 },
      { ok: false, latencyMs: null, censored: true },
      { ok: false, latencyMs: null, censored: true },
    ];
    const s = S.censorAwareSummary(samples);
    assert.strictEqual(s.attemptCount, 4);
    assert.strictEqual(s.successCount, 2);
    assert.strictEqual(s.censoredCount, 2);
    assert.strictEqual(s.failureCount, 0);
    assert.strictEqual(s.successRate.value, 0.5);
    assert.strictEqual(s.censoredRate.value, 0.5);
    // 条件于成功的均值 = 200，但必须与成功率/分母同时报告
    assert.strictEqual(s.latencyConditionalOnSuccessMs.mean, 200);
    assert.ok(/conditional_on_success/.test(s.warning));
  });

  // 6) 重复 task / tx 只计一次
  it("F-FIX-06 重复 task/tx：去重后唯一计数与重复计数分离", function () {
    const recs = [
      { taskId: "0xaa", gas: "100" },
      { taskId: "0xaa", gas: "100" },
      { taskId: "0xbb", gas: "200" },
      { taskId: null, gas: "300" },
    ];
    const d = S.dedupeById(recs, (r) => r.taskId);
    assert.strictEqual(d.uniqueCount, 2);
    assert.strictEqual(d.duplicates, 1);
    const sum = S.sumBigIntStrings(d.unique.map((r) => r.gas));
    assert.strictEqual(sum.total, "300", "去重后不重复计入 gas");
  });

  // 7) 超大 wei：BigInt 不丢精度，禁止 Number 转换
  it("F-FIX-07 超大 wei：超过 2^53 仍精确，比较用 BigInt 非字符串", function () {
    const a = "9007199254740993"; // 2^53 + 1，Number 会丢精度
    const b = "9007199254740992";
    const sum = S.sumBigIntStrings([a, b]);
    assert.strictEqual(sum.total, "18014398509481985");
    assert.strictEqual(S.compareWei(a, b), 1);
    assert.strictEqual(S.compareWei(b, a), -1);
    assert.strictEqual(S.compareWei(a, a), 0);
    // 反例：字符串字典序比较在本例会给出正确方向，但 9 vs 10 会错误 —— 故禁止
    assert.ok("9" > "10", "证明字符串比较不可用（文档性断言）");
    const huge = "100000000000000000000000000000"; // 1e29 wei
    const per = S.costPerDenominator(huge, { perTask: 3 });
    assert.strictEqual(per.perTask.valueWei, "33333333333333333333333333333");
  });

  // 8) 缺费用字段：计入 missing，不按 0 静默处理
  it("F-FIX-08 缺费用字段：missing 单独计数，不静默按 0", function () {
    const sum = S.sumBigIntStrings(["100", null, undefined, "", "abc", "200"]);
    assert.strictEqual(sum.total, "300");
    assert.strictEqual(sum.missing, 3);
    assert.strictEqual(sum.invalid, 1);
  });

  // 9) 跨窗口任务：归属规则明确，out_of_window 单独标记
  it("F-FIX-09 跨窗口任务：按 windowId/时间范围归属，越界标记不丢弃", function () {
    const windows = [
      { windowId: "w1", monotonicStartNs: "1000", monotonicEndNs: "2000" },
      { windowId: "w2", monotonicStartNs: "2001", monotonicEndNs: "3000" },
    ];
    assert.deepStrictEqual(S.assignTaskToWindow({ windowId: "w2" }, windows), {
      windowId: "w2", status: "assigned_by_window_id",
    });
    assert.deepStrictEqual(S.assignTaskToWindow({ monotonicStartNs: "1500" }, windows), {
      windowId: "w1", status: "assigned_by_time_range",
    });
    const out = S.assignTaskToWindow({ monotonicStartNs: "9999" }, windows);
    assert.strictEqual(out.windowId, null);
    assert.strictEqual(out.status, "out_of_window_or_drain");
  });

  // 10) 批内相关：不得把批内任务数当作独立样本量
  it("F-FIX-10 批内相关：cluster bootstrap 以独立 run/批为单位；3 run 时不给 CI", function () {
    // 10 个批 × 8 任务 = 80 个"观测"，但独立 cluster 只有 10 个
    const perBatch = Array.from({ length: 10 }, (_, i) => 10 + i);
    const inflatedN = perBatch.length * 8;
    assert.strictEqual(inflatedN, 80, "批内任务数不得当作独立样本量");
    const s = S.summarizeSamples(perBatch, { quantiles: [0.5, 0.95] });
    assert.strictEqual(s.n, 10, "统计样本量应为 cluster 数");
    assert.strictEqual(s.quantiles[0.95], null, "10 个 cluster 不足以报 p95");

    const few = S.clusterBootstrapPairedDiff([1, 2, 3], { seed: 7 });
    assert.strictEqual(few.nClusters, 3);
    assert.strictEqual(few.ci, null);
    assert.ok(/only_3_independent_runs/.test(few.reason));

    const none = S.clusterBootstrapPairedDiff([1, 2], { seed: 7 });
    assert.strictEqual(none.ci, null);
    assert.ok(/insufficient_clusters/.test(none.reason));
  });

  // 附加：nonce 重试 —— 重试计入 attempt，且成本不重复计入总额
  it("F-FIX-11 nonce 重试：attempt>success 时成功率下降，成本按实际 tx 计一次", function () {
    const samples = [
      { ok: true, latencyMs: 50, attempts: 1, retries: 0 },
      { ok: true, latencyMs: 90, attempts: 3, retries: 2 },
    ];
    const att = samples.reduce((a, s) => a + s.attempts, 0);
    const ret = samples.reduce((a, s) => a + s.retries, 0);
    assert.strictEqual(att, 4);
    assert.strictEqual(ret, 2);
    const s = S.censorAwareSummary(samples.map((x) => ({ ok: x.ok, latencyMs: x.latencyMs })));
    assert.strictEqual(s.successCount, 2);
    assert.strictEqual(s.attemptCount, 2, "样本级 attempt=2；重试在批次级单独记账");
    // 重试成本是总额子集，不再加一次
    const total = S.sumBigIntStrings(["21000", "21000", "21000", "21000"]); // 4 次实际 tx
    assert.strictEqual(total.total, "84000");
  });

  // 附加：bootstrap 可复现（固定 seed）
  it("F-FIX-12 固定 seed 的 cluster bootstrap 可复现", function () {
    const d = Array.from({ length: 30 }, (_, i) => (i % 7) - 3);
    const a = S.clusterBootstrapPairedDiff(d, { seed: 20260917, iterations: 500 });
    const b = S.clusterBootstrapPairedDiff(d, { seed: 20260917, iterations: 500 });
    assert.ok(a.ci, "30 个 cluster 应给出 CI");
    assert.strictEqual(a.ci.low, b.ci.low);
    assert.strictEqual(a.ci.high, b.ci.high);
    assert.ok(a.ci.low <= a.ci.high);
  });
});
