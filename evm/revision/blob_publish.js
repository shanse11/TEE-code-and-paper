#!/usr/bin/env node
// blob_publish.js — Publish a REAL blob batch to Sepolia via a type-3 transaction and
// anchor it through BlobBatchAnchor.anchorBlobBatch. RESUMABLE.
//
// Preflight (fail closed): requires SEPOLIA_RPC_URL + SEPOLIA_PRIVATE_KEY (+ a deployed
// BlobBatchAnchor address). If any are missing, the script exits 2 with NO network writes.
//
// Usage:
//   export REVISION_RUN=<abs> SEPOLIA_RPC_URL=... SEPOLIA_PRIVATE_KEY=0x...
//   export BLOB_BATCH_ANCHOR_ADDRESS=0x...   # address of a deployed BlobBatchAnchor
//   node evm/revision/blob_publish.js [<taskCount>_<payloadKiB>KiB]   # default 8_8KiB
//
// The blob payload is taken from the offline artifacts produced by blob_offline.js so the
// on-chain anchor and the independently-verifiable blob stay in lockstep.

const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");
const { beaconSlotFromTimestamp } = require("./beacon_blob.js");
const kzg = require("./kzg.js");
const { requireRun, readState, writeState, preflightOrFail, creds, safeHost } = require("./revision_env.js");

const TARGET = process.argv[2] || "8_8KiB";
const run = requireRun();

function loadArtifact(sub) {
  const dir = path.join(run, "artifacts", "blob_offline", sub);
  const meta = JSON.parse(fs.readFileSync(path.join(dir, "meta.json"), "utf8"));
  const blob = Buffer.from(fs.readFileSync(path.join(dir, "blob.hex"), "utf8"), "hex");
  const commitment = Buffer.from(fs.readFileSync(path.join(dir, "commitment.hex"), "utf8"), "hex");
  const proof = Buffer.from(fs.readFileSync(path.join(dir, "proof.hex"), "utf8"), "hex");
  return { meta, blob, commitment, proof };
}

