// SPDX-License-Identifier: MIT
//
// evm/revision/stageE_local.test.js
//
// 阶段 E 本地层（E-local）：真实密码学离线编码 / KZG、容量与填充度量、规范 manifest、
// 单向承诺（无循环）、M1 链下验证、畸形拒绝。
//
// 边界（阶段 E 提示词）：
//   - E-public-transport / E-DA-settlement / E-integrated 需要公网 RPC、测试币与广播授权，
//     当前不具备，一律 blocked，且不以本地结果冒充公网取回。
//   - 超容量样本必须 explicit blocked，不把失败样本从分母中消失，不截断、不缩小载荷。
//   - M1（摘要出现在 manifest）不等于 M2（payload 与 Blob 实际数据一致且足以裁决）；
//     M2 需要 KZG 求值证明与合约可验证路径，当前记为 partial/blocked。
//
// 运行：cd evm; REVISION_RUN=<abs> node node_modules/hardhat/internal/cli/cli.js \
//   test --config revision/hardhat.config.js revision/stageE_local.test.js

"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const crypto = require("node:crypto");
const { keccak256 } = require("ethers");
const blobcodec = require("./blobcodec");
const {
  MANIFEST_VERSION, BLOB_BYTES, MAX_FRAME_LEN, ENCODER_MAX_BLOBS,
  canonicalJson, buildTaskCoreDigest, buildManifest, encodeManifestToBlob, verifyM1, verifyBlobKzg,
} = require("./stageE_binding");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径的独立输出目录");
const OUT_DIR = path.join(REVISION_RUN, "stageE");
fs.mkdirSync(OUT_DIR, { recursive: true });

const DOMAIN = "hybrid-tee-rollup/batch/v1";
const CONTRACT = "0x1111111111111111111111111111111111111111";
const CHAIN_ID = 31337;

const CASES = [];
let pending = [];
function rec(caseId, fields) {
  const e = {
    caseId, stage: "E", schemaVersion: "hybrid-tee-rollup.stageE.case.v1",
    level: fields.level ?? "E-local",
    status: fields.status ?? "verified", // verified | blocked | partial
    realCrypto: fields.realCrypto ?? true,
    metrics: fields.metrics ?? null,
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
  fs.writeFileSync(path.join(OUT_DIR, "case_matrix.json"), JSON.stringify({
    schemaVersion: "hybrid-tee-rollup.stageE.case.v1", stage: "E",
    generatedAtUtc: new Date().toISOString(),
    note: "realCrypto=true 表示使用真实 c-kzg 与 trusted setup（非模拟）。status=blocked 表示缺少公网授权/合约能力，未冒充完成。",
    total: CASES.length, passed, failed: CASES.length - passed, cases: CASES,
  }, null, 2));
  console.log(`\n[stageE] case_matrix 已写入 ${path.join(OUT_DIR, "case_matrix.json")} (total=${CASES.length}, passed=${passed})`);
});

// 构造长度精确的 manifest 字节（用于容量边界测试）
function manifestBytesOfLen(n, { domain = DOMAIN, batchId = "batch-1" } = {}) {
  const base = {
    manifestVersion: MANIFEST_VERSION, encodingVersion: "blobcodec-field31-v1",
    domain, chainId: CHAIN_ID, contract: CONTRACT, batchId,
    taskCount: 1,
    tasks: [{ index: 0, taskId: "0x" + "11".repeat(32), payloadLen: 0, coreDigest: "0x" + "22".repeat(32) }],
    filler: "",
  };
  const L0 = canonicalJson(base).length;
  // filler="" 在 JSON 中已占 2 字符；改为 k 个字符后总长 = L0 + k
  const fillerLen = n - L0;
  assert.ok(fillerLen >= 0, `目标长度 ${n} 过小（最小 ${L0}）`);
  base.filler = "x".repeat(fillerLen);
  const s = canonicalJson(base);
  assert.equal(s.length, n, `构造长度不精确: ${s.length} != ${n}`);
  return Buffer.from(s, "utf8");
}
// frame 开销 = MAGIC(4) + 1 + domainLen + 8 + 8 + 32
function frameOverhead(domain = DOMAIN) {
  return 4 + 1 + Buffer.from(domain, "utf8").length + 8 + 8 + 32;
}

