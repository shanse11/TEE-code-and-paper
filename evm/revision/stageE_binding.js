// SPDX-License-Identifier: MIT
//
// evm/revision/stageE_binding.js
//
// 阶段 E 本地层（E1）：规范 batch manifest 版本、单向承诺构造、容量/填充度量、M1 链下验证。
//
// 关键设计（来自阶段 E 提示词，必须避免循环承诺）：
//   单向构造顺序：
//     原始任务数据（不含任务摘要/manifest）
//       -> inputDataHash
//       -> taskCoreDigest（域、task/nonce、程序、input/output/trace；**不含 DA 引用**）
//       -> manifest（含各 task 的 coreDigest）与帧
//       -> KZG commitment / versionedHash
//       -> 最终签名 envelope(coreDigests, manifestHash, daRef, epoch/expiry)
//   coreDigest 不得包含本帧 manifestHash 或自身 Blob 的 versionedHash；
//   输入数据 hash 不得对包含 coreDigest 的整帧再次取 hash 并倒灌。
//
// 口径（继承阶段 A，不得混淆）：
//   payloadBytes / frameBytes / encodedBytes / fieldPaddingBytes / fieldPrefixBytes / paddingBytes
//   encodedBytes = ceil(frameBytes/31)*32；blobCount = ceil(encodedBytes/131072)

"use strict";

const { keccak256, sha256 } = require("ethers");
const blobcodec = require("./blobcodec");
const kzg = require("./kzg");

const MANIFEST_VERSION = "hybrid-tee-rollup.batch-manifest.v1";
const ENCODING_VERSION = "blobcodec-field31-v1";
const BLOB_BYTES = blobcodec.BLOB_BYTE_LEN; // 131072
const DATA_BYTES_PER_FE = 31;
const BYTES_PER_FE = 32;
const MAX_FRAME_LEN = 4096 * DATA_BYTES_PER_FE; // 126976
const ENCODER_MAX_BLOBS = 1; // 当前实际编码器仅支持单 Blob

