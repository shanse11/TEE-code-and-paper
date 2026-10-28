// E2: fault-injection matrix (local Hardhat).
//
// Systems
//   teeOnly    AttestedTaskRollup(teeOnly=true): an OK instance settles at submission, no recomputation.
//   recompute  BoundedTaskRollup: long window only; finalize always recomputes on chain.
//   recomputeFast BoundedTaskRollup with a one-slot (12 s) window: every task is recomputed at
//              finalize, so no watcher is needed. This is the control for "why not just recompute".
//   hybrid     AttestedTaskRollup: OK instance gets the short window; everything else the long window;
//              unchallenged finalize does not recompute; a challenge triggers recomputation.
//
// TEE states
//   normal     honest result signed by an instance with TCB OK
//   forged     wrong result signed by an instance with TCB OK (compromised enclave or leaked key)
//   offline    honest result, no instance signature (TEE unavailable)
//   tcbStale   wrong result signed by an instance whose TCB is OUT_OF_DATE_CONFIGURATION_NEEDED
//
// Challenger states (the watcher only challenges wrong results)
//   online       challenges right after submission
//   lateOffline  offline during the short window, back after shortWindow + 60 s
//   allOffline   never challenges
//
// Run:
//   cd evm; REVISION_RUN=<abs> node node_modules/hardhat/internal/cli/cli.js \
//     run --config revision/hardhat.config.js revision/stageI_e2_matrix.js

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { ethers } = require("hardhat");
const {
  TCB, makeInput, deployAttested, deployReplay, registerInstance, sign, now, advance,
} = require("./attested_common");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN must be absolute");
const OUT = path.join(REVISION_RUN, "e2");
fs.mkdirSync(OUT, { recursive: true });

const BOND = ethers.parseEther("1");
const SHORT = 600;
const LONG = 7 * 24 * 3600;
const STEPS = Number(process.env.E2_STEPS || 64);
const BATCHES = Number(process.env.E2_BATCHES || 30);
const LATE_RETURN = SHORT + 60;
const FAST_RECOMPUTE_WINDOW = 12;
const SYSTEMS = ["teeOnly", "recompute", "recomputeFast", "hybrid"];
const BOUNDED = new Set(["recompute", "recomputeFast"]);
const TEE_STATES = ["normal", "forged", "offline", "tcbStale"];
const CHALLENGERS = ["online", "lateOffline", "allOffline"];

function isWrong(teeState) {
  return teeState === "forged" || teeState === "tcbStale";
}

async function setupSystem(system) {
  const verifier = await deployReplay();
  const okInstance = ethers.Wallet.createRandom();
  const staleInstance = ethers.Wallet.createRandom();
  let rollup;
  if (BOUNDED.has(system)) {
    const F = await ethers.getContractFactory("BoundedTaskRollup");
    rollup = await F.deploy(BOND, system === "recompute" ? LONG : FAST_RECOMPUTE_WINDOW, 10, 2);
    await rollup.waitForDeployment();
  } else {
    rollup = await deployAttested({ verifier, shortWindow: SHORT, longWindow: LONG, teeOnly: system === "teeOnly" });
    const r1 = await registerInstance(rollup, verifier, okInstance, { tcbStatus: TCB.OK, label: system + ":ok" });
    const r2 = await registerInstance(rollup, verifier, staleInstance, {
      tcbStatus: TCB.OUT_OF_DATE_CONFIGURATION_NEEDED, label: system + ":stale",
    });
    rollup.registrationGas = [r1.gasUsed.toString(), r2.gasUsed.toString()];
  }
  return { rollup, okInstance, staleInstance };
}

