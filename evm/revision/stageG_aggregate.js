// SPDX-License-Identifier: MIT
//
// evm/revision/stageG_aggregate.js
//
// 阶段 G 聚合器：从 raw/mechanism 重建机制微基准表与图表（提示词 §G5：统计从 raw 重建）。
//
// 用法：node evm/revision/stageG_aggregate.js <stageG_out_dir>

"use strict";

const fs = require("fs");
const path = require("path");
const S = require("./stageF_stats");

const OUT = process.argv[2];
if (!OUT) { console.error("usage: node stageG_aggregate.js <stageG_out_dir>"); process.exit(1); }
const RAW = path.join(OUT, "raw", "mechanism");
const SUM = path.join(OUT, "summary");
const FIG = path.join(OUT, "figures");
fs.mkdirSync(SUM, { recursive: true });
fs.mkdirSync(FIG, { recursive: true });

const recs = fs.readFileSync(path.join(RAW, "mechanism_records.jsonl"), "utf8")
  .trim().split("\n").filter(Boolean).map((l) => JSON.parse(l));
const design = JSON.parse(fs.readFileSync(path.join(OUT, "mechanism_design.frozen.json"), "utf8"));
const dec = (v) => BigInt(v).toString();

const groups = {};
for (const r of recs) {
  const k = `${r.system}::${r.arm}`;
  (groups[k] = groups[k] || []).push(r);
}

const rows = Object.entries(groups).map(([k, rs]) => {
  const [system, arm] = k.split("::");
  const m = rs.filter((r) => !r.warmup);
  const runs = [...new Set(m.map((r) => r.runIndex))];
  const perRun = runs.map((ri) => {
    const rr = m.filter((r) => r.runIndex === ri);
    return {
      runIndex: ri,
      batches: rr.length,
      correct: rr.filter((r) => r.outcome === "correct").length,
      incorrect: rr.filter((r) => r.outcome === "incorrect").length,
      unresolved: rr.filter((r) => r.outcome === "unresolved").length,
      notApplicable: rr.filter((r) => r.outcome === "not_applicable").length,
      meanTotalLatencyMs: rr.reduce((a, r) => a + r.segments.totalMs, 0) / (rr.length || 1),
      gas: {
        submit: dec(rr.reduce((a, r) => a + BigInt(r.gas.submitGas), 0n)),
        challenge: dec(rr.reduce((a, r) => a + BigInt(r.gas.challengeGas), 0n)),
        resolve: dec(rr.reduce((a, r) => a + BigInt(r.gas.resolveGas), 0n)),
        withdraw: dec(rr.reduce((a, r) => a + BigInt(r.gas.withdrawGas), 0n)),
      },
      txCount: rr.reduce((a, r) => a + r.counts.txCount, 0),
      interactiveMoves: rr.reduce((a, r) => a + r.counts.interactiveMoves, 0),
    };
  });
  const attempt = m.length;
  const correct = m.filter((r) => r.outcome === "correct").length;
  const incorrect = m.filter((r) => r.outcome === "incorrect").length;
  const unresolved = m.filter((r) => r.outcome === "unresolved").length;
  const na = m.filter((r) => r.outcome === "not_applicable").length;
  const censor = S.censorAwareSummary(m.map((r) => ({
    ok: r.outcome === "correct",
    censored: r.counts.censored > 0,
    latencyMs: r.segments.totalMs,
  })));
  return {
    system,
    arm,
    systemRole: design.systems[system] ? design.systems[system].role : null,
    nIndependentRuns: runs.length,
    batches: attempt,
    correctFinality: correct,
    incorrectFinality: incorrect,
    unresolved,
    notApplicable: na,
    correctFinalityRate: S.rate(correct, attempt, { unit: "correct_finality_per_attempt" }),
    incorrectFinalityRate: S.rate(incorrect, attempt, { unit: "incorrect_finality_per_attempt" }),
    latencyMs: S.summarizeSamples(perRun.map((p) => p.meanTotalLatencyMs), { quantiles: [0.5, 0.95] }),
    gas: {
      submit: dec(m.reduce((a, r) => a + BigInt(r.gas.submitGas), 0n)),
      challenge: dec(m.reduce((a, r) => a + BigInt(r.gas.challengeGas), 0n)),
      resolve: dec(m.reduce((a, r) => a + BigInt(r.gas.resolveGas), 0n)),
      withdraw: dec(m.reduce((a, r) => a + BigInt(r.gas.withdrawGas), 0n)),
    },
    totalGas: dec(m.reduce((a, r) => a + BigInt(r.gas.submitGas) + BigInt(r.gas.challengeGas) + BigInt(r.gas.resolveGas) + BigInt(r.gas.withdrawGas), 0n)),
    l1TxCount: m.reduce((a, r) => a + r.counts.txCount, 0),
    interactiveMovesPerBatch: S.summarizeSamples(m.map((r) => r.counts.interactiveMoves), { quantiles: [0.5, 0.95] }),
    censorAware: censor,
    perRun,
  };
});

