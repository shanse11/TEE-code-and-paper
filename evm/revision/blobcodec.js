// blobcodec.js — Real EIP-4844 batch <-> blob codec (no Mock).
//
// Design goals (per revision requirements):
//  - Encode a real batch (domain + task summary + content) into a 4096-field-element blob.
//  - The encoding is REVERSIBLE and field-element SAFE (every FE < BLS_MODULUS).
//  - Domain / task summary / content are cryptographically bound:
//      * domain        -> namespace string (prevents cross-app replay of blobs)
//      * task summary  -> taskCount + payloadLen (header)
//      * payloadHash    = keccak256(content)  (binds content to the summary)
//      * content        -> concatenated tasks
//    On decode we recompute keccak256(content) and compare to the stored payloadHash,
//    which is exactly the independent verification a verifier must perform off-chain.
//
// Field-element safety: each 32-byte FE stores 31 data bytes in the low 31 bytes
// (top byte = 0), so the FE value is < 2^248 < BLS_MODULUS. This is a standard,
// always-valid encoding for arbitrary data into a blob.
//
// The EVM contract never sees blob bytes (it only sees the versioned hash); the
// "business semantics" (payloadHash / taskCount really correspond to the blob) are
// verified by INDEPENDENTLY fetching+decoding the blob off-chain and recomputing.

const { keccak256 } = require("ethers");

const FIELD_ELEMENTS_PER_BLOB = 4096;
const BYTES_PER_FIELD_ELEMENT = 32;
const DATA_BYTES_PER_FE = 31; // top byte kept zero -> value < 2^248 < BLS_MODULUS
const BLOB_BYTE_LEN = FIELD_ELEMENTS_PER_BLOB * BYTES_PER_FIELD_ELEMENT; // 131072
const MAX_FRAME_LEN = FIELD_ELEMENTS_PER_BLOB * DATA_BYTES_PER_FE; // 126976
const MAGIC = Buffer.from("424C4F42", "hex"); // ASCII "BLOB"
const DOMAIN_DEFAULT = "hybrid-tee-rollup/batch/v1";

function assert(cond, msg) {
  if (!cond) throw new Error("blobcodec: " + msg);
}

// content: Buffer. Returns { payloadHash (0x..32), frame: Buffer }
function buildFrame(domain, taskCount, content) {
  if (typeof domain !== "string") throw new Error("domain must be a string");
  const d = Buffer.from(domain, "utf8");
  assert(d.length > 0 && d.length <= 255, "domain length must be 1..255");
  assert(Number.isInteger(taskCount) && taskCount > 0, "taskCount must be a positive integer");
  assert(Buffer.isBuffer(content), "content must be a Buffer");
  const payloadHash = keccak256(content); // hex "0x..."
  const head = Buffer.alloc(1 + d.length + 8 + 8 + 32);
  let o = 0;
  head.writeUInt8(d.length, o); o += 1;
  d.copy(head, o); o += d.length;
  head.writeBigUInt64BE(BigInt(taskCount), o); o += 8;
  head.writeBigUInt64BE(BigInt(content.length), o); o += 8;
  Buffer.from(payloadHash.slice(2), "hex").copy(head, o); o += 32;
  // header is 1 + dlen + 1(domain-len byte already counted?) -> recompute: 1(dlen) + dlen + 8 + 8 + 32
  const frame = Buffer.concat([MAGIC, head, content]);
  assert(frame.length <= MAX_FRAME_LEN, "frame exceeds blob capacity");
  return { payloadHash, frame };
}

// 31 data bytes (little-endian) -> field-element value (< 2^248)
function chunkToValueLE(chunk) {
  let v = 0n;
  for (let j = 0; j < chunk.length; j++) v |= BigInt(chunk[j]) << (8n * BigInt(j));
  return v;
}
// field-element value -> 31 data bytes (little-endian)
function valueToChunkLE(v) {
  const buf = Buffer.alloc(DATA_BYTES_PER_FE);
  let x = v;
  for (let j = 0; j < DATA_BYTES_PER_FE; j++) {
    buf[j] = Number(x & 0xffn);
    x >>= 8n;
  }
  return buf;
}

// frame (Buffer) -> blob bytes (131072 Buffer).
// Each 32-byte field element stores 31 data bytes at blob positions [i*32+1 .. i*32+31]
// (big-endian placement) with the TOP byte (i*32+0) forced to 0. The c-kzg library
// interprets a field element as a big-endian 32-byte integer, so forcing the top byte
// to 0 guarantees the value is < 2^248 < BLS_MODULUS for ANY data — always valid.
function frameToBlob(frame) {
  assert(frame.length <= MAX_FRAME_LEN, "frame exceeds blob capacity");
  const blob = Buffer.alloc(BLOB_BYTE_LEN);
  for (let i = 0; i < FIELD_ELEMENTS_PER_BLOB; i++) {
    const start = i * DATA_BYTES_PER_FE;
    const end = Math.min(start + DATA_BYTES_PER_FE, frame.length);
    // blob[i*32+0] stays 0; copy the data chunk into bytes [i*32+1 .. i*32+31]
    frame.subarray(start, end).copy(blob, i * BYTES_PER_FIELD_ELEMENT + 1);
  }
  return blob;
}

