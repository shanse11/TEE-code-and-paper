#!/usr/bin/env node
// blob_receipt.js — Fetch the receipt for a published blob tx and report fees SEPARATELY:
//   * execution_fee = gasUsed * effectiveGasPrice   (L1 execution gas only)
//   * blob_fee      = blobGasUsed * blobGasPrice    (EIP-4844 blob gas only)
// The two are reported independently and are NOT summed into a single "gas" figure, per spec.
//
// Preflight (fail closed): requires SEPOLIA_RPC_URL + a tx hash (from publish state or TX_HASH env).
//
// Usage:
//   export REVISION_RUN=<abs> SEPOLIA_RPC_URL=...
//   node evm/revision/blob_receipt.js

const { ethers } = require("ethers");
const { requireRun, readState, preflightOrFail, creds, safeHost } = require("./revision_env.js");

const run = requireRun();
const c = creds();
console.log(`[receipt] creds=${JSON.stringify({ SEPOLIA_RPC_URL: c.SEPOLIA_RPC_URL })}  rpc=${safeHost(process.env.SEPOLIA_RPC_URL)}`);

// ---- Preflight (fail closed) ----
preflightOrFail(c.SEPOLIA_RPC_URL, "SEPOLIA_RPC_URL is not set — cannot read receipt (no RPC).");

const publish = readState("blob_publish");
const txHash = process.env.TX_HASH || (publish && publish.txHash);
preflightOrFail(txHash, "No tx hash available: set TX_HASH or run blob_publish.js first.");

async function main() {
  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);

  // Resolve the effective gas price actually paid. For type-3 the receipt exposes the
  // execution gas price via the transaction; we use the included tx's gasPrice.
  const [receipt, tx] = await Promise.all([
    provider.getTransactionReceipt(txHash),
    provider.getTransaction(txHash),
  ]);
  if (!receipt) {
    console.error(`[receipt] receipt not found for ${txHash} (still pending or invalid).`);
    process.exit(1);
  }

  const gasUsed = receipt.gasUsed; // bigint
  const effectiveGasPrice = tx ? tx.gasPrice : receipt.gasPrice; // bigint (effective, post-EIP-1559)
  const executionFee = gasUsed * effectiveGasPrice;

  // Blob gas: a type-3 tx receipt carries blobGasUsed and blobGasPrice (bigints).
  const blobGasUsed = receipt.blobGasUsed ?? (tx && tx.blobVersionedHashes ? BigInt(tx.blobVersionedHashes.length) * 131072n : 0n);
  const blobGasPrice = receipt.blobGasPrice ?? 0n;
  const blobFee = blobGasUsed * blobGasPrice;

  console.log("=== Receipt fee breakdown (separate, not summed) ===");
  console.log(`  txHash            : ${receipt.hash}`);
  console.log(`  blockNumber       : ${receipt.blockNumber}`);
  console.log(`  status            : ${receipt.status === 1 ? "success" : "failure"}`);
  console.log(`  gasUsed           : ${gasUsed.toString()}  (execution gas)`);
  console.log(`  effectiveGasPrice : ${effectiveGasPrice.toString()} wei`);
  console.log(`  >> execution_fee  : ${executionFee.toString()} wei  (= gasUsed * effectiveGasPrice)`);
  console.log(`  blobGasUsed       : ${blobGasUsed.toString()}  (6 gas per blob * blobs)`);
  console.log(`  blobGasPrice      : ${blobGasPrice.toString()} wei`);
  console.log(`  >> blob_fee       : ${blobFee.toString()} wei  (= blobGasUsed * blobGasPrice)`);
  console.log(`  NOTE: execution_fee and blob_fee are reported SEPARATELY. Do NOT add them into one 'gas' figure.`);

  // Persist for downstream reference.
  const fs = require("fs");
  const path = require("path");
  fs.mkdirSync(path.join(run, "cache"), { recursive: true });
  fs.writeFileSync(
    path.join(run, "cache", "blob_receipt.json"),
    JSON.stringify(
      {
        txHash,
        blockNumber: Number(receipt.blockNumber),
        status: receipt.status,
        gasUsed: gasUsed.toString(),
        effectiveGasPrice: effectiveGasPrice.toString(),
        executionFee: executionFee.toString(),
        blobGasUsed: blobGasUsed.toString(),
        blobGasPrice: blobGasPrice.toString(),
        blobFee: blobFee.toString(),
        computedAt: new Date().toISOString(),
      },
      null,
      2
    )
  );
  console.log(`[receipt] saved to ${path.join(run, "cache", "blob_receipt.json")}`);
}

main().catch((e) => { console.error("[receipt] ERROR:", e.shortMessage || e.message); process.exit(1); });