// 配对差异：同一 arm 下 本方案 vs 基线（以独立 run 为 cluster）
const paired = [];
for (const arm of design.arms.map((a) => a.id)) {
  const a = rows.find((r) => r.system === "bounded-task-rollup" && r.arm === arm);
  const b = rows.find((r) => r.system === "mechanism-baseline" && r.arm === arm);
  if (!a || !b) { paired.push({ arm, metric: "meanTotalLatencyMs", value: null, reason: "arm_not_available_on_both_systems" }); continue; }
  const n = Math.min(a.perRun.length, b.perRun.length);
  const diff = [];
  for (let i = 0; i < n; ++i) diff.push(b.perRun[i].meanTotalLatencyMs - a.perRun[i].meanTotalLatencyMs);
  const bs = S.clusterBootstrapPairedDiff(diff, { seed: design.statistics.seed });
  paired.push({ arm, metric: "meanTotalLatencyMs(baseline - ours)", nClusters: bs.nClusters, meanDiff: bs.meanDiff, ci: bs.ci, reason: bs.reason });
}

// 校验
const validation = {
  records: recs.length,
  measuredRecords: recs.filter((r) => !r.warmup).length,
  warmupRecords: recs.filter((r) => r.warmup).length,
  duplicateSampleIds: recs.length - new Set(recs.map((r) => r.sampleId)).size,
  outcomeDistribution: recs.filter((r) => !r.warmup).reduce((a, r) => { a[r.outcome] = (a[r.outcome] || 0) + 1; return a; }, {}),
  gasTotalsMatchPerRunSum: (() => {
    let ok = true;
    for (const r of rows) {
      const s = r.perRun.reduce((a, p) => a + BigInt(p.gas.submit) + BigInt(p.gas.challenge) + BigInt(p.gas.resolve) + BigInt(p.gas.withdraw), 0n);
      if (s !== BigInt(r.totalGas)) ok = false;
    }
    return ok;
  })(),
  exclusions: { policy: "warmup 记录但不参与稳态统计；无按结果筛选剔除", excluded: 0 },
};

const writeJson = (n, o) => fs.writeFileSync(path.join(SUM, n), JSON.stringify(o, null, 2));
writeJson("mechanism_summary.json", { design: design.schemaVersion, rows, paired });
writeJson("mechanism_validation.json", validation);

const cols = ["system", "arm", "nIndependentRuns", "batches", "correctFinality", "incorrectFinality", "unresolved", "notApplicable", "totalGas", "l1TxCount"];
const csv = [cols.join(",")].concat(rows.map((r) => cols.map((c) => (r[c] === null || r[c] === undefined ? "" : String(r[c]))).join(",")))
  .concat(["", "# 派生列"])
  .concat([["system", "arm", "correctRate", "meanLatencyMs", "meanInteractiveMoves"].join(",")])
  .concat(rows.map((r) => [r.system, r.arm,
    r.correctFinalityRate.value === null ? "null" : r.correctFinalityRate.value.toFixed(3),
    r.latencyMs.mean === null ? "null" : r.latencyMs.mean.toFixed(2),
    r.interactiveMovesPerBatch.mean === null ? "null" : r.interactiveMovesPerBatch.mean.toFixed(2)].join(",")))
  .join("\n");
fs.writeFileSync(path.join(SUM, "mechanism_summary.csv"), csv);

