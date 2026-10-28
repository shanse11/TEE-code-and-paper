// SPDX-License-Identifier: MIT
//
// evm/revision/tee_attestation.js
//
// 阶段 D（D1/D2 部分）：统一 TEE 远程证明后端契约，并隔离真实与模拟。
//
// 设计约束（来自阶段 D 提示词）：
//   - 真实与模拟分开 entrypoint / backendId / 证据类别。
//   - real 模式缺设备、验证失败或无法取得 collateral 时 fail-closed；
//     绝不静默 fallback 到 Mock，也不把模拟结果记为 real。
//   - 仅显式 fixture 模式允许 Mock，且必须记录 realQuote=false。
//   - 本模块单元测试不得依赖联网；不伪造 Quote、不以普通签名或 HMAC 冒充 Quote。
//   - 不把 fixture 测出的延迟当作真实硬件延迟。
//
// 说明：本模块只负责「接口 + 规范编码 + 策略评估」。真实 Quote 的采集与
// DCAP/QVL 验证必须由独立进程在具备 SGX/TDX 的平台上执行（见 run_remote.sh 说明）。

"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");

// ------------------------------------------------------------------
// 后端标识与判定
// ------------------------------------------------------------------
const BACKEND = {
  SIMULATED: "simulated-hmac",
  SGX_DCAP: "sgx-dcap-real",
  TDX_DCAP: "tdx-dcap-real",
};
const REAL_BACKENDS = [BACKEND.SGX_DCAP, BACKEND.TDX_DCAP];

// DCAP/QVL 类验证结果枚举（不把所有非致命码当 pass）
const DECISION = {
  OK: "OK",
  INVALID: "invalid",
  REVOKED: "revoked",
  OUT_OF_DATE: "out-of-date",
  CONFIGURATION_NEEDED: "configuration-needed",
  UNKNOWN: "unknown",
  BLOCKED: "blocked", // 缺设备/缺资源，未产生任何验证结论
};

class AttestationError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "AttestationError";
    this.code = code;
  }
}

