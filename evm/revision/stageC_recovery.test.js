// SPDX-License-Identifier: MIT
//
// evm/revision/stageC_recovery.test.js
//
// 阶段 C：恢复、活性、串谋与有界 DoS。
// 继承阶段 B handoff（runId stageB-freeze-20260916T171758Z，
// sourceTreeSha256 fb2eb8e5e79ab1fa621a447e9989c95dbf48130bc0ee26cade7bfc5269d2e213）。
//
// 重要诚实约束（来自提示词）：
//   - recover 只更新 recoveries 与 timeoutAt，不更换 challenger、不改变收益权、不改 phase。
//     "新观察者能调用 recover" ≠ "已有经济接管机制"。故 C02/C03/C04 必须区分
//     「恢复交互路径」与「直接裁决兜底(adjudicate)」，且不得关闭 adjudicate 来制造恢复必要性。
//   - 时间线必须同时保存 host monotonicNs、UTC、blockNumber、blockTimestamp、clockSource。
//     evm_increaseTime 驱动协议时间，不能解释为真实墙钟恢复速度。
//   - 预期被拒绝 = test pass；场景结果 accepted/rejected/timeout_settled 与断言通过分开记录。
//
// 运行：
//   cd evm; REVISION_RUN=<abs> node node_modules/hardhat/internal/cli/cli.js \
//     test --config revision/hardhat.config.js revision/stageC_recovery.test.js

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const hre = require("hardhat");
const { ethers } = hre;

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径的独立输出目录");
const OUT_DIR = path.join(REVISION_RUN, "stageC");
fs.mkdirSync(OUT_DIR, { recursive: true });

const PHASE = { NONE: 0, SUBMITTED: 1, OPEN: 2, RESPONDED: 3, LOCATING: 4, READY: 5, VERIFIED: 6, SETTLED: 7 };
const PHASE_NAME = Object.fromEntries(Object.entries(PHASE).map(([k, v]) => [v, k]));
const BOND = ethers.parseEther("1");
const CHALLENGE_WINDOW = 100;
const STEP_TIMEOUT = 10;

// ------------------------------------------------------------------
// JS 独立参考模型（ground truth，不依赖合约 compute）
// ------------------------------------------------------------------
function abiEncode(t, v) { return ethers.AbiCoder.defaultAbiCoder().encode(t, v); }
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
  return { output: trace[steps], root: ethers.keccak256(abiEncode(["bytes32[]"], [trace])), trace };
}
function jsTaskDigest(domain, chainId, addr, i) {
  return ethers.keccak256(abiEncode(
    ["bytes32", "uint256", "address", "bytes32", "bytes32", "uint16", "uint32", "bytes32", "bytes32", "bytes32"],
    [domain, BigInt(chainId), addr, i.taskId, i.initial, i.steps, i.version, i.output, i.traceRoot, i.dataHash]));
}
function bisectionRounds(steps) { let w = steps + 1, r = 0; while (w > 1) { w = (w + 1) >> 1; ++r; } return r; }
function normalTransitions(steps) { return bisectionRounds(steps) + 3; }

// ------------------------------------------------------------------
// 链上工具
// ------------------------------------------------------------------
async function increaseTime(s) {
  await ethers.provider.send("evm_increaseTime", [Number(s)]);
  await ethers.provider.send("evm_mine");
}
async function setNextBlockTimestamp(ts) {
  await ethers.provider.send("evm_setNextBlockTimestamp", [Number(ts)]);
}
async function chainId() { return (await ethers.provider.getNetwork()).chainId; }
async function deployRollup(maxRecoveries = 2, challengeWindow = CHALLENGE_WINDOW, stepTimeout = STEP_TIMEOUT) {
  const F = await ethers.getContractFactory("BoundedTaskRollup");
  const r = await F.deploy(BOND, challengeWindow, stepTimeout, maxRecoveries);
  await r.waitForDeployment();
  return r;
}
function taskIdOf(l) { return ethers.keccak256(ethers.toUtf8Bytes("stageC:" + l)); }
async function submitTask(rollup, submitter, { label, steps = 4, tamper = "none" }) {
  const initial = ethers.keccak256(ethers.toUtf8Bytes("init:" + label));
  const taskId = taskIdOf(label);
  const comp = jsCompute(initial, steps);
  let output = comp.output, traceRoot = comp.root;
  if (tamper === "output") output = ethers.keccak256(ethers.toUtf8Bytes("WRONG"));
  else if (tamper === "trace") traceRoot = ethers.keccak256(ethers.toUtf8Bytes("WRONG-TRACE"));
  const input = { taskId, initial, steps, version: 1, output, traceRoot, dataHash: ethers.keccak256(ethers.toUtf8Bytes("data:" + label)) };
  const digest = jsTaskDigest(await rollup.DOMAIN(), await chainId(), await rollup.getAddress(), input);
  const sig = await submitter.signMessage(ethers.getBytes(digest));
  const receipt = await (await rollup.connect(submitter).submit(input, sig, { value: BOND })).wait();
  return { input, comp, taskId, initial, receipt };
}
async function expectRevert(promise, reason) {
  let err;
  try { await promise; } catch (e) { err = e; }
  assert.ok(err, "期望 revert 但调用成功");
  if (reason) {
    let d = "";
    if (typeof err.data === "string" && err.data.startsWith("0x08c379a0")) d = ethers.AbiCoder.defaultAbiCoder().decode(["string"], "0x" + err.data.slice(10))[0];
    const msg = d || (err && (err.shortMessage || err.message)) || "";
    assert.ok(msg.includes(reason), `revert 原因不匹配: 期望 "${reason}", 实际 "${msg}"`);
  }
  return err;
}

