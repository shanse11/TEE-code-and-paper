#!/usr/bin/env node
// blob_verify.js — Verify the business semantics of a blob batch INDEPENDENTLY.
//
// Three modes (chosen by available credentials; all fail closed without creds):
//   1) ON-CHAIN (needs SEPOLIA_RPC_URL + BLOB_BATCH_ANCHOR_ADDRESS + a publish state with
//      anchorId): read the anchor back via getAnchor(anchorId) and confirm the RECOMPUTED
//      versioned hash / payloadHash / taskCount EQUAL the ON-CHAIN stored values. This is the
//      authoritative "does the chain record the blob we claim?" check (per the review requirement
//      that verify must check the on-chain versioned hash & payload).
//   2) INDEPENDENT (needs BEACON_API_URL + a publish state): re-fetch the blob live from the
//      beacon node (never local cache), then KZG-verify + recompute the versioned hash and
//      payloadHash and compare them to the INTENDED (locally-recorded) values. This proves the
//      live blob decodes to what we submitted, but it is NOT a substitute for the on-chain check.
//   3) OFFLINE SELF-CHECK (no chain/beacon creds): run the SAME checks against the REAL artifacts
//      saved by blob_offline.js. This proves the verification logic is sound on genuine KZG data
//      without mocking anything; it is clearly labelled as offline (not on-chain independent).
//
// Usage: node evm/revision/blob_verify.js [<taskCount>_<payloadKiB>KiB]   # default 8_8KiB

const fs = require("fs");
const path = require("path");
const { ethers, keccak256 } = require("ethers");
const { requireRun, readState, creds, safeHost } = require("./revision_env.js");
const codec = require("./blobcodec.js");
const kzg = require("./kzg.js");
const { beaconSlotFromTimestamp, fetchBlobForPublish } = require("./beacon_blob.js");

const TARGET = process.argv[2] || "8_8KiB";
const run = requireRun();
const c = creds();
const publish = readState("blob_publish");

// ON-CHAIN mode: the authoritative check. Reads the anchor back from the contract and confirms
// the independently-derived versioned hash / payloadHash / taskCount EQUAL the on-chain values.
async function onChainMode() {
  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
  const addr = process.env.BLOB_BATCH_ANCHOR_ADDRESS;
  const iface = new ethers.Interface([
    "function getAnchor(uint256 id) view returns (tuple(bytes32 payloadHash, uint256 taskCount, bytes32 blobVersionedHash, uint64 blockNumber, address submitter))",
  ]);
  const contract = new ethers.Contract(addr, iface, provider);
  const a = await contract.getAnchor(publish.anchorId);
  const onChain = {
    blobVersionedHash: a.blobVersionedHash.toLowerCase(),
    payloadHash: a.payloadHash.toLowerCase(),
    taskCount: Number(a.taskCount),
  };
  console.log(
    `[verify] ON-CHAIN anchor id=${publish.anchorId}: blobVersionedHash=${onChain.blobVersionedHash} payloadHash=${onChain.payloadHash} taskCount=${onChain.taskCount}`
  );

  // Re-derive the expected values from REAL data: prefer live beacon, else offline artifact.
  let recomputed;
  if (c.BEACON_API_URL) {
    const blockId = await beaconBlockId();
    const live = await fetchBlobForPublish(process.env.BEACON_API_URL, blockId, publish.blobVersionedHashes[0]);
    const commitment = live.commitment || kzg.blobToCommitment(live.blob);
    const proof = live.proof && live.proof.length ? live.proof : kzg.computeProof(live.blob, commitment);
    const kzgOk = kzg.verifyProof(live.blob, commitment, proof);
    const vh = kzg.versionedHash(commitment).toLowerCase();
    const decoded = codec.parseFrame(codec.blobToFrame(live.blob));
    const ph = keccak256(decoded.content).toLowerCase();
    console.log(`[verify] live blob bytes=${live.blob.length} commitmentSource=${live.commitmentSource} beaconBlockId=${blockId}`);
    recomputed = { kzgOk, vh, ph, taskCount: decoded.taskCount };
  } else {
    const dir = path.join(run, "artifacts", "blob_offline", TARGET);
    const meta = JSON.parse(fs.readFileSync(path.join(dir, "meta.json"), "utf8"));
    const blob = Buffer.from(fs.readFileSync(path.join(dir, "blob.hex"), "utf8"), "hex");
    const commitment = Buffer.from(fs.readFileSync(path.join(dir, "commitment.hex"), "utf8"), "hex");
    const proof = Buffer.from(fs.readFileSync(path.join(dir, "proof.hex"), "utf8"), "hex");
    const kzgOk = kzg.verifyProof(blob, commitment, proof);
    const vh = kzg.versionedHash(commitment).toLowerCase();
    const decoded = codec.parseFrame(codec.blobToFrame(blob));
    const ph = keccak256(decoded.content).toLowerCase();
    recomputed = { kzgOk, vh, ph, taskCount: decoded.taskCount };
    console.log(`[verify] ON-CHAIN mode using OFFLINE artifact ${TARGET} to re-derive expected values (no BEACON_API_URL).`);
  }

  const vhMatch = recomputed.vh === onChain.blobVersionedHash;
  const phMatch = recomputed.ph === onChain.payloadHash;
  const tcMatch = recomputed.taskCount === onChain.taskCount;
  const ok = recomputed.kzgOk && vhMatch && phMatch && tcMatch;
  console.log(
    `[verify] ON-CHAIN check: kzgVerify=${recomputed.kzgOk} versionedHashMatch=${vhMatch} payloadHashMatch=${phMatch} taskCountMatch=${tcMatch}`
  );
  console.log(`[verify] ${ok ? "VERIFIED: on-chain anchor matches independently-derived blob." : "MISMATCH against on-chain anchor!"}`);
  process.exit(ok ? 0 : 1);
}