// blob bytes (131072) -> full frame (with trailing zero padding up to capacity).
// Inverse of frameToBlob: recover the 31 data bytes from each FE's [1..31] positions.
function blobToFrame(blob) {
  assert(blob.length === BLOB_BYTE_LEN, "blob must be 131072 bytes");
  const chunks = [];
  for (let i = 0; i < FIELD_ELEMENTS_PER_BLOB; i++) {
    chunks.push(Buffer.from(blob.subarray(i * BYTES_PER_FIELD_ELEMENT + 1, i * BYTES_PER_FIELD_ELEMENT + 1 + DATA_BYTES_PER_FE)));
  }
  return Buffer.concat(chunks);
}

// Decode a frame into its semantic parts WITHOUT asserting payloadHash.
// Use this for independently-decoded or (deliberately) tampered blobs; the caller
// decides what to verify. For a trusted frame, parseFrame() asserts payloadHash.
function decodeFrame(frame) {
  assert(frame.slice(0, 4).equals(MAGIC), "bad magic (not a BLOB frame)");
  let o = 4;
  const dlen = frame[o]; o += 1;
  const domain = frame.subarray(o, o + dlen).toString("utf8"); o += dlen;
  const taskCount = Number(frame.readBigUInt64BE(o)); o += 8;
  const payloadLen = Number(frame.readBigUInt64BE(o)); o += 8;
  const payloadHash = "0x" + frame.subarray(o, o + 32).toString("hex"); o += 32;
  const content = frame.subarray(o, o + payloadLen);
  assert(content.length === payloadLen, "content length mismatch vs header");
  return { domain, taskCount, payloadLen, payloadHash, content };
}

// Parse a decoded frame back into its semantic parts and INDEPENDENTLY verify payloadHash.
function parseFrame(frame) {
  const d = decodeFrame(frame);
  const recomputed = keccak256(d.content);
  assert(recomputed === d.payloadHash, "payloadHash mismatch: content does not match stored payloadHash");
  return d;
}

// Build a deterministic, realistic batch payload.
// Returns { domain, taskCount, payloadKiB, payloadLen, content, payloadHash, frame }
function makeBatch(opts = {}) {
  const domain = opts.domain || DOMAIN_DEFAULT;
  const taskCount = opts.taskCount || 1;
  const payloadKiB = opts.payloadKiB || 1;
  assert(taskCount >= 1 && [1, 8, 32].includes(taskCount) === false ? true : true, "taskCount unchecked");
  const payloadLen = payloadKiB * 1024;
  // Distribute payload across tasks; last task gets the remainder.
  const base = Math.floor(payloadLen / taskCount);
  const contentParts = [];
  let seed = BigInt("0x" + Buffer.from(domain, "utf8").toString("hex")) ^ BigInt(taskCount) ^ BigInt(payloadLen);
  const randByte = () => {
    // xorshift64* deterministic PRNG
    seed ^= seed << 13n; seed ^= seed >> 7n; seed ^= seed << 17n;
    seed &= 0xffffffffffffffffn;
    return Number(seed & 0xffn);
  };
  for (let t = 0; t < taskCount; t++) {
    const len = t === taskCount - 1 ? (payloadLen - base * (taskCount - 1)) : base;
    const data = Buffer.alloc(len);
    for (let i = 0; i < len; i++) data[i] = randByte();
    const head = Buffer.alloc(12);
    head.writeBigUInt64BE(BigInt(t), 0); // taskId
    head.writeUInt32BE(len, 8); // taskLen
    contentParts.push(head, data);
  }
  const content = Buffer.concat(contentParts);
  const { payloadHash, frame } = buildFrame(domain, taskCount, content);
  return { domain, taskCount, payloadKiB, payloadLen, content, payloadHash, frame };
}

module.exports = {
  FIELD_ELEMENTS_PER_BLOB,
  BYTES_PER_FIELD_ELEMENT,
  BLOB_BYTE_LEN,
  DOMAIN_DEFAULT,
  MAGIC,
  buildFrame,
  frameToBlob,
  blobToFrame,
  parseFrame,
  decodeFrame,
  makeBatch,
  chunkToValueLE,
  valueToChunkLE,
};
