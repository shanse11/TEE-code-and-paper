// E4: per-environment latency and cost table for the attested fast path.
// No new SGX measurement: the Aliyun SGX host refused SSH on 2026-10-17, so SGX timings come from
// the stage H run. Rows are kept per environment and are not summed into an end-to-end latency.
//
// Run: REVISION_RUN=<abs> node revision/stageI_e4_report.js

const fs = require("fs");
const path = require("path");
const assert = require("assert");

const RUN = process.env.REVISION_RUN;
assert.ok(RUN && path.isAbsolute(RUN), "REVISION_RUN must be absolute");
const STAGE_H = path.resolve(__dirname, "../../outputs/stageH_20261017T104800Z");

const e1 = JSON.parse(fs.readFileSync(path.join(RUN, "e1_dcap.json"), "utf8"));
const e2 = JSON.parse(fs.readFileSync(path.join(RUN, "e2", "e2_summary.json"), "utf8"));
const teeLink = JSON.parse(fs.readFileSync(path.join(STAGE_H, "tee_link.json"), "utf8"));

const cell = (system, teeState, challengerState) =>
  e2.summary.find((s) => s.system === system && s.teeState === teeState && s.challengerState === challengerState);
const reg = e1.partB_forkRegisterInstance.find((r) => r.policy === "strict" && r.quote === "quote_steps4.dat");

const rows = [
  {
    environment: "Aliyun ecs.g7t.large, real SGX (stage H run)",
    item: "enclave call, 4 / 128 steps, incl. report generation",
    value: "0.057 ms / 0.497 ms",
    source: "outputs/stageH_20261017T104800Z/report_zh.md, section 1",
  },
  {
    environment: "Aliyun ecs.g7t.large, real SGX (stage H run)",
    item: "quote generation wall clock (two bound quotes)",
    value: "0.99 s / 1.30 s",
    source: "outputs/stageH_20261017T104800Z/report_zh.md, section 1",
  },
  {
    environment: "Sepolia live state, eth_call (no broadcast)",
    item: "Automata verifyAndAttestOnChain estimateGas, 4 real quotes",
    value: e1.partA_liveEthCall.filter((r) => r.ok).map((r) => r.estimateGas).join(" / "),
    source: "e1_dcap.json partA_liveEthCall",
  },
  {
    environment: `Sepolia fork at block ${e1.forkBlock}`,
    item: "Automata direct call / registerInstance via adapter (strict policy)",
    value: `${e1.partB_forkDirectAutomata.gasUsed} / ${reg.gasUsed} gas, tcbStatus ${reg.tcbStatus}, action ${reg.action}`,
    source: "e1_dcap.json partB",
  },
  {
    environment: "local Hardhat, replay verifier",
    item: "hybrid normal path, 64 steps: protocol time to finality / total task gas",
    value: `${cell("hybrid", "normal", "allOffline").meanFinalitySeconds} s / ${cell("hybrid", "normal", "allOffline").meanTotalGas} gas`,
    source: "e2/e2_summary.json",
  },
  {
    environment: "local Hardhat",
    item: "recomputeFast control, 64 steps: protocol time to finality / total task gas",
    value: `${cell("recomputeFast", "normal", "allOffline").meanFinalitySeconds} s / ${cell("recomputeFast", "normal", "allOffline").meanTotalGas} gas`,
    source: "e2/e2_summary.json",
  },
  {
    environment: "local Hardhat, stage H link",
    item: "settling the real SGX traces (adjudicate, 4 / 128 steps)",
    value: teeLink.cases.map((c) => c.gas.adjudicate).join(" / ") + " gas",
    source: "outputs/stageH_20261017T104800Z/tee_link.json",
  },
];

const record = {
  schemaVersion: "hybrid-tee-rollup.stageI.e4.v1",
  rows,
  notGenerated: [
    "No instance-key quote from tee/attested_instance: the SGX host closed SSH during key exchange on 2026-10-17.",
    "No broadcast-to-inclusion wall clock on Sepolia: no funded key was used in this run.",
  ],
};
fs.writeFileSync(path.join(RUN, "e4_environments.json"), JSON.stringify(record, null, 2));
console.table(rows.map(({ environment, item, value }) => ({ environment, item, value })));