// ==================================================================
// E01-a 下界与正例：可逆、KZG 正确、长度与填充符合 A 口径
// ==================================================================
describe("E01 正例与容量下界", function () {
  it("小 manifest 编码可逆, KZG 真实可验证, 度量符合阶段 A 口径", function () {
    const task = {
      taskId: "0x" + "aa".repeat(32), nonce: "0xnonce-1", programVersion: "v1",
      inputCommitment: "0x" + "01".repeat(32), outputCommitment: "0x" + "02".repeat(32),
      traceCommitment: "0x" + "03".repeat(32), payloadLen: 1024,
    };
    const { manifest, manifestBytes, manifestHash, coreDigests } = buildManifest({
      domain: DOMAIN, chainId: CHAIN_ID, contract: CONTRACT, batchId: "batch-lower", tasks: [task],
    });
    const enc = encodeManifestToBlob({ domain: DOMAIN, manifestBytes, taskCount: 1 });

    // 度量口径（全部来自实际序列化）
    assert.equal(enc.payloadBytes, manifestBytes.length);
    assert.equal(enc.frameBytes, frameOverhead() + manifestBytes.length);
    assert.equal(enc.encodedBytes, Math.ceil(enc.frameBytes / 31) * 32);
    assert.equal(enc.blobCount, Math.ceil(enc.encodedBytes / BLOB_BYTES));
    assert.equal(enc.paddingBytes, enc.blobCount * BLOB_BYTES - enc.encodedBytes);
    assert.equal(enc.fieldPaddingBytes, Math.ceil(enc.frameBytes / 31) * 31 - enc.frameBytes);
    assert.equal(enc.fieldPrefixBytes, Math.ceil(enc.frameBytes / 31));
    assert.equal(enc.blobCount, 1, "下界样本应落在单 Blob 内");
    assert.equal(enc.blob.length, BLOB_BYTES);

    // 可逆性：blob -> frame -> manifest，hash 一致
    const back = blobcodec.blobToFrame(enc.blob);
    const backManifest = JSON.parse(blobcodec.decodeFrame(back).content.toString("utf8"));
    assert.equal(canonicalJson(backManifest), canonicalJson(manifest), "往返解码后 manifest 应完全一致");
    assert.equal(keccak256(Buffer.from(canonicalJson(backManifest), "utf8")), manifestHash, "manifestHash 往返一致");

    // 真实 KZG（非模拟）
    assert.equal(verifyBlobKzg(enc.blob, enc.commitment, enc.proof), true, "真实 KZG 证明必须验证通过");
    assert.equal(enc.commitment.length, 48);
    assert.ok(/^0x01[0-9a-f]{62}$/.test(enc.versionedHash), "versionedHash 应为 0x01||sha256(c)[1:]（32 字节）");

    // M1 链下验证
    const m1 = verifyM1({ blob: enc.blob, expectedCoreDigest: coreDigests[0], expectedDomain: DOMAIN, expectedVersionedHash: enc.versionedHash });
    assert.equal(m1.ok, true, m1.reason);

    rec("E01", {
      level: "E-local", status: "verified", realCrypto: true,
      metrics: {
        payloadBytes: enc.payloadBytes, frameBytes: enc.frameBytes, encodedBytes: enc.encodedBytes,
        fieldPaddingBytes: enc.fieldPaddingBytes, fieldPrefixBytes: enc.fieldPrefixBytes,
        blobCount: enc.blobCount, paddingBytes: enc.paddingBytes, blobBytes: enc.blobBytes,
        manifestHash, versionedHash: enc.versionedHash,
      },
      notes: "下界正例：可逆、真实 KZG 通过、度量符合 A 口径、M1 链下成立",
    });
  });
});

