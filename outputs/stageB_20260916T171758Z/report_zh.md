# 阶段 B 报告｜本地功能、安全与资金闭环

> 阶段：B（本地功能、安全与资金闭环）｜状态：**completed**
> 上级基线：阶段 A `stageA-freeze-20260916T162724Z`
> 本阶段 run：`stageB-freeze-20260916T171758Z`
> 环境：本地 Hardhat 31337 / Cancun / in-process automining，无公网、无真实 TEE、无真实 DA
> 声明：本报告为实验阶段结果，不构成生产安全审计，未修改论文，未 commit / push。

---

## 1. 实际修改与新增的文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `evm/revision/stageB_closure.test.js` | 新增 | B 阶段补充测试：资金闭环两层对账、B01/B04/B05/B06/B10/B11/B12/B13/B14 补齐，并生成机器可读 `case_matrix.json` |
| `outputs/stageB_20260916T171758Z/handoff.json` | 新增 | 本阶段交接契约 |
| `outputs/stageB_20260916T171758Z/report_zh.md` | 新增 | 本报告 |
| `outputs/stageB_20260916T171758Z/commands.txt` | 新增 | 实际验证过的复现命令 |

**合约零变更。** `BoundedTaskRollup.sol`、`BlobBatchAnchor.sol`、`MockTEEVerifier.sol`、`MockDARegistry.sol` 均未修改——既有回归 23/23 全绿，未发现需要修复的缺陷，因此不存在"最小修复"，也不存在经济分配或 timeout 规则改动（若需改动会先暂停并请用户裁决协议选项）。

### 1.1 权威实现清点（authority inventory）

- **被测主入口**：`evm/contracts/BoundedTaskRollup.sol`（206 行，`pragma ^0.8.24`）。
- **程序模型**：至多 **128 步**确定性重算（`MAX_STEPS=128`，从实现读取而非沿用历史常量）。`traceRoot = keccak256(abi.encode(bytes32[]))` 是**有序向量承诺**，明确**不是** Merkle 根、也**不是**单步证明。
- **实际外部接口**（共 15 个，均由源码生成 case，未臆造方法）：
  `getTask` `taskDigest` `compute` `submit` `normalTransitions` `openChallenge` `respond` `advance` `recover` `replay` `adjudicate` `settle` `terminate` `finalize` `withdraw`
  > 提示词特别提醒的"禁止臆造 `challenge()/settle()`"：实际方法名是 **`openChallenge()`**；`settle()` 确实存在但要求 `phase == VERIFIED`。
- **legacy 入口**：`HybridTEERollup.sol` 仅供旧反例对照（`legacy_counterexamples.js`），不混入新结果。
- **受控 mock 后端**：`MockTEEVerifier.sol`（ECDSA 签名校验，**非真实 Quote**）、`MockDARegistry.sol`（**无访问控制**，任意地址可改 `available`）。
- **账本变量**：`claimable(address)`、`locked`、`totalClaimable`、`totalDeposited`、`totalWithdrawn`、`totalBurned`。

---

## 2. 前后行为（before / after）

| 项目 | before（既有基线） | after（本阶段） |
|---|---|---|
| 既有安全回归 | 23/23 通过 | 23/23 通过（**未改动，保持原样复跑**） |
| B 阶段补充测试 | 不存在 | 新增 9/9 通过 |
| 断言总数 | 23 | **32**（23 既有 + 9 新增） |
| 资金守恒对账 | 单点断言（describe 11） | **两层全局对账**，覆盖提交/挑战/裁决/销毁/提现/多任务并行 |
| case matrix | 无机器可读产物 | `case_matrix.json`（9 条，含 expectedOutcome / faultOwner / accounting） |
| 合约 | 未变 | 未变 |

编译：8 个 Solidity 文件全部成功（Solidity 0.8.26、viaIR、optimizer runs 200、evmVersion cancun）。

---

## 3. B01–B14 结果

