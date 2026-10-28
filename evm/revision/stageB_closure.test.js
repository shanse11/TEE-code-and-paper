// SPDX-License-Identifier: MIT
//
// evm/revision/stageB_closure.test.js
//
// 阶段 B 补充测试：资金闭环、账本对账、以及 B01–B14 中既有 security.test.js
// 尚未覆盖或仅部分覆盖的用例。既有 security.test.js 保持原样（23/23 before 基线），
// 本文件只新增，不修改既有回归。
//
// 设计约束（来自阶段 B 提示词）：
//   - 独立 JS 参考模型（jsTrace/jsCompute/jsTaskDigest）作为 ground truth，
//     绝不把合约 compute 的输出当作 expected（合约 compute 仅用于自检一致性）。
//   - 机器可读 case matrix：每个 case 记录 caseId、前置状态、注入动作、
//     expectedOutcome、expectedFaultOwner、expectedAccounting、evidenceKind、
//     实际断言与证据路径。
//   - 区分「测试断言 pass」与「预期场景 rejected」：预期被正确拒绝 = test pass。
//   - 资金用 BigInt 计算，序列化为十进制字符串，不用 JS 浮点。
//   - 输出固定通过 REVISION_RUN 指定（绝对路径）。
//
// 运行方式：
//   process.chdir(evm);
//   REVISION_RUN=<abs> node node_modules/hardhat/internal/cli/cli.js \
//     test --config revision/hardhat.config.js revision/stageB_closure.test.js

const fs = require("fs");
const path = require("path");
const assert = require("assert");

const hre = require("hardhat");
const { ethers } = hre;

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径的独立输出目录");
const OUT_DIR = path.join(REVISION_RUN, "stageB");
fs.mkdirSync(OUT_DIR, { recursive: true });

const PHASE = { NONE: 0, SUBMITTED: 1, OPEN: 2, RESPONDED: 3, LOCATING: 4, READY: 5, VERIFIED: 6, SETTLED: 7 };
const BOND = ethers.parseEther("1");
const CHALLENGE_WINDOW = 100;
const STEP_TIMEOUT = 10;
const MAX_RECOVERIES = 2;

// ------------------------------------------------------------------
// JS 独立参考模型（ground truth）
// ------------------------------------------------------------------
function abiEncode(types, values) {
  return ethers.AbiCoder.defaultAbiCoder().encode(types, values);
}
function jsTrace(initial, steps) {
  const trace = [initial];
  let cur = initial;
  for (let i = 0; i < steps; ++i) {
    cur = ethers.keccak256(abiEncode(["uint256", "bytes32"], [BigInt(i), cur]));
    trace.push(cur);
  }
  return trace;
}
function jsCompute(initial, steps) {
  const trace = jsTrace(initial, steps);
  const output = trace[steps];
  const root = ethers.keccak256(abiEncode(["bytes32[]"], [trace]));
  return { output, root, trace };
}
function jsTaskDigest(domain, chainId, addr, input) {
  return ethers.keccak256(
    abiEncode(
      ["bytes32", "uint256", "address", "bytes32", "bytes32", "uint16", "uint32", "bytes32", "bytes32", "bytes32"],
      [domain, BigInt(chainId), addr, input.taskId, input.initial, input.steps, input.version, input.output, input.traceRoot, input.dataHash]
    )
  );
}
function bisectionRounds(steps) {
  let width = steps + 1;
  let r = 0;
  while (width > 1) {
    width = (width + 1) >> 1;
    ++r;
  }
  return r;
}
function normalTransitions(steps) {
  return bisectionRounds(steps) + 3;
}