// ==================================================================
// E01-b 刚好上界与超一字节
// ==================================================================
describe("E01 容量边界", function () {
  it("frame 恰好等于容量可通过; 超一字节必须 blocked(不截断)", function () {
    const overhead = frameOverhead();
    const maxContent = MAX_FRAME_LEN - overhead; // 126976 - 79 = 126897

    // 刚好上界
    const atCapacity = encodeManifestToBlob({ domain: DOMAIN, manifestBytes: manifestBytesOfLen(maxContent), taskCount: 1 });
    assert.equal(atCapacity.frameBytes, MAX_FRAME_LEN, "frame 应恰好等于单 Blob 帧容量");
    assert.equal(atCapacity.blobCount, 1);
    assert.equal(verifyBlobKzg(atCapacity.blob, atCapacity.commitment, atCapacity.proof), true);

    // 超一字节 -> 必须抛错（blocked），不截断
    let blocked = null;
    try {
      encodeManifestToBlob({ domain: DOMAIN, manifestBytes: manifestBytesOfLen(maxContent + 1), taskCount: 1 });
    } catch (e) { blocked = e; }
    assert.ok(blocked, "超容量必须显式失败，不得静默成功");
    assert.equal(blocked.code, "SINGLE_BLOB_CAPACITY_EXCEEDED", "应为明确的超容量错误");
    assert.equal(blocked.frameBytes, MAX_FRAME_LEN + 1);

    rec("E01", {
      level: "E-local", status: "verified", realCrypto: true,
      metrics: {
        maxFrameLen: MAX_FRAME_LEN, frameOverhead: overhead, maxContentLen: maxContent,
        atCapacityFrameBytes: atCapacity.frameBytes, atCapacityEncodedBytes: atCapacity.encodedBytes,
        atCapacityBlobCount: atCapacity.blobCount, atCapacityPaddingBytes: atCapacity.paddingBytes,
        overOneByteFrameBytes: blocked.frameBytes,
      },
      notes: "刚好上界 frame=126976 可通过且真实 KZG 通过；超一字节抛 SINGLE_BLOB_CAPACITY_EXCEEDED（blocked），不截断、不缩小载荷、不把失败样本从分母消失",
    });
  });
});

// ==================================================================
// 单向承诺 / 无循环（E1 核心要求）
// ==================================================================
describe("E1 单向承诺无循环", function () {
  it("coreDigest 不依赖 manifest/versionedHash: 同 task 在不同 manifest 中 coreDigest 相同", function () {
    const task = {
      taskId: "0x" + "bb".repeat(32), nonce: "0xn", programVersion: "v1",
      inputCommitment: "0x" + "04".repeat(32), outputCommitment: "0x" + "05".repeat(32),
      traceCommitment: "0x" + "06".repeat(32), payloadLen: 512,
    };
    const a = buildManifest({ domain: DOMAIN, chainId: CHAIN_ID, contract: CONTRACT, batchId: "batch-A", tasks: [task] });
    const b = buildManifest({ domain: DOMAIN, chainId: CHAIN_ID, contract: CONTRACT, batchId: "batch-B", tasks: [task] });
    assert.notEqual(a.manifestHash, b.manifestHash, "不同 manifest 的 hash 应不同");
    assert.equal(a.coreDigests[0], b.coreDigests[0], "coreDigest 不得依赖 manifest（否则构成循环）");

    // coreDigest 也不等于 manifestHash / 不含自身
    assert.notEqual(a.coreDigests[0], a.manifestHash);

    // 直接构造：coreDigest 不含 DA 引用字段
    const core = buildTaskCoreDigest({ ...task, domain: DOMAIN });
    assert.ok(!core.includes("versionedHash") && !core.includes("daRef"));

    rec("E01", {
      level: "E-local", status: "verified", realCrypto: true,
      notes: "验证单向构造：coreDigest 不随 manifest 变化（不含 manifestHash/versionedHash/DA引用），因此无循环承诺、无自引用倒灌",
    });
  });
});

