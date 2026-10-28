// SPDX-License-Identifier: MIT
//
// evm/revision/security.test.js
//
// 安全回归测试套件 (针对修订后的核心合约 BoundedTaskRollup)。
//
// 设计约束(来自任务要求):
//   - 仅用 node assert, 不依赖未安装的 chai 插件。
//   - 测试从 JS 独立实现 trace 与 digest, 绝不以合约 compute 作为"正确 oracle":
//     合约 compute 最多只用于"自检我的 JS 实现与规范一致", 而判定 verdict/winner
//     时只用 JS 计算出的"应然值"与合约行为对比; JS 是 ground truth。
//   - 覆盖 12 类安全: 见各级 describe。
//   - steps ∈ {4,16,64,128}; maxRecoveries ∈ {0,1,2} 在相关用例中作矩阵覆盖。
//   - 提现的拒收/重入仅由 evm/contracts 下明确标 _Test 的辅助合约触发。
//   - 每个 it 的名称与状态通过 mocha hooks 记录到 REVISION_RUN/security/security_report.json。
//   - 除非明确发现致命 bug, 不修改核心合约 (若有问题在报告中告知)。
//
// 运行方式(由外部 runner 负责):
//   process.chdir(evm);
//   process.argv = [node, "hardhat", "test", "--config", "revision/hardhat.config.js", "revision/security.test.js"];
//   require("hardhat/internal/cli/cli.js");
//
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const hre = require("hardhat");
const { ethers } = hre;

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN 必须是绝对路径的独立输出目录");
const OUT_DIR = path.join(REVISION_RUN, "security");
fs.mkdirSync(OUT_DIR, { recursive: true });

const STEPS_LIST = [4, 16, 64, 128];
const MR_LIST = [0, 1, 2];
const PHASE = { NONE: 0, SUBMITTED: 1, OPEN: 2, RESPONDED: 3, LOCATING: 4, READY: 5, VERIFIED: 6, SETTLED: 7 };

// ------------------------------------------------------------------
// JS 独立实现的 trace / digest (与合约规范一致, 作为 ground truth)
// ------------------------------------------------------------------
function abiEncode(types, values) {
  return ethers.AbiCoder.defaultAbiCoder().encode(types, values);
}
// 复刻 Solidity: keccak256(abi.encode(i, trace[i])) 累加, trace[0]=initial
function jsTrace(initial, steps) {
  const trace = [initial];
  let cur = initial;
  for (let i = 0; i < steps; ++i) {
    cur = ethers.keccak256(abiEncode(["uint256", "bytes32"], [BigInt(i), cur]));
    trace.push(cur);
  }
  return trace; // 长度 steps+1
}
// 复刻合约 compute: 返回 (output, root, trace)
function jsCompute(initial, steps) {
  const trace = jsTrace(initial, steps);
  const output = trace[steps];
  const root = ethers.keccak256(abiEncode(["bytes32[]"], [trace]));
  return { output, root, trace };
}
// 复刻合约 taskDigest: keccak256(abi.encode(DOMAIN, chainid, address(this), TaskInput{...}))
function jsTaskDigest(domain, chainId, addr, input) {
  return ethers.keccak256(
    abiEncode(
      ["bytes32", "uint256", "address", "bytes32", "bytes32", "uint16", "uint32", "bytes32", "bytes32", "bytes32"],
      [domain, BigInt(chainId), addr, input.taskId, input.initial, input.steps, input.version, input.output, input.traceRoot, input.dataHash]
    )
  );
}
// 复刻合约 normalTransitions 的轮数部分 (bisection rounds)
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
// 链上时间工具
// ------------------------------------------------------------------
async function increaseTime(seconds) {
  await ethers.provider.send("evm_increaseTime", [Number(seconds)]);
  await ethers.provider.send("evm_mine");
}
async function chainId() {
  return (await ethers.provider.getNetwork()).chainId;
}

// ------------------------------------------------------------------
// 部署与提交辅助
// ------------------------------------------------------------------
async function deployRollup(bond, challengeWindow, stepTimeout, maxRecoveries) {
  const Factory = await ethers.getContractFactory("BoundedTaskRollup");
  const rollup = await Factory.deploy(bond, challengeWindow, stepTimeout, maxRecoveries);
  await rollup.waitForDeployment();
  return rollup;
}