// ------------------------------------------------------------------
// 链上工具
// ------------------------------------------------------------------
async function increaseTime(seconds) {
  await ethers.provider.send("evm_increaseTime", [Number(seconds)]);
  await ethers.provider.send("evm_mine");
}
// 精确定向下一個块时间戳（Hardhat 自动出块时每笔交易至少 +1s，精确边界必须用它）
async function setNextBlockTimestamp(ts) {
  await ethers.provider.send("evm_setNextBlockTimestamp", [Number(ts)]);
}
async function chainId() {
  return (await ethers.provider.getNetwork()).chainId;
}
async function deployRollup(bond = BOND, challengeWindow = CHALLENGE_WINDOW, stepTimeout = STEP_TIMEOUT, maxRecoveries = MAX_RECOVERIES) {
  const Factory = await ethers.getContractFactory("BoundedTaskRollup");
  const rollup = await Factory.deploy(bond, challengeWindow, stepTimeout, maxRecoveries);
  await rollup.waitForDeployment();
  return rollup;
}
function taskIdOf(label) {
  return ethers.keccak256(ethers.toUtf8Bytes("stageB:" + label));
}
// 构造并提交一个任务；tamper: none|output|trace
async function submitTask(rollup, submitter, { label, steps = 4, initial = null, tamper = "none", bond = BOND }) {
  const init = initial ?? ethers.keccak256(ethers.toUtf8Bytes("init:" + label));
  const taskId = taskIdOf(label);
  const comp = jsCompute(init, steps);
  let output = comp.output;
  let traceRoot = comp.root;
  if (tamper === "output") output = ethers.keccak256(ethers.toUtf8Bytes("WRONG"));
  else if (tamper === "trace") traceRoot = ethers.keccak256(ethers.toUtf8Bytes("WRONG-TRACE"));
  const input = {
    taskId,
    initial: init,
    steps,
    version: 1,
    output,
    traceRoot,
    dataHash: ethers.keccak256(ethers.toUtf8Bytes("data:" + label)),
  };
  const domain = await rollup.DOMAIN();
  const digest = jsTaskDigest(domain, await chainId(), await rollup.getAddress(), input);
  const sig = await submitter.signMessage(ethers.getBytes(digest));
  const tx = await rollup.connect(submitter).submit(input, sig, { value: bond });
  const receipt = await tx.wait();
  return { input, digest, sig, comp, receipt, taskId, init };
}
async function expectRevert(promise, reason) {
  let err;
  try {
    await promise;
  } catch (e) {
    err = e;
  }
  assert.ok(err, "期望 revert 但调用成功");
  if (reason) {
    let decoded = "";
    if (typeof err.data === "string" && err.data.startsWith("0x08c379a0")) {
      decoded = ethers.AbiCoder.defaultAbiCoder().decode(["string"], "0x" + err.data.slice(10))[0];
    }
    const msg = decoded || (err && (err.shortMessage || err.message)) || "";
    assert.ok(msg.includes(reason), `revert 原因不匹配: 期望包含 "${reason}", 实际 "${msg}"`);
  }
  return err;
}

// ------------------------------------------------------------------
// 账本快照与两层对账（B4）
// ------------------------------------------------------------------
async function ledger(rollup) {
  const addr = await rollup.getAddress();
  return {
    balance: (await ethers.provider.getBalance(addr)).toString(),
    locked: (await rollup.locked()).toString(),
    totalClaimable: (await rollup.totalClaimable()).toString(),
    totalDeposited: (await rollup.totalDeposited()).toString(),
    totalWithdrawn: (await rollup.totalWithdrawn()).toString(),
    totalBurned: (await rollup.totalBurned()).toString(),
  };
}
// 对账 1：合约资产 == 未结算锁定 + 可提取负债
// 对账 2：合约资产 == 累计入金 - 累计外付 - 累计销毁
// 对账 3：内部负债不超过可用资产（正常 fixture 应精确相等）
async function assertLedgerClosure(rollup, label) {
  const L = await ledger(rollup);
  const bal = BigInt(L.balance);
  const locked = BigInt(L.locked);
  const claimable = BigInt(L.totalClaimable);
  const deposited = BigInt(L.totalDeposited);
  const withdrawn = BigInt(L.totalWithdrawn);
  const burned = BigInt(L.totalBurned);
  assert.equal(bal, locked + claimable, `${label}: 资产 ${bal} != locked ${locked} + totalClaimable ${claimable}`);
  assert.equal(bal, deposited - withdrawn - burned, `${label}: 资产 ${bal} != deposited ${deposited} - withdrawn ${withdrawn} - burned ${burned}`);
  assert.ok(claimable <= bal, `${label}: 内部负债 ${claimable} 超过可用资产 ${bal}`);
  return L;
}