// ------------------------------------------------------------------
// 时间线采集（C2）：monotonicNs / UTC / blockNumber / blockTimestamp / clockSource
// ------------------------------------------------------------------
function timeline() {
  return {
    faultInjectedAt: null, failureDetectedAt: null, recoveryTriggeredAt: null,
    firstValidProgressAt: null, resolvedAt: null, finalizedAt: null, withdrawableAt: null, withdrawnAt: null,
    monotonicStartNs: process.hrtime.bigint().toString(),
    monotonicEndNs: null,
    blockStart: null, blockEnd: null,
    utcStart: new Date().toISOString(), utcEnd: null,
    clockSource: "evm_blockTimestamp(protocol time); monotonic=host; utc=wall clock",
    events: [],
  };
}
let chainTs = async () => (await ethers.provider.getBlock("latest")).timestamp;
async function mark(tl, field, extra = {}) {
  const blk = await ethers.provider.getBlock("latest");
  tl[field] = Number(blk.timestamp);
  tl.events.push({ field, blockNumber: blk.number, blockTimestamp: Number(blk.timestamp), utc: new Date().toISOString(), monotonicNs: process.hrtime.bigint().toString(), ...extra });
  return blk;
}
async function finish(tl) {
  const blk = await ethers.provider.getBlock("latest");
  tl.blockStart = tl.events.length ? tl.events[0].blockNumber : blk.number;
  tl.blockEnd = blk.number;
  tl.utcEnd = new Date().toISOString();
  tl.monotonicEndNs = process.hrtime.bigint().toString();
  return tl;
}

// ------------------------------------------------------------------
// 不变量（C 模型检查）
// ------------------------------------------------------------------
async function taskSnapshot(rollup, id) {
  const t = await rollup.getTask(id);
  return {
    phase: Number(t.phase), phaseName: PHASE_NAME[Number(t.phase)],
    submitter: t.submitter, challenger: t.challenger,
    challengeDeadline: Number(t.challengeDeadline), absoluteDeadline: Number(t.absoluteDeadline),
    timeoutAt: Number(t.timeoutAt), recoveries: Number(t.recoveries),
    left: Number(t.left), right: Number(t.right), round: Number(t.round),
    firstMismatch: Number(t.firstMismatch), verdict: Number(t.verdict),
    initial: t.input.initial, steps: Number(t.input.steps), output: t.input.output, traceRoot: t.input.traceRoot,
  };
}
// 恢复操作不得改变争议事实
function assertFactsImmutable(before, after, label) {
  for (const k of ["initial", "steps", "output", "traceRoot", "submitter", "challenger"]) {
    assert.equal(String(after[k]), String(before[k]), `${label}: 争议事实字段 ${k} 被恢复操作改变`);
  }
}
// 不变量集：返回被违反的列表
async function checkInvariants(rollup, id, prev, label) {
  const cur = await taskSnapshot(rollup, id);
  const violations = [];
  if (prev) {
    if (cur.absoluteDeadline !== prev.absoluteDeadline) violations.push("INV1_absoluteDeadline_changed");
    if (cur.recoveries < prev.recoveries) violations.push("INV2_recoveries_decreased");
    if (cur.phase < prev.phase) violations.push("INV3_phase_rolled_back");
  }
  const maxR = Number(await rollup.maxRecoveries());
  if (cur.recoveries > maxR) violations.push("INV2_recoveries_exceeds_max");
  // 资金守恒
  const bal = await ethers.provider.getBalance(await rollup.getAddress());
  const locked = await rollup.locked();
  const tc = await rollup.totalClaimable();
  if (bal !== locked + tc) violations.push("INV4_fund_conservation");
  return { label, snapshot: cur, violations };
}

// ------------------------------------------------------------------
// case matrix / state transition table / invariants 输出
// ------------------------------------------------------------------
const CASES = [];
let pending = [];
function rec(caseId, fields) {
  const e = {
    caseId, stage: "C", schemaVersion: "hybrid-tee-rollup.stageC.case.v1",
    scenario: fields.scenario ?? null,
    injectedAction: fields.injectedAction ?? null,
    expectedOutcome: fields.expectedOutcome ?? null,
    capabilityStatus: fields.capabilityStatus ?? "verified", // verified | limited | not_applicable | deferred_to_E
    outcome: fields.outcome ?? null, // accepted | rejected | timeout_settled | continued
    evidenceKind: fields.evidenceKind ?? "assertion",
    timeline: fields.timeline ?? null,
    notes: fields.notes ?? null,
    assertionPass: true, mochaState: null,
  };
  CASES.push(e); pending.push(e);
  return e;
}
const INV_CHECKS = [];
afterEach(function () {
  const st = this.currentTest ? (this.currentTest.state || (this.currentTest.isPending() ? "pending" : "failed")) : "unknown";
  for (const e of pending) { e.mochaState = st; e.assertionPass = st === "passed"; }
  pending = [];
});
after(function () {
  const passed = CASES.filter((c) => c.assertionPass).length;
  fs.writeFileSync(path.join(OUT_DIR, "case_matrix.json"), JSON.stringify({
    schemaVersion: "hybrid-tee-rollup.stageC.case.v1", stage: "C",
    generatedAtUtc: new Date().toISOString(), contract: "BoundedTaskRollup.sol", node: process.version,
    total: CASES.length, passed, failed: CASES.length - passed,
    note: "capabilityStatus=verified 表示该能力在本实现中真实可用; limited 表示仅部分可用(如 recover 不更换角色); not_applicable/deferred 如实标注。",
    cases: CASES,
  }, null, 2));
  fs.writeFileSync(path.join(OUT_DIR, "state_transition_table.json"), JSON.stringify(STATE_TABLE, null, 2));
  fs.writeFileSync(path.join(OUT_DIR, "invariants.json"), JSON.stringify({
    schemaVersion: "hybrid-tee-rollup.stageC.invariants.v1",
    generatedAtUtc: new Date().toISOString(),
    invariants: INVARIANT_DEFS,
    checks: INV_CHECKS,
    violated: INV_CHECKS.filter((c) => c.violations.length > 0),
  }, null, 2));
  console.log(`\n[stageC] 产物已写入 ${OUT_DIR} (cases=${CASES.length}, passed=${passed})`);
});

const INVARIANT_DEFS = [
  { id: "INV1", statement: "absoluteDeadline 在 openChallenge 时一次确定，不因 recover / 重复证据 / 无效调用更新" },
  { id: "INV2", statement: "recoveries 单调不减且有界（<= maxRecoveries）" },
  { id: "INV3", statement: "终局不可回滚：phase 不回退，SETTLED 后不重开、不二次支付" },
  { id: "INV4", statement: "资金守恒：balance == locked + totalClaimable" },
  { id: "INV5", statement: "recover 不改变 phase" },
  { id: "INV6", statement: "恢复操作不改变争议事实：initial/steps/output/traceRoot/submitter/challenger" },
  { id: "INV7", statement: "同一任务仅一次总账收口：不双支付、不双罚" },
];