// tamper: "none" | "output" | "trace" | "both"
async function submitTask(rollup, submitter, opts) {
  const steps = opts.steps;
  const initial = opts.initial;
  const version = opts.version ?? Number(await rollup.TASK_VERSION());
  const taskId = opts.taskId;
  const comp = jsCompute(initial, steps);
  let output = comp.output;
  let traceRoot = comp.root;
  const wrong = ethers.keccak256(ethers.toUtf8Bytes("WRONG"));
  if (opts.tamper === "output") output = wrong;
  else if (opts.tamper === "trace") traceRoot = wrong;
  else if (opts.tamper === "both") {
    output = wrong;
    traceRoot = ethers.keccak256(ethers.toUtf8Bytes("WRONG-TRACE"));
  }
  const input = {
    taskId,
    initial,
    steps,
    version,
    output,
    traceRoot,
    dataHash: ethers.keccak256(ethers.toUtf8Bytes("data:" + taskId)),
  };
  const domain = await rollup.DOMAIN();
  const digest = jsTaskDigest(domain, await chainId(), await rollup.getAddress(), input);
  const sig = await submitter.signMessage(ethers.getBytes(digest));
  const tx = await rollup.connect(submitter).submit(input, sig, { value: opts.bond });
  const receipt = await tx.wait();
  return { input, digest, sig, comp, receipt };
}
async function openChallenge(rollup, challenger, taskId, bond) {
  const tx = await rollup.connect(challenger).openChallenge(taskId, { value: bond });
  return tx.wait();
}
// 把挑战推进到 READY (respond + 二分 advance), 再 replay -> VERIFIED
async function reachVerified(rollup, submitter, taskId, steps) {
  const comp = jsCompute(await (await rollup.getTask(taskId)).input.initial, steps);
  await rollup.connect(submitter).respond(taskId, comp.trace);
  let guard = 0;
  while (true) {
    const t = await rollup.getTask(taskId);
    if (Number(t.phase) === PHASE.READY) break;
    if (Number(t.phase) !== PHASE.RESPONDED && Number(t.phase) !== PHASE.LOCATING) break;
    await rollup.connect(submitter).advance(taskId);
    if (++guard > steps + 5) break;
  }
  await rollup.connect(submitter).replay(taskId);
}

// ------------------------------------------------------------------
// 守恒 / 真实余额断言
// ------------------------------------------------------------------
async function assertConservation(rollup, label) {
  const addr = await rollup.getAddress();
  const bal = await ethers.provider.getBalance(addr);
  const locked = await rollup.locked();
  const tc = await rollup.totalClaimable();
  assert.ok(bal === locked + tc, `${label}: 合约余额 ${bal} != locked+totalClaimable ${locked + tc}`);
  const td = await rollup.totalDeposited();
  const tw = await rollup.totalWithdrawn();
  assert.equal(bal, td - tw - await rollup.totalBurned(), `${label}: deposited-withdrawn-burned`);
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
    if (typeof err.data === "string" && err.data.startsWith("0x08c379a0")) decoded = ethers.AbiCoder.defaultAbiCoder().decode(["string"], "0x" + err.data.slice(10))[0];
    const msg = decoded || (err && (err.shortMessage || err.message)) || "";
    assert.ok(msg.includes(reason), `revert 原因不匹配: 期望包含 "${reason}", 实际 "${msg}"`);
  }
}

// ------------------------------------------------------------------
// mocha hooks: 记录每个 it 的状态
// ------------------------------------------------------------------
const results = [];
let runSummary = { startedAt: new Date().toISOString(), items: [] };
before(() => {
  runSummary.contract = "BoundedTaskRollup (修订版核心合约)";
  runSummary.node = process.version;
  runSummary.maxRecoveriesMatrix = MR_LIST;
  runSummary.stepsMatrix = STEPS_LIST;
});
afterEach(function () {
  const t = this.currentTest;
  const item = { name: t.title, fullName: t.fullTitle(), state: t.state || (t.isPending() ? "pending" : "failed") };
  if (t.state === "failed" && t.err) item.error = t.err.message;
  results.push(item);
});
after(async function () {
  const passed = results.filter((r) => r.state === "passed").length;
  const failed = results.filter((r) => r.state === "failed").length;
  const report = {
    generatedAt: new Date().toISOString(),
    contract: "BoundedTaskRollup.sol",
    node: process.version,
    config: "revision/hardhat.config.js",
    stepsMatrix: STEPS_LIST,
    maxRecoveriesMatrix: MR_LIST,
    total: results.length,
    passed,
    failed,
    pass: failed === 0 && passed > 0 && passed === results.length,
    items: results,
    note: "JS 独立实现 trace/digest 作为 ground truth; 合约 compute 仅用于自检一致性, 不作为判定 oracle。",
  };
  const outPath = path.join(OUT_DIR, "security_report.json");
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  // eslint-disable-next-line no-console
  console.log(`\n[security] 报告已写入 ${outPath} (total=${results.length}, passed=${passed}, failed=${failed})`);
});

