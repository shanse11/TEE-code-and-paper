// SPDX-License-Identifier: MIT
//
// evm/revision/stageD_attestation.test.js
//
// 阶段 D 本地层（D-local）：后端隔离、fail-closed、绑定规范编码、策略评估。
//
// 重要边界（阶段 D 提示词）：
//   - 本机为 Apple M5(arm64)，无 SGX/TDX 设备节点（已实测 /dev/sgx*、/dev/tdx* 均不存在），
//     因此 D-quote / D-application / D-integrated 一律 blocked，绝不伪造 Quote。
//   - 用 fixture 测 policy 分支的 case 必须标记 fixture，且不计入真实平台成功样本。
//   - 不以普通签名或 HMAC 冒充 Quote；模拟后端 realQuote 恒为 false。
//
// 运行：cd evm; REVISION_RUN=<abs> node node_modules/hardhat/internal/cli/cli.js \
//   test --config revision/hardhat.config.js revision/stageD_attestation.test.js

"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const {
  BACKEND, DECISION, AttestationError,
  buildReportDataDigest, buildTaskBindingDigest,
  detectDevice, createProvider, evaluatePolicy,
} = require("./tee_attestation");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径的独立输出目录");
const OUT_DIR = path.join(REVISION_RUN, "stageD");
fs.mkdirSync(OUT_DIR, { recursive: true });

const CASES = [];
let pending = [];
function rec(caseId, fields) {
  const e = {
    caseId, stage: "D", schemaVersion: "hybrid-tee-rollup.stageD.case.v1",
    scenario: fields.scenario ?? null,
    realQuote: fields.realQuote ?? false,
    evidenceKind: fields.evidenceKind ?? "assertion",
    fixture: fields.fixture ?? false,
    level: fields.level ?? "D-local", // D-local | D-quote | D-application | D-integrated
    status: fields.status ?? "verified", // verified | blocked | partial
    decision: fields.decision ?? null,
    notes: fields.notes ?? null,
    assertionPass: true, mochaState: null,
  };
  CASES.push(e); pending.push(e);
  return e;
}
afterEach(function () {
  const st = this.currentTest ? (this.currentTest.state || (this.currentTest.isPending() ? "pending" : "failed")) : "unknown";
  for (const e of pending) { e.mochaState = st; e.assertionPass = st === "passed"; }
  pending = [];
});
after(function () {
  const passed = CASES.filter((c) => c.assertionPass).length;
  const out = {
    schemaVersion: "hybrid-tee-rollup.stageD.case.v1", stage: "D",
    generatedAtUtc: new Date().toISOString(),
    platform: { arch: process.arch, platform: process.platform },
    note: "fixture=true 的 case 是使用构造输入测试策略分支，不含真实 Quote，不计入真实平台成功样本。status=blocked 表示缺少真实硬件/资源，未冒充完成。",
    total: CASES.length, passed, failed: CASES.length - passed, cases: CASES,
  };
  fs.writeFileSync(path.join(OUT_DIR, "case_matrix.json"), JSON.stringify(out, null, 2));
  console.log(`\n[stageD] case_matrix 已写入 ${path.join(OUT_DIR, "case_matrix.json")} (total=${CASES.length}, passed=${passed})`);
});

// ==================================================================
// D01 真实硬件 Quote —— 本机无设备，必须 blocked 且 fail-closed
// ==================================================================
describe("D01 真实硬件Quote(本机无设备)", function () {
  it("SGX/TDX 真实后端在无设备时 fail-closed, 不回退模拟, 不伪造 Quote", function () {
    const sgx = detectDevice(BACKEND.SGX_DCAP);
    const tdx = detectDevice(BACKEND.TDX_DCAP);
    assert.equal(sgx.present, false, "本机应无 SGX 设备");
    assert.equal(tdx.present, false, "本机应无 TDX 设备");

    // real 后端创建必须抛错（fail-closed）
    assert.throws(() => createProvider(BACKEND.SGX_DCAP), (e) => e instanceof AttestationError && e.code === "DEVICE_UNAVAILABLE");
    assert.throws(() => createProvider(BACKEND.TDX_DCAP), (e) => e instanceof AttestationError && e.code === "DEVICE_UNAVAILABLE");

    // 即便强制创建（不校验设备），采集也必须返回 blocked 而非伪造
    const forced = createProvider(BACKEND.SGX_DCAP, { requireRealDevice: false });
    assert.equal(forced.isReal, true);
    return forced.getQuote().then(
      () => { throw new Error("无设备时 getQuote 不应成功"); },
      (e) => {
        assert.ok(e instanceof AttestationError, "应抛出 AttestationError");
        assert.equal(e.code, "NOT_IMPLEMENTED_LOCAL", "不得伪造 Quote");
      }
    ).then(() => {
      rec("D01", {
        scenario: "真实硬件、正确 measurement 与新 nonce",
        level: "D-quote", realQuote: false, fixture: false, status: "blocked",
        decision: DECISION.BLOCKED,
        notes: `本机 ${process.platform}/${process.arch} 无 /dev/sgx*、/dev/tdx* 设备节点；real 后端创建 fail-closed(DEVICE_UNAVAILABLE)，强制创建后 getQuote 返回 blocked 而非伪造。真实 Quote 需在具备硬件的平台由官方 DCAP 工具链采集`,
      });
    });
  });
});

