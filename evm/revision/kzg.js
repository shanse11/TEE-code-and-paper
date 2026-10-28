// kzg.js — Thin, REAL KZG wrapper around the native c-kzg bindings (no Mock).
//
// Trusted setup: the canonical Ethereum mainnet EIP-4844 setup shipped with c-kzg
// (deps/c-kzg/trusted_setup.txt) is in the c-kzg v4 text format:
//   line1 = num_g1 (4096), line2 = num_g2 (65),
//   then G1_lagrange (4096 * 48B), G2_monomial (65 * 96B), G1_monomial (4096 * 48B),
//   all as a continuous hex byte stream. The native loader expects `precompute` to be a
//   NUMBER (1), not a boolean — hence loadTrustedSetup(1, path).
//
// Public helpers:
//   loadSetup()                       -> idempotent init
//   blobToCommitment(blobBuf)        -> Buffer(48)
//   computeProof(blobBuf, commit)    -> Buffer(48)
//   verifyProof(blobBuf, commit, pr) -> boolean
//   versionedHash(commitBuf)         -> "0x.." (0x01 || sha256(commit)[1:])  [EIP-4844]

const path = require("path");
const crypto = require("crypto");
const c_kzg = require("c-kzg");
const { sha256 } = require("ethers");

const TRUSTED_SETUP = path.join(__dirname, "trusted_setup.txt");
let _loaded = false;

function loadSetup() {
  if (_loaded) return;
  // precompute=1 (number, required by the native binding); explicit file path.
  c_kzg.loadTrustedSetup(1, TRUSTED_SETUP);
  _loaded = true;
}

// blobBuf: Buffer/Uint8Array of 131072 bytes -> Buffer(48)
function blobToCommitment(blobBuf) {
  loadSetup();
  return Buffer.from(c_kzg.blobToKzgCommitment(Uint8Array.from(blobBuf)));
}

function computeCellProof(blobBuf) {
  loadSetup();
  const [, proofs] = c_kzg.computeCellsAndKzgProofs(Uint8Array.from(blobBuf));
  return Buffer.concat(proofs.map((p) => Buffer.from(p)));
}

function computeProof(blobBuf, commitmentBuf) {
  loadSetup();
  return Buffer.from(c_kzg.computeBlobKzgProof(Uint8Array.from(blobBuf), Uint8Array.from(commitmentBuf)));
}

// returns true iff the blob authenticates against (commitment, proof)
function verifyProof(blobBuf, commitmentBuf, proofBuf) {
  loadSetup();
  try {
    return c_kzg.verifyBlobKzgProof(
      Uint8Array.from(blobBuf),
      Uint8Array.from(commitmentBuf),
      Uint8Array.from(proofBuf)
    ) === true;
  } catch (_e) {
    return false;
  }
}

// EIP-4844 versioned hash: VERSIONED_HASH_VERSION_KZG (0x01) || sha256(commitment)[1:]
function versionedHash(commitmentBuf) {
  const h = Buffer.from(sha256(Uint8Array.from(commitmentBuf)).slice(2), "hex"); // 32 bytes
  const out = Buffer.alloc(32);
  out[0] = 0x01;
  h.copy(out, 1, 1, 32); // drop first byte, keep bytes [1..31]
  return "0x" + out.toString("hex");
}

module.exports = { loadSetup, blobToCommitment, computeCellProof, computeProof, verifyProof, versionedHash };
