const fs = require("fs");
const path = require("path");
const { ethers, network } = require("hardhat");

const MISMATCH_RESPONSE = 1n << 0n;
const MISMATCH_TRACE = 1n << 3n;

function sha256Utf8(value) {
  return ethers.sha256(ethers.toUtf8Bytes(value));
}

function sha256Abi(types, values) {
  const coder = ethers.AbiCoder.defaultAbiCoder();
  return ethers.sha256(coder.encode(types, values));
}

function fieldHash(name) {
  return sha256Utf8(name);
}

function buildMerkleBundle(entries) {
  const leaves = entries.map((entry) => sha256Abi(["bytes32", "bytes32"], [fieldHash(entry.name), entry.valueHash]));
  let levels = [leaves];
  while (levels[levels.length - 1].length > 1) {
    const current = levels[levels.length - 1];
    const next = [];
    for (let i = 0; i < current.length; i += 2) {
      const left = current[i];
      const right = i + 1 < current.length ? current[i + 1] : left;
      next.push(sha256Abi(["bytes32", "bytes32"], [left, right]));
    }
    levels.push(next);
  }
  const proofs = {};
  for (let leafIndex = 0; leafIndex < entries.length; leafIndex++) {
    const siblingHashes = [];
    const siblingOnLeft = [];
    let index = leafIndex;
    for (let levelIndex = 0; levelIndex < levels.length - 1; levelIndex++) {
      const level = levels[levelIndex];
      let siblingIndex = index % 2 === 0 ? index + 1 : index - 1;
      if (siblingIndex >= level.length) siblingIndex = index;
      siblingHashes.push(level[siblingIndex]);
      siblingOnLeft.push(index % 2 === 1);
      index = Math.floor(index / 2);
    }
    proofs[entries[leafIndex].name] = { siblingHashes, siblingOnLeft };
  }
  return { merkleRoot: levels[levels.length - 1][0], proofs };
}

async function signAttestation(signer, inputHash, outputHash, nonce, mrenclave) {
  const digest = sha256Abi(["bytes32", "bytes32", "bytes32", "bytes32"], [inputHash, outputHash, nonce, mrenclave]);
  return signer.signMessage(ethers.getBytes(digest));
}

async function deployContracts() {
  const [deployer, teeSigner, challenger, responder, watchdog] = await ethers.getSigners();
  const verifierFactory = await ethers.getContractFactory("MockTEEVerifier");
  const verifier = await verifierFactory.deploy(teeSigner.address);
  await verifier.waitForDeployment();

  const daFactory = await ethers.getContractFactory("MockDARegistry");
  const daRegistry = await daFactory.deploy();
  await daRegistry.waitForDeployment();

  const rollupFactory = await ethers.getContractFactory("HybridTEERollup");
  const rollup = await rollupFactory.deploy(
    await verifier.getAddress(),
    await daRegistry.getAddress(),
    60,
    2,
    16
  );
  await rollup.waitForDeployment();

  return { deployer, teeSigner, challenger, responder, watchdog, verifier, daRegistry, rollup };
}

async function mineSeconds(seconds) {
  await network.provider.send("evm_increaseTime", [seconds]);
  await network.provider.send("evm_mine");
}

async function receiptOf(txPromise) {
  const tx = await txPromise;
  return tx.wait();
}