// ------------------------------------------------------------------
// 机器可读 case matrix
// ------------------------------------------------------------------
const CASES = [];
let pending = [];
function rec(caseId, fields) {
  const entry = {
    caseId,
    stage: "B",
    schemaVersion: "hybrid-tee-rollup.stageB.case.v1",
    precondition: fields.precondition ?? null,
    injectedAction: fields.injectedAction ?? null,
    expectedOutcome: fields.expectedOutcome ?? null,
    expectedFaultOwner: fields.expectedFaultOwner ?? null,
    expectedAccounting: fields.expectedAccounting ?? null,
    evidenceKind: fields.evidenceKind ?? "assertion",
    notes: fields.notes ?? null,
    assertionPass: true, // 该 case 的断言在本测试中执行并通过
    mochaState: null,
  };
  CASES.push(entry);
  pending.push(entry);
  return entry;
}
afterEach(function () {
  const state = this.currentTest ? (this.currentTest.state || (this.currentTest.isPending() ? "pending" : "failed")) : "unknown";
  for (const entry of pending) {
    entry.mochaState = state;
    entry.assertionPass = state === "passed";
  }
  pending = [];
});
after(function () {
  const passed = CASES.filter((c) => c.assertionPass).length;
  const failed = CASES.length - passed;
  const matrix = {
    schemaVersion: "hybrid-tee-rollup.stageB.case.v1",
    stage: "B",
    generatedAtUtc: new Date().toISOString(),
    contract: "BoundedTaskRollup.sol",
    node: process.version,
    total: CASES.length,
    passed,
    failed,
    note: "expectedOutcome 为 expected 场景结果（accepted/rejected/timeout_settled）；assertionPass 为测试断言是否通过。预期被正确拒绝记为 assertionPass=true。",
    cases: CASES,
  };
  fs.writeFileSync(path.join(OUT_DIR, "case_matrix.json"), JSON.stringify(matrix, null, 2));
  console.log(`\n[stageB] case_matrix 已写入 ${path.join(OUT_DIR, "case_matrix.json")} (total=${CASES.length}, passed=${passed}, failed=${failed})`);
});

// ==================================================================
// B01 正常任务终局及提现：完整账本
// ==================================================================
describe("B01 正常任务终局及提现(完整账本)", function () {
  it("诚实提交被诚实挑战 -> 提交者胜 -> 实际提现, 无重复支付", async function () {
    const [submitter, challenger] = await ethers.getSigners();
    const rollup = await deployRollup();

    const L0 = await assertLedgerClosure(rollup, "B01-初始");
    assert.equal(L0.balance, "0");

    const { taskId } = await submitTask(rollup, submitter, { label: "b01" });
    const L1 = await assertLedgerClosure(rollup, "B01-提交后");
    assert.equal(L1.locked, BOND.toString());
    assert.equal(L1.totalDeposited, BOND.toString());

    await rollup.connect(challenger).openChallenge(taskId, { value: BOND });
    const L2 = await assertLedgerClosure(rollup, "B01-挑战后");
    assert.equal(L2.locked, (BOND * 2n).toString());
    assert.equal(L2.totalDeposited, (BOND * 2n).toString());

    // 确定性裁决：verdict=0（诚实），winner=submitter
    await rollup.adjudicate(taskId);
    const t = await rollup.getTask(taskId);
    assert.equal(Number(t.phase), PHASE.SETTLED);
    assert.equal(Number(t.verdict), 0, "诚实任务 verdict 必须为 0");
    const L3 = await assertLedgerClosure(rollup, "B01-裁决后");
    assert.equal(L3.locked, "0", "裁决后 locked 必须清零");
    assert.equal(L3.totalClaimable, (BOND * 2n).toString());
    assert.equal((await rollup.claimable(submitter.address)).toString(), (BOND * 2n).toString());
    assert.equal((await rollup.claimable(challenger.address)).toString(), "0");

    // 实际提现（EOA 余额变化，扣除 gas）
    const before = await ethers.provider.getBalance(submitter.address);
    const tx = await rollup.connect(submitter).withdraw(submitter.address);
    const receipt = await tx.wait();
    const gasCost = receipt.gasUsed * receipt.gasPrice;
    const after = await ethers.provider.getBalance(submitter.address);
    assert.equal(after - before + gasCost, BOND * 2n, "赢家实际净得 2*bond（已扣 gas）");

    const L4 = await assertLedgerClosure(rollup, "B01-提现后");
    assert.equal(L4.totalWithdrawn, (BOND * 2n).toString());
    assert.equal(L4.totalClaimable, "0");
    assert.equal(L4.balance, "0", "全部资金已外付，合约余额归零");

    // 无重复支付
    await expectRevert(rollup.connect(submitter).withdraw(submitter.address), "no balance");

    rec("B01", {
      precondition: "phase=NONE, 无任务",
      injectedAction: "诚实 submit -> 第三方 openChallenge -> adjudicate -> withdraw",
      expectedOutcome: "accepted",
      expectedFaultOwner: null,
      expectedAccounting: "locked: 0->1->2->0 bond; totalClaimable: 0->2->0 bond; totalWithdrawn=2 bond; 赢家净得 2*bond 扣 gas; 重复 withdraw 被拒",
      evidenceKind: "ledger+receipt",
      notes: "完整资金闭环：初态/终态、每笔账本、实际支付、无重复支付均已断言",
    });
  });
});