async function runOne(system, ctx, teeState, challengerState, batch, signers) {
  const [submitter, challenger, keeper] = signers;
  const label = `${system}:${teeState}:${challengerState}:${batch}`;
  const input = makeInput(label, STEPS, { forge: isWrong(teeState) });
  const { rollup } = ctx;
  const gas = { submit: 0n, challenge: 0n, adjudicate: 0n, finalize: 0n };
  const subSig = await sign(submitter, rollup, input);
  let instanceSig = "0x";
  if (teeState === "normal" || teeState === "forged") instanceSig = await sign(ctx.okInstance, rollup, input);
  if (teeState === "tcbStale") instanceSig = await sign(ctx.staleInstance, rollup, input);

  const bounded = BOUNDED.has(system);
  const submitTx = bounded
    ? rollup.connect(submitter).submit(input, subSig, { value: BOND })
    : rollup.connect(submitter).submit(input, subSig, instanceSig, { value: BOND });
  const submitRc = await (await submitTx).wait();
  gas.submit = submitRc.gasUsed;
  const submittedAt = (await ethers.provider.getBlock(submitRc.blockNumber)).timestamp;

  let task = await rollup.getTask(input.taskId);
  const settledPhase = bounded ? 7 : 3;
  const deadline = Number(task.challengeDeadline);
  let challenged = false;
  const tryChallenge = async () => {
    try {
      const rc = await (await rollup.connect(challenger).openChallenge(input.taskId, { value: BOND })).wait();
      gas.challenge = rc.gasUsed;
      const adj = await (await rollup.connect(keeper).adjudicate(input.taskId)).wait();
      gas.adjudicate = adj.gasUsed;
      challenged = true;
    } catch (_e) {
      challenged = false;
    }
  };

  if (Number(task.phase) !== settledPhase && isWrong(teeState)) {
    if (challengerState === "online") await tryChallenge();
    if (challengerState === "lateOffline") {
      const wait = submittedAt + LATE_RETURN - (await now());
      if (wait > 0) await advance(wait);
      await tryChallenge();
    }
  }

  task = await rollup.getTask(input.taskId);
  if (Number(task.phase) !== settledPhase) {
    const wait = Number(task.challengeDeadline) + 1 - (await now());
    if (wait > 0) await advance(wait);
    const rc = await (await rollup.connect(keeper).finalize(input.taskId)).wait();
    gas.finalize = rc.gasUsed;
    task = await rollup.getTask(input.taskId);
  }

  let settledAt;
  if (bounded) {
    const block = await ethers.provider.getBlock("latest");
    settledAt = block.timestamp;
  } else {
    settledAt = Number(task.settledAt);
  }
  const verdict = Number(task.verdict);
  // Correct finality: honest results settle with verdict 0, wrong results end with verdict != 0.
  const correct = isWrong(teeState) ? verdict !== 0 : verdict === 0;
  const total = gas.submit + gas.challenge + gas.adjudicate + gas.finalize;
  return {
    system, teeState, challengerState, batch, steps: STEPS,
    correctFinality: correct,
    verdict,
    fastPath: bounded ? false : Boolean(task.fastPath),
    challenged,
    recomputed: bounded ? true : Boolean(task.recomputed),
    windowSeconds: bounded ? deadline - submittedAt : (deadline === 0 ? 0 : deadline - submittedAt),
    finalitySeconds: settledAt - submittedAt,
    gas: Object.fromEntries(Object.entries(gas).map(([k, v]) => [k, v.toString()])),
    totalGas: total.toString(),
  };
}

function summarise(rows) {
  const cells = new Map();
  for (const r of rows) {
    const key = `${r.system}|${r.teeState}|${r.challengerState}`;
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(r);
  }
  const out = [];
  for (const [key, list] of cells) {
    const [system, teeState, challengerState] = key.split("|");
    const n = list.length;
    const correct = list.filter((r) => r.correctFinality).length;
    const mean = (f) => list.reduce((a, r) => a + Number(f(r)), 0) / n;
    out.push({
      system, teeState, challengerState, n,
      correct, wrong: n - correct,
      fastPath: list.filter((r) => r.fastPath).length,
      recomputed: list.filter((r) => r.recomputed).length,
      meanFinalitySeconds: mean((r) => r.finalitySeconds),
      maxFinalitySeconds: Math.max(...list.map((r) => r.finalitySeconds)),
      meanTotalGas: Math.round(mean((r) => r.totalGas)),
    });
  }
  return out;
}

