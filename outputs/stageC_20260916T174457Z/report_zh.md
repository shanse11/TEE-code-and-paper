# 阶段 C 报告｜恢复、活性、串谋与有界 DoS

> 阶段：C｜状态：**completed**（含已显式标注的能力缺口，见 §6）
> 上级基线：阶段 B `stageB-freeze-20260916T171758Z`（sourceTree `fb2eb8e5…`）
> 本阶段 run：`stageC-freeze-20260916T174457Z`
> 声明：未 commit / push，未改论文，未对公网施加压力；所有故障注入仅在本地 Hardhat 隔离环境。

---

## 1. 改动

| 文件 | 类型 | 说明 |
|---|---|---|
| `evm/revision/stageC_recovery.test.js` | 新增 | C01–C17 对抗/恢复测试；产出 case_matrix、state_transition_table、invariants |
| `evm/revision/random_security.js` | **扩展**（非重写） | seed 可经 `RANDOM_SEED` 配置，默认保持原固定基线 `0x5eed2026`；输出按 seed 命名，避免多 seed 互相覆盖原始证据 |

**合约零变更。** 本阶段未修改任何合约——C 的目标是在既有协议语义下验证恢复/活性边界，而非改变经济或 timeout 规则。

---

## 2. 测试结果总览

| 项目 | 结果 |
|---|---|
| **B 回归（C 闸门）** | **32/32 通过**（在 C 的 run 下重跑 security.test.js + stageB_closure.test.js） |
| **C 阶段 case（C01–C17）** | **17/17 通过** |
| **不变量检查** | 5 次检查，**0 违反**（INV1–INV7） |
| **随机序列** | 4 seed × 1000 序列，**全部 pass=true**；合计 4000 序列 / 109,513 次调用 / 90,843 次 revert 状态检查 |

### 随机序列明细（本轮实际运行）

| seed | 序列数 | 调用数 | revert 状态检查 | pass |
|---|---|---|---|---|
| `0x5eed2026`（**原固定基线**） | 1000 | 27,401 | 22,686 | true |
| `0xa11ce` | 1000 | 27,296 | 22,706 | true |
| `0xb0b` | 1000 | 27,431 | 22,736 | true |
| `0xc0ffee` | 1000 | 27,385 | 22,715 | true |

> 原基线 `0x5eed2026` 的 27401 / 22686 是本轮**实际复跑**得到的确定性结果（seed 与参数相同），不是从历史报告沿用。

---

## 3. C01–C17 结果

`capabilityStatus` 说明：`verified`=能力真实可用；`limited`=仅部分可用；`deferred_to_E`/`not_applicable`=如实标注，未冒充完成。

| ID | 场景 | 结果 | capabilityStatus | 要点 |
|---|---|---|---|---|
| C01 | 无故障过早 recover | rejected | verified | 不破坏任务、不重置期限、不改 phase/事实 |
| C02 | 挑战者失联 → 新观察者 | continued | **limited** | recover **不更换 challenger**；事实延续靠 **adjudicate 兜底** |
| C03 | 提交者失联 | timeout_settled | **limited** | 第三方无签名不能 respond；只能 terminate 按计算结果判责 |
| C04 | 抢先占位后失联 | bounded+timeout_settled | verified | recoveries 上限=2；超上限后 terminate 仍可收口 |
| C05 | Sybil 多地址重复 recover | bounded | verified | 8 个 Sybil 仅 2 次成功；总期限未延长 |
| C06 | recover 时间边界 | rejected+accepted | verified | `timeoutAt < ts < absoluteDeadline` 两端严格；`evm_setNextBlockTimestamp` 精确控制 |
| C07 | recover 与 terminate 竞争 | accepted+rejected | verified | 两种顺序均只产生 1 个 `Settled` 事件，无双赢家/双支付 |
| C08 | 接近 absoluteDeadline | bounded+timeout_settled | verified | `_touch` 把 timeoutAt **截断**到 absoluteDeadline，不创建不可能义务 |
| C09 | maxRecoveries = 0/1/2 | bounded | verified | 各上限精确生效；超上限不丢原任务 |
| C10 | 重放与错误轨迹 | rejected | verified | 已终局任务旧证据重放被拒；跨任务 trace 不可复用 |
| C11 | 串谋抢占 | accepted | verified | 第三方 adjudicate 客观裁决；诚实反证不被永久排除 |
| C12 | DA 隐瞒 | not_applicable | **deferred_to_E** | 合约无 DA 义务，不能标"抗 DA 串谋" |
| C13 | 短时阻断/延迟 | continued | verified | 窗口内可恢复；永久阻断 `not_guaranteed` |
| C14 | 崩溃后恢复 | continued | verified | 仅凭链上 `getTask` 快照即可接续，不依赖原进程内存 |
| C15 | 快照回滚/双签 | rejected | **limited** | 协议层 taskId 防重放；**不宣称**硬件防回滚（deferred_to_D） |
| C16 | L1 重组 | not_applicable | not_applicable | 本地 automining 无真实重组 |
| C17 | 边界压力/最坏 gas | accepted | verified | steps=128、trace=129 可处理；20 次无效 recover 全 revert、状态无污染 |

