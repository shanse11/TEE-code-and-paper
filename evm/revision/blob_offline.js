#!/usr/bin/env node
// blob_offline.js — Real, runnable offline batch<->blob codec + KZG commitment/proof
// and a MALICIOUS-MODIFICATION negative example (no Mock, no network, no chain).
//
// Produces, for the matrix taskCount x payloadKiB in {1,8,32}:
//   - original frame bytes, blob (131072 B), KZG commitment(48 B), proof(48 B),
//     payloadHash (keccak256(content)), versionedHash (0x01||sha256(commit)[1:])
//   - a malicious-modification negative example (tampered content / tampered blob)
//     demonstrating cryptographic + application-layer detection.
// All artifacts are written under $REVISION_RUN/artifacts/blob_offline/ and the
// script is RESUMABLE (re-running re-verifies cached artifacts instead of recomputing).
//
// Usage:  node evm/revision/blob_offline.js
// (Requires REVISION_RUN to be the absolute run directory, matching evm/revision/hardhat.config.js.)

const fs = require("fs");
const path = require("path");
const codec = require("./blobcodec.js");
const kzg = require("./kzg.js");

const REVISION_RUN = process.env.REVISION_RUN;
if (!REVISION_RUN || !path.isAbsolute(REVISION_RUN)) {
  console.error("PREFLOW FAIL: REVISION_RUN must be an absolute run directory (same as evm/revision/hardhat.config.js).");
  console.error("  export REVISION_RUN=/abs/path/to/revision_runs/20260911T095029Z");
  process.exit(2);
}
const OUT_ROOT = path.join(REVISION_RUN, "artifacts", "blob_offline");
fs.mkdirSync(OUT_ROOT, { recursive: true });

const MATRIX = [];
for (const tc of [1, 8, 32]) for (const kb of [1, 8, 32]) MATRIX.push([tc, kb]);

function writeHex(dir, name, buf) {
  fs.writeFileSync(path.join(dir, name + ".hex"), Buffer.from(buf).toString("hex"));
}
function writeText(dir, name, s) {
  fs.writeFileSync(path.join(dir, name + ".txt"), s);
}

// One batch: encode, commit, prove, verify, build negative examples. Returns result object.
function processOne(taskCount, payloadKiB) {
  const batch = codec.makeBatch({ taskCount, payloadKiB });
  const blob = codec.frameToBlob(batch.frame);
  const commitment = kzg.blobToCommitment(blob);
  const proof = kzg.computeProof(blob, commitment);
  const vh = kzg.versionedHash(commitment);

  const posVerify = kzg.verifyProof(blob, commitment, proof);

  // Negative example A — content tampering: flip last content byte, re-encode, recompute.
  const tamperedFrame = Buffer.from(batch.frame);
  tamperedFrame[tamperedFrame.length - 1] ^= 0x01;
  const tamperedBlob = codec.frameToBlob(tamperedFrame);
  const tamperedCommitment = kzg.blobToCommitment(tamperedBlob);
  const tamperedProof = kzg.computeProof(tamperedBlob, tamperedCommitment);
  const tamperVsOriginal = kzg.verifyProof(tamperedBlob, commitment, proof); // expect false
  const tamperSelf = kzg.verifyProof(tamperedBlob, tamperedCommitment, tamperedProof); // expect true
  const tamperedVersionedHash = kzg.versionedHash(tamperedCommitment);
  // Application-layer detection: recompute keccak256 of the MODIFIED content and compare
  // to the ORIGINAL recorded payloadHash. A mismatch proves the blob content was altered.
  const tamperedContent = codec.decodeFrame(codec.blobToFrame(tamperedBlob)).content;
  const tamperedPayloadHash = require("ethers").keccak256(tamperedContent);
  const payloadHashChanged = tamperedPayloadHash !== batch.payloadHash;

  // Negative example B — blob-level tampering: flip a data byte in the serialized blob,
  // keep the ORIGINAL commitment+proof. Must fail.
  const blobTampered = Buffer.from(blob);
  blobTampered[40] ^= 0x01; // position inside first data region
  const blobLevelTamper = kzg.verifyProof(blobTampered, commitment, proof); // expect false

  // Decode independently and verify business semantics.
  const decoded = codec.parseFrame(codec.blobToFrame(blob));
  const decodeOk =
    decoded.payloadHash === batch.payloadHash &&
    decoded.taskCount === taskCount &&
    decoded.content.length === batch.content.length;

  const result = {
    taskCount,
    payloadKiB,
    frameLen: batch.frame.length,
    blobLen: blob.length,
    payloadHash: batch.payloadHash,
    versionedHash: vh,
    commitment: "0x" + commitment.toString("hex"),
    proof: "0x" + proof.toString("hex"),
    positiveVerify: posVerify,
    negative: {
      contentTamper_vsOriginalCommitment_valid: tamperVsOriginal, // expect false
      contentTamper_self_valid: tamperSelf, // expect true
      contentTamper_payloadHashChanged: payloadHashChanged, // expect true
      blobLevelTamper_valid: blobLevelTamper, // expect false
      tamperedVersionedHash: tamperedVersionedHash,
      tamperedPayloadHash: tamperedPayloadHash,
    },
    decodeOk,
    // Pass criteria for a REAL negative example:
    pass:
      posVerify === true &&
      tamperVsOriginal === false &&
      tamperSelf === true &&
      payloadHashChanged === true &&
      blobLevelTamper === false &&
      decodeOk === true,
  };
  return { result, blob, commitment, proof, tamperedBlob, tamperedCommitment, tamperedProof, batch };
}