// ==================================================================
// 测试主体
// ==================================================================
describe("1 未授权response", function () {
  it("非 submitter 调用 respond 必须 revert", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 100, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const attacker = signers[4];
    const { comp } = await submitTask(rollup, submitter, {
      taskId: ethers.keccak256(ethers.toUtf8Bytes("cat1")),
      initial: ethers.keccak256(ethers.toUtf8Bytes("init1")),
      steps: 16,
      bond,
    });
    await openChallenge(rollup, challenger, ethers.keccak256(ethers.toUtf8Bytes("cat1")), bond);
    // 无关第三方 attacker 响应 -> revert
    await expectRevert(rollup.connect(attacker).respond(ethers.keccak256(ethers.toUtf8Bytes("cat1")), comp.trace), "submitter only");
    // submitter 本人可响应
    await rollup.connect(submitter).respond(ethers.keccak256(ethers.toUtf8Bytes("cat1")), comp.trace);
    const t = await rollup.getTask(ethers.keccak256(ethers.toUtf8Bytes("cat1")));
    assert.strictEqual(Number(t.phase), PHASE.RESPONDED, "submitter 响应后应为 RESPONDED");
  });
});

describe("2 恶意challenge不罚诚实submitter", function () {
  it("矩阵 steps×maxRecoveries: 诚实 submitter 胜出且 challenger 被罚没", async function () {
    const bond = ethers.parseEther("1");
    for (const steps of STEPS_LIST) {
      for (const mr of MR_LIST) {
        const rollup = await deployRollup(bond, 200, 10, mr);
        const signers = await ethers.getSigners();
        const submitter = signers[1];
        const challenger = signers[2];
        const third = signers[3];
        const id = ethers.keccak256(ethers.toUtf8Bytes("cat2-" + steps + "-" + mr));
        await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i2")), steps, bond });
        await openChallenge(rollup, challenger, id, bond);
        // 任意第三方公开裁决
        await rollup.connect(third).adjudicate(id);
        const t = await rollup.getTask(id);
        assert.strictEqual(Number(t.verdict), 0, `steps=${steps},mr=${mr}: 诚实提交 verdict 应为 0`);
        assert.strictEqual(Number(t.phase), PHASE.SETTLED, `steps=${steps},mr=${mr}: 应为 SETTLED`);
        const subBalance = await rollup.claimable(await submitter.getAddress());
        const chBalance = await rollup.claimable(await challenger.getAddress());
        assert.ok(subBalance === 2n * bond, `steps=${steps},mr=${mr}: submitter 应获 2*bond, 实际 ${subBalance}`);
        assert.ok(chBalance === 0n, `steps=${steps},mr=${mr}: challenger 应被罚没(0), 实际 ${chBalance}`);
        await assertConservation(rollup, `cat2 steps=${steps},mr=${mr}`);
      }
    }
  });
});