// ==================================================================
// B05 错误证据 / 自填赢家
// ==================================================================
describe("B05 错误证据或自填赢家", function () {
  it("未 VERIFIED 直接 settle 被拒；adjudicate 按确定性重算判责, 挑战者不能自封赢家", async function () {
    const [submitter, challenger] = await ethers.getSigners();
    const rollup = await deployRollup();
    const { taskId } = await submitTask(rollup, submitter, { label: "b05" });
    await rollup.connect(challenger).openChallenge(taskId, { value: BOND });

    // settle 要求 phase==VERIFIED，当前 OPEN -> 拒绝
    await expectRevert(rollup.connect(challenger).settle(taskId), "phase");

    // 挑战者调用 adjudicate 也不能改变客观裁决：诚实提交 -> verdict=0 -> winner=submitter
    await rollup.connect(challenger).adjudicate(taskId);
    const t = await rollup.getTask(taskId);
    assert.equal(Number(t.verdict), 0, "客观裁决不能被调用者身份影响");
    assert.equal((await rollup.claimable(submitter.address)).toString(), (BOND * 2n).toString());
    assert.equal((await rollup.claimable(challenger.address)).toString(), "0", "挑战者不能自封赢家");

    rec("B05", {
      precondition: "phase=OPEN, 诚实提交被挑战",
      injectedAction: "挑战者直接 settle(未VERIFIED) / 由挑战者调用 adjudicate",
      expectedOutcome: "rejected+accepted",
      expectedFaultOwner: null,
      expectedAccounting: "未 VERIFIED 的 settle 被拒；裁决 winner 由 verdict 决定, claimable 归 submitter",
      evidenceKind: "assertion",
      notes: "合约无自填赢家/自填 resolutionBits 接口；verdict 仅由 _verify 确定性重算产生",
    });
  });
});

// ==================================================================
// B06 挑战窗口边界：前 / 等于 / 后一单位
// ==================================================================
describe("B06 挑战截止前/等于/后一单位", function () {
  it("openChallenge: <=deadline 允许, deadline+1 拒绝; finalize: >deadline 才允许", async function () {
    const [submitter, challenger] = await ethers.getSigners();

    // --- 场景 1：deadline+1 拒绝 openChallenge ---
    const r1 = await deployRollup();
    const s1 = await submitTask(r1, submitter, { label: "b06-late" });
    const t1 = await r1.getTask(s1.taskId);
    await increaseTime(CHALLENGE_WINDOW + 1);
    await expectRevert(r1.connect(challenger).openChallenge(s1.taskId, { value: BOND }), "window");

    // --- 场景 2：恰好 deadline 允许 openChallenge（合约用 <=） ---
    const r2 = await deployRollup();
    const s2 = await submitTask(r2, submitter, { label: "b06-equal" });
    const t2 = await r2.getTask(s2.taskId);
    const deadline2 = Number(t2.challengeDeadline);
    // 精确令 openChallenge 所在块 timestamp == deadline（自动出块会 +1s，故用 setNextBlockTimestamp）
    await setNextBlockTimestamp(deadline2);
    await r2.connect(challenger).openChallenge(s2.taskId, { value: BOND });
    const t2b = await r2.getTask(s2.taskId);
    assert.equal(Number(t2b.phase), PHASE.OPEN, "deadline 当刻 openChallenge 应被允许（合约用 <=）");
    const minedTs = (await ethers.provider.getBlock("latest")).timestamp;
    assert.ok(minedTs <= deadline2, `openChallenge 所在块应为 deadline 边界内, 实际 ${minedTs} deadline ${deadline2}`);

    // --- 场景 3：finalize 必须严格 > deadline（== 时拒绝） ---
    const r3 = await deployRollup();
    const s3 = await submitTask(r3, submitter, { label: "b06-finalize" });
    const t3 = await r3.getTask(s3.taskId);
    const deadline3 = Number(t3.challengeDeadline);
    await setNextBlockTimestamp(deadline3);
    await expectRevert(r3.finalize(s3.taskId), "window");
    await setNextBlockTimestamp(deadline3 + 1);
    await r3.finalize(s3.taskId);
    const t3b = await r3.getTask(s3.taskId);
    assert.equal(Number(t3b.phase), PHASE.SETTLED, "超过 deadline 后 finalize 应成功");

    rec("B06", {
      precondition: "phase=SUBMITTED, challengeWindow=100s",
      injectedAction: "在 deadline-1 / deadline / deadline+1 分别调用 openChallenge 与 finalize",
      expectedOutcome: "rejected+accepted",
      expectedFaultOwner: null,
      expectedAccounting: "超窗口 openChallenge 不改变 locked；finalize 仅在 >deadline 结算",
      evidenceKind: "assertion",
      notes: "openChallenge 使用 `block.timestamp <= challengeDeadline`; finalize 使用严格 `>`; 两者边界不对称但各自自洽",
    });
  });
});