`assertionPass=true` 表示**测试断言通过**；`expectedOutcome` 表示**预期场景结果**。二者独立：预期被正确拒绝时 `expectedOutcome=rejected` 而 `assertionPass=true`。

| ID | 用例 | 来源 | expectedOutcome | 结果 | 要点 |
|---|---|---|---|---|---|
| B01 | 正常任务终局及提现 | 新增 | accepted | pass | 完整账本：locked 0→1→2→0 bond；实际提现净得 2 bond（已扣 gas）；重复 withdraw 被拒 |
| B02 | 错链/错合约/错 nonce 签名 | 既有 describe 4 | rejected | pass | digest 绑定 `chainid + address(this)`；跨 deployment 重放被拒 |
| B03 | 未授权 respond/step | 既有 describe 1 | rejected | pass | 非 submitter 调用 respond revert（`submitter only`） |
| B04 | 改写输出/轨迹/步数 | 新增 + 既有 describe 3 | rejected+accepted | pass | 篡改 output → verdict 含 bit0；篡改 traceRoot → respond `trace binding` 拒绝；短 trace → `trace length` 拒绝 |
| B05 | 错误证据或自填赢家 | 新增 | rejected+accepted | pass | 未 VERIFIED 直接 `settle` 被拒；`adjudicate` 客观裁决，挑战者不能自封赢家 |
| B06 | 挑战截止前/等于/后一单位 | 新增 | rejected+accepted | pass | `openChallenge` 用 `<= deadline`；`finalize` 用严格 `> deadline`。用 `evm_setNextBlockTimestamp` 精确控制（Hardhat 自动出块每笔 +1s，否则边界会漂移） |
| B07 | 重复提交/挑战/resolve/finalize/withdraw | 既有 describe 10 | rejected | pass | 全部明确 revert，不重复锁定/支付 |
| B08 | 已终局任务旧证据重放 | 既有 describe 4 + 8 | rejected | pass | 不重开、不回滚、不二次罚没 |
| B09 | 恶意接收者回退/重入 | 既有 describe 12 | rejected+accepted | pass | 拒收 recipient 使 withdraw revert 且 claimable 不变；重入 recipient 仅得一次 |
| B10 | 多任务并行与资金隔离 | 新增 | accepted | pass | 3+ 任务并存，每任务抵押独立；全局两层守恒成立 |
| B11 | 自挑战及串谋转移 | 新增 | rejected+accepted | pass | 自挑战被拒（`msg.sender != submitter`）；Sybil 仅自有地址间转移，控制人净收益 = 对手押金 1 bond，**非经济惩罚** |
| B12 | 输入上限 0/1/最大/超步数 | 新增 + 既有 describe 5 | rejected+accepted | pass | steps=0/129 提交前拒绝；1/128 可提交并正确裁决；`normalTransitions` 与 JS 参考逐点一致 |
| B13 | legacy 反例重放到新入口 | 新增 | rejected | pass | R1–R5 均不复现（详见 §4） |
| B14 | Mock 证明/DA 与未实现接口 | 新增 | deferred_to_E / deferred_to_D | pass | 记录边界，不冒充真实能力 |

### B13 legacy 反例（R1–R5）逐条复验

| 旧风险 | 旧行为 | 新入口行为 | 结论 |
|---|---|---|---|
| R1 respondChallenge 任意人可调用 | 可劫持 responder | `respond` 要求 `msg.sender == submitter` | 不复现 |
| R2 replayChallenge 接受自填 expectedHash | 无真实重执行校验 | `replay(taskId)` **仅 1 个入参**，verdict 由 `_verify` 确定性重算 | 不复现 |
| R3 resolveChallenge 接受自填 resolutionBits | 任意人可决定胜负 | `adjudicate(taskId)` **仅 1 个入参**，无自填裁决位 | 不复现 |
| R4 recoverChallenge 不限次数且状态回退 | REPLAYED→READY_FOR_REPLAY | `maxRecoveries=2` 限次；recover **不改变 phase** | 不复现 |
| R5 SLASHED 仅标记不扣款 | 无资金后果 | 错误任务 `finalize` **真实 burn**，`totalBurned += bond`，无人获 claimable | 不复现 |

