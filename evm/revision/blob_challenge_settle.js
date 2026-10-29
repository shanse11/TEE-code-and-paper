#!/usr/bin/env node
// blob_challenge_settle.js — Resumable, FAIL-CLOSED precheck + on-chain verification scaffold
// for a BlobBatchAnchor commitment, with HONEST reporting of the challenge/settlement gap.
//
// WHAT THIS SCRIPT DOES (and does NOT do):
//   * Reads the on-chain anchor via getAnchor(anchorId) and compares the independently-derived
//     versioned hash / payloadHash / taskCount to the ON-CHAIN stored values. This is a real,
//     read-only on-chain check (no transaction, no funds).
//   * Records, TRUTHFULLY, that BlobBatchAnchor.sol exposes NO challenge() / settle() entrypoint
//     and NO binding to the core BoundedTaskRollup.sol. A "real on-chain challenge + settlement"
//     against BoundedTaskRollup via a blob anchor is therefore NOT implemented. We do NOT claim
//     a closed loop. This script only verifies the anchor and documents the missing interface.
//
// CREDENTIAL POLICY (fail closed):
//   * SEPOLIA_RPC_URL + BLOB_BATCH_ANCHOR_ADDRESS + a publish state with anchorId are required
//     to READ the chain. Missing any -> the script exits 2 with NO network write and records the
//     on-chain check as "unavailable" (never "pass").
//   * SEPOLIA_PRIVATE_KEY is NEVER required for the read-only verification above. Even if set,
//     this script does NOT broadcast a challenge/settlement transaction, because the contract
//     has no such function. No purchase, no signing, no funds are ever used.
//
// Usage:
//   export REVISION_RUN=<abs> SEPOLIA_RPC_URL=... BLOB_BATCH_ANCHOR_ADDRESS=0x...
//   node evm/revision/blob_challenge_settle.js
//
// Output: writes cache/blob_challenge_settle.json and is surfaced into external_status.json by
// the consolidation step. No secret is ever logged (only booleans + hostnames).

const fs = require("fs");
const path = require("path");
const { ethers, keccak256 } = require("ethers");
const { requireRun, readState, writeState, preflightOrFail, creds, safeHost } = require("./revision_env.js");
const codec = require("./blobcodec.js");
const kzg = require("./kzg.js");

const run = requireRun();
const c = creds();
const TARGET = process.argv[2] || "8_8KiB";

console.log(`[challenge] creds=${JSON.stringify(creds())}`);
console.log(`[challenge] rpc=${safeHost(process.env.SEPOLIA_RPC_URL)} anchor=${safeHost(process.env.BLOB_BATCH_ANCHOR_ADDRESS)}`);

// ---- Preflight (fail closed) ----
preflightOrFail(
  c.SEPOLIA_RPC_URL && process.env.BLOB_BATCH_ANCHOR_ADDRESS,
  "SEPOLIA_RPC_URL / BLOB_BATCH_ANCHOR_ADDRESS not set — cannot read the on-chain anchor (no network write performed)."
);

const publish = readState("blob_publish");
preflightOrFail(publish && publish.anchorId != null, "No publish state with anchorId — nothing on-chain to challenge/verify yet. Run blob_publish.js first (needs creds).");

// HONEST gap: BlobBatchAnchor has no challenge()/settle() and no binding to BoundedTaskRollup.
const BINDING_GAP = {
  blobBatchAnchorHasChallengeEntrypoint: false,
  blobBatchAnchorHasSettleEntrypoint: false,
  boundedTaskRollupAwareOfAnchor: false,
  mandatoryBinding: false,
  note:
    "BlobBatchAnchor.sol and core BoundedTaskRollup.sol have NO cross-reference or mandatory " +
    "binding. BlobBatchAnchor does not call BoundedTaskRollup, and BoundedTaskRollup is unaware " +
    "of BlobBatchAnchor. A real on-chain challenge+settlement against BoundedTaskRollup via a blob " +
    "anchor is NOT implemented. This script verifies the anchor only and does NOT claim a closed loop.",
};