// ------------------------------------------------------------------
// 规范编码（canonical JSON + sha256）
// ------------------------------------------------------------------
function canonicalJson(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(",")}}`;
}
function sha256Hex(input) {
  return crypto.createHash("sha256").update(input).digest("hex");
}
function sha256HexUtf8(text) {
  return sha256Hex(Buffer.from(text, "utf8"));
}

/**
 * D2: 写入平台 reportData 的摘要。
 * 把 执行公钥 / 协议域 / 验证方 fresh nonce / session 或 epoch / 应用摘要 规范编码后取摘要。
 * 注意：reportData 长度有限（SGX/TDX 为 64 字节），不能假定任意长字段可直接装入；
 * 这里固定输出 32 字节摘要，调用方负责放入 reportData 的前 32 字节并补齐。
 */
function buildReportDataDigest({ execPubkey, domain, nonce, epoch, appDigest }) {
  for (const [k, v] of Object.entries({ execPubkey, domain, nonce, epoch, appDigest })) {
    if (v === undefined || v === null || v === "") throw new AttestationError("MISSING_FIELD", `buildReportDataDigest 缺少字段 ${k}`);
  }
  return sha256HexUtf8(canonicalJson({ execPubkey: String(execPubkey), domain: String(domain), nonce: String(nonce), epoch: String(epoch), appDigest: String(appDigest) }));
}

/**
 * D2: 任务签名绑定摘要。绑定 chainId / verifyingContract / taskId / nonce /
 * input·output·trace 承诺 / 程序版本 / DA 引用，防跨链跨任务重放。
 */
function buildTaskBindingDigest({ chainId, verifyingContract, taskId, nonce, inputCommitment, outputCommitment, traceCommitment, programVersion, daRef }) {
  const required = { chainId, verifyingContract, taskId, nonce, inputCommitment, outputCommitment, traceCommitment, programVersion };
  for (const [k, v] of Object.entries(required)) {
    if (v === undefined || v === null || v === "") throw new AttestationError("MISSING_FIELD", `buildTaskBindingDigest 缺少字段 ${k}`);
  }
  return sha256HexUtf8(canonicalJson({
    chainId: String(chainId),
    verifyingContract: String(verifyingContract).toLowerCase(),
    taskId: String(taskId),
    nonce: String(nonce),
    inputCommitment: String(inputCommitment),
    outputCommitment: String(outputCommitment),
    traceCommitment: String(traceCommitment),
    programVersion: String(programVersion),
    daRef: daRef === undefined || daRef === null ? null : String(daRef),
  }));
}

// ------------------------------------------------------------------
// 设备探测（real 模式 fail-closed 的依据）
// ------------------------------------------------------------------
const DEVICE_PATHS = {
  [BACKEND.SGX_DCAP]: ["/dev/sgx_enclave", "/dev/sgx_provision", "/dev/sgx/enclave", "/dev/sgx/provision"],
  [BACKEND.TDX_DCAP]: ["/dev/tdx_guest", "/dev/tdx-guest"],
};
function detectDevice(backendId) {
  const paths = DEVICE_PATHS[backendId];
  if (!paths) return { present: false, reason: `未知后端 ${backendId}` };
  const found = paths.filter((p) => {
    try { return fs.existsSync(p); } catch { return false; }
  });
  return { present: found.length > 0, probedPaths: paths, found, reason: found.length ? "found" : `未找到任何设备节点: ${paths.join(", ")}` };
}

// ------------------------------------------------------------------
// Provider 契约
// ------------------------------------------------------------------
/**
 * 创建证明后端。
 * - backendId 为 real(SGX/TDX) 且本机无设备 → 抛错（fail-closed），绝不回退到模拟。
 * - backendId 为 simulated → 仅用于功能控制组，realQuote 恒为 false。
 */
function createProvider(backendId, { requireRealDevice = true } = {}) {
  const isReal = REAL_BACKENDS.includes(backendId);
  if (isReal) {
    const device = detectDevice(backendId);
    if (!device.present && requireRealDevice) {
      throw new AttestationError("DEVICE_UNAVAILABLE", `真实后端 ${backendId} 需要本机设备但未找到: ${device.reason}；阶段 D 不允许回退到模拟后端`);
    }
    return {
      backendId,
      isReal: true,
      device,
      // 真实路径：必须由具备硬件的独立进程产出，本模块不伪造
      async getQuote() {
        throw new AttestationError("NOT_IMPLEMENTED_LOCAL", `真实 Quote 采集(${backendId})必须在具备硬件的平台上由官方工具链执行；本机无设备, 返回 blocked 而非伪造`);
      },
    };
  }
  if (backendId !== BACKEND.SIMULATED) throw new AttestationError("UNKNOWN_BACKEND", `未知后端 ${backendId}`);
  return {
    backendId,
    isReal: false,
    device: { present: false, reason: "simulated backend 无硬件依赖" },
    // 模拟后端：HMAC 仅作功能控制组，明确 realQuote=false
    async getQuote({ nonce, appDigest, secret }) {
      if (!secret) throw new AttestationError("MISSING_FIELD", "模拟后端需要 secret（仅为功能控制，不代表任何安全属性）");
      const message = { scheme: "simulated-hmac-sha256", nonce: String(nonce), appDigest: String(appDigest) };
      const signature = crypto.createHmac("sha256", Buffer.from(String(secret), "utf8")).update(canonicalJson(message)).digest("hex");
      return {
        realQuote: false, // 关键：模拟证据必须自证非真实
        backendId,
        evidenceClass: "simulated",
        quote: { ...message, signature },
        measurement: null,
        tcbStatus: null,
        collateralStatus: null,
      };
    },
  };
}

// ------------------------------------------------------------------
// 策略评估（显式区分各类状态，不把非致命码一律当 pass）
// ------------------------------------------------------------------
/**
 * policy: { allowedMeasurements: string[], revokedMeasurements: string[], requireUpToDate: boolean, allowConfigurationNeeded: boolean }
 * verification: { realQuote, measurement, reportDataDigest, tcbStatus, collateralStatus, execPubkey, validUntil, signatureValid, nonceMatches }
 */
function evaluatePolicy(verification, policy = {}) {
  const {
    allowedMeasurements = [],
    revokedMeasurements = [],
    requireUpToDate = true,
    allowConfigurationNeeded = false,
  } = policy;

  if (!verification) return { decision: DECISION.BLOCKED, reason: "缺少验证结果" };
  // 模拟证据永远不能通过真实策略
  if (verification.realQuote !== true) {
    return { decision: DECISION.BLOCKED, reason: "realQuote=false：模拟证据不得通过真实 TEE 策略（不得将 HMAC/普通签名冒充 Quote）" };
  }
  if (verification.signatureValid === false) return { decision: DECISION.INVALID, reason: "Quote 签名或证书链验证失败" };
  if (verification.nonceMatches === false) return { decision: DECISION.INVALID, reason: "reportData/nonce 与验证方挑战不一致（缺少新鲜性）" };
  if (verification.tcbStatus === "Revoked") return { decision: DECISION.REVOKED, reason: "TCB 已撤销" };
  if (revokedMeasurements.includes(verification.measurement)) return { decision: DECISION.REVOKED, reason: "measurement 在撤销名单中" };
  if (allowedMeasurements.length && !allowedMeasurements.includes(verification.measurement)) {
    return { decision: DECISION.INVALID, reason: "合法签名但 measurement 不在允许策略内（这是策略拒绝，不是密码学损坏）" };
  }
  if (verification.tcbStatus === "OutOfDate") {
    return requireUpToDate
      ? { decision: DECISION.OUT_OF_DATE, reason: "TCB out-of-date，策略要求 up-to-date" }
      : { decision: DECISION.OK, reason: "TCB out-of-date 但策略允许" };
  }
  if (verification.tcbStatus === "ConfigurationNeeded") {
    return allowConfigurationNeeded
      ? { decision: DECISION.OK, reason: "configuration-needed 但策略允许（需记录限制）" }
      : { decision: DECISION.CONFIGURATION_NEEDED, reason: "需要配置/更新，策略不允许" };
  }
  if (verification.collateralStatus === "expired" || verification.collateralStatus === "unavailable") {
    return { decision: DECISION.OUT_OF_DATE, reason: `collateral ${verification.collateralStatus}` };
  }
  // DCAP/QVL 的「可视为通过」状态：OK 与 UpToDate（SWHardeningNeeded 视为可配置通过）
  if (["OK", "UpToDate"].includes(verification.tcbStatus)) {
    return { decision: DECISION.OK, reason: "Quote 签名/证书链有效、nonce 与挑战匹配、measurement 与 TCB 均满足策略" };
  }
  if (verification.tcbStatus === "SWHardeningNeeded") {
    return allowConfigurationNeeded
      ? { decision: DECISION.OK, reason: "SWHardeningNeeded 但策略允许（需记录限制）" }
      : { decision: DECISION.CONFIGURATION_NEEDED, reason: "需要软件加固，策略不允许" };
  }
  if (verification.tcbStatus == null) {
    return { decision: DECISION.UNKNOWN, reason: "缺少 TCB 状态，无法给出通过结论" };
  }
  return { decision: DECISION.UNKNOWN, reason: `TCB 状态无法归类(${verification.tcbStatus})，需人工判定` };
}

module.exports = {
  BACKEND,
  REAL_BACKENDS,
  DECISION,
  AttestationError,
  canonicalJson,
  sha256Hex,
  sha256HexUtf8,
  buildReportDataDigest,
  buildTaskBindingDigest,
  detectDevice,
  createProvider,
  evaluatePolicy,
};