async function gasVsSteps(signers) {
  const [submitter, , keeper] = signers;
  const rows = [];
  for (const steps of [4, 16, 64, 128]) {
    const hybrid = await setupSystem("hybrid");
    const bounded = await setupSystem("recompute");
    for (const [name, ctx] of [["hybridFastFinalize", hybrid], ["recomputeFinalize", bounded], ["hybridChallenged", hybrid]]) {
      const input = makeInput(`gas:${name}:${steps}`, steps, { forge: name === "hybridChallenged" });
      const subSig = await sign(submitter, ctx.rollup, input);
      let submitRc;
      if (name === "recomputeFinalize") {
        submitRc = await (await ctx.rollup.connect(submitter).submit(input, subSig, { value: BOND })).wait();
      } else {
        const instSig = await sign(ctx.okInstance, ctx.rollup, input);
        submitRc = await (await ctx.rollup.connect(submitter).submit(input, subSig, instSig, { value: BOND })).wait();
      }
      let settleGas = 0n;
      let challengeGas = 0n;
      if (name === "hybridChallenged") {
        challengeGas = (await (await ctx.rollup.connect(signers[1]).openChallenge(input.taskId, { value: BOND })).wait()).gasUsed;
        settleGas = (await (await ctx.rollup.connect(keeper).adjudicate(input.taskId)).wait()).gasUsed;
      } else {
        const t = await ctx.rollup.getTask(input.taskId);
        await advance(Number(t.challengeDeadline) + 1 - (await now()));
        settleGas = (await (await ctx.rollup.connect(keeper).finalize(input.taskId)).wait()).gasUsed;
      }
      rows.push({
        path: name, steps,
        submitGas: submitRc.gasUsed.toString(),
        challengeGas: challengeGas.toString(),
        settleGas: settleGas.toString(),
        totalGas: (submitRc.gasUsed + challengeGas + settleGas).toString(),
      });
    }
  }
  return rows;
}

async function main() {
  const signers = await ethers.getSigners();
  const rows = [];
  const registration = {};
  for (const system of SYSTEMS) {
    const ctx = await setupSystem(system);
    if (ctx.rollup.registrationGas) registration[system] = ctx.rollup.registrationGas;
    for (const teeState of TEE_STATES) {
      for (const challengerState of CHALLENGERS) {
        for (let b = 0; b < BATCHES; ++b) {
          rows.push(await runOne(system, ctx, teeState, challengerState, b, signers));
        }
        process.stdout.write(`${system} ${teeState} ${challengerState} done\n`);
      }
    }
  }
  fs.writeFileSync(path.join(OUT, "e2_records.jsonl"), rows.map((r) => JSON.stringify(r)).join("\n") + "\n");
  const summary = summarise(rows);
  const steps = await gasVsSteps(signers);
  const record = {
    schemaVersion: "hybrid-tee-rollup.stageI.e2.v1",
    environment: "local Hardhat in-process chain, solc 0.8.26, cancun; protocol time via evm_increaseTime",
    parameters: { steps: STEPS, batchesPerCell: BATCHES, shortWindow: SHORT, longWindow: LONG, fastRecomputeWindow: FAST_RECOMPUTE_WINDOW, lateReturnSeconds: LATE_RETURN, bondWei: BOND.toString() },
    instanceRegistrationGasReplayVerifier: registration,
    summary,
    gasVsSteps: steps,
    notes: [
      "Replay verifier: quote verification cost is not included; see e1_dcap.json for the Sepolia Automata cost.",
      "Finality time is block-timestamp seconds from submission to settlement, not wall-clock time.",
      "recompute = BoundedTaskRollup with challengeWindow = longWindow; recomputeFast uses a 12 s window. Both recompute every task at finalize.",
    ],
  };
  fs.writeFileSync(path.join(OUT, "e2_summary.json"), JSON.stringify(record, null, 2));
  console.table(summary.map((s) => ({ ...s })));
  console.table(steps);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