---

## 4. 资金闭环与经济合理性（B4）

### 4.1 三条会计恒等式（所有场景均断言）

```
(1) balance            == locked + totalClaimable
(2) balance            == totalDeposited - totalWithdrawn - totalBurned
(3) totalClaimable     <= balance          （正常 fixture 下精确相等）
```

含义：累计受控入金 − 累计外付 − 累计销毁 = 合约资产净变化；内部负债不超过可用资产。

### 4.2 结论

- 在**提交 / 挑战 / 裁决 / 销毁 / 提现 / 多任务并行**全部 B 阶段场景下，三条恒等式均成立。
- **单任务抵押未被其他任务扣除或重复使用**（B10 验证：结算某任务不影响其他任务的 locked）。
- **slash 改变责任方权利后，受益人实际 `withdraw` 才算支付完成**（B01 验证了真实 EOA 到账）。
- 记账口径：`locked` 与 `claimable` 是**不重叠**的两类账户状态，`totalBurned` 单独记账；押金退款与罚没赔付属**价值转移**，不计为系统资源费用。
- 金额全部以 **BigInt** 计算并序列化为十进制字符串，未使用 JS 浮点。EOA 余额断言已扣除实际交易 gas。

### 4.3 自挑战与串谋（诚实报告，不夸大）

- submitter **不能自挑战**（合约 `require(msg.sender != t.submitter)`）。
- 用同一控制人的第二地址（Sybil）挑战**诚实**提交：客观裁决仍判 submitter 胜，控制人净收益 = 对手押金 **1 bond**。
- **这只是在两个自有地址之间转移押金，不构成经济惩罚**。协议未定义 burn 之外的额外反串谋处罚，本阶段不引入未定义的惩罚，也不把任意转账宣称成抗串谋能力。

---

## 5. API / 状态表（供阶段 C 复用）

### 5.1 Phase 流转

`NONE → SUBMITTED → OPEN → RESPONDED → LOCATING* → READY → VERIFIED → SETTLED`

（`LOCATING` 为二分中间态；`adjudicate` 可从 `OPEN..READY` 任意点**绕过定位**直达 `VERIFIED`→`SETTLED`）

### 5.2 操作表

| 操作 | 调用者 | 前置 phase | 时间条件 | 状态变化 | 资金变化 |
|---|---|---|---|---|---|
| `submit` | 任意（须为签名者） | NONE | — | →SUBMITTED，设 challengeDeadline | `locked += bond`，`totalDeposited += bond` |
| `openChallenge` | 非 submitter | SUBMITTED | `ts <= challengeDeadline` | →OPEN，设 absoluteDeadline | `locked += bond`，`totalDeposited += bond` |
| `respond` | **submitter** | OPEN | 未超时 | →RESPONDED，记录 firstMismatch | 无 |
| `advance` | 任意 | RESPONDED/LOCATING | 未超时 | →LOCATING 或 READY | 无 |
| `recover` | **任意** | OPEN..READY | `timeoutAt < ts < absoluteDeadline` 且 `recoveries < maxRecoveries` | **不改 phase**，`recoveries++`，`_touch` | 无 |
| `replay` | 任意 | READY | 未超时 | →VERIFIED（确定性重算） | 无 |
| `adjudicate` | **任意** | OPEN..(<SETTLED) | **无时间门槛** | →VERIFIED→SETTLED | 见 `_settle` |
| `settle` | 任意 | VERIFIED | — | →SETTLED | 见 `_settle` |
| `terminate` | 任意 | OPEN..(<SETTLED) | `ts > timeoutAt` 或 `ts >= absoluteDeadline` | →VERIFIED→SETTLED | 见 `_settle` |
| `finalize` | 任意 | SUBMITTED | `ts > challengeDeadline` | →SETTLED | verdict=0 按 `_settle`；否则 burn 到零地址 |
| `withdraw` | claimable 所有者 | — | — | — | `claimable→0`，实际转账 |