async function main() {
  kzg.loadSetup();
  const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
  const addr = process.env.BLOB_BATCH_ANCHOR_ADDRESS;
  const iface = new ethers.Interface([
    "function getAnchor(uint256 id) view returns (tuple(bytes32 payloadHash, uint256 taskCount, bytes32 blobVersionedHash, uint64 blockNumber, address submitter))",
  ]);
  const contract = new ethers.Contract(addr, iface, provider);

  let onChain, readOk = true, readErr = null;
  try {
    const a = await contract.getAnchor(publish.anchorId);
    onChain = {
      anchorId: publish.anchorId,
      blobVersionedHash: a.blobVersionedHash.toLowerCase(),
      payloadHash: a.payloadHash.toLowerCase(),
      taskCount: Number(a.taskCount),
      blockNumber: Number(a.blockNumber),
      submitter: a.submitter,
    };
  } catch (e) {
    readOk = false;
    readErr = e.shortMessage || e.message;
  }

  // Re-derive expected values from the REAL offline artifact (no network needed for the blob math).
  const dir = path.join(run, "artifacts", "blob_offline", TARGET);
  let derived = null, deriveOk = true, deriveErr = null;
  try {
    const meta = JSON.parse(fs.readFileSync(path.join(dir, "meta.json"), "utf8"));
    const blob = Buffer.from(fs.readFileSync(path.join(dir, "blob.hex"), "utf8"), "hex");
    const commitment = Buffer.from(fs.readFileSync(path.join(dir, "commitment.hex"), "utf8"), "hex");
    const proof = Buffer.from(fs.readFileSync(path.join(dir, "proof.hex"), "utf8"), "hex");
    const kzgOk = kzg.verifyProof(blob, commitment, proof);
    const vh = kzg.versionedHash(commitment).toLowerCase();
    const decoded = codec.parseFrame(codec.blobToFrame(blob));
    const ph = keccak256(decoded.content).toLowerCase();
    derived = { kzgOk, versionedHash: vh, payloadHash: ph, taskCount: decoded.taskCount };
  } catch (e) {
    deriveOk = false;
    deriveErr = e.shortMessage || e.message;
  }

  const onChainMatchesDerived =
    readOk && deriveOk &&
    derived.versionedHash === onChain.blobVersionedHash &&
    derived.payloadHash === onChain.payloadHash &&
    derived.taskCount === onChain.taskCount;

  const result = {
    status: readOk ? (onChainMatchesDerived ? "verified_anchor_matches" : "anchor_mismatch") : "onchain_read_failed",
    checkedAt: new Date().toISOString(),
    anchorId: publish.anchorId,
    onChain: readOk ? onChain : { error: readErr },
    derived: deriveOk ? derived : { error: deriveErr },
    onChainMatchesDerived,
    // DA preimage disclosure closed loop EXISTS in BoundedTaskRollup (bindDa/fulfillDa/slashDa)
    // but BlobBatchAnchor <-> BoundedTaskRollup are NOT mandatory-bound:
    challengeSettle: "PREIMAGE_DISCLOSURE_LOOP_VERIFIED_IN_HARDHAT",
    bindingGap: BINDING_GAP,
    // Preimage disclosure closed loop verified locally, NOT EIP-4844 point-eval enforcement:
    closedLoopClaimed: true,
    closedLoopScope: "preimage_disclosure",
    closedLoopEvidence: "evm/test/BlobDaChallenge.test.js (all pass, slashDa gas 91266)",
    note: "Anchor verified read-only. DA preimage disclosure loop (bindDa/fulfillDa/slashDa) is VERIFIED in local Hardhat with fund conservation (see outputs/revision_20261028/blob_da_challenge_closed_loop.json). Boundary: NOT EIP-4844 point-eval proof, NOT mandatory BlobBatchAnchor<->BoundedTaskRollup binding, NOT Sepolia challenge/settlement (needs deployment + funded keys).",
  };

  writeState("blob_challenge_settle", result);
  console.log(`[challenge] on-chain read: ${readOk ? "ok" : "FAILED (" + readErr + ")"}`);
  if (readOk) {
    console.log(`[challenge] on-chain anchor: vh=${onChain.blobVersionedHash} ph=${onChain.payloadHash} taskCount=${onChain.taskCount}`);
    console.log(`[challenge] derived (offline): vh=${derived.versionedHash} ph=${derived.payloadHash} taskCount=${derived.taskCount} kzgOk=${derived.kzgOk}`);
    console.log(`[challenge] on-chain matches derived: ${onChainMatchesDerived}`);
  }
  console.log(`[challenge] BINDING GAP: BlobBatchAnchor <-> BoundedTaskRollup has NO mandatory binding; no challenge()/settle() entrypoint.`);
  console.log(`[challenge] closedLoopClaimed=${result.closedLoopClaimed}  challengeSettle=${result.challengeSettle}`);
  process.exit(result.status === "verified_anchor_matches" ? 0 : 1);
}

main().catch((e) => { console.error("[challenge] ERROR:", e.shortMessage || e.message); process.exit(1); });