---

## 4. 恢复 vs 超时结算（关键区别）

**`recover` 交易成功 ≠ 恢复完成。** 本阶段未把"调用 recover 成功"记为恢复完成。

| 类别 | case | 机制 | 首个有效推进取自 |
|---|---|---|---|
| **continuation（延续）** | C02 / C13 / C14 | 同一争议事实延续；真实续跑路径是 **adjudicate**（任何人可调用、无时间门槛、确定性重算） | 实际推进时刻（adjudicate/respond），**不是** recover 触发时刻 |
| **timeout settlement（超时结算）** | C03 / C04 / C07 / C08 | `terminate` 在 `ts>timeoutAt` 或 `ts>=absoluteDeadline` 时**按计算结果判责** | 结算时刻 |

关键事实：`recover` **只**做 `recoveries++` 与 `_touch(timeoutAt)`，**不迁移 phase、不更换 challenger、不改变收益权**。因此：
- 挑战者失联（C02）→ 任何人可 adjudicate 推进同一事实（**未关闭 adjudicate 兜底以制造恢复必要性**）。
- 提交者失联（C03）→ 第三方无 submitter 签名则不能 respond；只能 terminate，且**按计算结果判责而非仅因离线惩罚**。

---

## 5. 总时间预算与对抗上限

- **absoluteDeadline**：在 `openChallenge` 时**一次确定**，`absoluteDeadline = openTs + (normalTransitions(steps) + maxRecoveries) × stepTimeout`。
  例：steps=4、mr=2 → `(6 + 2) × 10 = 80s` 协议时间。**recover 不更新它**（INV1 已验证）。
- **恢复次数上限**：`maxRecoveries ≤ 2`（constructor 约束），矩阵 0/1/2 均精确生效。
- **`_touch` 截断**：`timeoutAt = min(now + stepTimeout, absoluteDeadline)`——这是"不创建不可能义务"的实际机制（C08）。
- **对抗上限实测**：
  - Sybil：8 个地址轮流 recover，仅 2 次成功，总期限不变。
  - 无效交易风暴（C17）：对已终局任务连续 20 次 recover，**全部 revert**，状态无污染，作废 gas 由攻击者承担。
  - 最大任务：steps=128、trace 长度 129 可正常提交/响应/裁决，无截断、无无界循环。

> 说明：`evm_increaseTime` 驱动的是**协议时间**；本阶段所有时间线同时保存 host `monotonicNs`、UTC、`blockNumber`、`blockTimestamp` 与 `clockSource`，**不把协议时间转换为真实墙钟恢复速度**。

---

## 6. 能力缺口与残余信任假设（诚实标注）

### 6.1 能力缺口（limited）

1. **第三方经济接管未实现**。当前 `recover` 不更换挑战者角色与收益权，"新观察者能调用 recover" ≠ "存在经济接管机制"。若需真正改换挑战权与收益权，属**显式协议变更**：需先说明新增假设与信任影响、取得用户授权，再回归 B——**不能仅在测试中换 `msg.sender` 后声称完成**。
2. **提交者失联且无可转发证据时无法"重新执行"**。只能超时结算，已如实记为 `timeout_settled`，不假称恢复成功。

### 6.2 残余信任假设

- 最终终止依赖**至少一个诚实、有数据、有资金且能上链调用的参与者**。
- **永久 L1 审查 / 无限分区不承诺活性**（C13 记为 `not_guaranteed`）。
- 硬件回滚、真实 DA 故障不在本阶段能力内（分别 deferred 到 D / E）。

---

## 7. 当前源码 / 配置哈希

| 项 | 值 |
|---|---|
| gitHead | `615bb3e9f1ae3b88b87f488decc61854cd555e16` |
| gitDirty | `true` |
| **C 阶段 sourceTreeSha256** | `ead8b96a915afa53ca94e3bb99208d6621b970be8d261033540c3ad6b227a298` |
| C 阶段 configSha256 | `044f0feabdfea2f4cf47f8bd29931aee2724b7a17b223796c3617841f764befc` |
| 父（B）sourceTreeSha256 | `fb2eb8e5e79ab1fa621a447e9989c95dbf48130bc0ee26cade7bfc5269d2e213` |

---

## 8. 供 D / E 复用的接口

- **恢复/超时语义**：`recover`（有界、不改角色）、`terminate`（按计算结果判责）、`adjudicate`（无时间门槛兜底）——D 的撤销处理与 E 的 DA 结算需与这三条路径互锁。
- **争议事实字段**：`TaskInput{ taskId, initial, steps, version, output, traceRoot, dataHash }` 与 `taskDigest = keccak256(DOMAIN, chainid, address(this), input)`——E 的任务绑定必须绑定到**这一** `taskDigest`，D 的 reportData/签名必须绑定 `chainId + verifyingContract + taskId + nonce + input/output/trace 承诺`。
- **不变量清单**：`invariants.json` 中的 INV1–INV7 可直接作为 D/E 修改合约后的回归断言。
- **缺失字段（E 需新增）**：核心合约当前**没有 DA 引用/指针字段**，因此 C12 无法验证；E 增加 DA 绑定后必须重跑 B/C 回归。
