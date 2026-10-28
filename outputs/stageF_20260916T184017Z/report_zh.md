# 【F 阶段】性能、费用、统计与消融 — 实施报告

- 阶段状态：**F-local = completed；F-TEE / F-Blob / F-full = blocked；整体 = partial**
- 冻结版本：runId `stageF-freeze-20260916T184017Z`
  - `sourceTreeSha256 = ab26edb78bb1a6be50ceb6261e69de523eeda0b725bd66f02be477273480377b`
  - `configSha256 = d12d58ce77d720ebc352f9e72a0fa0d2654f37d28456615a34aa43d6e1c297e7`
- 上游引用：A `stageA_20260916T162724Z`（配置/记录器/schema 复用）、B/C handoff、D/E handoff（均为 partial）
- 未做：未部署主网、未广播、未付费、未 commit/push、未改论文正文

---

## 1. 设计先冻结、后执行（§F2）

`design.frozen.json` 在测量开始前落盘，包含主要指标、矩阵、warmup、固定尝试数、独立 run 数、停止/超时/预算规则、失败处理与统计方法。**没有在观察初步结果后删除任何格子**。

| 项 | 取值 |
|---|---|
| 矩阵 | batchSize 1/8/32；payloadKiBPerTask 1/8/32；configuredConcurrency 1/4/16；steps 1/64/128 |
| 采样计划 | 每格 3 独立 run × (5 预热批 + 30 稳态批)；预热记录但不参与稳态统计 |
| 重试 | maxAttempts=3，退避 20 ms；失败与重试全部保留 |
| 超时 | 单批 120 s 记右删失，不删除 |
| 负载模型 | **closed-loop**（固定批数，批完成才补新批）— 不能宣称无限到达压力下的容量 |
| 应用样例 | bounded-keccak-chain-accumulator（确定性合成微基准，**不是真实 DApp 业务负载**） |

**矩阵未展开为全笛卡尔积**（3×3×3×3=81 格），而是按 §F3 要求：先单变量筛查（除被测维度外固定 baseline `b8/p8/c4/s64`），再加预设交叉角点，共 **13 格**：

- 筛查：batchSize{1,8,32}、concurrency{1,4,16}、payload{1,8,32}、steps{1,64,128}
- 强制（§F3 明确要求）：batchSize=1 × concurrency=1/4/16 三格
- 交叉角点：`b32-p32-c16-s128`（heavy）、`b1-p1-c1-s1`（light）

**步数边界**：`MAX_STEPS=128`；`steps=0` 与 `steps=129` 的 submit **均被拒绝**（不缩小 payload、不截断后重测）。

---

## 2. 数据身份与记录扩展（§F1）

- A 的每样本一逻辑批约定保持不变：batch record 的 `taskCount = batchSize`，吞吐 numerator 不超过该样本 taskCount。
- 跨批次汇总是**独立版本化**的 `hybrid-tee-rollup.stageF.window.v1` 记录，引用所有 `sampleId`，并含 batchCount、distinctTaskCount、attemptCount、accepted/executed/finalized 计数、失败/重试/删失、起止单调时钟与队列信息。**未用 A `experiment_record` 冒充窗口记录或单样本**。
- 耗时用 `process.hrtime.bigint()` 单调 ns（字符串）计算；UTC 仅用于跨进程关联；区块 timestamp 是链时钟，不用于墙钟结论。
- A schema 回归：21 个 node:test 子测试全部 ok；B（9/9）、C（17/17）在同输出目录复跑通过。

---

## 3. 并发与队列（§F3）

并发单位为 `inflight_batches`，**未使用 `min(batchSize, concurrency)` 折叠**（`runPool(limit = configuredConcurrency)`）。

| 格 | configured | observed peak | observed mean |
|---|---|---|---|
| b1-p8-c1-s64 | 1 | 1 | 1.00 |
| b1-p8-c4-s64 | 4 | 4 | 3.83 |
| b1-p8-c16-s64 | 16 | **16** | 12.57 |