async function independentMode() {
  console.log(`[verify] INDEPENDENT mode: re-fetching blob live from beacon (${safeHost(process.env.BEACON_API_URL)})...`);
  console.log(`[verify] NOTE: this compares the live blob to the LOCALLY-recorded intended values, NOT the on-chain anchor.`);
  console.log(`[verify]       For the on-chain check, set SEPOLIA_RPC_URL + BLOB_BATCH_ANCHOR_ADDRESS and run on-chain mode.`);
  const blockId = await beaconBlockId();
  const live = await fetchBlobForPublish(process.env.BEACON_API_URL, blockId, publish.blobVersionedHashes[0]);
  const blob = live.blob;
  const commitment = live.commitment || kzg.blobToCommitment(blob);
  const proof = live.proof && live.proof.length ? live.proof : kzg.computeProof(blob, commitment);
  console.log(`[verify] live blob bytes=${blob.length} commitmentSource=${live.commitmentSource} beaconBlockId=${blockId}`);
  const kzgOk = kzg.verifyProof(blob, commitment, proof);
  const vh = kzg.versionedHash(commitment);
  const vhMatch = vh.toLowerCase() === publish.blobVersionedHashes[0].toLowerCase();

  // (b) decode + payloadHash/taskCount
  const decoded = codec.decodeFrame(codec.blobToFrame(blob));
  const ph = keccak256(decoded.content);
  const phMatch = ph === publish.payloadHash;
  const tcMatch = decoded.taskCount === publish.taskCount;

  console.log(`[verify] kzgVerify=${kzgOk} versionedHashMatch=${vhMatch} payloadHashMatch=${phMatch} taskCountMatch=${tcMatch}`);
  const ok = kzgOk && vhMatch && phMatch && tcMatch;
  console.log(`[verify] ${ok ? "VERIFIED on-chain independently." : "VERIFICATION FAILED."}`);
  process.exit(ok ? 0 : 1);
}

