const { expect } = require("chai");
const { ethers, network } = require("hardhat");

const MISMATCH_RESPONSE = 1n << 0n;
const MISMATCH_ATTESTATION = 1n << 1n;
const MISMATCH_DA = 1n << 2n;
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
  return {
    merkleRoot: levels[levels.length - 1][0],
    proofs,
  };
}

async function signAttestation(signer, inputHash, outputHash, nonce, mrenclave) {
  const digest = sha256Abi(["bytes32", "bytes32", "bytes32", "bytes32"], [inputHash, outputHash, nonce, mrenclave]);
  return signer.signMessage(ethers.getBytes(digest));
}

async function deployFixture() {
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

async function submitSample(env, overrides = {}) {
  const prompt = overrides.prompt || "prompt";
  const response = overrides.response || "line1\nline2\nline3\nline4";
  const inputHash = sha256Utf8(prompt);
  const outputHash = sha256Utf8(response);
  const mrenclave = overrides.mrenclave || sha256Utf8("mrenclave-test");
  const nonce = overrides.nonce || sha256Utf8("nonce-1");
  const attestationSignature = overrides.signature || await signAttestation(env.teeSigner, inputHash, outputHash, nonce, mrenclave);

  const entries = [
    { name: "tx_id", valueHash: sha256Utf8(overrides.txLabel || "tx-1") },
    { name: "prompt", valueHash: inputHash },
    { name: "response", valueHash: outputHash },
    { name: "mrenclave", valueHash: mrenclave },
  ];
  const bundle = buildMerkleBundle(entries);
  const payloadHash = sha256Abi(
    ["bytes32", "bytes32", "bytes32", "bytes32"],
    [entries[0].valueHash, entries[1].valueHash, entries[2].valueHash, entries[3].valueHash]
  );
  const daPointer = sha256Abi(["bytes32", "bytes32"], [payloadHash, bundle.merkleRoot]);
  await env.daRegistry.registerRecord(daPointer, payloadHash, bundle.merkleRoot);

  const proofHash = await env.verifier.computeProofHash(nonce, attestationSignature);
  const commit = {
    stateRoot: sha256Abi(["bytes32", "bytes32", "bytes32"], [inputHash, outputHash, mrenclave]),
    outputHash,
    proofHash,
    daPointer,
    daMerkleRoot: bundle.merkleRoot,
  };
  const txId = overrides.txId || sha256Utf8(overrides.txLabel || "tx-1");
  await env.rollup.submitRollup(txId, inputHash, mrenclave, nonce, attestationSignature, commit);

  return {
    txId,
    prompt,
    response,
    inputHash,
    outputHash,
    mrenclave,
    nonce,
    attestationSignature,
    bundle,
    payloadHash,
    daPointer,
    commit,
  };
}

describe("HybridTEERollup", function () {
  it("submits a valid compact commit anchored to DA and attestation", async function () {
    const env = await deployFixture();
    const sample = await submitSample(env);
    const txRecord = await env.rollup.getTransaction(sample.txId);

    expect(txRecord.status).to.equal(1n);
    expect(txRecord.commit.outputHash).to.equal(sample.outputHash);
    expect(txRecord.commit.daMerkleRoot).to.equal(sample.bundle.merkleRoot);
  });

  it("runs recoverable challenge flow and slashes after replay mismatch", async function () {
    const env = await deployFixture();
    const sample = await submitSample(env, { txLabel: "tx-recover" });
    const responseProof = sample.bundle.proofs.response;
    await env.rollup
      .connect(env.challenger)
      .openChallenge(
        sample.txId,
        Number(MISMATCH_RESPONSE),
        4,
        false,
        fieldHash("response"),
        sample.outputHash,
        responseProof.siblingHashes,
        responseProof.siblingOnLeft
      );
    await env.rollup.connect(env.responder).respondChallenge(sample.txId, Number(MISMATCH_RESPONSE));
    await env.rollup.stepChallenge(sample.txId, 3);
    await network.provider.send("evm_increaseTime", [3]);
    await network.provider.send("evm_mine");
    await env.rollup.connect(env.watchdog).recoverChallenge(sample.txId);
    await env.rollup.stepChallenge(sample.txId, 3);
    await env.rollup.replayChallenge(sample.txId, 3, sha256Utf8("expected"), sha256Utf8("claimed"), false);
    await env.rollup.resolveChallenge(sample.txId, Number(MISMATCH_RESPONSE | MISMATCH_TRACE));

    const session = await env.rollup.getChallengeSession(sample.txId);
    const txRecord = await env.rollup.getTransaction(sample.txId);
    expect(session.challengeSuccess).to.equal(true);
    expect(txRecord.status).to.equal(3n);
  });

  it("finalizes pending transactions after the dispute window", async function () {
    const env = await deployFixture();
    const sample = await submitSample(env, { txLabel: "tx-finalize" });

    await network.provider.send("evm_increaseTime", [61]);
    await network.provider.send("evm_mine");
    await env.rollup.finalizeExpired([sample.txId]);

    const txRecord = await env.rollup.getTransaction(sample.txId);
    expect(txRecord.status).to.equal(2n);
  });

  it("rejects invalid attestation signatures", async function () {
    const env = await deployFixture();
    const prompt = "invalid";
    const response = "output";
    const inputHash = sha256Utf8(prompt);
    const outputHash = sha256Utf8(response);
    const mrenclave = sha256Utf8("mrenclave-invalid");
    const nonce = sha256Utf8("nonce-invalid");
    const badSignature = await env.challenger.signMessage(
      ethers.getBytes(sha256Abi(["bytes32", "bytes32", "bytes32", "bytes32"], [inputHash, outputHash, nonce, mrenclave]))
    );
    const bundle = buildMerkleBundle([
      { name: "tx_id", valueHash: sha256Utf8("tx-bad") },
      { name: "prompt", valueHash: inputHash },
      { name: "response", valueHash: outputHash },
      { name: "mrenclave", valueHash: mrenclave },
    ]);
    const payloadHash = sha256Abi(
      ["bytes32", "bytes32", "bytes32", "bytes32"],
      [sha256Utf8("tx-bad"), inputHash, outputHash, mrenclave]
    );
    const daPointer = sha256Abi(["bytes32", "bytes32"], [payloadHash, bundle.merkleRoot]);
    await env.daRegistry.registerRecord(daPointer, payloadHash, bundle.merkleRoot);
    const proofHash = await env.verifier.computeProofHash(nonce, badSignature);
    const commit = {
      stateRoot: sha256Abi(["bytes32", "bytes32", "bytes32"], [inputHash, outputHash, mrenclave]),
      outputHash,
      proofHash,
      daPointer,
      daMerkleRoot: bundle.merkleRoot,
    };

    let reverted = false;
    try {
      await env.rollup.submitRollup(sha256Utf8("tx-bad"), inputHash, mrenclave, nonce, badSignature, commit);
    } catch (error) {
      reverted = String(error.message).includes("attestation invalid");
    }
    expect(reverted).to.equal(true);
  });

  it("verifies DA field witnesses against the stored Merkle root", async function () {
    const env = await deployFixture();
    const sample = await submitSample(env, { txLabel: "tx-da-proof" });
    const responseProof = sample.bundle.proofs.response;

    const proofStatus = await env.rollup.verifyDAField(
      sample.txId,
      fieldHash("response"),
      sample.outputHash,
      responseProof.siblingHashes,
      responseProof.siblingOnLeft
    );

    expect(proofStatus[0]).to.equal(true);
    expect(proofStatus[1]).to.equal(true);
  });
});