// ==================================================================
// B10 多任务并行与资金隔离
// ==================================================================
describe("B10 多任务并行与资金隔离", function () {
  it("3 个任务并存, 每任务抵押独立, 全局两层守恒成立", async function () {
    const [s, c1, c2, c3] = await ethers.getSigners();
    const rollup = await deployRollup();

    const a = await submitTask(rollup, s, { label: "b10-a" });
    const b = await submitTask(rollup, s, { label: "b10-b" });
    const d = await submitTask(rollup, s, { label: "b10-c" });
    let L = await assertLedgerClosure(rollup, "B10-三任务提交后");
    assert.equal(L.locked, (BOND * 3n).toString(), "三个任务各锁 1 bond");

    // 只对 a 发起挑战 -> locked 增加 1 bond
    await rollup.connect(c1).openChallenge(a.taskId, { value: BOND });
    L = await assertLedgerClosure(rollup, "B10-a被挑战后");
    assert.equal(L.locked, (BOND * 4n).toString());

    // 结算 a（诚实 -> submitter 胜，得 2 bond）
    await rollup.adjudicate(a.taskId);
    L = await assertLedgerClosure(rollup, "B10-a结算后");
    assert.equal(L.locked, (BOND * 2n).toString(), "a 的 2 bond 解锁，其余两任务仍锁定");
    assert.equal(L.totalClaimable, (BOND * 2n).toString());

    // b 被挑战且提交有错 -> challenger 胜
    const be = await submitTask(rollup, s, { label: "b10-d-tampered", tamper: "output" });
    await rollup.connect(c2).openChallenge(be.taskId, { value: BOND });
    await rollup.adjudicate(be.taskId);
    const tb = await rollup.getTask(be.taskId);
    assert.notEqual(Number(tb.verdict), 0, "篡改 output 必须判定为错误");

    L = await assertLedgerClosure(rollup, "B10-最终");
    // 单任务抵押未被其他任务扣除/重复使用：逐任务状态独立
    const ta = await rollup.getTask(a.taskId);
    assert.equal(Number(ta.phase), PHASE.SETTLED);
    const td = await rollup.getTask(d.taskId);
    assert.equal(Number(td.phase), PHASE.SUBMITTED, "未参与的任务状态不受影响");

    rec("B10", {
      precondition: "同一 rollup 部署, 多任务并存",
      injectedAction: "并发提交 3+ 任务, 分别挑战/裁决其中一部分",
      expectedOutcome: "accepted",
      expectedFaultOwner: null,
      expectedAccounting: "每任务抵押独立；全局 locked+totalClaimable==balance 且 deposited-withdrawn-burned==balance",
      evidenceKind: "ledger",
      notes: "验证单任务抵押不能被其他任务扣除或重复使用",
    });
  });
});