async function measureSample(env, sampleIndex, payloadSize) {
  const prompt = `gas sample ${sampleIndex} payload ${payloadSize}`;
  const response = "x".repeat(payloadSize);
  const inputHash = sha256Utf8(prompt);
  const outputHash = sha256Utf8(response);
  const mrenclave = sha256Utf8(`mrenclave-${sampleIndex}`);
  const nonce = sha256Utf8(`nonce-${sampleIndex}`);
  const signature = await signAttestation(env.teeSigner, inputHash, outputHash, nonce, mrenclave);
  const txId = sha256Utf8(`tx-${sampleIndex}-${payloadSize}`);
  const txIdHash = sha256Utf8(`tx-label-${sampleIndex}-${payloadSize}`);
  const entries = [
    { name: "tx_id", valueHash: txIdHash },
    { name: "prompt", valueHash: inputHash },
    { name: "response", valueHash: outputHash },
    { name: "mrenclave", valueHash: mrenclave },
  ];
  const bundle = buildMerkleBundle(entries);
  const payloadHash = sha256Abi(["bytes32", "bytes32", "bytes32", "bytes32"], [txIdHash, inputHash, outputHash, mrenclave]);
  const daPointer = sha256Abi(["bytes32", "bytes32"], [payloadHash, bundle.merkleRoot]);
  const proofHash = await env.verifier.computeProofHash(nonce, signature);
  const commit = {
    stateRoot: sha256Abi(["bytes32", "bytes32", "bytes32"], [inputHash, outputHash, mrenclave]),
    outputHash,
    proofHash,
    daPointer,
    daMerkleRoot: bundle.merkleRoot,
  };
  const responseProof = bundle.proofs.response;

  const registerReceipt = await receiptOf(env.daRegistry.registerRecord(daPointer, payloadHash, bundle.merkleRoot));
  const submitReceipt = await receiptOf(env.rollup.submitRollup(txId, inputHash, mrenclave, nonce, signature, commit));
  const openReceipt = await receiptOf(
    env.rollup
      .connect(env.challenger)
      .openChallenge(
        txId,
        Number(MISMATCH_RESPONSE),
        8,
        false,
        fieldHash("response"),
        outputHash,
        responseProof.siblingHashes,
        responseProof.siblingOnLeft
      )
  );
  const respondReceipt = await receiptOf(
    env.rollup.connect(env.responder).respondChallenge(txId, Number(MISMATCH_RESPONSE))
  );
  const stepOneReceipt = await receiptOf(env.rollup.stepChallenge(txId, 7));
  await mineSeconds(3);
  const recoverReceipt = await receiptOf(env.rollup.connect(env.watchdog).recoverChallenge(txId));
  const stepTwoReceipt = await receiptOf(env.rollup.stepChallenge(txId, 7));
  const stepThreeReceipt = await receiptOf(env.rollup.stepChallenge(txId, 7));
  const replayReceipt = await receiptOf(
    env.rollup.replayChallenge(txId, 7, sha256Utf8("expected"), sha256Utf8("claimed"), false)
  );
  const resolveReceipt = await receiptOf(
    env.rollup.resolveChallenge(txId, Number(MISMATCH_RESPONSE | MISMATCH_TRACE))
  );

  const finalSampleId = sha256Utf8(`tx-final-${sampleIndex}-${payloadSize}`);
  const finalTxLabel = sha256Utf8(`tx-final-label-${sampleIndex}-${payloadSize}`);
  const finalEntries = [
    { name: "tx_id", valueHash: finalTxLabel },
    { name: "prompt", valueHash: inputHash },
    { name: "response", valueHash: outputHash },
    { name: "mrenclave", valueHash: mrenclave },
  ];
  const finalBundle = buildMerkleBundle(finalEntries);
  const finalPayloadHash = sha256Abi(["bytes32", "bytes32", "bytes32", "bytes32"], [finalTxLabel, inputHash, outputHash, mrenclave]);
  const finalPointer = sha256Abi(["bytes32", "bytes32"], [finalPayloadHash, finalBundle.merkleRoot]);
  const finalProofHash = await env.verifier.computeProofHash(nonce, signature);
  const finalCommit = {
    stateRoot: sha256Abi(["bytes32", "bytes32", "bytes32"], [inputHash, outputHash, mrenclave]),
    outputHash,
    proofHash: finalProofHash,
    daPointer: finalPointer,
    daMerkleRoot: finalBundle.merkleRoot,
  };
  await receiptOf(env.daRegistry.registerRecord(finalPointer, finalPayloadHash, finalBundle.merkleRoot));
  await receiptOf(env.rollup.submitRollup(finalSampleId, inputHash, mrenclave, nonce, signature, finalCommit));
  await mineSeconds(61);
  const finalizeReceipt = await receiptOf(env.rollup.finalizeExpired([finalSampleId]));

  return {
    sample_index: sampleIndex,
    payload_size: payloadSize,
    register_da_gas: Number(registerReceipt.gasUsed),
    submit_rollup_gas: Number(submitReceipt.gasUsed),
    challenge_open_gas: Number(openReceipt.gasUsed),
    challenge_respond_gas: Number(respondReceipt.gasUsed),
    challenge_step_round1_gas: Number(stepOneReceipt.gasUsed),
    challenge_recover_gas: Number(recoverReceipt.gasUsed),
    challenge_step_round2_gas: Number(stepTwoReceipt.gasUsed),
    challenge_step_round3_gas: Number(stepThreeReceipt.gasUsed),
    challenge_replay_gas: Number(replayReceipt.gasUsed),
    challenge_resolve_gas: Number(resolveReceipt.gasUsed),
    finalize_gas: Number(finalizeReceipt.gasUsed),
  };
}