function canonicalJson(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(",")}}`;
}
function keccakUtf8(text) {
  return keccak256(Buffer.from(text, "utf8"));
}

/**
 * 任务核心摘要 taskCoreDigest：绑定域、task 身份、程序版本与 input/output/trace 承诺。
 * 明确不含 manifestHash、versionedHash 或 DA 引用 —— 这是避免循环承诺的关键。
 */
function buildTaskCoreDigest({ domain, taskId, nonce, programVersion, inputCommitment, outputCommitment, traceCommitment }) {
  for (const [k, v] of Object.entries({ domain, taskId, nonce, programVersion, inputCommitment, outputCommitment, traceCommitment })) {
    if (v === undefined || v === null || v === "") throw new Error(`buildTaskCoreDigest 缺少字段 ${k}`);
  }
  return keccakUtf8(canonicalJson({
    domain: String(domain),
    taskId: String(taskId),
    nonce: String(nonce),
    programVersion: String(programVersion),
    inputCommitment: String(inputCommitment),
    outputCommitment: String(outputCommitment),
    traceCommitment: String(traceCommitment),
  }));
}

/**
 * 构造规范 manifest（字节与其 hash）。
 * tasks: [{ taskId, nonce, programVersion, inputCommitment, outputCommitment, traceCommitment, payloadLen, index }]
 */
function buildManifest({ domain, chainId, contract, batchId, tasks, encodingVersion = ENCODING_VERSION }) {
  const entries = tasks.map((t, i) => ({
    index: i,
    taskId: String(t.taskId),
    payloadLen: Number(t.payloadLen ?? 0),
    coreDigest: buildTaskCoreDigest({ ...t, domain }),
  }));
  const manifest = {
    manifestVersion: MANIFEST_VERSION,
    encodingVersion,
    domain: String(domain),
    chainId: Number(chainId),
    contract: String(contract).toLowerCase(),
    batchId: String(batchId),
    taskCount: entries.length,
    blobOrder: 0,
    shardIndex: 0,
    shardTotal: 1,
    tasks: entries,
  };
  const bytes = Buffer.from(canonicalJson(manifest), "utf8");
  return { manifest, manifestBytes: bytes, manifestHash: keccak256(bytes), coreDigests: entries.map((e) => e.coreDigest) };
}

/**
 * 把 manifest 字节编码为真实 Blob 并做真实 KZG 承诺。
 * 返回阶段 A 口径下的完整度量（全部来自实际序列化，不是估计）。
 */
function encodeManifestToBlob({ domain, manifestBytes, taskCount }) {
  const payloadBytes = manifestBytes.length;
  // 超容量由 codec 判定（codec 是容量真相来源），此处把它的断言转换为带明确 code 的 blocked 错误
  let built;
  try {
    built = blobcodec.buildFrame(domain, taskCount, manifestBytes);
  } catch (e) {
    if (e && /exceeds blob capacity/.test(e.message)) {
      const overhead = 4 + 1 + Buffer.from(domain, "utf8").length + 8 + 8 + 32;
      const err = new Error(`frame 超过单 Blob 帧容量 ${MAX_FRAME_LEN}（payloadBytes=${payloadBytes}）；当前编码器仅支持单 Blob，必须 blocked`);
      err.code = "SINGLE_BLOB_CAPACITY_EXCEEDED";
      err.frameBytes = overhead + payloadBytes;
      throw err;
    }
    throw e;
  }
  const { payloadHash, frame } = built;
  const frameBytes = frame.length;
  if (frameBytes > MAX_FRAME_LEN) {
    const err = new Error(`frame ${frameBytes} 超过单 Blob 帧容量 ${MAX_FRAME_LEN}；当前编码器仅支持单 Blob，必须 blocked`);
    err.code = "SINGLE_BLOB_CAPACITY_EXCEEDED";
    err.frameBytes = frameBytes;
    throw err;
  }
  const blob = blobcodec.frameToBlob(frame);
  const fields = Math.ceil(frameBytes / DATA_BYTES_PER_FE);
  const encodedBytes = fields * BYTES_PER_FE;
  const blobCount = Math.ceil(encodedBytes / BLOB_BYTES);
  const commitment = kzg.blobToCommitment(blob);
  const proof = kzg.computeProof(blob, commitment);
  return {
    payloadBytes,
    payloadHash,
    frameBytes,
    fieldPrefixBytes: fields,                                  // 每个 32 字节域一个前置零字节
    fieldPaddingBytes: fields * DATA_BYTES_PER_FE - frameBytes, // 最后数据域补齐字节
    encodedBytes,
    blobBytes: BLOB_BYTES,
    blobCount,
    paddingBytes: blobCount * BLOB_BYTES - encodedBytes,        // 仅 Blob 尾部填充
    encoderMaxBlobs: ENCODER_MAX_BLOBS,
    blob,
    commitment,
    proof,
    versionedHash: kzg.versionedHash(commitment),
  };
}

/**
 * M1（链下部分）验证：给定的 taskCoreDigest 确实出现在该 versionedHash 对应 Blob 的规范 manifest 中。
 * 注意：这只证明「摘要存在于 manifest」，不等于 M2（manifest 承诺的 payload/input/trace 与实际数据一致且足以裁决）。
 */
function verifyM1({ blob, expectedCoreDigest, expectedDomain, expectedVersionedHash = null }) {
  const frame = blobcodec.blobToFrame(blob);
  const decoded = blobcodec.decodeFrame(frame); // 不预先信任，交由调用方决定
  const recomputed = keccak256(decoded.content);
  if (recomputed !== decoded.payloadHash) {
    return { ok: false, reason: "payloadHash 与内容不一致（内容被篡改或编码损坏）", decoded: null };
  }
  if (expectedDomain && decoded.domain !== expectedDomain) {
    return { ok: false, reason: `域不匹配: ${decoded.domain} != ${expectedDomain}`, decoded: null };
  }
  let manifest;
  try {
    manifest = JSON.parse(decoded.content.toString("utf8"));
  } catch {
    return { ok: false, reason: "manifest 不是合法 JSON", decoded };
  }
  if (manifest.manifestVersion !== MANIFEST_VERSION) {
    return { ok: false, reason: `manifest 版本不符: ${manifest.manifestVersion}`, decoded, manifest };
  }
  const hit = manifest.tasks.some((t) => t.coreDigest === expectedCoreDigest);
  if (!hit) return { ok: false, reason: "taskCoreDigest 不在该 manifest 中（M1 不成立）", decoded, manifest };

  if (expectedVersionedHash) {
    const c = kzg.blobToCommitment(blob);
    if (kzg.versionedHash(c) !== expectedVersionedHash) {
      return { ok: false, reason: "versionedHash 与 Blob 不匹配", decoded, manifest };
    }
  }
  return { ok: true, reason: "M1 链下验证通过：coreDigest 出现在规范 manifest 中且内容自洽", decoded, manifest };
}

/** 独立 KZG 验证（真实密码学，不是模拟） */
function verifyBlobKzg(blob, commitment, proof) {
  return kzg.verifyProof(blob, commitment, proof);
}

module.exports = {
  MANIFEST_VERSION,
  ENCODING_VERSION,
  BLOB_BYTES,
  MAX_FRAME_LEN,
  ENCODER_MAX_BLOBS,
  canonicalJson,
  buildTaskCoreDigest,
  buildManifest,
  encodeManifestToBlob,
  verifyM1,
  verifyBlobKzg,
};