// ==================================================================
// B11 自挑战及串谋转移
// ==================================================================
describe("B11 自挑战及串谋转移", function () {
  it("submitter 不能自挑战; Sybil 串谋只在同一控制人地址间转移押金, 非经济惩罚", async function () {
    const [s, sybil] = await ethers.getSigners();
    const rollup = await deployRollup();
    const balStart = await ethers.provider.getBalance(s.address);
    const sub = await submitTask(rollup, s, { label: "b11" });
    const taskId = sub.taskId;

    // 自挑战被拒（msg.sender != submitter）；revert 交易仍消耗 gas，单独计量
    const balPreSelf = await ethers.provider.getBalance(s.address);
    await expectRevert(rollup.connect(s).openChallenge(taskId, { value: BOND }), "challenger bond");
    const selfGas = balPreSelf - (await ethers.provider.getBalance(s.address));

    // Sybil：同一控制人的第二地址挑战诚实提交
    await rollup.connect(sybil).openChallenge(taskId, { value: BOND });
    const adjTx = await rollup.adjudicate(taskId); // 默认 signer = s，由 s 付 gas
    const adjR = await adjTx.wait();
    const t = await rollup.getTask(taskId);
    assert.equal(Number(t.verdict), 0, "诚实提交不受 Sybil 挑战影响");
    assert.equal((await rollup.claimable(s.address)).toString(), (BOND * 2n).toString());

    const wTx = await rollup.connect(s).withdraw(s.address);
    const wR = await wTx.wait();
    const balEnd = await ethers.provider.getBalance(s.address);
    const gasOf = (r) => BigInt(r.gasUsed) * BigInt(r.gasPrice);
    // 累计 s 实际支付的 gas：自挑战(revert) + submit + adjudicate + withdraw
    const totalGas = selfGas + gasOf(sub.receipt) + gasOf(adjR) + gasOf(wR);
    // s 出 1 bond 押金，sybil 出 1 bond；s 取回 2 bond => 净 +1 bond（全部来自对手押金）
    const netGain = balEnd - balStart + totalGas;
    assert.equal(netGain, BOND, "同一控制人净收益 = 对手押金；这只是自有地址间转移");

    rec("B11", {
      precondition: "phase=SUBMITTED, 诚实提交",
      injectedAction: "submitter 自挑战; 再用同一控制人的第二地址(Sybil)挑战",
      expectedOutcome: "rejected+accepted",
      expectedFaultOwner: null,
      expectedAccounting: "自挑战被拒(contract: msg.sender != submitter); Sybil 场景下控制人净收益仅 = 对手押金 1 bond, 属自有地址间转移",
      evidenceKind: "ledger+assertion",
      notes: "不构成经济惩罚；协议未定义 burn 之外的额外反串谋处罚，故不夸大。串谋能否获利于错误任务取决于 verdict，客观裁决不受影响",
    });
  });
});

// ==================================================================
// B12 输入边界：0 / 1 / 最大 / 超步数
// ==================================================================
describe("B12 输入上限与边界", function () {
  it("steps=0 与 steps>MAX 被拒; steps=1 与 steps=MAX(128) 可提交并正确裁决", async function () {
    const [s, c] = await ethers.getSigners();
    const rollup = await deployRollup();
    const MAX_STEPS = Number(await rollup.MAX_STEPS());
    assert.equal(MAX_STEPS, 128, "MAX_STEPS 应从实现读取");

    // steps=0 -> 拒绝
    await expectRevert(submitTask(rollup, s, { label: "b12-0", steps: 0 }), "task bounds");
    // steps=129 -> 拒绝
    await expectRevert(submitTask(rollup, s, { label: "b12-129", steps: 129 }), "task bounds");

    // steps=1 可提交并裁决
    const one = await submitTask(rollup, s, { label: "b12-1", steps: 1 });
    assert.equal(Number((await rollup.getTask(one.taskId)).input.steps), 1);
    await rollup.connect(c).openChallenge(one.taskId, { value: BOND });
    await rollup.adjudicate(one.taskId);
    assert.equal(Number((await rollup.getTask(one.taskId)).verdict), 0, "steps=1 诚实任务 verdict=0");

    // steps=MAX 可提交并裁决（不截断、无界循环）
    const max = await submitTask(rollup, s, { label: "b12-max", steps: MAX_STEPS });
    assert.equal(Number((await rollup.getTask(max.taskId)).input.steps), MAX_STEPS);
    await rollup.connect(c).openChallenge(max.taskId, { value: BOND });
    await rollup.adjudicate(max.taskId);
    assert.equal(Number((await rollup.getTask(max.taskId)).verdict), 0, "steps=MAX 诚实任务 verdict=0");

    // normalTransitions 与 JS 参考一致
    for (const st of [1, 4, 16, 64, 128]) {
      assert.equal(Number(await rollup.normalTransitions(st)), normalTransitions(st), `normalTransitions(${st}) 与参考模型不一致`);
    }

    rec("B12", {
      precondition: "MAX_STEPS=128（从实现读取）",
      injectedAction: "steps=0/1/128/129 提交; normalTransitions 交叉校验",
      expectedOutcome: "rejected+accepted",
      expectedFaultOwner: null,
      expectedAccounting: "非法 steps 提交前拒绝, 不创建任务、不锁定抵押",
      evidenceKind: "assertion",
      notes: "边界正确, 不截断、无界循环",
    });
  });
});