// ==================================================================
// 篡改与畸形拒绝
// ==================================================================
describe("E01 篡改与畸形拒绝", function () {
  it("内容篡改导致 payloadHash 不匹配; 坏 magic 与长度不符被拒", function () {
    const task = {
      taskId: "0x" + "cc".repeat(32), nonce: "0xn", programVersion: "v1",
      inputCommitment: "0x" + "07".repeat(32), outputCommitment: "0x" + "08".repeat(32),
      traceCommitment: "0x" + "09".repeat(32), payloadLen: 256,
    };
    const { manifestBytes, coreDigests } = buildManifest({ domain: DOMAIN, chainId: CHAIN_ID, contract: CONTRACT, batchId: "batch-t", tasks: [task] });
    const enc = encodeManifestToBlob({ domain: DOMAIN, manifestBytes, taskCount: 1 });

    // 篡改 blob 中的数据字节 -> M1 的 payloadHash 自洽检查必须失败
    const tampered = Buffer.from(enc.blob);
    tampered[100] ^= 0xff;
    const m1t = verifyM1({ blob: tampered, expectedCoreDigest: coreDigests[0], expectedDomain: DOMAIN });
    assert.equal(m1t.ok, false, "篡改后 M1 必须失败");
    assert.ok(/payloadHash/.test(m1t.reason), `原因应指向内容不一致, 实际: ${m1t.reason}`);
    // 篡改后 KZG 也必须失败
    assert.equal(verifyBlobKzg(tampered, enc.commitment, enc.proof), false, "篡改后真实 KZG 验证必须失败");

    // 坏 magic
    const badMagic = Buffer.from(enc.blob);
    // 第一个域元素的数据起始位置是 blob[1]
    badMagic[1] ^= 0xff;
    assert.throws(() => blobcodec.decodeFrame(blobcodec.blobToFrame(badMagic)), /bad magic/);

    // 域元素顶字节非零（非法 FE）不改变 codec 语义（codec 忽略顶字节），如实记录
    const feTop = Buffer.from(enc.blob);
    feTop[0] = 0xff; // 顶字节置非零
    const frameFromFeTop = blobcodec.blobToFrame(feTop);
    assert.equal(frameFromFeTop.length, MAX_FRAME_LEN, "blobToFrame 固定返回 4096*31 字节；顶字节未被读取");

    rec("E01", {
      level: "E-local", status: "verified", realCrypto: true,
      notes: "篡改 blob 数据 -> payloadHash 不自洽且真实 KZG 验证失败；坏 magic 被拒。注意：当前 codec 解码时忽略每个域元素的顶字节，因此顶字节被置非零不会改变解码结果——这是编码设计使然（顶字节恒 0），已如实记录而非声称校验了非法域元素",
    });
  });
});

// ==================================================================
// trusted setup 来源、hash 与库版本（可复核）
// ==================================================================
describe("E01 trusted setup 与库版本", function () {
  it("记录 trusted setup 文件 hash 与 c-kzg 版本, 供独立复核", function () {
    const setupPath = path.join(__dirname, "trusted_setup.txt");
    const setupSha = crypto.createHash("sha256").update(fs.readFileSync(setupPath)).digest("hex");
    const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, "package.json"), "utf8"));
    const cKzgPkg = JSON.parse(fs.readFileSync(path.join(__dirname, "node_modules", "c-kzg", "package.json"), "utf8"));
    const setupInfo = {
      path: "evm/revision/trusted_setup.txt",
      sha256: setupSha,
      bytes: fs.statSync(setupPath).size,
      declaredDependency: pkg.dependencies["c-kzg"],
      installedVersion: cKzgPkg.version,
    };
    fs.writeFileSync(path.join(OUT_DIR, "trusted_setup.json"), JSON.stringify(setupInfo, null, 2));
    assert.ok(/^[0-9a-f]{64}$/.test(setupSha));
    assert.ok(setupInfo.bytes > 0);

    rec("E01", {
      level: "E-local", status: "verified", realCrypto: true,
      metrics: { trustedSetupSha256: setupSha, trustedSetupBytes: setupInfo.bytes, cKzgVersion: cKzgPkg.version },
      notes: `trusted setup 来源与 hash 已记录（${setupSha.slice(0, 16)}…），c-kzg 版本 ${cKzgPkg.version} 可复核；证据 stageE/trusted_setup.json`,
    });
  });
});

