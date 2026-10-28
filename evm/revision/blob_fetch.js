#!/usr/bin/env node
// blob_fetch.js — INDEPENDENT retrieval of the real blob from a beacon node (Fusaka/PeerDAS
// aware: uses the official GET /eth/v1/beacon/blobs/{block_id} endpoint). RESUMABLE.
//
// Security / independence guarantees:
//   * The blob is fetched LIVE from the beacon API every run — it is NEVER read from the
//     locally-encoded artifact ("independent retrieval, no local cache").
//   * A calldata benchmark anchor (no blobVersionedHash) is explicitly NOT treated as a blob.
//   * BEACON_API_URL is required; on absence the script fails closed with NO network call.
//
// Usage:
//   export REVISION_RUN=<abs> BEACON_API_URL=https://...  (BLOCK_ID optional; else from publish state)
//   node evm/revision/blob_fetch.js

const { ethers, keccak256 } = require("ethers");
const { requireRun, readState, writeState, preflightOrFail, creds, safeHost } = require("./revision_env.js");
const codec = require("./blobcodec.js");
const { beaconSlotFromTimestamp, fetchBlobForPublish } = require("./beacon_blob.js");

const run = requireRun();
const c = creds();
console.log(`[fetch] creds=${JSON.stringify({ BEACON_API_URL: c.BEACON_API_URL })}  beaconHost=${safeHost(process.env.BEACON_API_URL)}`);

// ---- Preflight (fail closed) ----
preflightOrFail(c.BEACON_API_URL, "BEACON_API_URL is not set — independent blob retrieval is impossible. Refusing (no fetch performed).");

// PeerDAS / Fusaka note (Sepolia activated Fusaka 2025-10-14; EIP-7594 erasure-codes blobs into
// 128 columns and most nodes custody only part of them). A REGULAR beacon node therefore will NOT
// serve a full blob it does not custody — independent retrieval requires a supernode
// (Teku --rest-api-getblobs-sidecars-download-enabled / Lighthouse --prune-blobs false /
// Prysm --semi-supernode) or a public keyless endpoint such as Pinax
// (GET /eth/v1/beacon/blobs/{block_id}?versioned_hashes=...). The script itself performs a LIVE
// fetch and never substitutes the local artifact; if the configured node cannot serve the blob it
// will fail (see 404 handling below) rather than impersonate a successful retrieval.
console.log(`[fetch] PeerDAS note: ensure BEACON_API_URL is a supernode or public endpoint (e.g. Pinax); regular nodes under Fusaka may 404.`);

const publish = readState("blob_publish");
const versionedHash = publish ? publish.blobVersionedHashes[0] : undefined;
preflightOrFail(versionedHash, "No versioned hash available: run blob_publish.js first to learn the blob's versioned hash.");

// For a calldata-only anchor there is no blob to fetch.
if (publish && !publish.blobVersionedHashes) {
  console.error("[fetch] The published anchor was a CALDATA batch (no blobVersionedHash). Nothing to fetch; use blob_verify.js (calldata path).");
  process.exit(0);
}

async function resolveBlockId() {
  if (process.env.BLOCK_ID) return { blockId: process.env.BLOCK_ID, source: "BLOCK_ID" };
  if (publish.beaconSlot != null) return { blockId: publish.beaconSlot, source: "publish.beaconSlot" };
  preflightOrFail(process.env.SEPOLIA_RPC_URL && publish.blockNumber != null, "Cannot derive a beacon slot: set BLOCK_ID or publish.beaconSlot.");
  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
  const block = await provider.getBlock(publish.blockNumber);
  const slot = beaconSlotFromTimestamp(block.timestamp);
  return { blockId: slot, source: "execution-timestamp", executionBlock: Number(publish.blockNumber), timestamp: Number(block.timestamp) };
}

async function main() {
  const resolved = await resolveBlockId();
  const blockId = resolved.blockId;
  const beacon = process.env.BEACON_API_URL.replace(/\/+$/, "");
  console.log(`[fetch] beacon block id=${blockId} source=${resolved.source} executionBlock=${resolved.executionBlock ?? publish.blockNumber}`);
  console.log(`[fetch] GET ${safeHost(beacon)}/eth/v1/beacon/blobs/${blockId}?versioned_hashes=<hash>  (live, independent)`);
  let live;
  try {
    live = await fetchBlobForPublish(beacon, blockId, versionedHash);
  } catch (e) {
    console.error(`[fetch] ${e.message}`);
    if (e.status === 404) {
      console.error("[fetch] Block/slot not found, or this endpoint does not serve that blob.");
    }
    process.exit(1);
  }
  const blob = live.blob;
  console.log(`[fetch] retrieved blob bytes=${blob.length} commitmentSource=${live.commitmentSource} query=${live.querySource} id=${live.queriedBlockId}`);

  // Decode independently and recompute payloadHash — this is the off-chain verification.
  const decoded = codec.decodeFrame(codec.blobToFrame(blob));
  const recomputed = keccak256(decoded.content);
  const phMatch = recomputed === publish.payloadHash;
  console.log(`[fetch] decoded taskCount=${decoded.taskCount}  recomputedPayloadHash=${recomputed}`);
  console.log(`[fetch] expectedPayloadHash   =${publish.payloadHash}`);
  console.log(`[fetch] payloadHash match=${phMatch}  expectedTaskCount=${publish.taskCount} got=${decoded.taskCount}`);

  // NOTE: we deliberately do NOT persist the blob bytes as the source of truth for verification;
  // the blob is re-fetched on every run. We only record metadata + the match result.
  writeState("blob_fetch", {
    status: phMatch ? "fetched_and_matched" : "fetched_mismatch",
    blockId: String(blockId),
    blockIdSource: resolved.source,
    beaconHost: safeHost(beacon),
    retrievedAt: new Date().toISOString(),
    blobBytes: blob.length,
    recomputedPayloadHash: recomputed,
    onChainPayloadHash: publish.payloadHash,
    onChainTaskCount: publish.taskCount,
    decodedTaskCount: decoded.taskCount,
    payloadHashMatch: phMatch,
    taskCountMatch: decoded.taskCount === publish.taskCount,
  });
  console.log(`[fetch] ${phMatch ? "OK: independently retrieved blob matches anchored payloadHash." : "MISMATCH: retrieved blob does NOT match anchored payloadHash!"}`);
  console.log(`[fetch] next: node evm/revision/blob_verify.js`);
  process.exit(phMatch ? 0 : 1);
}

main().catch((e) => { console.error("[fetch] ERROR:", e.shortMessage || e.message); process.exit(1); });