function saveArtifacts(dir, data) {
  writeHex(dir, "blob", data.blob);
  writeHex(dir, "commitment", data.commitment);
  writeHex(dir, "proof", data.proof);
  writeHex(dir, "frame_original", data.batch.frame);
  writeHex(dir, "blob_tampered", data.tamperedBlob);
  writeHex(dir, "commitment_tampered", data.tamperedCommitment);
  writeHex(dir, "proof_tampered", data.tamperedProof);
  writeText(dir, "payloadHash", data.result.payloadHash);
  writeText(dir, "versionedHash", data.result.versionedHash);
  writeText(dir, "tampered_payloadHash", data.result.negative.tamperedPayloadHash);
  writeText(dir, "tampered_versionedHash", data.result.negative.tamperedVersionedHash);
  fs.writeFileSync(path.join(dir, "meta.json"), JSON.stringify(data.result, null, 2));
}

function main() {
  console.log(`[blob_offline] REVISION_RUN=${REVISION_RUN}`);
  console.log(`[blob_offline] trusted setup: ${path.join(__dirname, "trusted_setup.txt")}`);
  kzg.loadSetup();
  console.log(`[blob_offline] KZG trusted setup loaded (real Ethereum mainnet EIP-4844 SRS).\n`);

  let allPass = true;
  const rows = [];
  for (const [tc, kb] of MATRIX) {
    const dir = path.join(OUT_ROOT, `${tc}_${kb}KiB`);
    const metaPath = path.join(dir, "meta.json");
    let data;
    if (fs.existsSync(metaPath)) {
      // Resume: re-verify cached artifacts instead of recomputing.
      const cached = JSON.parse(fs.readFileSync(metaPath, "utf8"));
      const blob = Buffer.from(fs.readFileSync(path.join(dir, "blob.hex"), "utf8"), "hex");
      const commitment = Buffer.from(fs.readFileSync(path.join(dir, "commitment.hex"), "utf8"), "hex");
      const proof = Buffer.from(fs.readFileSync(path.join(dir, "proof.hex"), "utf8"), "hex");
      const reverify = kzg.verifyProof(blob, commitment, proof);
      const cachedPass = reverify && cached.negative.contentTamper_vsOriginalCommitment_valid === false;
      rows.push({ tc, kb, cached: true, pass: cachedPass, vh: cached.versionedHash });
      allPass = allPass && cachedPass;
      console.log(`[cached] tc=${tc} kb=${kb}KiB re-verify=${reverify} => ${cachedPass ? "PASS" : "FAIL"}  vh=${cached.versionedHash.slice(0, 14)}..`);
      continue;
    }
    fs.mkdirSync(dir, { recursive: true });
    data = processOne(tc, kb);
    saveArtifacts(dir, data);
    allPass = allPass && data.result.pass;
    rows.push({ tc, kb, cached: false, pass: data.result.pass, vh: data.result.versionedHash });
    const n = data.result.negative;
    console.log(
      `[new] tc=${tc} kb=${kb}KiB  pos=${data.result.positiveVerify}  ` +
        `tamperVsOrig=${n.contentTamper_vsOriginalCommitment_valid}(F)  ` +
        `tamperSelf=${n.contentTamper_self_valid}  blobLevelTamper=${n.blobLevelTamper_valid}(F)  ` +
        `phChanged=${n.contentTamper_payloadHashChanged}  decode=${data.result.decodeOk}  => ${data.result.pass ? "PASS" : "FAIL"}`
    );
  }

  // A dedicated, human-readable negative example artifact set.
  const negDir = path.join(OUT_ROOT, "NEGATIVE_EXAMPLE");
  if (!fs.existsSync(path.join(negDir, "meta.json"))) {
    fs.mkdirSync(negDir, { recursive: true });
    const ex = processOne(8, 8);
    saveArtifacts(negDir, ex);
    console.log(`\n[neg] Negative-example artifacts saved to ${negDir}`);
  }

  console.log(`\n[summary] ${allPass ? "ALL PASS" : "SOME FAIL"}  (${rows.length} batches)`);
  console.log(`[summary] artifacts root: ${OUT_ROOT}`);
  process.exit(allPass ? 0 : 1);
}

main();