// ==================================================================
// E08 多 Blob：当前编码器不支持 -> blocked
// ==================================================================
describe("E08 多Blob(当前不支持)", function () {
  it("超容量即 blocked; 不实现少片/重复/调序/跨批拼接的假通过", function () {
    const overhead = frameOverhead();
    let err = null;
    try {
      encodeManifestToBlob({ domain: DOMAIN, manifestBytes: manifestBytesOfLen(MAX_FRAME_LEN - overhead + 1), taskCount: 1 });
    } catch (e) { err = e; }
    assert.ok(err && err.code === "SINGLE_BLOB_CAPACITY_EXCEEDED", "超容量必须 blocked");
    rec("E08", {
      level: "E-local", status: "blocked", realCrypto: true,
      notes: "当前实际编码器 encoderMaxBlobs=1，仅支持单 Blob。多 Blob 分片/重组、少片/重复片/调序/跨批拼接校验未实现，故 E08 记为 blocked，不做任何假通过。按提示词策略二选一：本阶段选择『保留单 Blob 能力，只选可容纳矩阵；超容量样本 explicit blocked』",
    });
  });
});

// ==================================================================
// 需要公网 / 合约 DA 义务 / 联调的 case：登记 blocked
// ==================================================================
describe("E02-E15 需公网或合约DA义务(登记blocked)", function () {
  it("公网发布/独立取回/DA结算/联调 一律 blocked, 不冒充", function () {
    const blocked = [
      ["E02", "E-public-transport", "实际 type-3 发布与链上确认：需 Sepolia RPC、测试币与广播授权"],
      ["E03", "E-public-transport", "独立取回：需不同于发布者的 endpoint 与进程，且不挂载发布者本地 Blob 目录"],
      ["E04", "E-binding", "Blob A 配 task/manifest B：核心合约当前无 DA 引用字段，无法链上裁决"],
      ["E05", "E-binding", "错索引/无关 anchor/旧 batch 复用：同上，需合约侧约束"],
      ["E06", "E-binding", "内容改动重算 KZG：需 KZG 求值证明与链上验证路径"],
      ["E07", "E-binding", "只改 payload 保持 manifest（M2）：需 point-evaluation 证明与合约可验证裁决，当前 partial/blocked"],
      ["E09", "E-DA-settlement", "责任方按时补发：核心合约无 DA 披露义务与窗口"],
      ["E10", "E-DA-settlement", "责任方超时/重复 DA 挑战：同上，无罚没闭环"],
      ["E11", "E-DA-settlement", "RPC 失败/保留期过期：需公网观测，且不能罚没无责任外部方"],
      ["E12", "E-DA-settlement", "观察者崩溃恢复：需公网取回链路"],
      ["E13", "E-public-transport", "广播后崩溃/reorg/nonce 冲突：需公网"],
      ["E14", "E-integrated", "E 与 B/C/D 联调：D 真实 TEE 已 blocked"],
      ["E15", "E-DA-settlement", "DA 待决时直接 adjudicate/finalize/withdraw：需合约 DA 互锁，当前不存在"],
    ];
    for (const [id, level, reason] of blocked) {
      rec(id, { level, status: "blocked", realCrypto: false, notes: `blocked：${reason}。未以本地/Mock 结果冒充公网或真实 DA 结算` });
    }
    assert.equal(blocked.length, 13);
  });
});