三组差异明确保留。c16 的 mean 低于 peak，原因是批生命周期极短（批完成后才补新批，closed-loop），属正常；**没有通过改配置数字来"修"这个现象**。
signer 策略固定：每批 2 个 EOA（submitter / challenger），nonce 分配按 slot 轮转，pool=39；观察者/续推角色由 challenger 承担（合约未限制 `recover/advance/replay/settle` 调用者）——若引入第三个独立 EOA，concurrency=16 时需 48 个无冲突账户 > 可用 39 个，会改变系统条件，故在此显式报告。

---

## 4. 主矩阵结果（3 独立 run 均值）

| 格 | finalized tasks/s | 批总延迟均值(ms) | finalized 任务 | 失败率 | 说明 |
|---|---|---|---|---|---|
| b1-p8-c4-s64 | 144.63 | 22.3 | 90 | 0 | |
| b8-p8-c4-s64（baseline） | **162.78** | 161.8 | 720 | 0 | |
| b32-p8-c4-s64 | 5.63 | 575.4 | 93 / 2880 | **96.8%** | 挑战窗口假象，见 §5 |
| b8-p8-c1-s64 | 128.19 | 53.3 | 720 | 0 | |
| b8-p8-c16-s64 | 15.51 | 118.0 | 72 / 720 | **90%** | 同上 |
| b8-p1-c4-s64 | 137.38 | 191.5 | 720 | 0 | |
| b8-p32-c4-s64 | 138.54 | 188.4 | 720 | 0 | |
| b8-p8-c4-s1 | **518.75** | 51.8 | 720 | 0 | 步数最少 |
| b8-p8-c4-s128 | 83.51 | 309.9 | 720 | 0 | 步数最大 |
| b1-p8-c1-s64 | 121.79 | 7.0 | 90 | 0 | |
| b1-p8-c16-s64 | 117.19 | 93.8 | 90 | 0 | |
| b32-p32-c16-s128 | 9.37 | 777.4 | 288/2880 | **90%** | 同上 |
| b1-p1-c1-s1 | 277.13 | 3.0 | 90 | 0 | |

**真实效应的维度**：steps（518.75 → 162.78 → 83.51，s1/s64/s128）与 batchSize 有明显单调影响。
**名义维度**：payloadKiBPerTask 1 → 32 为 137.38 vs 138.54，无实质差异——因为有界模型的 `dataHash` 固定 32 字节，计算只处理 hash 链，**payload 不改变链上数据大小**。已如实标记 `payloadIsNominal=true`，不据此声称大 payload 吞吐，也不把吞吐称为高频 DApp 通用业务 TPS。
**concurrency 在 batchSize=1 下无单调增益**（121.79 → 144.63 → 117.19）：Hardhat automining 把交易串行写入区块，客户端在途批次可重叠但区块产出不并行，属环境限制而非协议结论。

---

## 5. 挑战窗口失败归因（诚实报告，非"删格子"）

三格出现 `revert 'window'`：`openChallenge` 时 `block.timestamp > challengeDeadline`。

- 根因：Hardhat 每块链钟 +1 秒且 automining 串行；固定 `challengeWindow=100`（链秒）在 batchSize=32 或 concurrency=16 的排队下被越过。
- **这是一次仪器/部署参数假象，不是协议吞吐上限**。为此另做归因运行（新增旋钮 `F_CHALLENGE_WINDOW` 后重新冻结：`sourceTreeSha256=d7752e7e…` / `configSha256=d9a3083d…`），仅改部署参数、不改协议机制：

| 格 | 主运行 finalize 率 | 归因运行（window=100000）finalize 率 | 归因运行 finalized tasks/s |
|---|---|---|---|
| b32-p8-c4-s64 | 0.032 | **1.0** | 156.93 |
| b8-p8-c16-s64 | 0.100 | **1.0** | 154.04 |
| b32-p32-c16-s128 | 0.100 | **1.0** | 87.07 |

主运行数据仍然保留并全部报告（未删除、未替换），归因运行单独归档在 `attribution/`，两者分表呈现。

---

## 6. 消融（§5，不关闭兜底伪造"无恢复必失败"）

batchSize=1、steps=64、concurrency=1、故障注入需全局时间推进故串行；每臂 3 run × (2 预热 + 10 稳态)。