describe("3 篡改output/root/trace", function () {
  it("JS trace 实现与合约 compute 一致(自检 oracle)", async function () {
    const rollup = await deployRollup(ethers.parseEther("1"), 100, 10, 2);
    for (const steps of STEPS_LIST) {
      const initial = ethers.keccak256(ethers.toUtf8Bytes("seed" + steps));
      const js = jsCompute(initial, steps);
      const onchain = await rollup.compute(initial, steps);
      assert.strictEqual(onchain[0], js.output, `steps=${steps}: output 不一致`);
      assert.strictEqual(onchain[1], js.root, `steps=${steps}: root 不一致`);
    }
  });
  it("篡改 output -> verdict 含 bit0, challenger 胜出", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 100, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat3a"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i3a")), steps: 16, bond, tamper: "output" });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(challenger).adjudicate(id);
    const t = await rollup.getTask(id);
    assert.ok((Number(t.verdict) & 1) === 1, "篡改 output 应置 bit0");
    const chBalA = await rollup.claimable(await challenger.getAddress());
    assert.ok(chBalA === 2n * bond, "篡改 output 时 challenger 应获 2*bond");
  });
  it("篡改 traceRoot -> verdict 含 bit1, challenger 胜出", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 100, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat3b"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i3b")), steps: 16, bond, tamper: "trace" });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(challenger).adjudicate(id);
    const t = await rollup.getTask(id);
    assert.ok((Number(t.verdict) & 2) === 2, "篡改 traceRoot 应置 bit1");
    const chBalB = await rollup.claimable(await challenger.getAddress());
    assert.ok(chBalB === 2n * bond, "篡改 traceRoot 时 challenger 应获 2*bond");
  });
  it("未挑战且篡改 output -> finalize 销毁 bond，调用者不能取回罚没", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 60, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const finalizer = signers[3];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat3c"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i3c")), steps: 16, bond, tamper: "output" });
    await increaseTime(61);
    await rollup.connect(finalizer).finalize(id);
    const t = await rollup.getTask(id);
    assert.strictEqual(Number(t.phase), PHASE.SETTLED, "未挑战篡改应被 finalize 结算");
    assert.ok((Number(t.verdict) & 1) === 1, "篡改 output 应置 bit0");
    const subBal = await rollup.claimable(await submitter.getAddress());
    const finBal = await rollup.claimable(await finalizer.getAddress());
    assert.ok(subBal === 0n, "被篡改的提交者不应获得资金");
    assert.ok(finBal === 0n, "finalizer cannot reclaim a slash");
    assert.strictEqual(await rollup.totalBurned(), bond);
    await assertConservation(rollup, "cat3c");
  });
});

describe("4 跨task/deployment域重放", function () {
  it("离线 JS digest 与合约一致, 且绑定 chainid/address(可离线验证 domain)", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 100, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat4a"));
    const initial = ethers.keccak256(ethers.toUtf8Bytes("i4a"));
    const steps = 16;
    const comp = jsCompute(initial, steps);
    const input = {
      taskId: id,
      initial,
      steps,
      version: Number(await rollup.TASK_VERSION()),
      output: comp.output,
      traceRoot: comp.root,
      dataHash: ethers.keccak256(ethers.toUtf8Bytes("data:cat4a")),
    };
    const domain = await rollup.DOMAIN();
    const cid = await chainId();
    const addr = await rollup.getAddress();
    const jsDigest = jsTaskDigest(domain, cid, addr, input);
    const onDigest = await rollup.taskDigest(input);
    assert.strictEqual(jsDigest, onDigest, "JS digest 应与合约 taskDigest 一致");
    // 离线篡改 chainid / address 必须改变 digest (domain 绑定可离线验证)
    const otherChain = jsTaskDigest(domain, cid + 1n, addr, input);
    const otherAddr = jsTaskDigest(domain, cid, ethers.Wallet.createRandom().address, input);
    assert.notStrictEqual(otherChain, jsDigest, "不同 chainid 必须产生不同 digest");
    assert.notStrictEqual(otherAddr, jsDigest, "不同 deployment 地址必须产生不同 digest");
  });
  it("跨 deployment 重放同一签名必须 revert (digest 绑定 address)", async function () {
    const bond = ethers.parseEther("1");
    const rollupA = await deployRollup(bond, 100, 10, 2);
    const rollupB = await deployRollup(bond, 100, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat4b"));
    const initial = ethers.keccak256(ethers.toUtf8Bytes("i4b"));
    const steps = 16;
    const comp = jsCompute(initial, steps);
    const input = {
      taskId: id,
      initial,
      steps,
      version: Number(await rollupA.TASK_VERSION()),
      output: comp.output,
      traceRoot: comp.root,
      dataHash: ethers.keccak256(ethers.toUtf8Bytes("data:cat4b")),
    };
    const domain = await rollupA.DOMAIN();
    const digestA = jsTaskDigest(domain, await chainId(), await rollupA.getAddress(), input);
    const sig = await submitter.signMessage(ethers.getBytes(digestA));
    // 在 A 上合法提交
    await rollupA.connect(submitter).submit(input, sig, { value: bond });
    // 在 B 上用同一签名重放 -> digest 不同 -> 签名校验失败
    await expectRevert(rollupB.connect(submitter).submit(input, sig, { value: bond }), "signature");
  });
  it("同 deployment 同 taskId 在已结算后重复提交必须 revert", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 100, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const third = signers[3];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat4c"));
    const initial = ethers.keccak256(ethers.toUtf8Bytes("i4c"));
    const steps = 16;
    const comp = jsCompute(initial, steps);
    const input = {
      taskId: id,
      initial,
      steps,
      version: Number(await rollup.TASK_VERSION()),
      output: comp.output,
      traceRoot: comp.root,
      dataHash: ethers.keccak256(ethers.toUtf8Bytes("data:cat4c")),
    };
    const domain = await rollup.DOMAIN();
    const digest = jsTaskDigest(domain, await chainId(), await rollup.getAddress(), input);
    const sig = await submitter.signMessage(ethers.getBytes(digest));
    await rollup.connect(submitter).submit(input, sig, { value: bond });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(third).adjudicate(id);
    // 再次提交相同 taskId -> 已被占用
    await expectRevert(rollup.connect(submitter).submit(input, sig, { value: bond }), "task id");
  });
});