// ---- 图 ----
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function svg(w, h, title, body, unit) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" font-family="Helvetica,Arial,sans-serif">
<rect width="${w}" height="${h}" fill="#ffffff"/>
<text x="20" y="26" font-size="15" font-weight="bold" fill="#111827">${esc(title)}</text>
<text x="20" y="44" font-size="11" fill="#6b7280">${esc(unit || "")}</text>
${body}
</svg>`;
}
{
  // 正确终局率
  const items = rows.map((r) => ({
    label: `${r.system === "bounded-task-rollup" ? "本方案" : "基线"}/${r.arm}`,
    value: r.correctFinalityRate.value || 0,
    labelValue: `${r.correctFinality}/${r.batches}`,
    color: r.system === "bounded-task-rollup" ? "#2563eb" : "#dc2626",
  }));
  const x0 = 70, y0 = 70, w = 550, h = 260;
  const bw = w / items.length * 0.6, gap = w / items.length;
  let body = `<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y0 + h}" stroke="#374151" stroke-width="1.5"/>
<line x1="${x0}" y1="${y0 + h}" x2="${x0 + w}" y2="${y0 + h}" stroke="#374151" stroke-width="1.5"/>`;
  items.forEach((it, k) => {
    const bh = it.value * h;
    const x = x0 + gap * k + (gap - bw) / 2;
    const y = y0 + h - bh;
    body += `<rect x="${x}" y="${y}" width="${bw}" height="${Math.max(bh, 0.5)}" fill="${it.color}"/>`;
    body += `<text x="${x + bw / 2}" y="${y - 4}" font-size="9" fill="#111827" text-anchor="middle">${esc(it.labelValue)}</text>`;
    body += `<text x="${x + bw / 2}" y="${y0 + h + 26}" font-size="8" fill="#374151" text-anchor="middle">${esc(it.label.split("/")[0])}</text>`;
    body += `<text x="${x + bw / 2}" y="${y0 + h + 37}" font-size="8" fill="#374151" text-anchor="middle">${esc(it.label.split("/")[1])}</text>`;
  });
  body += `<text x="${x0}" y="${y0 + h + 60}" font-size="10" fill="#374151">蓝=本方案 BoundedTaskRollup；红=机制基线 MechanismBaseline（非官方实现）</text>`;
  fs.writeFileSync(path.join(FIG, "fig_g_correct_finality.svg"), svg(700, 440,
    "图G1 同模型机制微基准：正确终局率（正确提交的 trace）", body,
    "单位：正确终局批次数 / 稳态批次数；分母见标签"));
}
{
  // 总 gas
  const items = rows.map((r) => ({
    label: `${r.system === "bounded-task-rollup" ? "本方案" : "基线"}/${r.arm}`,
    value: Number(BigInt(r.totalGas) / 1000n) / 1000,
    labelValue: (Number(BigInt(r.totalGas) / 1000n) / 1000).toFixed(1),
    color: r.system === "bounded-task-rollup" ? "#0f766e" : "#b45309",
  }));
  const x0 = 70, y0 = 70, w = 550, h = 260;
  const max = Math.max(...items.map((i) => i.value), 1e-9);
  const bw = w / items.length * 0.6, gap = w / items.length;
  let body = `<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y0 + h}" stroke="#374151" stroke-width="1.5"/>
<line x1="${x0}" y1="${y0 + h}" x2="${x0 + w}" y2="${y0 + h}" stroke="#374151" stroke-width="1.5"/>`;
  items.forEach((it, k) => {
    const bh = (it.value / max) * h;
    const x = x0 + gap * k + (gap - bw) / 2;
    const y = y0 + h - bh;
    body += `<rect x="${x}" y="${y}" width="${bw}" height="${Math.max(bh, 0.5)}" fill="${it.color}"/>`;
    body += `<text x="${x + bw / 2}" y="${y - 4}" font-size="9" fill="#111827" text-anchor="middle">${esc(it.labelValue)}</text>`;
    body += `<text x="${x + bw / 2}" y="${y0 + h + 26}" font-size="8" fill="#374151" text-anchor="middle">${esc(it.label.split("/")[0])}</text>`;
    body += `<text x="${x + bw / 2}" y="${y0 + h + 37}" font-size="8" fill="#374151" text-anchor="middle">${esc(it.label.split("/")[1])}</text>`;
  });
  fs.writeFileSync(path.join(FIG, "fig_g_gas.svg"), svg(700, 420,
    "图G2 同模型机制微基准：争议解决总 gas（3 run 合计）", body, "单位：千 gas（kgas）"));
}

console.log("[G-agg] rows=", rows.length, "records=", recs.length,
  "dupSampleIds=", validation.duplicateSampleIds,
  "gasTotalsMatch=", validation.gasTotalsMatchPerRunSum);
console.log("[G-agg] outputs:", SUM, FIG);