function toCsv(rows) {
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((key) => row[key]).join(","));
  }
  return lines.join("\n");
}

function average(rows, key) {
  return rows.reduce((sum, row) => sum + row[key], 0) / rows.length;
}

async function main() {
  const env = await deployContracts();
  const payloadSizes = [128, 512, 2048];
  const rows = [];
  let sampleIndex = 1;
  for (const payloadSize of payloadSizes) {
    rows.push(await measureSample(env, sampleIndex++, payloadSize));
  }

  const summary = {
    samples: rows.length,
    payload_sizes: payloadSizes,
    averages: {
      register_da_gas: average(rows, "register_da_gas"),
      submit_rollup_gas: average(rows, "submit_rollup_gas"),
      challenge_open_gas: average(rows, "challenge_open_gas"),
      challenge_respond_gas: average(rows, "challenge_respond_gas"),
      challenge_step_round1_gas: average(rows, "challenge_step_round1_gas"),
      challenge_recover_gas: average(rows, "challenge_recover_gas"),
      challenge_replay_gas: average(rows, "challenge_replay_gas"),
      challenge_resolve_gas: average(rows, "challenge_resolve_gas"),
      finalize_gas: average(rows, "finalize_gas"),
    },
  };

  const outputDir = path.resolve(__dirname, "../../paper_outputs/evm_gas");
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(path.join(outputDir, "measured_gas.csv"), toCsv(rows), "utf8");
  fs.writeFileSync(path.join(outputDir, "measured_gas_summary.json"), JSON.stringify(summary, null, 2), "utf8");

  const markdown = [
    "# 本地 EVM 实测 Gas 报告",
    "",
    "说明：本报告基于 Hardhat 本地测试链，对当前 Solidity 原型的关键操作进行 `gasUsed` 实测。",
    "",
    "## 样本结果",
    "",
    "| Payload | register DA | submit | open | respond | step1 | recover | replay | resolve | finalize |",
    "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ...rows.map((row) =>
      `| ${row.payload_size} | ${row.register_da_gas} | ${row.submit_rollup_gas} | ${row.challenge_open_gas} | ${row.challenge_respond_gas} | ${row.challenge_step_round1_gas} | ${row.challenge_recover_gas} | ${row.challenge_replay_gas} | ${row.challenge_resolve_gas} | ${row.finalize_gas} |`
    ),
    "",
    "## 平均结果",
    "",
    `- register DA: ${summary.averages.register_da_gas.toFixed(2)}`,
    `- submit rollup: ${summary.averages.submit_rollup_gas.toFixed(2)}`,
    `- challenge open: ${summary.averages.challenge_open_gas.toFixed(2)}`,
    `- challenge respond: ${summary.averages.challenge_respond_gas.toFixed(2)}`,
    `- challenge step (round1): ${summary.averages.challenge_step_round1_gas.toFixed(2)}`,
    `- challenge recover: ${summary.averages.challenge_recover_gas.toFixed(2)}`,
    `- challenge replay: ${summary.averages.challenge_replay_gas.toFixed(2)}`,
    `- challenge resolve: ${summary.averages.challenge_resolve_gas.toFixed(2)}`,
    `- finalize: ${summary.averages.finalize_gas.toFixed(2)}`,
    "",
    "## 解释",
    "",
    "- 这些结果是本地 EVM 实测，不再只是纯字节估算。",
    "- 当前合约主要测量链上提交、挑战、恢复、重放和结算的状态推进成本。",
    "- 真实主网部署成本仍会受 calldata 定价、blob 价格和网络环境影响，因此这组数据更适合作为“本地合约实测基线”。",
    "",
  ].join("\n");

  fs.writeFileSync(path.join(outputDir, "measured_gas_report.md"), markdown, "utf8");
  console.log(`Gas measurement outputs written to: ${outputDir}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