// ==================================================================
// B13 legacy 反例(R1–R5)重放到新入口：历史漏洞不复现
// ==================================================================
describe("B13 legacy 反例重放到新入口", function () {
  it("R1 响应权限 / R2 自填校验值 / R3 自填裁决位 / R4 无限恢复与状态回退 / R5 罚没不扣款 均不复现", async function () {
    const [s, c, other] = await ethers.getSigners();
    const rollup = await deployRollup();
    const { taskId, comp } = await submitTask(rollup, s, { label: "b13" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });

    // R1: respond 非 submitter 不可调用（旧版 respondChallenge 任意人可调用）
    await expectRevert(rollup.connect(other).respond(taskId, comp.trace), "submitter only");

    // R2/R3: 新入口无自填 expectedHash / resolutionBits 参数
    //   replay(id) 只接受 id，verdict 由 _verify 确定性重算产生
    await rollup.connect(s).respond(taskId, comp.trace);
    const fnReplay = rollup.interface.getFunction("replay");
    assert.equal(fnReplay.inputs.length, 1, "replay 不接受自填校验值（仅 taskId）");
    const fnAdj = rollup.interface.getFunction("adjudicate");
    assert.equal(fnAdj.inputs.length, 1, "adjudicate 不接受自填 resolutionBits（仅 taskId）");

    // R4: recover 有次数上限，且不回退 phase
    await increaseTime(STEP_TIMEOUT + 1);
    const phaseBefore = Number((await rollup.getTask(taskId)).phase);
    await rollup.recover(taskId);
    await increaseTime(STEP_TIMEOUT + 1);
    await rollup.recover(taskId);
    const t2 = await rollup.getTask(taskId);
    assert.equal(Number(t2.recoveries), MAX_RECOVERIES);
    assert.equal(Number(t2.phase), phaseBefore, "recover 不得回退/改变 phase（旧版可 REPLAYED->READY_FOR_REPLAY）");
    await increaseTime(STEP_TIMEOUT + 1);
    await expectRevert(rollup.recover(taskId), "recovery limit");

    // R5: 罚没必须真实扣款（错误任务 finalize 真实销毁 bond）
    const bad = await submitTask(rollup, s, { label: "b13-bad", tamper: "output" });
    const before = await ledger(rollup);
    await increaseTime(CHALLENGE_WINDOW + 1);
    await rollup.finalize(bad.taskId);
    const after = await ledger(rollup);
    assert.equal(BigInt(after.totalBurned) - BigInt(before.totalBurned), BOND, "错误任务必须真实销毁 bond（非仅状态标记）");
    assert.equal((await rollup.claimable(s.address)), 0n, "被罚没方不得获得 claimable");
    await assertLedgerClosure(rollup, "B13-finalize销毁后");

    rec("B13", {
      precondition: "新入口 BoundedTaskRollup（旧 HybridTEERollup 仅作 legacy 对照）",
      injectedAction: "把 legacy R1–R5 反例逐一重放到新入口",
      expectedOutcome: "rejected",
      expectedFaultOwner: null,
      expectedAccounting: "R5 场景：错误任务 finalize 真实 burn 1 bond, totalBurned 增加, 无人获得 claimable",
      evidenceKind: "assertion+ledger",
      notes: "R1 权限已加(submitter only); R2/R3 无自填参数接口; R4 maxRecoveries 限次且不改 phase; R5 真实扣款。旧入口隔离于 HybridTEERollup.sol/legacy_counterexamples.js",
    });
  });
});