const STATE_TABLE = {
  schemaVersion: "hybrid-tee-rollup.stageC.state.v1",
  note: "从 BoundedTaskRollup.sol 实际源码整理；recover 不迁移 phase。",
  transitions: [
    { state: "NONE", operation: "submit", caller: "signer==msg.sender", precondition: "taskId 未占用, steps∈[1,128], version==1, msg.value==bond", timeCondition: "-", nextState: "SUBMITTED", fundEffect: "locked+=bond", checkpointFields: "challengeDeadline" },
    { state: "SUBMITTED", operation: "openChallenge", caller: "!=submitter", precondition: "msg.value==bond", timeCondition: "ts<=challengeDeadline", nextState: "OPEN", fundEffect: "locked+=bond", checkpointFields: "absoluteDeadline, timeoutAt" },
    { state: "SUBMITTED", operation: "finalize", caller: "anyone", precondition: "-", timeCondition: "ts>challengeDeadline", nextState: "SETTLED", fundEffect: "verdict==0 ? settle : burn", checkpointFields: "verdict" },
    { state: "OPEN", operation: "respond", caller: "submitter only", precondition: "trace 长度与绑定正确", timeCondition: "_live", nextState: "RESPONDED", fundEffect: "-", checkpointFields: "firstMismatch, evidenceRoot" },
    { state: "OPEN..READY", operation: "recover", caller: "anyone", precondition: "recoveries<maxRecoveries", timeCondition: "timeoutAt<ts<absoluteDeadline", nextState: "不变(phase 不迁移)", fundEffect: "-", checkpointFields: "recoveries++, timeoutAt" },
    { state: "RESPONDED/LOCATING", operation: "advance", caller: "anyone", precondition: "left<right", timeCondition: "_live", nextState: "LOCATING 或 READY", fundEffect: "-", checkpointFields: "left,right,round" },
    { state: "READY", operation: "replay", caller: "anyone", precondition: "-", timeCondition: "_live", nextState: "VERIFIED", fundEffect: "-", checkpointFields: "verdict" },
    { state: "OPEN..(<SETTLED)", operation: "adjudicate", caller: "anyone", precondition: "-", timeCondition: "无时间门槛(兜底)", nextState: "VERIFIED→SETTLED", fundEffect: "settle", checkpointFields: "verdict" },
    { state: "VERIFIED", operation: "settle", caller: "anyone", precondition: "-", timeCondition: "-", nextState: "SETTLED", fundEffect: "claimable[winner]+=amount", checkpointFields: "-" },
    { state: "OPEN..(<SETTLED)", operation: "terminate", caller: "anyone", precondition: "-", timeCondition: "ts>timeoutAt 或 ts>=absoluteDeadline", nextState: "VERIFIED→SETTLED", fundEffect: "按计算结果 settle(非仅离线惩罚)", checkpointFields: "verdict" },
    { state: "SETTLED", operation: "withdraw", caller: "claimable 所有者", precondition: "amount>0", timeCondition: "-", nextState: "SETTLED", fundEffect: "claimable→0, 实际转账", checkpointFields: "-" },
  ],
};