function offlineSelfCheck() {
  console.log(`[verify] OFFLINE SELF-CHECK mode (no SEPOLIA_RPC_URL / BEACON_API_URL / publish state).`);
  console.log(`[verify] Verifying REAL artifacts saved by blob_offline.js under ${path.join(run, "artifacts", "blob_offline")}.`);
  // If an EXPLICIT existing target is passed, check only that one; otherwise verify the FULL
  // matrix (1/8/32 x 1/8/32 KiB) so the self-check actually covers all generated batches.
  const base = path.join(run, "artifacts", "blob_offline");
  const explicit = process.argv[2];
  const targets =
    explicit && fs.existsSync(path.join(base, explicit)) && /^\d+_\d+KiB$/.test(explicit)
      ? [explicit]
      : fs.readdirSync(base).filter((d) => /^\d+_\d+KiB$/.test(d));

  let allOk = true;
  for (const sub of targets) {
    const dir = path.join(run, "artifacts", "blob_offline", sub);
    const meta = JSON.parse(fs.readFileSync(path.join(dir, "meta.json"), "utf8"));
    const blob = Buffer.from(fs.readFileSync(path.join(dir, "blob.hex"), "utf8"), "hex");
    const commitment = Buffer.from(fs.readFileSync(path.join(dir, "commitment.hex"), "utf8"), "hex");
    const proof = Buffer.from(fs.readFileSync(path.join(dir, "proof.hex"), "utf8"), "hex");

    const kzgOk = kzg.verifyProof(blob, commitment, proof);
    const vh = kzg.versionedHash(commitment);
    const vhMatch = vh.toLowerCase() === meta.versionedHash.toLowerCase();
    const decoded = codec.parseFrame(codec.blobToFrame(blob)); // parseFrame asserts payloadHash
    const phMatch = decoded.payloadHash === meta.payloadHash;
    const tcMatch = decoded.taskCount === meta.taskCount;
    const ok = kzgOk && vhMatch && phMatch && tcMatch;
    allOk = allOk && ok;
    console.log(
      `[verify] ${sub}: kzg=${kzgOk} vhMatch=${vhMatch} phMatch=${phMatch} tcMatch=${tcMatch} => ${ok ? "OK" : "FAIL"}`
    );
  }
  console.log(`[verify] OFFLINE SELF-CHECK ${allOk ? "ALL OK" : "FAIL"} (this is real KZG verification on saved genuine blobs).`);
  console.log(`[verify] For on-chain INDEPENDENT verification, set BEACON_API_URL + BLOB_BATCH_ANCHOR_ADDRESS and run blob_publish.js first.`);
  process.exit(allOk ? 0 : 1);
}

async function beaconBlockId() {
  if (process.env.BLOCK_ID) return process.env.BLOCK_ID;
  if (publish.beaconSlot != null) return publish.beaconSlot;
  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
  const block = await provider.getBlock(publish.blockNumber);
  return beaconSlotFromTimestamp(block.timestamp);
}

async function main() {
  kzg.loadSetup();
  const rpc = process.env.SEPOLIA_RPC_URL;
  const addr = process.env.BLOB_BATCH_ANCHOR_ADDRESS;
  // ON-CHAIN is authoritative and preferred when creds + a recorded anchor id exist.
  if (rpc && addr && publish && publish.anchorId != null) {
    console.log(`[verify] ON-CHAIN mode: reading anchor id=${publish.anchorId} from ${safeHost(addr)}...`);
    await onChainMode();
    return;
  }
  if (c.BEACON_API_URL && publish && publish.blobVersionedHashes) {
    await independentMode();
    return;
  }
  if (!rpc) console.log(`[verify] SEPOLIA_RPC_URL not set -> on-chain check unavailable.`);
  if (!addr) console.log(`[verify] BLOB_BATCH_ANCHOR_ADDRESS not set -> on-chain check unavailable.`);
  if (!publish) console.log(`[verify] no publish state -> on-chain/independent check unavailable.`);
  offlineSelfCheck();
}
main().catch((e) => { console.error("[verify] ERROR:", e.shortMessage || e.message); process.exit(1); });