| 策略 | 批总延迟均值(ms) | adjudicate 类 gas | recover gas | 本地费用合计(wei) | 交互续推成功 | 兜底使用 |
|---|---|---|---|---|---|---|
| direct-fallback | **7.3** | 3,960,444 | 0 | 14,299,321,100,095,247 | 0/30 | 30/30 |
| no-recovery-with-fault-fallback | 8.7 | 8,150,328 | 0 | 18,489,251,129,424,757 | **0/30** | 30/30 |
| recovery-under-fault | 12.6 | 15,211,236 | 970,644 | 26,520,665,185,644,655 | **30/30** | 0/30 |
| recovery-interactive | 13.5 | 15,211,080 | 0 | 25,550,213,204,401,704 | 30/30 | 0/30 |

四臂的**任务终局率均为 100%**（30/30 批、36/36 次尝试含预热），因为当前有界合约保留了不依赖恢复的 `adjudicate` 直接重算兜底。**没有关闭兜底来伪造"无恢复必失败"**。

**诚实的负面结论**：在 `MAX_STEPS=128` 的有界模型中，恢复**没有**改善正确终局时间（recovery-under-fault 12.6 ms vs no-recovery 8.7 ms，且 gas 与本地费用更高）。`recover` 的唯一作用是：提交方超时离线后，第三方仍能继续**交互**路径（30/30 vs 0/30）。因此不得宣称"恢复降低结算延迟"或"恢复提升终局速度"。

配对差异（以独立 run 为 cluster，固定 seed 20260917）：3 个 cluster，**不给 bootstrap CI**（`only_3_independent_runs`，仅描述性）：
- recovery-under-fault → no-recovery-with-fault-fallback：+3.97 ms（恢复更慢）
- recovery-interactive → direct-fallback：+6.13 ms（交互路径更慢）
- recovery-under-fault → direct-fallback：+5.30 ms

---

## 7. 指标、费用与整数记账（§F4 / §F5）

- 端点分离记录：提交确认 / 乐观可用 / 协议终局 / 可提现 / **实际提现** 五个端点各自有 UTC + 单调 ns。并行阶段**不直接相加**，只报告各段批级均值。
- gas 与 wei 全部 BigInt + 十进制字符串序列化，无 JS Number 中转、无字符串比较大小。
- 本地 gas 与真实货币费用分开：`feeSource = "local-gas-only"`，`feeStatus = "local_measured_not_monetary"`；**未取得真实字段不填 0、不填估算**。无 `blobGasUsed`/`blobGasPrice`（E 公网发布 blocked）。
- 押金 / 退款 / 罚没 / 销毁作为**价值转移单列**，不与 gas 费用总额相加；失败重试成本是总额子集，不重复加一次。
- 三种分母的单位成本（baseline `b8-p8-c4-s64`，3 run 合计本地费用 286,264,196,290,113,552 wei）：
  - per finalized task = 397,589,161,514,046 wei
  - per accepted task = 397,589,161,514,046 wei
  - per batch = 3,180,713,292,112,372 wei
  - 分母 0 / 未测一律 `null + reason`。

---

## 8. 统计与 fixture 测试（§F6）

- raw 落盘后由 `stageF_aggregate.js` **单独重建**全部汇总与图表；统计逻辑抽到纯函数模块 `stageF_stats.js`。
- `stageF_stats.test.js` **12/12 通过**，覆盖：已知分位数、样本量不足省略高分位（n=5 不报 p95）、分母 0/未测、全失败、右删失、重复 task/tx 去重、超大 wei（>2^53 精确）、缺费用字段（missing 单列）、跨窗口任务归属、批内相关（cluster=run/批，禁止 80 个批内任务当大样本）、nonce 重试、固定 seed 可复现。
- 报告口径：每格给尝试/成功/失败/重试/删失、独立 run 数、均值、中位数(p50)、p95（n≥20 才给）、分位算法与样本量。**3 个独立 run 时不给 CI、不报 p99**。
- 不按均值先筛异常；唯一预设排除是"warmup 不参与稳态统计"，原数据全部保留。

**校验结果**（`summary/validation.json`）：
- batch 记录 1509（其中 measured 1290、warmup 219），window 记录 51（矩阵 39 + 消融 12）
- task 记录 13164，**重复 taskId = 0**；去重后 distinct = 13164（measured 11280）
- 费用：window 求和 = cell 求和（2,280,444,527,876,761,988 wei）✅；每个 window 的 `totalFeeWei` = 五项分项之和 ✅（0 处不一致）
- 图表数值直接由与表格同一数据结构生成，一致性由构造保证