describe("5 非法steps/version", function () {
  it("steps=0 / steps>MAX / version!=TASK_VERSION 提交必须 revert", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 100, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const version = Number(await rollup.TASK_VERSION());
    const MAX = Number(await rollup.MAX_STEPS());
    const bad = [
      { steps: 0, version, reason: "task bounds" },
      { steps: MAX + 1, version, reason: "task bounds" },
      { steps: 16, version: version + 1, reason: "task bounds" },
    ];
    for (const b of bad) {
      const initial = ethers.keccak256(ethers.toUtf8Bytes("bad" + b.steps));
      const comp = jsCompute(initial, b.steps > MAX ? MAX : b.steps);
      const input = {
        taskId: ethers.keccak256(ethers.toUtf8Bytes("cat5-" + b.steps + "-" + b.version)),
        initial,
        steps: b.steps,
        version: b.version,
        output: b.steps === 0 || b.steps > MAX ? comp.output : comp.output,
        traceRoot: comp.root,
        dataHash: ethers.keccak256(ethers.toUtf8Bytes("d")),
      };
      const domain = await rollup.DOMAIN();
      const digest = jsTaskDigest(domain, await chainId(), await rollup.getAddress(), input);
      const sig = await submitter.signMessage(ethers.getBytes(digest));
      await expectRevert(rollup.connect(submitter).submit(input, sig, { value: bond }), b.reason);
    }
    // 边界合法: steps=1 与 steps=MAX 应成功
    for (const s of [1, MAX]) {
      const initial = ethers.keccak256(ethers.toUtf8Bytes("ok" + s));
      const comp = jsCompute(initial, s);
      const input = {
        taskId: ethers.keccak256(ethers.toUtf8Bytes("cat5-ok-" + s)),
        initial,
        steps: s,
        version,
        output: comp.output,
        traceRoot: comp.root,
        dataHash: ethers.keccak256(ethers.toUtf8Bytes("d")),
      };
      const domain = await rollup.DOMAIN();
      const digest = jsTaskDigest(domain, await chainId(), await rollup.getAddress(), input);
      const sig = await submitter.signMessage(ethers.getBytes(digest));
      await rollup.connect(submitter).submit(input, sig, { value: bond });
    }
  });
  it("compute 越界 steps 必须 revert", async function () {
    const rollup = await deployRollup(ethers.parseEther("1"), 100, 10, 2);
    const MAX = Number(await rollup.MAX_STEPS());
    await expectRevert(rollup.compute(ethers.keccak256(ethers.toUtf8Bytes("x")), 0), "steps");
    await expectRevert(rollup.compute(ethers.keccak256(ethers.toUtf8Bytes("x")), MAX + 1), "steps");
  });
});