`_settle`：`amount = (challenger == 0 ? bond : 2*bond)`；`winner = (verdict == 0 ? submitter : errorRecipient)`，其中 `adjudicate/terminate` 的 errorRecipient 为 `challenger`。

### 5.3 对阶段 C 的关键语义提醒（已在 B 中确认，不得在 C 中关闭）

1. **`respond` 是可选诊断步骤**，不是可因离线而罚没的义务。
2. **`adjudicate` 允许任何人绕过定位直接确定性重算并结算**，且**无时间门槛**——C 测试恢复交互路径时**不得关闭此兜底**来制造恢复必要性。
3. **`terminate` 超时仍按计算结果判责**，不是仅因某角色离线而惩罚。
4. **`recover` 只更新 `recoveries` 与 `timeoutAt`**，**不更换 challenger、不改变收益权**——"新观察者能调用函数"≠"已有经济接管机制"。
5. `absoluteDeadline` 在 `openChallenge` 时一次确定，`recover` 不更新它；`maxRecoveries <= 2`（constructor 约束）。

---

## 6. 当前源码 / 配置哈希

| 项 | 值 |
|---|---|
| gitHead | `615bb3e9f1ae3b88b87f488decc61854cd555e16` |
| gitBranch | `main` |
| gitDirty | `true`（工作区含既有未跟踪成果；未 reset/clean/commit/push） |
| **B 阶段 sourceTreeSha256** | `fb2eb8e5e79ab1fa621a447e9989c95dbf48130bc0ee26cade7bfc5269d2e213` |
| B 阶段 configSha256 | `0d5d86dd89f8b5e38346cc2feb3104c25721a0bc69a7932b7da3969d9566b381` |
| 父（A）sourceTreeSha256 | `7998677f3f19f1433d3f3a92c8698ef8b27a10ab924f8d6561786e982089f126` |
| 父（A）configSha256 | `3c8fe631e98dbf0a3cda7c1d18233ed3f6255c121d68dc60617eeea6c784a4b4` |

sourceTree 变化原因：新增 `stageB_closure.test.js`。configSha256 变化原因：`--run-id` 覆盖 `config.runId`，且 `build.nodeVersion/pythonVersion` 由运行时写入；**配置语义未变**。

---

## 7. 可信边界、限制与 deferred 项

- **已验证**：本地 Hardhat 上的功能正确性、权限、重放防护、边界、资金守恒、提现安全（拒收/重入）、多任务隔离。
- **未验证 / 不属于本阶段能力**（明示，不冒充）：
  - **DA 强绑定与有责任主体的可归责罚没 → deferred_to_E**。`MockDARegistry` 无访问控制（任意地址可 `setAvailability`），**不能**把 mock setter 当作 DA 罚没已实现。
  - **真实 TEE 远程证明 → deferred_to_D**。`MockTEEVerifier` 是 `ecrecover` 普通签名校验，不含 Quote / TCB / collateral。
  - **Merkle 单步证明 / 通用 VM → not_applicable**。当前为 128 步向量重算，未设置虚假"区间缩小 pass"。
- 本地 automining 无真实共识最终性；本阶段不产生公网性能或真实费用结论。

---

## 8. 进入阶段 C 的条件

**C 已就绪（`nextStageConditions.C.ready = true`）**，前提是 C 必须遵守 §5.3 的语义约束：

1. Phase 与转换语义已公开；
2. `recover` 语义已确认（不改 challenger / 收益权 / phase）；
3. `adjudicate` 兜底已确认且**不得关闭**；
4. `terminate` 按计算结果判责已确认；
5. `maxRecoveries=2` 与 `absoluteDeadline` 固定性已确认。

**D / E 未就绪**：需真实 SGX/TDX 硬件（或已授权远端）与公网 RPC / 测试币 / 广播授权，当前均不具备。