---

## 9. Blob 填充阶梯（codec 计算，**非链上实测**）

来源：E 阶段真实 `blobcodec`（4096 FE × 31 data bytes，单 Blob 上限 **126,976** 数据字节）。

| taskCount | payloadKiB | frame bytes | blobs | 填充率 |
|---|---|---|---|---|
| 1 | 32 | 32,859 | 1 | 0.2588 |
| 1 | 64 | 65,627 | 1 | 0.5168 |
| 1 | 128 | 131,163（预测） | **2** | 0.5165 → **blocked（不缩小 payload、不截断）** |
| 8 | 32 | 32,943 | 1 | 0.2594 |
| 32 | 32 | 33,231 | 1 | 0.2617 |

30 行阶梯中 17 行超出单 Blob 容量，全部标 `blocked`。所有在容量内的行均用真实 codec 逐点核对（predicted == actual，`codecVerified=true`）。此表为 **modelled / codec-computed**，不是公网发布或链上实测结果。

---

## 10. 产出清单

```
outputs/stageF_20260916T184017Z/
├── handoff.json
├── report_zh.md
├── commands.txt
├── comparability_contract.json          # 供 G 引用
├── stageF_freeze/                       # 冻结清单 + 运行日志
└── hardhat_run/stageF/
    ├── design.frozen.json
    ├── raw/{batch_records.jsonl, window_records.jsonl, boundary_records.json}
    ├── summary/{cell_summary.json|csv, ablation_summary.json|csv,
    │            concurrency_check.json, boundary_summary.json,
    │            blob_fill_ladder.json|csv, data_dictionary.json, validation.json}
    └── figures/{fig_param_scaling, fig_stage_latency, fig_recovery,
                 fig_gas_fee, fig_blob_fill_ladder, fig_ablation}.svg
└── attribution/                         # 挑战窗口归因运行（独立冻结）
```

新增/修改代码：`evm/revision/stageF_perf.js`（测量 runner）、`stageF_stats.js`（纯统计）、`stageF_stats.test.js`（fixture 测试）、`stageF_aggregate.js`（raw→汇总/图表）。

---

## 11. 本阶段没有测到的项与限制

1. **F-TEE（blocked）**：真实 TEE 执行/证明时间 — 需 D 阶段真实应用执行验收（本机 Apple M5/arm64，无 `/dev/sgx*`、`/dev/tdx*`，无远程 Quote）。
2. **F-Blob（blocked）**：真实 blobGas、Blob 发布与独立取回耗时、DA 披露与罚没结算 — 需 E 阶段公网验收（缺 RPC/测试币/广播授权）。
3. **F-full（blocked）**：同一任务真实后端联调。
4. **不能外推的结论**：Hardhat automining 无共识最终性 → 不报最终性延迟；closed-loop 负载模型 → 不宣称无限到达压力下的容量；3 个独立 run → 不报 p99、不给稳定 CI；本地 gas → 不换算真实法币、不给领先百分比。
5. **提交形态对照**（全量 vs 紧凑提交）：当前合约只有一种提交形态，标 `not_applicable`。
6. **裁决对照**（有界重算 vs Merkle 单步）：仓库内存在 `MerkleVerifier.sol`，但 `BoundedTaskRollup` 未接入单步证明路径，二者语义不可比 → 标 `not_applicable`，不强行对照。
7. **去掉签名/DA 强绑定的负控制**：属 `security-weakened`，本阶段未做，不带入任何公网结论。

---

## 12. 交付给 G 的内容

- 可直接使用：F-local 各格 gas / 本地费用 / 延迟 / 吞吐（**含失败率与分母**）、交互轮数映射（`txCount` 与 `recovery` 字段）、四臂恢复能力对照、`comparability_contract.json` 的端点定义与可比性标签。
- 阻塞项：真实货币费用比较、Blob DA 实付成本比较、TEE 执行时间比较。
- **G-mechanism 放行条件已满足**（F-local + comparability contract 验收通过）；G-official 的量化优势比较须等对应 F 子组验收，本轮标 blocked。