describe("6 提前/重复/超限recover", function () {
  it("矩阵 maxRecoveries={0,1,2}: 提前/重复/超限 recover 均 revert", async function () {
    const bond = ethers.parseEther("1");
    const stepTimeout = 10;
    for (const mr of MR_LIST) {
      const rollup = await deployRollup(bond, 200, stepTimeout, mr);
      const signers = await ethers.getSigners();
      const submitter = signers[1];
      const challenger = signers[2];
      const id = ethers.keccak256(ethers.toUtf8Bytes("cat6-mr" + mr));
      await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i6")), steps: 16, bond });
      await openChallenge(rollup, challenger, id, bond);
      // 提前 recover (仍在 timeoutAt 内) -> revert
      await expectRevert(rollup.connect(challenger).recover(id), "recovery time");
      // 推进超过 timeoutAt
      await increaseTime(stepTimeout + 1);
      // 重复 recover 在同一 timeout 窗口内 -> revert
      if (mr > 0) {
        await rollup.connect(challenger).recover(id);
        await expectRevert(rollup.connect(challenger).recover(id), "recovery time");
      } else {
        // mr=0: 任何 recover 都因超限 revert
        await expectRevert(rollup.connect(challenger).recover(id), "recovery limit");
      }
      // 尝试达到上限次数
      for (let k = 1; k < mr; ++k) {
        await increaseTime(stepTimeout + 1);
        await rollup.connect(challenger).recover(id);
      }
      // 超限 recover
      await increaseTime(stepTimeout + 1);
      await expectRevert(rollup.connect(challenger).recover(id), "recovery limit");
      const t = await rollup.getTask(id);
      assert.strictEqual(Number(t.recoveries), mr, `mr=${mr}: recoveries 应等于上限 ${mr}, 实际 ${t.recoveries}`);
    }
  });
});

describe("7 固定absoluteDeadline", function () {
  it("recover 不改变 absoluteDeadline, 且到 absoluteDeadline 可 terminate", async function () {
    const bond = ethers.parseEther("1");
    const stepTimeout = 10;
    const mr = 2;
    const rollup = await deployRollup(bond, 200, stepTimeout, mr);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const third = signers[3];
    const steps = 16;
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat7"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i7")), steps, bond });
    await openChallenge(rollup, challenger, id, bond);
    const t0 = await rollup.getTask(id);
    const openedAt = BigInt((await ethers.provider.getBlock("latest")).timestamp);
    const expectedAbs = openedAt + BigInt(normalTransitions(steps) + mr) * BigInt(stepTimeout);
    assert.strictEqual(BigInt(t0.absoluteDeadline), expectedAbs, "absoluteDeadline 计算应与规范一致");
    const abs0 = t0.absoluteDeadline;
    // 执行 maxRecoveries 次 recover, 每次后检查 absoluteDeadline 不变
    for (let k = 0; k < mr; ++k) {
      await increaseTime(stepTimeout + 1);
      await rollup.connect(challenger).recover(id);
      const t = await rollup.getTask(id);
      assert.strictEqual(t.absoluteDeadline, abs0, "recover 不应改变 absoluteDeadline");
    }
    // 推进到 absoluteDeadline 之后, 第三方 terminate 仍可结算
    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const toAbs = Number(abs0) - Number(now) + 1;
    await increaseTime(Math.max(1, toAbs));
    await rollup.connect(third).terminate(id);
    const t = await rollup.getTask(id);
    assert.strictEqual(Number(t.phase), PHASE.SETTLED, "到 absoluteDeadline 后 terminate 应结算");
  });
});