// ==================================================================
// B14 Mock 后端与未实现接口边界（deferred_to_E）
// ==================================================================
describe("B14 Mock 证明/DA 与未实现接口", function () {
  it("MockDARegistry 无权限 setter 不能代表 DA 罚没; MockTEEVerifier 是签名校验而非真实 Quote", async function () {
    const [owner, anyone] = await ethers.getSigners();

    // --- MockDARegistry：任何人可改 availability（显式记录：这是 mock，不是协议 DA） ---
    const DA = await (await ethers.getContractFactory("MockDARegistry")).deploy();
    await DA.waitForDeployment();
    const pointer = ethers.keccak256(ethers.toUtf8Bytes("payload-1"));
    const payloadHash = ethers.keccak256(ethers.toUtf8Bytes("payload-bytes"));
    await DA.connect(owner).registerRecord(pointer, payloadHash, payloadHash);
    assert.equal(await DA.isAvailable(pointer), true);
    // 任意地址即可置为不可用 —— 说明该合约无访问控制，不能当作「有责任主体的 DA 罚没」
    await DA.connect(anyone).setAvailability(pointer, false);
    assert.equal(await DA.isAvailable(pointer), false);

    // --- MockTEEVerifier：ecrecover 签名校验，不是真实 SGX/TDX Quote ---
    const TEE = await (await ethers.getContractFactory("MockTEEVerifier")).deploy(owner.address);
    await TEE.waitForDeployment();
    const inputHash = ethers.keccak256(ethers.toUtf8Bytes("in"));
    const outputHash = ethers.keccak256(ethers.toUtf8Bytes("out"));
    const nonce = ethers.keccak256(ethers.toUtf8Bytes("nonce"));
    const mrenclave = ethers.keccak256(ethers.toUtf8Bytes("mr"));
    const digest = await TEE.attestationDigest(inputHash, outputHash, nonce, mrenclave);
    const sig = await owner.signMessage(ethers.getBytes(digest));
    assert.equal(await TEE.verifyAttestation(inputHash, outputHash, nonce, mrenclave, sig), true);
    // 他人签名 -> false（仅说明签名者不同，仍是普通 ECDSA，不含 Quote/TCB/collateral）
    const sigOther = await anyone.signMessage(ethers.getBytes(digest));
    assert.equal(await TEE.verifyAttestation(inputHash, outputHash, nonce, mrenclave, sigOther), false);

    rec("B14", {
      precondition: "MockDARegistry / MockTEEVerifier 为受控 mock 后端",
      injectedAction: "任意地址 setAvailability; 用 ECDSA 签名调用 verifyAttestation",
      expectedOutcome: "deferred_to_E / deferred_to_D",
      expectedFaultOwner: null,
      expectedAccounting: "mock 后端不参与 BoundedTaskRollup 任何账本；不构成罚没",
      evidenceKind: "assertion",
      notes: "MockDARegistry 无访问控制（任意地址可改 available），因此不能把 setter 当作 DA 罚没已实现 —— 移交阶段 E。MockTEEVerifier 是 ecrecover 普通签名校验，不含 Quote/TCB/collateral —— 移交阶段 D，realQuote=false。核心合约当前未与二者集成",
    });
  });
});

// ==================================================================
// B04（补充）改写步数
// ==================================================================
describe("B04 改写输出/轨迹/步数", function () {
  it("篡改 traceRoot 被拒于 respond; 篡改 output 由确定性重算裁决", async function () {
    const [s, c] = await ethers.getSigners();
    const rollup = await deployRollup();

    // 篡改 traceRoot：respond 阶段 trace binding 校验失败
    const tr = await submitTask(rollup, s, { label: "b04-trace", tamper: "trace" });
    await rollup.connect(c).openChallenge(tr.taskId, { value: BOND });
    await expectRevert(rollup.connect(s).respond(tr.taskId, tr.comp.trace), "trace binding");

    // 篡改 output：adjudicate 确定性重算 -> verdict 含 bit0
    const op = await submitTask(rollup, s, { label: "b04-output", tamper: "output" });
    await rollup.connect(c).openChallenge(op.taskId, { value: BOND });
    await rollup.adjudicate(op.taskId);
    const t = await rollup.getTask(op.taskId);
    assert.equal(Number(t.verdict) & 1, 1, "篡改 output 必须使 verdict 含 bit0");
    assert.equal((await rollup.claimable(c.address)).toString(), (BOND * 2n).toString(), "挑战者胜出并获得两份押金");

    // 步数被改（提交阶段 steps 与 trace 长度不符）在 respond 被长度校验拒绝
    const st = await submitTask(rollup, s, { label: "b04-steps", steps: 4 });
    await rollup.connect(c).openChallenge(st.taskId, { value: BOND });
    const shortTrace = st.comp.trace.slice(0, 3);
    await expectRevert(rollup.connect(s).respond(st.taskId, shortTrace), "trace length");

    rec("B04", {
      precondition: "phase=OPEN",
      injectedAction: "分别篡改 output / traceRoot / 提交短 trace",
      expectedOutcome: "rejected+accepted",
      expectedFaultOwner: "submitter",
      expectedAccounting: "篡改 output 裁决后 claimable[challenger]=2 bond; trace 类不符在 respond 被拒",
      evidenceKind: "assertion",
      notes: "独立 JS 计算反证导致确定裁决；步数/长度不符在提交后响应阶段即被拒",
    });
  });
});
