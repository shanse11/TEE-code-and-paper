// E3: two boundaries of the attested fast path (local Hardhat).
//
// Part A, short-window catch rate. Forged results from an OK instance on the hybrid contract.
// A watcher reacts after an exponentially distributed delay with mean mu plus one 12 s slot,
// drawn from a fixed-seed PRNG. The cell value is how many of 30 forged tasks were slashed.
//
// Part B, recomputation cost. RecomputeProbe runs the same hash chain without the 128-step cap.
// Gas is measured by sending the transaction, up to the 60M local block gas limit.
//
// Run:
//   cd evm; REVISION_RUN=<abs> node node_modules/hardhat/internal/cli/cli.js \
//     run --config revision/hardhat.config.js revision/stageI_e3_window.js

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { ethers } = require("hardhat");
const {
  TCB, makeInput, deployAttested, deployReplay, registerInstance, sign, now, advance,
} = require("./attested_common");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN must be absolute");
const OUT = path.join(REVISION_RUN, "e3");
fs.mkdirSync(OUT, { recursive: true });

const BOND = ethers.parseEther("1");
const WINDOWS = [60, 300, 600, 3600];
const MEAN_DELAYS = [30, 120, 600, 1800];
const TRIALS = 30;
const SLOT = 12;
const SEED = 20261017;

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

async function partA() {
  const [submitter, challenger, keeper] = await ethers.getSigners();
  const rows = [];
  for (const window of WINDOWS) {
    const verifier = await deployReplay();
    const rollup = await deployAttested({ verifier, shortWindow: window, longWindow: 7 * 24 * 3600 });
    const inst = ethers.Wallet.createRandom();
    await registerInstance(rollup, verifier, inst, { tcbStatus: TCB.OK, label: "e3:" + window });
    for (const mu of MEAN_DELAYS) {
      const rand = mulberry32(SEED + window * 7919 + mu);
      let caught = 0;
      const delays = [];
      for (let k = 0; k < TRIALS; ++k) {
        const delay = Math.max(1, Math.round(-mu * Math.log(1 - rand()))) + SLOT;
        delays.push(delay);
        const input = makeInput(`e3:${window}:${mu}:${k}`, 64, { forge: true });
        const rc = await (await rollup.connect(submitter).submit(
          input, await sign(submitter, rollup, input), await sign(inst, rollup, input), { value: BOND })).wait();
        const t0 = (await ethers.provider.getBlock(rc.blockNumber)).timestamp;
        const wait = t0 + delay - (await now()) - 1;
        if (wait > 0) await advance(wait);
        try {
          await (await rollup.connect(challenger).openChallenge(input.taskId, { value: BOND })).wait();
          await (await rollup.connect(keeper).adjudicate(input.taskId)).wait();
        } catch (_e) {
          const t = await rollup.getTask(input.taskId);
          const w = Number(t.challengeDeadline) + 1 - (await now());
          if (w > 0) await advance(w);
          await (await rollup.connect(keeper).finalize(input.taskId)).wait();
        }
        const t = await rollup.getTask(input.taskId);
        if (Number(t.verdict) !== 0) caught += 1;
      }
      const analytic = 1 - Math.exp(-Math.max(0, window - SLOT) / mu);
      rows.push({
        shortWindowSeconds: window, meanDelaySeconds: mu, slotSeconds: SLOT, trials: TRIALS,
        caught, missed: TRIALS - caught,
        medianDelaySeconds: delays.sort((a, b) => a - b)[Math.floor(TRIALS / 2)],
        analyticCatchProbability: Number(analytic.toFixed(4)),
      });
      console.log("A", window, mu, caught, "/", TRIALS);
    }
  }
  return rows;
}

async function partB() {
  const F = await ethers.getContractFactory("RecomputeProbe");
  const probe = await F.deploy();
  await probe.waitForDeployment();
  const initial = "0x" + "11".repeat(32);
  const rows = [];
  for (const steps of [128, 1024, 4096, 8192, 16384, 20480, 24576, 28672, 32768]) {
    try {
      const rc = await (await probe.recompute(initial, steps, { gasLimit: 59000000 })).wait();
      rows.push({ steps, gasUsed: rc.gasUsed.toString(), fits60M: true });
      console.log("B", steps, rc.gasUsed.toString());
    } catch (err) {
      rows.push({ steps, gasUsed: null, fits60M: false, reason: (err.shortMessage || err.message).split("\n")[0] });
      console.log("B", steps, "failed");
    }
  }
  const ok = rows.filter((r) => r.gasUsed);
  const a = ok[0];
  const b = ok[ok.length - 1];
  const perStep = (Number(b.gasUsed) - Number(a.gasUsed)) / (b.steps - a.steps);
  return { rows, perStepGasBetweenEnds: Number(perStep.toFixed(1)) };
}

async function main() {
  const a = await partA();
  const b = await partB();
  const record = {
    schemaVersion: "hybrid-tee-rollup.stageI.e3.v1",
    environment: "local Hardhat in-process chain, solc 0.8.26, cancun, blockGasLimit 60000000",
    partA_shortWindowCatch: { seed: SEED, delayModel: "exponential(mean) + one 12 s slot", rows: a },
    partB_recomputeCost: b,
    notes: [
      "Part A delays are a synthetic watcher model, not measured network latencies.",
      "Part B measures gas only; quadratic memory cost makes per-step gas grow with steps.",
    ],
  };
  fs.writeFileSync(path.join(OUT, "e3_summary.json"), JSON.stringify(record, null, 2));
  console.table(a);
  console.table(b.rows);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