describe("8 VERIFIED/SETTLED不能回退", function () {
  it("SETTLED 后所有结算/响应调用必须 revert", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const third = signers[3];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat8a"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i8a")), steps: 16, bond });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(third).adjudicate(id);
    const t = await rollup.getTask(id);
    assert.strictEqual(Number(t.phase), PHASE.SETTLED, "应已 SETTLED");
    await expectRevert(rollup.connect(third).settle(id), "phase");
    await expectRevert(rollup.connect(third).adjudicate(id), "phase");
    await expectRevert(rollup.connect(third).terminate(id), "phase");
    await expectRevert(rollup.connect(submitter).respond(id, []), "phase");
    await expectRevert(rollup.connect(submitter).advance(id), "phase");
    await expectRevert(rollup.connect(submitter).recover(id), "phase");
    await expectRevert(rollup.connect(submitter).replay(id), "phase");
  });
  it("VERIFIED 后无法回退到更早阶段", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat8b"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i8b")), steps: 16, bond });
    await openChallenge(rollup, challenger, id, bond);
    await reachVerified(rollup, submitter, id, 16);
    const t = await rollup.getTask(id);
    assert.strictEqual(Number(t.phase), PHASE.VERIFIED, "应已 VERIFIED");
    // 无法回退: respond 需要 OPEN, advance 需要 RESPONDED/LOCATING, recover 需要 OPEN..READY
    await expectRevert(rollup.connect(submitter).respond(id, []), "phase");
    await expectRevert(rollup.connect(submitter).advance(id), "phase");
    await expectRevert(rollup.connect(submitter).recover(id), "phase");
  });
});

describe("9 timeout/双方offline仍公开裁决", function () {
  it("矩阵 steps×maxRecoveries: 超时后第三方广告裁决仍可结算", async function () {
    const bond = ethers.parseEther("1");
    const stepTimeout = 10;
    for (const steps of STEPS_LIST) {
      for (const mr of MR_LIST) {
        const rollup = await deployRollup(bond, 200, stepTimeout, mr);
        const signers = await ethers.getSigners();
        const submitter = signers[1];
        const challenger = signers[2];
        const third = signers[3]; // 双方"离线", 由无关第三方裁决
        const id = ethers.keccak256(ethers.toUtf8Bytes("cat9-" + steps + "-" + mr));
        await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i9")), steps, bond });
        await openChallenge(rollup, challenger, id, bond);
        const t0 = await rollup.getTask(id);
        const abs = Number(t0.absoluteDeadline);
        const now = Number((await ethers.provider.getBlock("latest")).timestamp);
        await increaseTime(Math.max(1, abs - now + 1));
        // 第三方公开裁决 (双方均不参与)
        await rollup.connect(third).adjudicate(id);
        const t = await rollup.getTask(id);
        assert.strictEqual(Number(t.verdict), 0, `steps=${steps},mr=${mr}: 诚实提交 verdict 应 0`);
        assert.strictEqual(Number(t.phase), PHASE.SETTLED, `steps=${steps},mr=${mr}: 应 SETTLED`);
        const subBal = await rollup.claimable(await submitter.getAddress());
        assert.ok(subBal === 2n * bond, `steps=${steps},mr=${mr}: submitter 应获 2*bond`);
        await assertConservation(rollup, `cat9 steps=${steps},mr=${mr}`);
      }
    }
  });
});

describe("10 重复settle/finalize/withdraw", function () {
  it("重复 settle 必须 revert", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat10a"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i10a")), steps: 16, bond });
    await openChallenge(rollup, challenger, id, bond);
    await reachVerified(rollup, submitter, id, 16);
    await rollup.connect(challenger).settle(id);
    const t = await rollup.getTask(id);
    assert.strictEqual(Number(t.phase), PHASE.SETTLED, "settle 后应 SETTLED");
    await expectRevert(rollup.connect(challenger).settle(id), "phase");
  });
  it("重复 finalize 必须 revert, 且窗口内 finalize 也 revert", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 60, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const finalizer = signers[3];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat10b"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i10b")), steps: 16, bond });
    // 窗口内 finalize -> revert
    await expectRevert(rollup.connect(finalizer).finalize(id), "window");
    await increaseTime(61);
    await rollup.connect(finalizer).finalize(id);
    const t = await rollup.getTask(id);
    assert.strictEqual(Number(t.phase), PHASE.SETTLED, "finalize 后应 SETTLED");
    await expectRevert(rollup.connect(finalizer).finalize(id), "phase");
  });
  it("重复 withdraw 必须 revert", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const third = signers[3];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat10c"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i10c")), steps: 16, bond });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(third).adjudicate(id);
    const subAddr = await submitter.getAddress();
    const tx = await rollup.connect(submitter).withdraw(subAddr);
    await tx.wait();
    const t = await rollup.getTask(id);
    void t;
    const after = await rollup.claimable(subAddr);
    assert.ok(after === 0n, "首次 withdraw 后 claimable 应清零");
    await expectRevert(rollup.connect(submitter).withdraw(subAddr), "no balance");
  });
});