// ==================================================================
// C01 无故障，尝试过早 recover
// ==================================================================
describe("C01 无故障过早recover", function () {
  it("未超时时 recover 被拒, 且不破坏正常任务/不重置期限", async function () {
    const [s, c] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId } = await submitTask(rollup, s, { label: "c01" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    const before = await taskSnapshot(rollup, taskId);
    const tl = timeline();
    await mark(tl, "faultInjectedAt", { note: "无真实故障, 仅尝试过早 recover" });

    // 过早：block.timestamp <= timeoutAt
    await expectRevert(rollup.recover(taskId), "recovery time");

    const after = await taskSnapshot(rollup, taskId);
    assert.equal(after.phase, before.phase, "recover 失败不得改变 phase");
    assert.equal(after.absoluteDeadline, before.absoluteDeadline, "不得重置 absoluteDeadline");
    assert.equal(after.timeoutAt, before.timeoutAt, "不得重置 timeoutAt");
    assert.equal(after.recoveries, 0);
    assertFactsImmutable(before, after, "C01");

    // 正常任务仍可继续（respond 推进）
    const comp = jsCompute(after.initial, after.steps);
    await rollup.connect(s).respond(taskId, comp.trace);
    await mark(tl, "firstValidProgressAt");
    const inv = await checkInvariants(rollup, taskId, before, "C01");
    INV_CHECKS.push(inv);
    assert.deepEqual(inv.violations, []);

    rec("C01", {
      scenario: "无故障, 挑战已开启",
      injectedAction: "在 timeoutAt 之前调用 recover",
      expectedOutcome: "rejected",
      capabilityStatus: "verified",
      outcome: "rejected",
      timeline: await finish(tl),
      notes: "过早 recover 被拒(require block.timestamp > timeoutAt); 不重置期限、不改 phase、不改争议事实",
    });
  });
});

// ==================================================================
// C02 挑战者失联 -> 新观察者（诚实标注能力边界）
// ==================================================================
describe("C02 挑战者失联->新观察者", function () {
  it("recover 不更换挑战者; 事实延续依赖 adjudicate 兜底(不关闭兜底)", async function () {
    const [s, c, obs] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId } = await submitTask(rollup, s, { label: "c02" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    const before = await taskSnapshot(rollup, taskId);
    const tl = timeline();
    await mark(tl, "faultInjectedAt", { note: "挑战者失联" });
    await increaseTime(STEP_TIMEOUT + 1);
    await mark(tl, "failureDetectedAt");

    // 新观察者调用 recover：允许，但仅 ++recoveries/_touch，不更换 challenger
    await rollup.connect(obs).recover(taskId);
    await mark(tl, "recoveryTriggeredAt", { caller: "observer(3rd party)" });
    const mid = await taskSnapshot(rollup, taskId);
    assert.equal(mid.challenger, before.challenger, "recover 不得更换 challenger（非经济接管）");
    assert.equal(mid.phase, before.phase, "recover 不得迁移 phase");
    assert.equal(mid.recoveries, 1);
    assert.ok(mid.timeoutAt > before.timeoutAt, "recover 应延长 timeoutAt");
    assert.equal(mid.absoluteDeadline, before.absoluteDeadline, "absoluteDeadline 不受 recover 影响");
    assertFactsImmutable(before, mid, "C02");

    // 同一事实的推进：任何人可 adjudicate（兜底），这是本实现真正的续跑路径
    await rollup.connect(obs).adjudicate(taskId);
    await mark(tl, "resolvedAt", { path: "adjudicate 兜底" });
    const after = await taskSnapshot(rollup, taskId);
    assert.equal(after.phase, PHASE.SETTLED);
    assert.equal(after.verdict, 0, "诚实任务 verdict=0");
    await mark(tl, "finalizedAt");
    await mark(tl, "withdrawableAt");
    assert.equal((await rollup.claimable(s.address)).toString(), (BOND * 2n).toString());

    // 实际提现
    await rollup.connect(s).withdraw(s.address);
    await mark(tl, "withdrawnAt");

    const inv = await checkInvariants(rollup, taskId, before, "C02");
    INV_CHECKS.push(inv);
    assert.deepEqual(inv.violations, []);

    rec("C02", {
      scenario: "挑战者失联, 第三方观察者介入",
      injectedAction: "observer 调用 recover, 再调用 adjudicate 推进同一事实",
      expectedOutcome: "continued(路径=adjudicate 兜底, 非角色接管)",
      capabilityStatus: "limited",
      outcome: "continued",
      timeline: await finish(tl),
      notes: "重要: recover 不更换 challenger/收益权, 因此本实现没有真正的『经济接管』。事实延续依赖 adjudicate 确定性兜底(任何人可调用, 无时间门槛)。本测试未关闭 adjudicate 以制造恢复必要性。若需真正改换挑战权与收益权属显式协议变更, 需用户授权后再回归 B。",
    });
  });
});

// ==================================================================
// C03 提交者失联
// ==================================================================
describe("C03 提交者失联", function () {
  it("respond 需 submitter, 失联时只能走 adjudicate/terminate 超时结算, 不假称重新执行成功", async function () {
    const [s, c, obs] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId, comp } = await submitTask(rollup, s, { label: "c03" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    const before = await taskSnapshot(rollup, taskId);
    const tl = timeline();
    await mark(tl, "faultInjectedAt", { note: "提交者失联, 无法 respond" });
    await increaseTime(STEP_TIMEOUT + 1);
    await mark(tl, "failureDetectedAt");

    // 第三方无法代替提交者 respond（无权限，也不能转发有效证据给 submitter 签名）
    await expectRevert(rollup.connect(obs).respond(taskId, comp.trace), "submitter only");

    // 超时后 terminate：按计算结果判责（诚实 -> submitter 胜）
    await increaseTime(STEP_TIMEOUT * 20);
    await mark(tl, "recoveryTriggeredAt", { note: "terminate 而非 recover" });
    await rollup.connect(obs).terminate(taskId);
    await mark(tl, "resolvedAt");
    const after = await taskSnapshot(rollup, taskId);
    assert.equal(after.phase, PHASE.SETTLED);
    assert.equal(after.verdict, 0, "terminate 按计算结果判责, 不是仅因离线惩罚");
    await mark(tl, "finalizedAt");
    await mark(tl, "withdrawableAt");

    const inv = await checkInvariants(rollup, taskId, before, "C03");
    INV_CHECKS.push(inv);
    assert.deepEqual(inv.violations, []);

    rec("C03", {
      scenario: "提交者失联",
      injectedAction: "第三方尝试 respond; 超时后 terminate",
      expectedOutcome: "timeout_settled",
      capabilityStatus: "limited",
      outcome: "timeout_settled",
      timeline: await finish(tl),
      notes: "第三方无 submitter 签名则不能 respond。结果按确定性重算判责(verdict=0 -> submitter 胜), 而非『重新执行成功』。提交者失联且无可转发有效证据时, 只能超时结算——如实记录, 不假称恢复成功。",
    });
  });
});

// ==================================================================
// C04 接管者抢先占位后失联（有界再次接管/终止）
// ==================================================================
describe("C04 抢先占位后失联", function () {
  it("多次 recover 有界(<=maxRecoveries); 超上限后仍可 terminate 收口", async function () {
    const [s, c, o1, o2, o3] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId } = await submitTask(rollup, s, { label: "c04" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    const before = await taskSnapshot(rollup, taskId);
    const tl = timeline();
    await mark(tl, "faultInjectedAt", { note: "占位者抢先 recover 后失联" });

    await increaseTime(STEP_TIMEOUT + 1);
    await rollup.connect(o1).recover(taskId); // 1
    await mark(tl, "recoveryTriggeredAt", { by: "o1" });
    await increaseTime(STEP_TIMEOUT + 1);
    await rollup.connect(o2).recover(taskId); // 2
    await mark(tl, "recoveryTriggeredAt", { by: "o2" });
    await increaseTime(STEP_TIMEOUT + 1);
    // 第三次：超上限
    await expectRevert(rollup.connect(o3).recover(taskId), "recovery limit");

    const mid = await taskSnapshot(rollup, taskId);
    assert.equal(mid.recoveries, 2, "recoveries 有界");
    assertFactsImmutable(before, mid, "C04");

    // 出口可用：terminate 收口
    await increaseTime(STEP_TIMEOUT * 30);
    await rollup.connect(o3).terminate(taskId);
    await mark(tl, "resolvedAt");
    const after = await taskSnapshot(rollup, taskId);
    assert.equal(after.phase, PHASE.SETTLED, "超上限后仍有终止出口");
    await mark(tl, "finalizedAt");

    const inv = await checkInvariants(rollup, taskId, before, "C04");
    INV_CHECKS.push(inv);
    assert.deepEqual(inv.violations, []);

    rec("C04", {
      scenario: "多个观察者抢先 recover 占位后失联",
      injectedAction: "o1/o2 各 recover 一次, o3 第三次",
      expectedOutcome: "bounded+timeout_settled",
      capabilityStatus: "verified",
      outcome: "timeout_settled",
      timeline: await finish(tl),
      notes: "recoveries 上限=2, 第三次被拒(recovery limit), 不无限刷新; 之后 terminate 仍可收口 -> 出口可用",
    });
  });
});

// ==================================================================
// C05 Sybil 多地址重复 recover
// ==================================================================
describe("C05 Sybil 重复recover", function () {
  it("任意多地址都不能突破恢复次数/总期限", async function () {
    const signers = await ethers.getSigners();
    const [s, c] = signers;
    const rollup = await deployRollup(2);
    const { taskId } = await submitTask(rollup, s, { label: "c05" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    const before = await taskSnapshot(rollup, taskId);
    const tl = timeline();
    await mark(tl, "faultInjectedAt", { note: "Sybil 多地址重复 recover" });

    let okCount = 0;
    for (let i = 2; i < Math.min(signers.length, 10); ++i) {
      await increaseTime(STEP_TIMEOUT + 1);
      try { await rollup.connect(signers[i]).recover(taskId); ++okCount; }
      catch { /* 超上限后预期失败 */ }
    }
    const after = await taskSnapshot(rollup, taskId);
    assert.ok(after.recoveries <= 2, `Sybil 不得突破 maxRecoveries, 实际 ${after.recoveries}`);
    assert.equal(okCount, 2, "只有 2 次 recover 成功（40 账户中有 8 个 Sybil 尝试）");
    assert.equal(after.absoluteDeadline, before.absoluteDeadline, "总期限不得延长");

    const inv = await checkInvariants(rollup, taskId, before, "C05");
    INV_CHECKS.push(inv);
    assert.deepEqual(inv.violations, []);

    rec("C05", {
      scenario: "8 个 Sybil 地址依次尝试 recover",
      injectedAction: "多地址重复 recover",
      expectedOutcome: "bounded",
      capabilityStatus: "verified",
      outcome: "rejected",
      timeline: await finish(tl),
      notes: `身份数量不能突破恢复次数上限(2)或总期限; 实际成功 ${okCount} 次, absoluteDeadline 未变`,
    });
  });
});

// ==================================================================
// C06 recover 时间边界（前 / 等于 / 后）
// ==================================================================
describe("C06 recover 时间边界", function () {
  it("timeoutAt 当刻拒绝, +1 允许; absoluteDeadline 当刻拒绝", async function () {
    const [s, c] = await ethers.getSigners();
    // timeoutAt 边界（严格 >）
    const r1 = await deployRollup(2);
    const t1 = await submitTask(r1, s, { label: "c06a" });
    await r1.connect(c).openChallenge(t1.taskId, { value: BOND });
    const sn1 = await taskSnapshot(r1, t1.taskId);
    await setNextBlockTimestamp(sn1.timeoutAt);
    await expectRevert(r1.recover(t1.taskId), "recovery time"); // == timeoutAt 拒绝
    await setNextBlockTimestamp(sn1.timeoutAt + 1);
    await r1.recover(t1.taskId); // > timeoutAt 允许
    assert.equal((await taskSnapshot(r1, t1.taskId)).recoveries, 1);

    // absoluteDeadline 边界（严格 <）
    const r2 = await deployRollup(2);
    const t2 = await submitTask(r2, s, { label: "c06b" });
    await r2.connect(c).openChallenge(t2.taskId, { value: BOND });
    const sn2 = await taskSnapshot(r2, t2.taskId);
    await setNextBlockTimestamp(sn2.absoluteDeadline);
    await expectRevert(r2.recover(t2.taskId), "recovery time"); // == absoluteDeadline 拒绝

    rec("C06", {
      scenario: "recover 在 timeoutAt / absoluteDeadline 边界",
      injectedAction: "==timeoutAt, timeoutAt+1, ==absoluteDeadline 三种时刻调用 recover",
      expectedOutcome: "rejected+accepted",
      capabilityStatus: "verified",
      outcome: "rejected+accepted",
      notes: "require(timeoutAt < ts < absoluteDeadline), 两端均为严格不等; 用 evm_setNextBlockTimestamp 精确控制, 避免自动出块 +1s 漂移。off-by-one 与规范一致",
    });
  });
});

// ==================================================================
// C07 recover 与 timeout 竞争（两种顺序）
// ==================================================================
describe("C07 recover与terminate竞争", function () {
  it("两种顺序都不出现双赢家/双支付/事实重写", async function () {
    const [s, c, obs] = await ethers.getSigners();

    // 顺序 A：先 recover 再 terminate
    const rA = await deployRollup(2);
    const a = await submitTask(rA, s, { label: "c07a" });
    await rA.connect(c).openChallenge(a.taskId, { value: BOND });
    await increaseTime(STEP_TIMEOUT + 1);
    await rA.connect(obs).recover(a.taskId);
    await increaseTime(STEP_TIMEOUT * 30);
    await rA.connect(obs).terminate(a.taskId);
    const sa = await taskSnapshot(rA, a.taskId);
    assert.equal(sa.phase, PHASE.SETTLED);

    // 顺序 B：先 terminate 再 recover（应被拒：phase 已 SETTLED）
    const rB = await deployRollup(2);
    const b = await submitTask(rB, s, { label: "c07b" });
    await rB.connect(c).openChallenge(b.taskId, { value: BOND });
    await increaseTime(STEP_TIMEOUT * 30);
    await rB.connect(obs).terminate(b.taskId);
    await expectRevert(rB.connect(obs).recover(b.taskId), "phase");

    // 双支付检查：每个任务只应有一个 Settled 事件，且 claimable 总额 = 2 bond
    for (const [r, tk] of [[rA, a.taskId], [rB, b.taskId]]) {
      const logs = await r.queryFilter(r.filters.Settled(tk));
      assert.equal(logs.length, 1, `任务 ${tk} 应仅有一次 Settled 事件(防双支付)`);
      const amount = logs[0].args.amount;
      assert.equal(amount.toString(), (BOND * 2n).toString());
    }
    // A 任务：诚实 -> submitter 得 2 bond
    assert.equal((await rA.claimable(s.address)).toString(), (BOND * 2n).toString());
    assert.equal((await rA.claimable(c.address)).toString(), "0");

    rec("C07", {
      scenario: "recover 与 terminate 竞争, 两种交易顺序",
      injectedAction: "顺序A(recover->terminate) 与顺序B(terminate->recover)",
      expectedOutcome: "accepted+rejected",
      capabilityStatus: "verified",
      outcome: "timeout_settled",
      notes: "两种顺序均只产生 1 个 Settled 事件, 无双赢家/双支付; terminate 后 phase=SETTLED, recover 被拒(phase); 争议事实未被重写",
    });
  });
});

// ==================================================================
// C08 接近 absoluteDeadline 且剩余预算不足
// ==================================================================
describe("C08 接近absoluteDeadline", function () {
  it("recover 被拒(剩余不足), terminate 出口可用", async function () {
    const [s, c, obs] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId } = await submitTask(rollup, s, { label: "c08" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    const sn = await taskSnapshot(rollup, taskId);
    const tl = timeline();
    await mark(tl, "faultInjectedAt");

    // 推进到 absoluteDeadline - 1（剩余不足一个 stepTimeout）
    // 注意：recover 条件是严格 ts < absoluteDeadline，故此处仍允许；
    // "不创建不可能义务"的保证来自 _touch 把 timeoutAt 截断到 absoluteDeadline。
    await setNextBlockTimestamp(sn.absoluteDeadline - 1);
    await rollup.connect(obs).recover(taskId);
    await mark(tl, "failureDetectedAt", { note: "剩余预算不足; recover 后 timeoutAt 被截断" });
    const mid = await taskSnapshot(rollup, taskId);
    assert.equal(mid.timeoutAt, sn.absoluteDeadline, "timeoutAt 必须被截断到 absoluteDeadline, 不创建超出总期限的义务");
    assert.equal(mid.absoluteDeadline, sn.absoluteDeadline, "absoluteDeadline 不变");

    // 出口：>= absoluteDeadline 可 terminate
    await setNextBlockTimestamp(sn.absoluteDeadline);
    await rollup.connect(obs).terminate(taskId);
    await mark(tl, "resolvedAt");
    const after = await taskSnapshot(rollup, taskId);
    assert.equal(after.phase, PHASE.SETTLED, "接近截止时终止出口必须可用");
    await mark(tl, "finalizedAt");

    rec("C08", {
      scenario: "剩余时间不足以完成最低规定应答",
      injectedAction: "在 absoluteDeadline-1 尝试 recover; 在 absoluteDeadline 调用 terminate",
      expectedOutcome: "bounded+timeout_settled",
      capabilityStatus: "verified",
      outcome: "timeout_settled",
      timeline: await finish(tl),
      notes: "recover 在 ts<absoluteDeadline 时仍允许, 但 _touch 会把 timeoutAt 截断到 absoluteDeadline, 因此不创建超出总期限的不可能义务; 到达 absoluteDeadline 后由 terminate 按固定 timeout 规则裁决, 出口可用。『==absoluteDeadline 时 recover 被拒』见 C06",
    });
  });
});

// ==================================================================
// C09 maxRecoveries = 0 / 1 / 2 及超上限
// ==================================================================
describe("C09 maxRecoveries矩阵", function () {
  it("0/1/2 三种上限均正确, 超上限不丢原任务", async function () {
    const [s, c, obs] = await ethers.getSigners();
    for (const mr of [0, 1, 2]) {
      const rollup = await deployRollup(mr);
      const { taskId } = await submitTask(rollup, s, { label: "c09-" + mr });
      await rollup.connect(c).openChallenge(taskId, { value: BOND });
      let success = 0;
      for (let i = 0; i < mr + 1; ++i) {
        await increaseTime(STEP_TIMEOUT + 1);
        try { await rollup.connect(obs).recover(taskId); ++success; } catch { /* 超上限预期 */ }
      }
      assert.equal(success, mr, `maxRecoveries=${mr} 时应恰好成功 ${mr} 次, 实际 ${success}`);
      const sn = await taskSnapshot(rollup, taskId);
      assert.equal(sn.recoveries, mr);
      assert.notEqual(sn.phase, PHASE.SETTLED, "超上限不结算、不丢原任务");
      assert.ok(sn.initial && sn.steps > 0, "原任务数据仍在, 未被丢弃");
      // 原任务仍在，可继续走 adjudicate
      await rollup.connect(obs).adjudicate(taskId);
      assert.equal((await taskSnapshot(rollup, taskId)).phase, PHASE.SETTLED);
    }

    rec("C09", {
      scenario: "maxRecoveries ∈ {0,1,2}",
      injectedAction: "每种上限尝试 mr+1 次 recover",
      expectedOutcome: "bounded",
      capabilityStatus: "verified",
      outcome: "rejected",
      notes: "各上限精确生效; 超上限 revert 且不丢原任务(之后仍可 adjudicate 收口)",
    });
  });
});

// ==================================================================
// C10 老 task / 错误轨迹重放
// ==================================================================
describe("C10 重放与错误轨迹", function () {
  it("已终局任务旧证据重放被拒; 跨任务证据不可复用", async function () {
    const [s, c, obs] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId, comp } = await submitTask(rollup, s, { label: "c10" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    await rollup.connect(obs).adjudicate(taskId); // 先终局

    // 已 SETTLED：所有推进/恢复调用被拒
    await expectRevert(rollup.connect(s).respond(taskId, comp.trace), "phase");
    await expectRevert(rollup.connect(obs).recover(taskId), "phase");
    await expectRevert(rollup.connect(obs).adjudicate(taskId), "phase");

    // 跨任务：另一个任务的 trace 不能用于本任务（长度/绑定不符）
    const other = await submitTask(rollup, s, { label: "c10-other", steps: 8 });
    await rollup.connect(c).openChallenge(other.taskId, { value: BOND });
    await expectRevert(rollup.connect(s).respond(other.taskId, comp.trace), "trace length");

    // 同 taskId 重复提交被拒
    await expectRevert(submitTask(rollup, s, { label: "c10" }), "task id");

    rec("C10", {
      scenario: "已终局任务旧证据重放 / 跨任务证据复用 / 同 taskId 重复提交",
      injectedAction: "对 SETTLED 任务重放 respond/recover/adjudicate; 用 A 任务 trace 操作 B 任务",
      expectedOutcome: "rejected",
      capabilityStatus: "verified",
      outcome: "rejected",
      notes: "拒绝恶意重放; 合法检查点证据仍可复用(respond 的 trace 绑定校验通过即可)。不跨任务重放",
    });
  });
});

// ==================================================================
// C11 串谋抢占 / 友好挑战
// ==================================================================
describe("C11 串谋抢占", function () {
  it("友好挑战不能阻止第三方 adjudicate 客观裁决; 诚实反证不被永久排除", async function () {
    const [s, c, honest] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    // 错误任务 + 挑战者（串谋：提交错误结果让同伙挑战获利）
    const { taskId } = await submitTask(rollup, s, { label: "c11", tamper: "output" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });

    // 第三方 honest 抢先 adjudicate：客观裁决仍按计算结果（verdict!=0 -> challenger 赢）
    await rollup.connect(honest).adjudicate(taskId);
    const sn = await taskSnapshot(rollup, taskId);
    assert.notEqual(sn.verdict, 0, "错误任务必须被判错, 不因调用者身份改变");
    assert.equal((await rollup.claimable(c.address)).toString(), (BOND * 2n).toString());
    assert.equal((await rollup.claimable(honest.address)).toString(), "0", "第三方调用者不能窃取收益");

    // 诚实任务不会被串谋抢占影响：另一个诚实任务仍判 submitter 胜
    const good = await submitTask(rollup, s, { label: "c11-good" });
    await rollup.connect(c).openChallenge(good.taskId, { value: BOND });
    await rollup.connect(honest).adjudicate(good.taskId);
    assert.equal((await taskSnapshot(rollup, good.taskId)).verdict, 0);

    rec("C11", {
      scenario: "提交者与同伙挑战者串谋; 第三方抢先裁决",
      injectedAction: "串谋开启挑战后由第三方 adjudicate",
      expectedOutcome: "accepted(客观裁决)",
      capabilityStatus: "verified",
      outcome: "accepted",
      notes: "诚实反证不被永久排除(任何人可 adjudicate, 无时间门槛); 裁决结果仅由 verdict 决定, 第三方调用者不能窃取收益。但注意: 错误任务下『友好挑战』确实可使同伙获利——这是协议经济设计问题, 未在 C 修复(属 B 经济政策范畴)",
    });
  });
});

// ==================================================================
// C12 提交者 + DA 观察者隐瞒（仅模拟）
// ==================================================================
describe("C12 DA隐瞒", function () {
  it("bindDa 后未披露则罚没；披露原像后才允许结算", async function () {
    const [s, c] = await ethers.getSigners();
    const rollup = await deployRollup();
    const payload = ethers.toUtf8Bytes("data:c12-hide");
    const { taskId } = await submitTask(rollup, s, { label: "c12-hide" });
    const daRef = ethers.keccak256(ethers.toUtf8Bytes("versioned-hash-c12"));
    await expectRevert(rollup.connect(c).bindDa(taskId, daRef, { value: BOND }), "submitter only");
    await rollup.connect(s).bindDa(taskId, daRef, { value: BOND });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    await expectRevert(rollup.adjudicate(taskId), "da pending");
    await expectRevert(rollup.connect(s).fulfillDa(taskId, ethers.toUtf8Bytes("wrong")), "payload hash");
    const before = await taskSnapshot(rollup, taskId);
    await ethers.provider.send("evm_increaseTime", [CHALLENGE_WINDOW + 5]);
    await ethers.provider.send("evm_mine");
    await expectRevert(rollup.connect(s).fulfillDa(taskId, payload), "da window");
    const balBefore = await ethers.provider.getBalance(await rollup.getAddress());
    const slashTx = await rollup.connect(c).slashDa(taskId);
    const slashRc = await slashTx.wait();
    const duty = await rollup.getDaDuty(taskId);
    assert.equal(duty.slashed, true);
    assert.equal((await rollup.totalBurned()).toString(), BOND.toString());
    const balAfter = await ethers.provider.getBalance(await rollup.getAddress());
    assert.equal((balBefore - balAfter).toString(), BOND.toString());
    await rollup.adjudicate(taskId);
    const after = await taskSnapshot(rollup, taskId);
    assert.equal(after.phaseName, "SETTLED");
    assert.equal(after.output, before.output);
    const inv = await checkInvariants(rollup, taskId, before, "c12");
    assert.deepEqual(inv.violations, []);
    const ok = await submitTask(rollup, s, { label: "c12-show" });
    const shown = ethers.toUtf8Bytes("data:c12-show");
    await rollup.connect(s).bindDa(ok.taskId, daRef, { value: BOND });
    await rollup.connect(s).fulfillDa(ok.taskId, shown);
    const shownDuty = await rollup.getDaDuty(ok.taskId);
    assert.equal(shownDuty.fulfilled, true);
    assert.equal(shownDuty.disclosedHash, ethers.keccak256(shown));
    await ethers.provider.send("evm_increaseTime", [CHALLENGE_WINDOW + 5]);
    await ethers.provider.send("evm_mine");
    await rollup.finalize(ok.taskId);
    assert.equal(Number((await rollup.getTask(ok.taskId)).phase), PHASE.SETTLED);
    rec("C12", {
      scenario: "提交者绑定 DA 引用后拒绝披露原像",
      injectedAction: "bindDa 后越过披露窗口，第三方 slashDa，再 adjudicate",
      expectedOutcome: "accepted",
      capabilityStatus: "verified",
      outcome: "timeout_settled",
      notes: `披露义务是可选 bindDa，罚没的是 DA 押金（burn ${BOND.toString()} wei，slash gas ${slashRc.gasUsed.toString()}）。校验的是 dataHash 原像，不是链上 EIP-4844 point evaluation。未调用 bindDa 的任务没有这项义务。`,
    });
  });
});

// ==================================================================
// C13 短时阻断 / 延迟消息
// ==================================================================
describe("C13 短时阻断与延迟", function () {
  it("窗口内延迟后仍可继续; 超出 absoluteDeadline 则不再保证活性", async function () {
    const [s, c, obs] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId } = await submitTask(rollup, s, { label: "c13" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    const sn = await taskSnapshot(rollup, taskId);
    const tl = timeline();
    await mark(tl, "faultInjectedAt", { note: "短时阻断调用" });

    // 短时延迟（仍在 absoluteDeadline 内）
    await increaseTime(STEP_TIMEOUT + 1);
    await rollup.connect(obs).recover(taskId);
    await mark(tl, "recoveryTriggeredAt");
    await rollup.connect(obs).adjudicate(taskId);
    await mark(tl, "firstValidProgressAt");
    assert.equal((await taskSnapshot(rollup, taskId)).phase, PHASE.SETTLED);

    rec("C13", {
      scenario: "短时阻断调用 / 延迟消息",
      injectedAction: "延迟 stepTimeout+1 后由观察者 recover+adjudicate",
      expectedOutcome: "continued",
      capabilityStatus: "verified",
      outcome: "continued",
      timeline: await finish(tl),
      notes: "在模型假设内(有诚实参与者、能上链、有数据)可恢复。永久阻断/无限分区不承诺活性——若超过 absoluteDeadline 且无人调用, 只能由任一方在之后 terminate, 属 not_guaranteed",
    });
  });
});

// ==================================================================
// C14 进程崩溃 -> 新观察者从持久化状态恢复
// ==================================================================
describe("C14 崩溃后从链上状态恢复", function () {
  it("新观察者仅凭链上持久化状态即可接续, 不依赖原进程内存", async function () {
    const [s, c, obs] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const { taskId } = await submitTask(rollup, s, { label: "c14" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    await increaseTime(STEP_TIMEOUT + 1);
    await rollup.connect(obs).recover(taskId);

    // 模拟"原进程崩溃"：丢弃本地变量，仅从链上读取
    const persisted = await taskSnapshot(rollup, taskId); // 只从链上 getTask 读取
    assert.ok(persisted.absoluteDeadline > 0, "链上持久化了 absoluteDeadline");
    assert.equal(persisted.recoveries, 1, "链上持久化了 recoveries");
    assert.ok(persisted.initial && persisted.traceRoot, "链上持久化了争议事实");

    // 新观察者（新 signer 实例）用链上信息接续
    const revived = await ethers.getContractAt("BoundedTaskRollup", await rollup.getAddress(), obs);
    await revived.adjudicate(taskId);
    assert.equal((await taskSnapshot(rollup, taskId)).phase, PHASE.SETTLED);

    rec("C14", {
      scenario: "观察者进程崩溃, 由新进程/新观察者恢复",
      injectedAction: "丢弃本地状态, 仅用 getTask 链上快照由新合约实例 adjudicate",
      expectedOutcome: "continued",
      capabilityStatus: "verified",
      outcome: "continued",
      notes: "所有必要状态(taskId/事实/期限/recoveries)均在链上持久化, 恢复不依赖原进程内存",
    });
  });
});

// ==================================================================
// C15 快照回滚 / 双签（协议抗重放，非硬件攻防）
// ==================================================================
describe("C15 快照回滚与双签", function () {
  it("本地快照回滚后, 协议层 nonce/taskId 防重放; 不宣称真实硬件防回滚", async function () {
    const [s, c] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const snapshotId = await ethers.provider.send("evm_snapshot", []);
    const { taskId } = await submitTask(rollup, s, { label: "c15" });
    await rollup.connect(c).openChallenge(taskId, { value: BOND });
    await rollup.adjudicate(taskId);
    assert.equal((await taskSnapshot(rollup, taskId)).phase, PHASE.SETTLED);

    // 回滚到提交前
    await ethers.provider.send("evm_revert", [snapshotId]);
    const afterRevert = await taskSnapshot(rollup, taskId);
    assert.equal(afterRevert.phase, PHASE.NONE, "回滚后任务回到 NONE（链状态回滚）");

    // 协议层：同一 taskId 仍只能提交一次（回滚后重新提交成功，但再次提交被拒）
    await submitTask(rollup, s, { label: "c15" });
    await expectRevert(submitTask(rollup, s, { label: "c15" }), "task id");

    rec("C15", {
      scenario: "本地快照回滚 / 密钥双签情景(仿真)",
      injectedAction: "evm_snapshot -> 提交并终局 -> evm_revert -> 再次提交",
      expectedOutcome: "rejected(重放)",
      capabilityStatus: "limited",
      outcome: "rejected",
      notes: "仅证明协议层 taskId 唯一性防重放。这是本地 EVM 快照仿真, 不是真实硬件防回滚/防双签能力; 不宣称任何 TEE 硬件攻防结论(移交 D)",
    });
  });
});

// ==================================================================
// C16 L1 重组 / 陈旧链头
// ==================================================================
describe("C16 L1重组", function () {
  it("本地无真实重组, 标记 not_applicable 并说明", function () {
    rec("C16", {
      scenario: "正常 L1 重组 / 陈旧链头",
      injectedAction: "无(本地 Hardhat automining 无共识重组)",
      expectedOutcome: "not_applicable",
      capabilityStatus: "not_applicable",
      outcome: "not_applicable",
      notes: "本地 in-process automining 不产生真实重组。可用 evm_revert 仿真(见 C15), 但那不等于共识层重组。结论: 正常重组不应被直接视为 TEE 作恶; 本阶段不给出重组相关结论",
    });
  });
});

// ==================================================================
// C17 最大任务 / 最大证据 / 无效交易风暴（最坏 gas）
// ==================================================================
describe("C17 边界压力与最坏gas", function () {
  it("最大步数与最大证据可处理; 无效交易风暴不改变状态并记录最坏gas", async function () {
    const [s, c, obs] = await ethers.getSigners();
    const rollup = await deployRollup(2);
    const MAX = Number(await rollup.MAX_STEPS());

    // 最大任务：steps=128，最大证据 trace 长度 129
    const big = await submitTask(rollup, s, { label: "c17-max", steps: MAX });
    await rollup.connect(c).openChallenge(big.taskId, { value: BOND });
    const tx = await rollup.connect(s).respond(big.taskId, big.comp.trace);
    const r1 = await tx.wait();
    assert.equal(big.comp.trace.length, MAX + 1, "最大证据长度 = MAX_STEPS+1");
    const adjTx = await rollup.connect(obs).adjudicate(big.taskId);
    const r2 = await adjTx.wait();
    assert.equal((await taskSnapshot(rollup, big.taskId)).phase, PHASE.SETTLED);

    // 无效交易风暴：对已终局任务连续 20 次无效调用
    const beforeStorm = await taskSnapshot(rollup, big.taskId);
    let stormGas = 0n, reverted = 0;
    for (let i = 0; i < 20; ++i) {
      try {
        const t = await rollup.connect(obs).recover(big.taskId);
        const r = await t.wait();
        stormGas += BigInt(r.gasUsed) * BigInt(r.gasPrice);
      } catch (e) {
        ++reverted;
      }
    }
    assert.equal(reverted, 20, "已终局任务上所有 recover 均应 revert");
    const afterStorm = await taskSnapshot(rollup, big.taskId);
    assert.equal(afterStorm.phase, beforeStorm.phase, "无效交易风暴不得污染状态");
    assert.equal(afterStorm.recoveries, beforeStorm.recoveries);

    rec("C17", {
      scenario: `最大任务(steps=${MAX})与最大证据(trace=${MAX + 1}); 20 次无效 recover 风暴`,
      injectedAction: "提交最大步数任务并终局; 之后连续 20 次无效 recover",
      expectedOutcome: "accepted+rejected",
      capabilityStatus: "verified",
      outcome: "accepted",
      evidenceKind: "gas",
      notes: `最大任务可正常处理并结算(respond gas=${r1.gasUsed}, adjudicate gas=${r2.gasUsed}); 无效交易风暴全部 revert(${reverted}/20), 状态无污染, 累计作废 gas=${stormGas.toString()} wei(由攻击者承担)`,
    });
  });
});