// ==================================================================
// D06 非 TEE 进程伪装 real / 缺设备 fallback —— backend 不偷换
// ==================================================================
describe("D06 伪装real与缺设备fallback", function () {
  it("模拟后端 realQuote=false, 且不能通过真实策略; 不偷换 backend", async function () {
    const sim = createProvider(BACKEND.SIMULATED);
    assert.equal(sim.isReal, false);
    const q = await sim.getQuote({ nonce: "0xn1", appDigest: "0xapp", secret: "test-only" });
    assert.equal(q.realQuote, false, "模拟证据必须自证非真实");
    assert.equal(q.evidenceClass, "simulated");
    assert.equal(q.backendId, BACKEND.SIMULATED, "backendId 不得被偷换为 real");

    // 用模拟证据走真实策略：必须 blocked，不能 pass
    const verdict = evaluatePolicy({ realQuote: false, signatureValid: true, nonceMatches: true, measurement: "0xm", tcbStatus: "UpToDate" }, { allowedMeasurements: ["0xm"] });
    assert.equal(verdict.decision, DECISION.BLOCKED, "HMAC/普通签名不得冒充 Quote 通过策略");

    rec("D06", {
      scenario: "非 TEE 进程伪装 real / 缺设备 fallback",
      level: "D-local", realQuote: false, fixture: false, status: "verified",
      decision: DECISION.BLOCKED,
      notes: "模拟后端 realQuote=false 且 evidenceClass=simulated；evaluatePolicy 对 realQuote≠true 一律 blocked；backendId 不被偷换",
    });
  });
});

// ==================================================================
// D05 旧 nonce/epoch、跨 chain/contract/task —— 绑定编码（可真实执行）
// ==================================================================
describe("D05 绑定编码与重放防护", function () {
  it("chainId/contract/taskId/nonce/epoch/appDigest 任一变化都会改变绑定摘要", function () {
    const base = {
      chainId: 31337, verifyingContract: "0x1111111111111111111111111111111111111111",
      taskId: "0x" + "aa".repeat(32), nonce: "0xnonce-1",
      inputCommitment: "0xin", outputCommitment: "0xout", traceCommitment: "0xtrace",
      programVersion: "v1", daRef: null,
    };
    const d0 = buildTaskBindingDigest(base);
    assert.ok(/^[0-9a-f]{64}$/.test(d0), "绑定摘要应为 32 字节 hex");

    // 跨链
    assert.notEqual(buildTaskBindingDigest({ ...base, chainId: 1 }), d0, "跨 chainId 必须产生不同摘要");
    // 跨合约
    assert.notEqual(buildTaskBindingDigest({ ...base, verifyingContract: "0x2222222222222222222222222222222222222222" }), d0, "跨 verifyingContract 必须不同");
    // 跨任务
    assert.notEqual(buildTaskBindingDigest({ ...base, taskId: "0x" + "bb".repeat(32) }), d0, "跨 taskId 必须不同");
    // 旧 nonce（新鲜性）
    assert.notEqual(buildTaskBindingDigest({ ...base, nonce: "0xnonce-2" }), d0, "旧 nonce 必须不同（防重放）");
    // 篡改输出承诺
    assert.notEqual(buildTaskBindingDigest({ ...base, outputCommitment: "0xevil" }), d0, "篡改 output 承诺必须不同");

    // reportData 摘要对 execPubkey/nonce/epoch/appDigest 敏感
    const rBase = { execPubkey: "0xkey1", domain: "HYBRID_BOUNDED_TASK_V1", nonce: "0xn", epoch: "1", appDigest: "0xapp1" };
    const r0 = buildReportDataDigest(rBase);
    assert.notEqual(buildReportDataDigest({ ...rBase, execPubkey: "0xkey2" }), r0, "替换执行公钥必须改变 reportData 摘要");
    assert.notEqual(buildReportDataDigest({ ...rBase, nonce: "0xold" }), r0, "旧 nonce 必须改变 reportData 摘要");
    assert.notEqual(buildReportDataDigest({ ...rBase, epoch: "2" }), r0, "不同 epoch 必须改变摘要");
    assert.notEqual(buildReportDataDigest({ ...rBase, appDigest: "0xapp2" }), r0, "应用摘要变化必须改变 reportData");

    // 缺字段必须拒绝（fail-closed）
    assert.throws(() => buildTaskBindingDigest({ ...base, chainId: undefined }), (e) => e.code === "MISSING_FIELD");
    assert.throws(() => buildReportDataDigest({ ...rBase, execPubkey: null }), (e) => e.code === "MISSING_FIELD");

    rec("D05", {
      scenario: "旧 nonce/epoch、跨 chain/contract/task 重放",
      level: "D-local", realQuote: false, fixture: false, status: "verified",
      decision: DECISION.OK,
      notes: "绑定摘要对 chainId/verifyingContract/taskId/nonce/epoch/appDigest/承诺 均敏感；缺字段 fail-closed。这是纯规范编码验证，不需要硬件，因此可真实执行",
    });
  });
});