describe("11 真实余额(扣gas后)与守恒", function () {
  it("守恒不变量在各阶段成立", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat11a"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i11a")), steps: 16, bond });
    await assertConservation(rollup, "cat11a 提交后");
    await openChallenge(rollup, challenger, id, bond);
    await assertConservation(rollup, "cat11a 挑战后");
    await rollup.connect(challenger).adjudicate(id);
    await assertConservation(rollup, "cat11a 结算后");
  });
  it("提现后赢家真实余额 = amount - 扣gas", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const third = signers[3];
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat11b"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i11b")), steps: 16, bond });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(third).adjudicate(id);
    const amount = 2n * bond;
    const subAddr = await submitter.getAddress();
    const before = await ethers.provider.getBalance(subAddr);
    const txr = await rollup.connect(submitter).withdraw(subAddr);
    const receipt = await txr.wait();
    const after = await ethers.provider.getBalance(subAddr);
    const tx = await ethers.provider.getTransaction(receipt.hash);
    const feePerGas = tx.gasPrice ?? tx.maxFeePerGas ?? 0n;
    const gasCost = receipt.gasUsed * feePerGas;
    assert.strictEqual(after - before + gasCost, amount, "提现后真实余额应为 amount - 扣gas");
    await assertConservation(rollup, "cat11b 提现后");
  });
});

describe("12 拒收与重入提现", function () {
  it("拒收 recipient 导致 withdraw revert 且 claimable 不变", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const third = signers[3];
    const reject = await (await ethers.getContractFactory("WithdrawRejectRecipient_Test")).deploy();
    await reject.waitForDeployment();
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat12a"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i12a")), steps: 16, bond });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(third).adjudicate(id);
    const subAddr = await submitter.getAddress();
    const claimBefore = await rollup.claimable(subAddr);
    assert.ok(claimBefore === 2n * bond, "结算后 claimable 应为 2*bond");
    const balBefore = await ethers.provider.getBalance(await rollup.getAddress());
    // 拒收 -> revert
    await expectRevert(rollup.connect(submitter).withdraw(await reject.getAddress()), "transfer failed");
    const claimAfter = await rollup.claimable(subAddr);
    const balAfter = await ethers.provider.getBalance(await rollup.getAddress());
    assert.ok(claimAfter === claimBefore, "拒收后 claimable 不应改变");
    assert.ok(balAfter === balBefore, "拒收后合约余额不应改变");
    assert.ok((await ethers.provider.getBalance(await reject.getAddress())) === 0n, "拒收合约不应收到任何 ETH");
  });
  it("重入 recipient 仅获得一次 amount 且守恒", async function () {
    const bond = ethers.parseEther("1");
    const rollup = await deployRollup(bond, 200, 10, 2);
    const signers = await ethers.getSigners();
    const submitter = signers[1];
    const challenger = signers[2];
    const third = signers[3];
    const reentry = await (await ethers.getContractFactory("WithdrawReentrancyRecipient_Test")).deploy(await rollup.getAddress());
    await reentry.waitForDeployment();
    const id = ethers.keccak256(ethers.toUtf8Bytes("cat12b"));
    await submitTask(rollup, submitter, { taskId: id, initial: ethers.keccak256(ethers.toUtf8Bytes("i12b")), steps: 16, bond });
    await openChallenge(rollup, challenger, id, bond);
    await rollup.connect(third).adjudicate(id);
    const amount = 2n * bond;
    const recAddr = await reentry.getAddress();
    const balBefore = await ethers.provider.getBalance(await rollup.getAddress());
    const tx = await rollup.connect(submitter).withdraw(recAddr);
    await tx.wait();
    const balAfter = await ethers.provider.getBalance(await rollup.getAddress());
    const recBal = await ethers.provider.getBalance(recAddr);
    const received = await reentry.receivedTotal();
    assert.strictEqual(received, amount, "重入 recipient 只能收到一次 amount, 不能双重支付");
    assert.strictEqual(recBal, amount, "recipient 实际余额应恰为 amount");
    assert.strictEqual(balBefore - balAfter, amount, "合约余额只应减少一次 amount");
    await assertConservation(rollup, "cat12b 重入后");
  });
});