async function main() {
  const c = creds();
  console.log(`[publish] target=${TARGET}  creds=${JSON.stringify(c)}  rpc=${safeHost(process.env.SEPOLIA_RPC_URL)}`);

  // ---- Preflight (fail closed) ----
  preflightOrFail(c.SEPOLIA_RPC_URL, "SEPOLIA_RPC_URL is not set — cannot publish (no RPC).");
  preflightOrFail(c.SEPOLIA_PRIVATE_KEY, "SEPOLIA_PRIVATE_KEY is not set — cannot publish (no signer).");
  const contractAddr = process.env.BLOB_BATCH_ANCHOR_ADDRESS;
  preflightOrFail(
    contractAddr && /^0x[0-9a-fA-F]{40}$/.test(contractAddr),
    "BLOB_BATCH_ANCHOR_ADDRESS is not set to a deployed BlobBatchAnchor — cannot anchor."
  );

  // Resume: if already confirmed, skip.
  const prev = readState("blob_publish");
  if (prev && prev.status === "confirmed") {
    console.log(`[publish] already confirmed: tx=${prev.txHash} anchorId=${prev.anchorId}. Skipping (resume).`);
    process.exit(0);
  }

  const { meta, blob, commitment, proof } = loadArtifact(TARGET);
  console.log(`[publish] batch payloadHash=${meta.payloadHash} versionedHash=${meta.versionedHash} blobLen=${blob.length}`);

  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
  const network = await provider.getNetwork();
  preflightOrFail(network.chainId === 11155111n, `Unexpected chainId ${network.chainId} (expected Sepolia 11155111).`);
  const wallet = new ethers.Wallet(process.env.SEPOLIA_PRIVATE_KEY, provider);
  const bal = await provider.getBalance(wallet.address);
  console.log(`[publish] signer=${wallet.address} balanceWei=${bal.toString()}`);
  preflightOrFail(bal > 0n, "Signer has zero balance — will not broadcast (no mainnet funds are ever used).");

  const iface = new ethers.Interface([
    "function anchorBlobBatch(bytes32 payloadHash, uint256 taskCount, uint256 blobIndex) returns (uint256)",
  ]);
  const data = iface.encodeFunctionData("anchorBlobBatch", [
    meta.payloadHash,
    BigInt(meta.taskCount),
    0n, // 0-based blob slot; the single blob we attach is at index 0 (EIP-4844)
  ]);

  // Type-3 transaction carrying the REAL blob. ethers attaches the blob + KZG artifacts.
  const feeData = await provider.getFeeData();
  const tx = {
    type: 3,
    to: contractAddr,
    data,
    blobVersionedHashes: [meta.versionedHash],
    // Sepolia is past Osaka. The mempool rejects a legacy one-proof sidecar
    // and requires wrapper version 1 with 128 cell proofs.
    blobWrapperVersion: 1,
    blobs: [{ data: blob, commitment, proof: kzg.computeCellProof(blob) }],
    maxFeePerBlobGas: feeData.maxFeePerBlobGas || ethers.parseUnits("10", "gwei"),
    maxFeePerGas: feeData.maxFeePerGas,
    maxPriorityFeePerGas: feeData.maxPriorityFeePerGas,
    gasLimit: 1000000n,
  };

  console.log(`[publish] sending type-3 tx (blobIndex=0, 1 blob) ...`);
  const sent = await wallet.sendTransaction(tx);
  console.log(`[publish] sent txHash=${sent.hash}`);
  const receipt = await sent.wait();
  // Recover the authoritative on-chain anchor id from the BlobBatchAnchored event.
  // This is the only reliable source of the id (the return value is not decoded here).
  let anchorId = null;
  try {
    const anchorIface = new ethers.Interface([
      "event BlobBatchAnchored(uint256 indexed id, bytes32 payloadHash, uint256 taskCount, uint256 blobIndex, bytes32 blobVersionedHash, address submitter)",
    ]);
    for (const log of receipt.logs) {
      try {
        const parsed = anchorIface.parseLog({ topics: log.topics, data: log.data });
        if (parsed && parsed.name === "BlobBatchAnchored") {
          anchorId = Number(parsed.args.id);
          break;
        }
      } catch (_e) {
        /* not this event */
      }
    }
  } catch (_e) {
    anchorId = null;
  }
  console.log(`[publish] anchorId=${anchorId} (from BlobBatchAnchored event)`);
  const block = await provider.getBlock(receipt.blockNumber);
  const beaconSlot = beaconSlotFromTimestamp(block.timestamp);
  console.log(`[publish] beaconSlot=${beaconSlot} blockTimestamp=${block.timestamp}`);
  writeState("blob_publish", {
    status: "confirmed",
    txHash: receipt.hash,
    anchorId,
    blockNumber: Number(receipt.blockNumber),
    blockTimestamp: Number(block.timestamp),
    beaconSlot,
    blobVersionedHashes: [meta.versionedHash],
    payloadHash: meta.payloadHash,
    taskCount: meta.taskCount,
    target: TARGET,
    contract: contractAddr,
    blobIndex: 0,
    gasUsed: Number(receipt.gasUsed),
  });
  console.log(`[publish] CONFIRMED block=${receipt.blockNumber} gasUsed=${receipt.gasUsed}`);
  console.log(`[publish] next: node evm/revision/blob_fetch.js  (independent beacon retrieval)`);
}

main().catch((e) => {
  console.error("[publish] ERROR:", e.shortMessage || e.message);
  if (e.error) console.error("[publish] cause:", e.error.shortMessage || e.error.message || e.error);
  if (e.info && e.info.error) console.error("[publish] rpc:", JSON.stringify(e.info.error).slice(0, 500));
  process.exit(1);
});