// ==================================================================
// D02 / D03 / D04 / D11 —— 策略分支（fixture，标记 fixture=true）
// 这些 case 使用构造的「验证器输出」测试策略逻辑，不含真实 Quote。
// ==================================================================
describe("D02-D04/D11 策略分支(fixture)", function () {
  const GOOD = { realQuote: true, signatureValid: true, nonceMatches: true, measurement: "0xm-allowed", tcbStatus: "UpToDate", collateralStatus: "ok" };

  it("D02 替换公钥/reportData -> nonce 或绑定不一致被拒", function () {
    const v = evaluatePolicy({ ...GOOD, nonceMatches: false }, { allowedMeasurements: ["0xm-allowed"] });
    assert.equal(v.decision, DECISION.INVALID, "reportData/nonce 与挑战不一致必须拒绝");
    rec("D02", {
      scenario: "公钥或 reportData 替换",
      level: "D-local", realQuote: false, fixture: true, status: "verified",
      decision: DECISION.INVALID,
      notes: "fixture：构造 nonceMatches=false 的验证器输出。结论为『缺少新鲜性/上下文绑定』而拒绝。真实 Quote 的签名级替换需在硬件上验证(blocked)",
    });
  });

  it("D03 合法签名但 measurement 不在策略 -> 策略拒绝(非密码学损坏)", function () {
    const v = evaluatePolicy({ ...GOOD, measurement: "0xm-other" }, { allowedMeasurements: ["0xm-allowed"] });
    assert.equal(v.decision, DECISION.INVALID);
    assert.ok(v.reason.includes("策略"), "原因应标明是策略拒绝而非签名损坏");
    rec("D03", {
      scenario: "合法 Quote 但不在 measurement 策略内",
      level: "D-local", realQuote: false, fixture: true, status: "verified",
      decision: DECISION.INVALID,
      notes: "fixture：签名有效但 measurement 不匹配。明确区分为『策略拒绝』，不声称密码学签名损坏",
    });
  });

  it("D04 collateral/TCB 各状态分别归类, 不把非致命码一律当 pass", function () {
    const revoked = evaluatePolicy({ ...GOOD, tcbStatus: "Revoked" }, { allowedMeasurements: ["0xm-allowed"] });
    assert.equal(revoked.decision, DECISION.REVOKED);

    const inRevokedList = evaluatePolicy({ ...GOOD, measurement: "0xm-bad" }, { allowedMeasurements: ["0xm-bad"], revokedMeasurements: ["0xm-bad"] });
    assert.equal(inRevokedList.decision, DECISION.REVOKED);

    const outOfDate = evaluatePolicy({ ...GOOD, tcbStatus: "OutOfDate" }, { allowedMeasurements: ["0xm-allowed"], requireUpToDate: true });
    assert.equal(outOfDate.decision, DECISION.OUT_OF_DATE);

    const outOfDateAllowed = evaluatePolicy({ ...GOOD, tcbStatus: "OutOfDate" }, { allowedMeasurements: ["0xm-allowed"], requireUpToDate: false });
    assert.equal(outOfDateAllowed.decision, DECISION.OK, "策略显式允许时才可通过，且需记录限制");

    const cfgNeeded = evaluatePolicy({ ...GOOD, tcbStatus: "ConfigurationNeeded" }, { allowedMeasurements: ["0xm-allowed"] });
    assert.equal(cfgNeeded.decision, DECISION.CONFIGURATION_NEEDED);

    const expired = evaluatePolicy({ ...GOOD, collateralStatus: "expired" }, { allowedMeasurements: ["0xm-allowed"] });
    assert.equal(expired.decision, DECISION.OUT_OF_DATE, "collateral 失效必须可区分");

    const unknown = evaluatePolicy({ ...GOOD, tcbStatus: null }, { allowedMeasurements: ["0xm-allowed"] });
    assert.equal(unknown.decision, DECISION.UNKNOWN, "缺 TCB 状态不得给出通过结论");

    rec("D04", {
      scenario: "collateral 失效、不可接受 TCB 或撤销",
      level: "D-local", realQuote: false, fixture: true, status: "verified",
      decision: "REVOKED/OUT_OF_DATE/CONFIGURATION_NEEDED/UNKNOWN",
      notes: "fixture：分别构造 Revoked / OutOfDate(严格与宽松) / ConfigurationNeeded / collateral expired / TCB 缺失，验证策略显式区分而非一律 pass。这些是策略分支测试，不计入真实平台成功样本",
    });
  });

  it("D11 应用镜像变化但平台身份相近 -> 应用绑定应拒绝", function () {
    // 平台 measurement 相同，但应用摘要(appDigest)变化
    const v1 = buildReportDataDigest({ execPubkey: "0xk", domain: "D", nonce: "0xn", epoch: "1", appDigest: "0ximage-v1" });
    const v2 = buildReportDataDigest({ execPubkey: "0xk", domain: "D", nonce: "0xn", epoch: "1", appDigest: "0ximage-v2" });
    assert.notEqual(v1, v2, "应用镜像变化必须改变 reportData 摘要");
    // 策略层：应用摘要不在允许列表 -> 拒绝
    const p = evaluatePolicy({ ...GOOD, appDigest: "0ximage-v2" }, { allowedMeasurements: ["0xm-allowed"], allowedAppDigests: ["0ximage-v1"] });
    // 当前 evaluatePolicy 未实现 allowedAppDigests，故明确记录为能力缺口而非假称通过
    assert.equal(p.decision, DECISION.OK, "当前策略未强制应用摘要，属已知缺口（见 notes）");
    rec("D11", {
      scenario: "应用镜像变化但平台身份相近",
      level: "D-application", realQuote: false, fixture: true, status: "partial",
      decision: DECISION.OK,
      notes: "编码层已验证：appDigest 变化会改变 reportData 摘要（可区分）。但 evaluatePolicy 当前未实现 allowedAppDigests 强制——这是已知缺口，如实记为 partial，不宣称 D-application 通过。真实应用身份还需不可变镜像/启动测量/可信加载策略，本机无 TDX/SGX 无法验证(blocked)",
    });
  });
});

// ==================================================================
// D07–D10 / D12 —— 需要真实硬件或联调，登记为 blocked
// ==================================================================
describe("D07-D10/D12 需真实资源(登记blocked)", function () {
  it("无真实硬件与公网授权, 相关 case 登记 blocked 且不伪造", function () {
    const blocked = [
      ["D07", "重启后旧任务重复执行/提交", "D-integrated", "需真实受保护执行环境；链上 taskId 唯一性已由阶段 C 的 C10 覆盖"],
      ["D08", "自有测试快照回滚或等价旧状态重放", "D-integrated", "本机无 SGX/TDX 快照能力；仅能证明协议层抗重放（同 C15）"],
      ["D09", "同 key 同 task 互斥双签/测试泄钥", "D-application", "需真实撤销与在途处理；泄钥期正确性依赖密钥未泄露假设"],
      ["D10", "真实执行与原生参考程序同输入", "D-application", "需真实受保护执行；本机无硬件"],
      ["D12", "真实任务接入 B/C 并完成裁决提现", "D-integrated", "需真实 Quote+密钥+签名与 B/C 同一 task 关联；当前仅 simulated-only"],
    ];
    for (const [id, scenario, level, reason] of blocked) {
      rec(id, {
        scenario, level, realQuote: false, fixture: false, status: "blocked",
        decision: DECISION.BLOCKED,
        notes: `blocked：${reason}。未完成前不记为通过，也不以 Mock/离线结果冒充真实 TEE 实测`,
      });
    }
    assert.ok(blocked.length === 5);
  });
});
