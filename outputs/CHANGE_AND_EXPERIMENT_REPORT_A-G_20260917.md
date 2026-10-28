# Hybrid TEE-Rollup 阶段 A–G 变更清单、实验报告与技术文档

- **文档版本**：v1.0
- **生成时间**：2026-09-17
- **覆盖范围**：阶段 A（复核与冻结基线）→ B → C → D → E → F → G，共 7 项变更
- **证据根目录**：`/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/`
- **Git 基线**：branch `main`，HEAD `615bb3e9f1ae3b88b87f488decc61854cd555e16`，工作区 `gitDirty=true`（含既有未跟踪成果与新增文件）；**全程未执行 reset / clean / commit / push**
- **诚实声明**：本文所有数值均来自本轮实际运行产物（`handoff.json` / `*_report.md` / `raw/*.jsonl` / `summary/*.json`）。凡本轮未测、未核实或原文未报的项，一律显式标注 `blocked` / `not_verified` / `not_reported` / **待补充**，不做推断填充、不把离线或模拟结果写成真实结果。

---

# 第一部分 · 变更清单

## 1. 变更总览

| # | 阶段 | 主题 | 状态 | 是否修改生产合约 | 冻结 runId | sourceTreeSha256（前 8 位） |
|---|---|---|---|---|---|---|
| 1 | A | 复核与冻结基线 | completed（复核，无代码改动） | 否（本次仅为复核 + 新 run） | `stageA-freeze-20260916T162724Z` | `7998677f` |
| 2 | B | 本地功能安全与资金闭环 | completed | **否** | `stageB-freeze-20260916T171758Z` | `fb2eb8e5` |
| 3 | C | 恢复活性、串谋与有界 DoS | completed（含能力缺口） | **否** | `stageC-freeze-20260916T174457Z` | `ead8b96a` |
| 4 | D | 真实 TEE 证明与应用执行 | partial（D-local completed） | **否** | `stageD-freeze-20260916T180557Z` | `e8467bd4` |
| 5 | E | 真实 Blob 绑定与 DA 结算 | partial（E-local completed） | **否** | `stageE-freeze-20260916T181622Z` | `9da9f378` |
| 6 | F | 性能、费用、统计与消融 | partial（F-local completed） | **否**（仅新增仪器旋钮） | `stageF-freeze-20260916T184017Z` | `ab26edb7` |
| 7 | G | 第三方机制与定量比较 | partial（G-official blocked） | **否**（新增基线合约为对照件，非生产协议，见 §1.7） | `stageG-freeze-20260916T185200Z` | `d1aeba5e` |

> 说明：`configSha256` 每阶段各不相同。原因是解析后的配置含 `--run-id` 覆盖与运行时写入的 `build.nodeVersion` / `pythonVersion`，**配置语义未变**；各阶段均重新冻结，未沿用阶段 A 的哈希。

---

## 2. 逐项说明

### 2.1 变更 ①：阶段 A — 复核与冻结基线

| 项 | 内容 |
|---|---|
| **目的** | 建立可复现、可追溯的实验基线：锁定配置、记录器与 schema，冻结源码树与配置哈希，作为 B–G 的共同起点 |
| **涉及模块/文件** | 新增/既有（2026-09-12 主实现）：`evm/revision/experiment_config.js`、`evm/revision/freeze_experiment.js`、`evm/revision/config/stageA.local.json`、`evm/revision/schemas/run_manifest.schema.json`、`evm/revision/stageA_config.test.js`；复用未改：`experiment_record.js`、`metric_definitions.json`、`schemas/experiment_record.schema.json`、`schemas/experiment_event.schema.json`、`stageA_record.test.js` |
| **实现方案与关键逻辑** | 配置解析 → 依赖快照 → 环境快照 → 源码树哈希 → 冻结清单 `run_manifest.json`；配套 `--validate-only`（只校验不落盘）与续写前校验（历史污染/跨文件断裂/身份不符拒绝续写） |
| **本次会话实际改动** | **无代码改动**（`git diff --stat` 为空）。仅重新跑通验收项并新增 2026-09-16 的本地 self-test run |
| **验证结果** | 冻结状态 ready；21 个 node:test 子测试全部 ok（含哈希不符、符号链接逃逸、锁定拒绝、重复 eventId 等） |
| **依赖** | 无上游；**被 B–G 全部依赖** |

### 2.2 变更 ②：阶段 B — 本地功能安全与资金闭环

| 项 | 内容 |
|---|---|
| **目的** | 在真实合约接口上做功能安全与资金一致性回归，并补齐资金闭环对账用例 |
| **涉及模块/文件** | 新增 `evm/revision/stageB_closure.test.js`；复用既有 `evm/revision/security.test.js`；产出 `handoff.json` / `report_zh.md` / `commands.txt` |
| **实现方案与关键逻辑** | 先跑 before 基线再跑新增用例；`ledger()` 夹具做两级对账；`setNextBlockTimestamp` 做精确边界控制；Sybil 净收益**扣除全部实际 gas** 后计算；产出机器可读 `case_matrix.json` |
| **关键结论** | 三条会计恒等式在所有场景下成立：`balance == locked + totalClaimable`、`balance == totalDeposited − totalWithdrawn − totalBurned`、`totalClaimable <= balance`；金额全部 BigInt 十进制字符串，未用 JS 浮点 |
| **验证结果** | before 基线 23/23；新增 9/9；合计 32 项断言通过；编译合约 8 个 |
| **合约改动** | **无**。既有回归全绿，未发现需修复缺陷，故无最小修复、无经济/timeout 规则变更 |
| **依赖** | 依赖 A；**被 C、E、F、G 依赖**（C 的闸门要求重跑 B 全套） |

### 2.3 变更 ③：阶段 C — 恢复活性、串谋与有界 DoS

| 项 | 内容 |
|---|---|
| **目的** | 在故障、串谋与 DoS 场景下检验活性与终止性，并**如实标注协议能力缺口** |
| **涉及模块/文件** | 新增 `evm/revision/stageC_recovery.test.js`；**扩展（非重写）** `evm/revision/random_security.js`（seed 经 `RANDOM_SEED` 配置，默认保持原固定基线 `0x5eed2026`，输出按 seed 命名避免覆盖原证据）；产出 `case_matrix` / `state_transition_table` / `invariants` |
| **实现方案与关键逻辑** | C01–C17；`assertFactsImmutable` 校验争议事实不可变；`checkInvariants` 检查 INV1–INV7；随机序列多 seed 扩展 |
| **关键逻辑澄清** | `recover()` **仅** `++recoveries` 并 `_touch(timeoutAt)`，**不更换 challenger、不改变收益权、不改变 phase**；真实续跑路径是 `adjudicate`（任何人可调用、无时间门槛、确定性重算）。**`recover` 交易成功 ≠ 恢复完成** |
| **验证结果** | C 阶段 17/17；**B 全套在 C 的 run 下重跑 32/32**（C-completed 闸门）；不变量 5 次检查 0 违反；随机安全 4 seed × 1000 序列全部 `pass=true`（合计 4000 序列 / 109,513 次操作 / 90,843 次 revert 状态检查），原始基线 seed 结果保持不变 |
| **能力缺口（如实标记，非"已完成"）** | ①第三方**经济接管**：`limited`（属显式协议变更，需先说明新增假设与信任影响、取得授权并回归 B，不能在测试中仅换 `msg.sender` 后声称完成）；②提交者失联且无可转发证据时的重新执行：`limited`（只能走 `terminate` 超时结算） |
| **依赖** | 依赖 A、B；**被 F、G 依赖**（F 的消融臂设计、G 的恢复能力字段均沿用 C 的故障模型） |

### 2.4 变更 ④：阶段 D — 真实 TEE 证明与应用执行

| 项 | 内容 |
|---|---|
| **目的** | 建立真实/模拟 TEE 后端的统一契约与策略评估框架，并**不伪造**无硬件条件下的真实 Quote |
| **涉及模块/文件** | 新增 `evm/revision/tee_attestation.js`、`evm/revision/stageD_attestation.test.js`、`outputs/stageD_.../REMOTE_QUOTE_RUNBOOK.md`；产出 `handoff.json` / `report_zh.md` / `commands.txt` |
| **实现方案与关键逻辑** | `BACKEND` 枚举（simulated-hmac / sgx-dcap-real / tdx-dcap-real）与 `REAL_BACKENDS` 隔离；`DECISION` 枚举显式区分 OK / invalid / revoked / out-of-date / configuration-needed / unknown / blocked；`buildReportDataDigest`、`buildTaskBindingDigest`（规范 JSON + sha256）；`detectDevice`；`createProvider` **fail-closed**（真实后端无设备时抛 `DEVICE_UNAVAILABLE`）；`evaluatePolicy`（`realQuote !== true` → blocked） |
| **平台探测结果** | darwin / arm64 / Apple M5；`/dev/sgx_enclave`、`/dev/sgx_provision`、`/dev/sgx/*`、`/dev/tdx_guest`、`/dev/tdx-guest` **均不存在** |
| **验证结果** | D-local **8/8** 通过；12 个 case：verified=5、partial=1、blocked=6（其中 4 个为 fixture 用例，明确不计入真实平台成功样本） |
| **层级状态** | `D-local = completed`；`D-quote / D-application / D-integrated = blocked`（本机无 SGX/TDX 设备） |
| **依赖** | 依赖 A、C；**被 F、G 依赖**（F-TEE 与含 TEE 的定量对照均阻塞于此） |

### 2.5 变更 ⑤：阶段 E — 真实 Blob 绑定与 DA 结算

| 项 | 内容 |
|---|---|
| **目的** | 建立真实 EIP-4844 Blob 编码与单向绑定（无循环承诺），并量化容量/填充阶梯 |
| **涉及模块/文件** | 新增 `evm/revision/stageE_binding.js`、`evm/revision/stageE_local.test.js`；复用 `evm/revision/blobcodec.js`、`evm/revision/kzg.js` |
| **实现方案与关键逻辑** | `MANIFEST_VERSION = "hybrid-tee-rollup.batch-manifest.v1"`；单向构造链：原始任务数据 → `inputDataHash` → `taskCoreDigest`（**不含** manifestHash/versionedHash/DA 引用）→ manifest 与帧 → KZG commitment / versionedHash → 最终签名 envelope；`encodeManifestToBlob` 超容量抛类型化错误 `SINGLE_BLOB_CAPACITY_EXCEEDED`；`verifyM1`、`verifyBlobKzg` |
| **无循环承诺证据** | 同一 task 置于不同 manifest（不同 batchId）时 `coreDigest` 保持不变 → 证明 `coreDigest` 不依赖 `manifestHash`/`versionedHash` |
| **真实密码学证据** | c-kzg **4.1.0**；trusted setup `evm/revision/trusted_setup.txt`（sha256 `d39b9f2d047cc9dca2de58f264b6a094…`）；实际调用 `blobToKzgCommitment` / `computeBlobKzgProof` / `verifyBlobKzgProof`（非模拟）；`versionedHash = 0x01 ‖ sha256(commitment)[1:]` |
| **容量实测** | blobBytes 131072；fieldElements 4096；每 FE 31 数据字节；`maxFrameLen = 126976`；帧开销 79 字节（domain 26 字节）；`maxContentLen = 126897`；**满容量 126976 字节 KZG 验证通过**；**超 1 字节（126977）→ blocked** |
| **验证结果** | E-local **7/7** 通过；19 个 case：verified=5、blocked=14 |
| **阻塞原因** | 核心合约 `BoundedTaskRollup` **当前没有 DA 引用/指针字段** → E-binding 与 E-DA-settlement 需显式协议变更并重跑 B/C；E-public-transport 需 Sepolia RPC、测试币与广播授权 |
| **依赖** | 依赖 A、B、C；**被 F、G 依赖**（F-Blob 与 Blob DA 定量对照阻塞于此） |

### 2.6 变更 ⑥：阶段 F — 性能、费用、统计与消融

| 项 | 内容 |
|---|---|
| **目的** | 修正仪器与统计口径，建立可复现的性能/费用/消融测量；**本阶段默认不改协议机制** |
| **涉及模块/文件** | 新增 `evm/revision/stageF_stats.js`（纯统计，无 IO）、`evm/revision/stageF_stats.test.js`、`evm/revision/stageF_perf.js`（测量 runner）、`evm/revision/stageF_aggregate.js`（raw → 汇总/图表） |
| **实现方案与关键逻辑** | ①**设计先冻结后执行** `design.frozen.json`；②A 每样本一逻辑批不变，跨批汇总另设独立版本化 `hybrid-tee-rollup.stageF.window.v1`（不用 A `experiment_record` 冒充窗口/单样本）；③并发单位 `inflight_batches`，**禁用 `min(batchSize, concurrency)` 折叠**；④单变量筛查（非全笛卡尔积）→ 13 格 + 预设交叉角点；⑤gas/wei 全 BigInt + 十进制字符串；⑥raw 落盘后由独立脚本重建汇总与图表 |
| **仪器旋钮（默认值=主矩阵冻结值）** | `F_CHALLENGE_WINDOW`（默认 100）、`F_ONLY_CELLS`、`F_WARMUP` / `F_MEASURE` / `F_RUNS`、`STAGEF_SMOKE`；**改动后必须先重新冻结再测** |
| **发现并归因的仪器假象** | Hardhat 每块链钟 +1 秒且 automining 串行，固定 `challengeWindow=100`（链秒）在 `batchSize=32` 或 `concurrency=16` 下被越过 → `openChallenge` 大量 `revert 'window'`。已用 `challengeWindow=100000` 归因运行（独立冻结 `d7752e7e…`）确认是**部署参数/仪器假象，非协议吞吐上限**，三格均回到 100% 终局 |
| **验证结果** | 统计 fixture 测试 **12/12**；主矩阵 13 格 × 3 run ×（5 预热 + 30 稳态）+ 4 消融臂 × 3 run ×（2+10）；1509 条 batch 记录（1290 稳态 / 219 预热）、51 条 window 记录、13164 条 task 记录、**重复 taskId = 0**；费用 window 求和 == cell 求和，每个 window `totalFeeWei` == 五项分项之和（0 处不一致）；A schema 回归 21 子测试 ok，B 9/9、C 17/17 在同 run 复跑通过 |
| **依赖** | 依赖 A、B、C；D/E 为 partial → F-TEE / F-Blob / F-full **blocked** |

### 2.7 变更 ⑦：阶段 G — 第三方机制与定量比较

| 项 | 内容 |
|---|---|
| **目的** | 对 TeeRollup / Arbitrum BoLD / Optimism FDG 做来源锁定、可比性分析与同模型机制对照 |
| **涉及模块/文件** | 新增 `evm/contracts/MechanismBaseline.sol`、`evm/revision/stageG_mechanism.js`、`evm/revision/stageG_aggregate.js`；产出 `sources.json` / `mechanism_matrix.json` / `feasibility.json` / `metric_mapping.json` / `comparability_contract.json` / `claim_evidence_matrix.json` / `literature.json` / `citation_locator.md` |
| **关键界定** | `MechanismBaseline.sol` 是**机制基线（mechanism baseline）**，用于同模型对照；**不是** Arbitrum / Optimism / TeeRollup 的任何官方实现，**也不属于本项目生产协议**（详见第三部分 §4 兼容性影响） |
| **基线设计** | 与本方案相同的有界 hash 链模型与 submit/openChallenge/respond/advance 流程，但**去掉 `adjudicate` 兜底重算**，改为"定位后单步证明 `step()`"，超时只能 `terminate()`（判挑战方获胜 → 正确提交方被罚没） |
| **来源锁定（版本固定）** | TeeRollup **arXiv:2409.14647v3**；BoLD **arXiv:2404.10491v1** + `OffchainLabs/bold@30e78f67…`（BSL 1.1、Go 1.24.5）；OP FDG **specs.optimism.io**（访问 2026-09-16）+ `FaultDisputeGame.sol` @ `ethereum-optimism/optimism` `c4a68ab`（MIT、solidity 0.8.15） |
| **验证结果** | L1 实测 7 个（系统×臂）组合 × 3 run，252 条记录（210 稳态）、重复 sampleId = 0、各臂 `totalGas` == per-run 之和；回归 **53 passing**（F 统计 12 + B 9 + C 17 + D 8 + E 7） |
| **依赖** | 依赖 A、F（F-local 与 comparability contract 验收 → G-mechanism 放行）；D/E partial → G-official **blocked** |

---

## 3. 变更间依赖关系

| 上游 | 下游 | 传递的内容 | 若缺失的后果 |
|---|---|---|---|
| A | B / C / D / E / F / G | 配置、记录器、schema、冻结清单、身份约定 | 无基线可比，哈希不可追溯 |
| B | C / E / F / G | 功能安全与资金闭环结论、case_matrix | C 的 32/32 闸门不成立；F 不敢测受影响路径 |
| C | F / G | 故障模型、`recover` 语义澄清、能力缺口标记 | F 的消融臂会漏列"无恢复但有兜底"；G 的恢复能力字段无定义 |
| D | F / G | 真实 TEE 后端契约与设备探测结论 | F-TEE blocked；G 无 TEE 时间对照 |
| E | F / G | Blob codec、容量/填充度量、单向绑定 | F-Blob blocked；Blob 阶梯无来源 |
| F | G | 实测记录、`comparability_contract`、统计口径 | G-mechanism 不放行；无同口径 runner |
| G | — | 机制对照、文献表、claim-evidence | — |

**反向修正（重要）**：G 的源码核实结果要求**回改本文表述**（见 `citation_locator.md`），即 G 对上游表述存在反向约束，但未修改任何生产代码。

---

# 第二部分 · 实验报告

## 1. 实验目的

1. **正确性**：验证有界任务 Rollup（`BoundedTaskRollup`）在功能安全、资金守恒、故障活性与抗 DoS 方面的行为符合设计。
2. **真实性边界**：在真实 TEE（D）与真实 Blob/DA（E）两条外部资源线上，明确"哪些做到了、哪些没做到"，不以模拟或离线结果冒充真实。
3. **可量化**：建立可复现的性能、费用与消融测量体系，并给出具备分母与失败率的指标。
4. **可比较**：在固定版本与固定口径下，与 TeeRollup / BoLD / Optimism FDG 做机制与定量对照，输出可比性标签与禁止性结论。

## 2. 运行环境与依赖版本

| 类别 | 项 | 值 |
|---|---|---|
| 硬件 | 平台 / 架构 / CPU | darwin / arm64 / Apple M5 |
| 硬件 | SGX / TDX 设备节点 | **无**（`/dev/sgx_enclave`、`/dev/sgx_provision`、`/dev/sgx/*`、`/dev/tdx_guest`、`/dev/tdx-guest` 均不存在） |
| 运行时 | Node.js | v22.22.2 |
| 运行时 | Python | 3.13.12（仅用于既有脚本，本轮测量主体为 Node） |
| 运行时 | Go / Foundry | **未安装**（`go: command not found`、`forge not found`） |
| 合约 | Solidity | 0.8.26（G 的官方 FDG 源码为 0.8.15，仅下载未编译） |
| 合约 | 优化器 / viaIR / evmVersion | enabled, runs=200 / true / cancun |
| 链 | 后端 / chainId / hardfork | hardhat in-process / 31337 / cancun |
| 链 | accounts / blockGasLimit / initialBaseFeePerGas | 40 / 60,000,000 / 1 gwei |
| 链 | 出块 | automining（**无真实共识最终性**；每块链钟 +1 秒） |
| 密码学 | c-kzg | 4.1.0 |
| 密码学 | trusted setup | `evm/revision/trusted_setup.txt`，sha256 `d39b9f2d047cc9dca2de58f264b6a094…` |
| 测试 | 框架 | hardhat + mocha（timeout 120000）；A 阶段为 node:test（TAP） |

## 3. 实验设计与验证方法

### 3.1 通用纪律

- **先冻结后测量**：任何代码/参数变更后重新冻结 `sourceTreeSha256` 与 `configSha256`，再执行测量；不沿用阶段 A 的哈希。
- **before 基线 → after 新增**：每个阶段先跑既有回归，再跑新增用例。
- **真实 vs 模拟分层**：`simulated / offline / local / public` 分层记录，禁止跨层冒充。
- **整数记账**：gas 与 wei 全部 BigInt + 十进制字符串，禁止 JS Number 中转与字符串比较大小。
- **分母保护**：分母 0 或未测返回 `null + reason`，不填 0、不填估算。

### 3.2 各阶段设计要点

| 阶段 | 设计要点 |
|---|---|
| A | 配置解析 → 依赖/环境快照 → 源码树哈希 → 冻结清单；续写前校验（污染/断裂/身份不符拒绝） |
| B | 两级会计恒等式 + 精确边界控制 + Sybil 净收益扣 gas |
| C | C01–C17 + INV1–INV7 不变量 + 事实不可变断言；随机安全多 seed（保留原基线 seed） |
| D | fail-closed 后端契约；`DECISION` 显式分状态；`realQuote !== true` → blocked |
| E | 单向承诺链（无循环）；容量下界/刚好上界/超一字节三档；真实 KZG 与篡改拒绝 |
| F | 单变量筛查 → 预设交叉；并发单位 `inflight_batches`；warmup 记录但不入稳态；失败/重试/删失全保留；统计从 raw 重建 |
| G | L1 同模型配对测量；L2 官方可行性清单（未运行）；L3 文献定量表（标 `literature_reported`） |

### 3.3 统计口径（F 与 G 一致）

- cluster 单位 = **独立 run / 批**（批内任务不是独立样本，禁止用批内任务数伪造大样本）。
- 分位算法 nearest-rank；**n < 20 不报 p95，n < 100 不报 p99**。
- **3 个独立 run 不输出 bootstrap CI**（返回 `only_3_independent_runs`），仅描述性。
- 条件于成功的延迟必须与成功率、分母、删失数同时报告。

## 4. 实验结果

### 4.1 功能、安全与资金（A / B / C）

| 指标 | 结果 | 证据 |
|---|---|---|
| A 冻结状态 | ready | `stageA_.../stageA_freeze/manifest/run_manifest.json` |
| A schema 回归 | 21 个 node:test 子测试全部 ok | `stageA_config.test.js` + `stageA_record.test.js` |
| B before 基线 | **23 / 23** 通过 | `hardhat_run/security/security_report.json` |
| B 新增闭环用例 | **9 / 9** 通过 | `hardhat_run/stageB/case_matrix.json` |
| B 会计恒等式 | 3 条恒等式在所有场景成立（BigInt，无浮点） | `handoff.json.fundingClosure` |
| C 新增用例 | **17 / 17** 通过 | `hardhat_run/stageC/case_matrix.json` |
| C 不变量 | INV1–INV7，5 次检查 **0 违反** | `hardhat_run/stageC/invariants.json` |
| C 中 B 回归 | **32 / 32** 通过（C-completed 闸门） | 同 run 复跑 |
| C 随机安全 | 4 seed × 1000 序列 `pass=true`；合计 4000 序列 / 109,513 次操作 / 90,843 次 revert 状态检查；原始基线 seed 结果未变 | `random_security.js` 输出 |

### 4.2 真实资源线（D / E）

| 层级 | 状态 | 关键结果 |
|---|---|---|
| D-local | **completed** | 8/8 测试通过；12 case（verified 5 / partial 1 / blocked 6，其中 4 个 fixture 用例不计入真实平台成功样本） |
| D-quote / D-application / D-integrated | **blocked** | 本机无 SGX/TDX 设备；已给 `REMOTE_QUOTE_RUNBOOK.md`（无杜撰命令） |
| E-local | **completed** | 7/7 测试通过；19 case（verified 5 / blocked 14） |
| E 真实 KZG | 通过 | c-kzg 4.1.0；commitment / proof / verify 均真实调用；versionedHash 格式符合 EIP-4844 |
| E 容量 | 实测 | `maxFrameLen=126976`；`maxContentLen=126897`；满容量 KZG 通过；**126977 字节 → blocked（不缩小、不截断）** |
| E-binding / E-DA-settlement | **blocked** | 核心合约无 DA 引用/指针字段，需显式协议变更并重跑 B/C |
| E-public-transport | **blocked** | 缺 Sepolia RPC、测试币、广播授权 |

### 4.3 性能与消融（F）

**矩阵规模**：13 格 × 3 独立 run ×（5 预热 + 30 稳态）；4 消融臂 × 3 run ×（2 + 10）；共 1509 条 batch / 51 条 window / 13164 条 task 记录。

**主矩阵（3 run 均值，已剔除挑战窗口假象影响的格子另见归因）**

| 格（b=批大小 / p=payload KiB / c=并发 / s=步数） | finalized tasks/s | 批总延迟均值 (ms) | finalized 任务 | 说明 |
|---|---|---|---|---|
| b1-p8-c4-s64 | 144.63 | 22.3 | 90 | |
| **b8-p8-c4-s64（baseline）** | **162.78** | 161.8 | 720 | 基准格 |
| b32-p8-c4-s64 | 5.63 | 575.4 | 93 / 2880 | 96.8% 未终局（见归因） |
| b8-p8-c1-s64 | 128.19 | 53.3 | 720 | |
| b8-p8-c16-s64 | 15.51 | 118.0 | 72 / 720 | 90% 未终局（见归因） |
| b8-p1-c4-s64 | 137.38 | 191.5 | 720 | payload 名义参数 |
| b8-p32-c4-s64 | 138.54 | 188.4 | 720 | payload 名义参数 |
| b8-p8-c4-s1 | **518.75** | 51.8 | 720 | 步数最少 |
| b8-p8-c4-s128 | 83.51 | 309.9 | 720 | 步数最大 |
| b1-p8-c1-s64 | 121.79 | 7.0 | 90 | |
| b1-p8-c16-s64 | 117.19 | 93.8 | 90 | |
| b32-p32-c16-s128 | 9.37 | 777.4 | 288 / 2880 | 90% 未终局（见归因） |
| b1-p1-c1-s1 | 277.13 | 3.0 | 90 | 轻角点 |

**并发差异保留检查**（`batchSize=1`）

| 配置并发 | 观测在途峰值 | 观测在途均值 | finalized tasks/s |
|---|---|---|---|
| 1 | 1 | 1.00 | 121.79 |
| 4 | 4 | 3.83 | 144.63 |
| 16 | **16** | 12.57 | 117.19 |

> 并发未被折叠（峰值达到配置值）；但吞吐**无单调增益** —— Hardhat automining 串行出块，客户端在途可重叠、区块产出不并行。属环境限制，不得外推为生产并发扩展性。

**挑战窗口失败归因**

| 格 | 主运行终局率 | 归因运行（window=100000）终局率 | 归因运行 finalized tasks/s |
|---|---|---|---|
| b32-p8-c4-s64 | 0.032 | **1.0** | 156.93 |
| b8-p8-c16-s64 | 0.100 | **1.0** | 154.04 |
| b32-p32-c16-s128 | 0.100 | **1.0** | 87.07 |

> 失败原因 100% 为 `revert 'window'`（`openChallenge` 时 `block.timestamp > challengeDeadline`）。归因运行仅改部署参数、不改协议机制，独立冻结 `d7752e7e…`。主运行数据**全部保留未删除**，与归因运行分表呈现。

**消融四臂（batchSize=1 / steps=64 / 并发=1，每臂 3 run × 12 批 = 30 稳态批）**

| 策略 | 批总延迟均值 (ms) | adjudicate 类 gas | recover gas | 本地费用合计 (wei) | 交互续推成功 | 兜底使用 |
|---|---|---|---|---|---|---|
| direct-fallback | **7.3** | 3,960,444 | 0 | 14,299,321,100,095,247 | 0/30 | 30/30 |
| no-recovery-with-fault-fallback | 8.7 | 8,150,328 | 0 | 18,489,251,129,424,757 | **0/30** | 30/30 |
| recovery-under-fault | 12.6 | 15,211,236 | 970,644 | 26,520,665,185,644,655 | **30/30** | 0/30 |
| recovery-interactive | 13.5 | 15,211,080 | 0 | 25,550,213,204,401,704 | 30/30 | 0/30 |

> 四臂任务终局率均为 **100%**（30/30 批、36/36 次尝试含预热）—— 因为合约保留了不依赖恢复的 `adjudicate` 兜底。**未关闭兜底来伪造"无恢复必失败"**。
> 配对差异（3 cluster，无 CI）：recovery-under-fault → no-recovery **+3.97 ms**；recovery-interactive → direct-fallback **+6.13 ms**；recovery-under-fault → direct-fallback **+5.30 ms**。

**单位成本（baseline b8-p8-c4-s64，3 run 合计本地费用 286,264,196,290,113,552 wei）**

| 分母 | 单位成本 (wei) |
|---|---|
| per finalized task | 397,589,161,514,046 |
| per accepted task | 397,589,161,514,046 |
| per batch | 3,180,713,292,112,372 |

**Blob 填充阶梯（codec 计算，modelled，非链上实测）**

| taskCount | payload KiB | frame bytes | blobs | 填充率 | 状态 |
|---|---|---|---|---|---|
| 1 | 32 | 32,859 | 1 | 0.2588 | computed（codec 核对通过） |
| 1 | 64 | 65,627 | 1 | 0.5168 | computed（codec 核对通过） |
| 1 | 128 | 131,163（预测） | **2** | 0.5165 | **blocked：超单 Blob 容量** |
| 8 | 32 | 32,943 | 1 | 0.2594 | computed |
| 32 | 32 | 33,231 | 1 | 0.2617 | computed |

> 30 行阶梯中 17 行超出单 Blob 容量，全部标 `blocked`；容量内各行 `predictedFrameBytes == codec` 实际值（`codecVerified=true`）。

### 4.4 机制对照（G）

**L1 同模型实测**（steps=64、batchSize=1、同部署参数、同进程配对、3 run × 12 批）

| 系统 | 臂 | 正确终局 | 错误终局 | 总 gas（3 run） | L1 交易数 |
|---|---|---|---|---|---|
| 本方案 | interactive | **30/30** | 0/30 | 25,918,326 | 360 |
| 本方案 | fault-no-recovery | **30/30** | 0/30 | 18,857,820 | 150 |
| 本方案 | fault-with-recovery | **30/30** | 0/30 | 26,889,540 | 390 |
| 本方案 | direct-no-response | **30/30** | 0/30 | 14,668,132 | 120 |
| 机制基线 | interactive | **30/30** | 0/30 | 20,404,304 | 330 |
| 机制基线 | fault-no-recovery | **0/30** | 30/30 | 13,781,198 | 150 |
| 机制基线 | direct-no-response | **0/30** | 30/30 | 10,490,070 | 120 |

> 配对延迟差（baseline − ours）：interactive −1.20 ms、fault-no-recovery −0.47 ms（3 cluster，无 CI）。
> 解读：去掉兜底重算后，提交方离线时正确终局率从 30/30 掉到 **0/30**（正确提交方被罚没）；代价是本方案交互路径 gas 更高 —— 这是**成本/可用性权衡**，不是单边优势。

**来源与版本锁定**

| 目标 | 固定版本 | artifact | 访问状态 |
|---|---|---|---|
| TeeRollup | arXiv:2409.14647 **v3** | **未找到公开仓库** | 已抓取（abstract + HTML 全文） |
| BoLD | arXiv:2404.10491 **v1** + `OffchainLabs/bold@30e78f67…`（BSL 1.1，Go 1.24.5，18 MB） | 已浅克隆**未执行** | 已抓取 + 已克隆 |
| Optimism FDG | specs.optimism.io（访问 2026-09-16）+ `FaultDisputeGame.sol` @ `c4a68ab`（MIT，solidity 0.8.15，67 KB） | 已下载源码**未运行** | 已抓取 + 已下载 |

**官方实现复现（L2）**

| 目标 | 缺口 | 状态 |
|---|---|---|
| TeeRollup | 无公开仓库/artifact | **blocked** |
| BoLD | 需 Go 1.24.5（本机无）+ bazel；端到端另需 devnet | **blocked** |
| Optimism FDG | 需 foundry/forge（本机无；`foundryup` 属远程安装脚本） | **blocked** |

**文献定量（L3，全部标 `literature_reported`，非本机实测）**

| 目标 | 指标 | 值 | 单位 | 定位 |
|---|---|---|---|---|
| TeeRollup v3 | 吞吐 | ≈28 K | TPS | Sec. VI-C（5 sequencer、batch=2000、LAN） |
| TeeRollup v3 | 峰值延迟 | 119 | ms | Sec. VI-C |
| TeeRollup v3 | WAN 变化 | −15.74% 吞吐 / +20.17% 延迟 | % | Sec. VI-C（20 sequencer） |
| TeeRollup v3 | UpdateState gas | 156,263 | gas | Table IV（ETH/USD 3376.77、19.26 Gwei、2025-01-01） |
| TeeRollup v3 | 摊销后单笔 | 78 gas（0.005 USD） | — | Sec. VI-B（按 2000 笔摊销） |
| TeeRollup v3 | 成本降低 | ≈86%（基线 **StarkNet** 0.043 → 0.006 USD） | % | Sec. VI-D |
| TeeRollup v3 | 挑战等待 τ | several hours（无精确数字） | h | Sec. IV-E |
| BoLD v1 | 终止上界 | `2·(Cmax + D)`，Cmax ≈ 1 周、D = 数小时 | time | Sec. 2.1.1 / 2.2.1 |
| BoLD v1 | 腐/诚成本比 | 10 | ratio | Sec. 2.2.3 |
| BoLD v1 | 诚实方质押 | 1 次聚合断言（对比 Classic 的 M 次） | count | Sec. 2.2.1 |
| BoLD v1 | 具体 gas / 质押面额 | **not_reported** | — | 原文未报 |
| OP FDG | 四个参数（MAX_GAME_DEPTH / SPLIT_DEPTH / MAX_CLOCK_DURATION / CLOCK_EXTENSION） | **not_verified**（部署时 immutable） | — | `FaultDisputeGame.sol:128/132/135/139` |
| OP FDG | 三档时钟延期规则 | `CLOCK_EXTENSION` / `×2`（SPLIT_DEPTH−1）/ `+ oracle().challengePeriod()`（MAX_GAME_DEPTH−1） | rule | `move()` 内分支（源码核实） |

### 4.5 变更前后对比

| 维度 | 变更前（阶段 A 冻结基线） | 变更后（A–G 累计） | 判定 |
|---|---|---|---|
| 生产合约 `BoundedTaskRollup.sol` | 既有实现 | **零改动**（B/C/D/E 明确 `contractChanges: []`；F 未改机制；G 新增的是对照件） | 无兼容性破坏 |
| 安全回归 | 23/23 | 23/23（before 基线）+ 9/9（B 新增）+ 17/17（C 新增）= **49** 项 | 增强 |
| 不变量体系 | 无 | INV1–INV7，0 违反 | 新增 |
| 随机安全 | 1 个固定 seed | 4 个 seed，原基线结果不变 | 增强（可复现性提升） |
| 真实密码学 | 离线 KZG（既有） | c-kzg 4.1.0 真实证明 + 版本/哈希锁定 + 篡改拒绝 | 增强 |
| 测量体系 | 单一 A `experiment_record` | A 单样本语义不变 + 独立版本化 window/mechanism 记录 + 纯统计模块 + 12 项 fixture | 增强（旧 schema 未失效） |
| 归因能力 | 无 | 挑战窗口假象被定位并独立归因验证 | 新增 |
| 第三方对照 | 仅既有文献材料 | 版本锁定 + 源码级证据 + 同模型实测 + claim-evidence 矩阵 | 增强 |
| 协议能力缺口 | 未显式化 | `recover` 非经济接管、合约无 DA 字段 —— 均显式标记 `limited` / `blocked` | 透明度提升 |

## 5. 结论

1. **正确性与资金闭环成立**。三条会计恒等式在所有 B/C 场景成立；C 的 INV1–INV7 零违反；随机安全 4 seed 全通过。
2. **恢复机制的真实作用被量化且为负面结论**。在本有界模型（`MAX_STEPS=128`）中，`adjudicate` 全量重算极廉价，**`recover` 不改善正确终局时间**（12.6 ms vs 兜底 8.7 ms，gas 与本地费用更高）；其唯一价值是让第三方在提交方超时离线后继续**交互**路径（30/30 vs 0/30）。不得宣称"恢复降低结算延迟"。
3. **兜底重算的价值被量化为可用性而非成本**。同模型对照显示：去掉兜底后，提交方离线场景正确终局率 30/30 → **0/30**（正确方被罚没）；代价是交互路径 gas 更高（25.92M vs 20.40M）。这是明确的成本/可用性权衡。
4. **并发瓶颈来自本地出块串行，不是协议并发设计**。峰值在途达到配置值（1/4/16）证明并发未被折叠，但吞吐无单调增益，属 Hardhat automining 环境限制，不可外推。
5. **payload 维度是有界模型的名义参数**。1 KiB 与 32 KiB 吞吐 137.38 vs 138.54 tasks/s，无实质差异；不得据此外推为高频 DApp 通用 TPS。
6. **三个第三方目标均未完成官方运行复现**（TeeRollup 无仓库；缺 Go 1.24.5 与 foundry）。已交付源码级证据、可行性清单与 runbook，**不写"已复现"**。
7. **"第三方接续"不是本文首创**。OP FDG 已有时钟继承 + 三档 `CLOCK_EXTENSION`（源码 `move()` 内核实），相关表述必须修正。
8. **TeeRollup 存在版本差异**：早期版本称实验用 AMD SEV、可容忍至多半数 TEE；v3 为 SGX:TDX:CSV=1:2:2、f 由服务商设定。比较必须固定版本，本轮固定 v3。

## 6. 后续优化计划

| 优先级 | 事项 | 前置条件 | 预期产出 |
|---|---|---|---|
| P0 | 补齐真实 TEE（D-quote 及以上） | 一台带 SGX(DCAP) 或 TDX 的 Linux 机器/已授权远端实例；DCAP SDK、QVL、PCCS 或可访问 Intel PCS | 真实 Quote 生成与验证、TEE 执行时间（解除 F-TEE） |
| P0 | 补齐真实 Blob 发布与独立取回（E-public-transport） | 目标网络与 chainId、钱包地址、交易/Blob 数量、费用上限、最大重试、测试币余额、**明确批准** | 真实 blobGas、取回耗时、可归责 DA 罚没（解除 F-Blob） |
| P1 | 协议变更：为核心合约引入 DA 引用/指针字段 | 先说明新增假设与信任影响并取得授权 | 解除 E-binding / E-DA-settlement，需重跑 B/C 回归 |
| P1 | 协议变更：明确"恢复/接管"语义 | 同上 | 解除 C 的 `limited` 缺口，或正式声明该能力不存在 |
| P1 | 官方实现复现 | Go ≥ 1.24.5（BoLD）；foundry（OP FDG，须先单独授权安装） | L2 component benchmark，须标 `component benchmark` |
| P2 | 多 Blob 分片编码 | 编码器 `encoderMaxBlobs > 1` | 解除 E08 与超容量 blocked |
| P2 | 真实网络下的排队/到达压力实验 | 独立 interval mining 模式并冻结参数 | 开放模型容量（当前为 closed-loop） |
| P3 | Merkle 单步证明路径 | 合约接入且语义可比 | 与有界重算做裁决对照（当前 `not_applicable`） |

---

# 第三部分 · 技术文档

## 1. 整体架构与数据流

### 1.1 分层

```
┌─────────────────────────────────────────────────────────────┐
│ L4 交付层    report_zh.md / handoff.json / commands.txt /     │
│              comparability_contract.json / citation_locator  │
├─────────────────────────────────────────────────────────────┤
│ L3 分析层    stageF_stats.js（纯统计）                        │
│              stageF_aggregate.js / stageG_aggregate.js       │
│              （raw → 汇总 CSV/JSON + SVG，无外部依赖）         │
├─────────────────────────────────────────────────────────────┤
│ L2 测量层    stageF_perf.js（主矩阵 + 消融）                  │
│              stageG_mechanism.js（L1 机制微基准）             │
│              tee_attestation.js（D 后端契约）                 │
│              stageE_binding.js（E Blob 绑定）                 │
├─────────────────────────────────────────────────────────────┤
│ L1 冻结层    experiment_config.js / freeze_experiment.js      │
│              config/stageA.local.json / schemas/*.json        │
├─────────────────────────────────────────────────────────────┤
│ L0 执行层    Hardhat in-process（cancun, chainId 31337,       │
│              automining, 40 accounts）                        │
│              BoundedTaskRollup.sol / MechanismBaseline.sol    │
│              MockTEEVerifier.sol / MockDARegistry.sol         │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心数据流

**任务生命周期（生产协议 `BoundedTaskRollup`）**

```
submit(input, sig, bond)
   └─ 校验 bond / taskId / steps∈[1,128] / version / 签名
   └─ phase = SUBMITTED；challengeDeadline = ts + challengeWindow
        ├─ [无挑战] finalize()  ── 过 challengeDeadline 后按 verdict 结算或销毁
        └─ openChallenge(id, bond)  ── 非提交方、窗口内
             └─ phase = OPEN；absoluteDeadline = ts + (normalTransitions + maxRecoveries) × stepTimeout
                  ├─ respond(trace)  [仅提交方，可选诊断]
                  │    └─ advance()*  ── 二分定位（任何人可调用）
                  │         └─ replay() → phase = VERIFIED → settle()
                  ├─ recover()  ── 任何人；仅 ++recoveries 与 _touch(timeoutAt)，不改 phase/challenger
                  ├─ adjudicate()  ── 任何人、任何时刻、无时间门槛 → 确定性重算 → _settle（兜底）
                  └─ terminate()  ── 超时后按计算结果判责
```

**E 阶段 Blob 单向绑定链（无循环）**

```
原始任务数据 → inputDataHash → taskCoreDigest（不含 manifestHash/versionedHash/DA 引用）
    → manifest + frame → KZG commitment / versionedHash → 最终签名 envelope
```

**F/G 测量数据流**

```
design.frozen.json（先冻结） → runner → raw/*.jsonl（batch / window / task / mechanism）
    → aggregate.js（独立重建） → summary/*.json|csv + figures/*.svg
    → validation.json（总数、身份去重、费用一致性、图表=表格）
```

## 2. 接口与配置说明

### 2.1 生产合约主要接口（`BoundedTaskRollup.sol`）

| 方法 | 调用者限制 | 时间门槛 | 语义 |
|---|---|---|---|
| `submit(input, sig)` payable | 任何（须自签） | 无 | 提交任务并押 bond |
| `openChallenge(id)` payable | 非提交方 | `ts <= challengeDeadline` | 开启争议 |
| `respond(id, trace)` | **仅提交方** | `_live` | 可选诊断，非义务 |
| `advance(id)` | **无限制** | `_live` | 二分定位推进 |
| `recover(id)` | **无限制** | `ts > timeoutAt && ts < absoluteDeadline`；`recoveries < maxRecoveries(≤2)` | 仅续期与计数，**不接管、不改 phase** |
| `replay(id)` | **无限制** | `_live`；phase=READY | 触发链上重算 |
| `adjudicate(id)` | **无限制** | **无** | 绕过定位直接重算并结算（兜底） |
| `settle(id)` | **无限制** | phase=VERIFIED | 结算 |
| `terminate(id)` | **无限制** | 超时后 | 按计算结果判责 |
| `finalize(id)` | **无限制** | 过 `challengeDeadline` 且 phase=SUBMITTED | 无挑战终局 |
| `withdraw(recipient)` | 有 claimable | 无 | 实际支付（重入保护） |

### 2.2 关键配置

| 配置 | 位置 | 本轮取值 | 说明 |
|---|---|---|---|
| Hardhat 编译 | `evm/revision/hardhat.config.js` | solidity 0.8.26、viaIR、`optimizer.runs=200`、evmVersion cancun | 编译相关，**不得改动后不重新冻结** |
| 网络 | 同上 | hardhat、chainId 31337、cancun、accounts 40、blockGasLimit 60,000,000、initialBaseFeePerGas 1 gwei | |
| 输出根 | 环境变量 `REVISION_RUN` | **必须是绝对路径的独立输出目录** | 否则 hardhat 直接抛错 |
| A 配置 | `evm/revision/config/stageA.local.json` | 见 `manifest/config.resolved.json` | 各阶段复用，语义未变 |
| 随机 seed | `RANDOM_SEED` | 默认 `0x5eed2026` | 输出按 seed 命名，不覆盖原证据 |
| F 仪器旋钮 | `F_CHALLENGE_WINDOW` / `F_ONLY_CELLS` / `F_WARMUP` / `F_MEASURE` / `F_RUNS` / `STAGEF_SMOKE` | 默认 100 / null / 5 / 30 / 3 / 0 | **改动必须先重新冻结再测** |
| Blob domain | `blobcodec.js` `DOMAIN_DEFAULT` | `hybrid-tee-rollup/batch/v1`（26 字节） | 决定帧开销 79 字节 |

### 2.3 产物 schema

| Schema | 版本串 | 用途 |
|---|---|---|
| batch 记录 | `hybrid-tee-rollup.stageF.batch.v1` | 单逻辑批样本（taskCount = batchSize） |
| window 记录 | `hybrid-tee-rollup.stageF.window.v1` | 跨批窗口聚合（**独立于 A `experiment_record`**） |
| task 记录 | `hybrid-tee-rollup.stageF.task.v1` | 任务身份，用于去重与跨窗口归属 |
| mechanism 记录 | `hybrid-tee-rollup.stageG.mechanism.v1` | L1 机制微基准 |
| design | `hybrid-tee-rollup.stageF.design.v1` / `stageG.mechanism-design.v1` | 先冻结的实验设计 |

## 3. 使用方式

### 3.1 前置

```bash
cd /Users/shanse/Documents/ChatGPT/Hybrid\ TEE-Rollup
node -v            # v22.22.2
# 注意：hardhat 二进制在本机存在权限问题，统一用 node 直接调用 CLI
```

### 3.2 冻结一个测量版本

```bash
node evm/revision/freeze_experiment.js \
  --config evm/revision/config/stageA.local.json \
  --run-dir "<绝对路径>/stageX_freeze" \
  --run-id "stageX-freeze-<UTC时间戳>"
# 只校验不落盘：追加 --validate-only
```

### 3.3 运行测试

```bash
cd evm
REVISION_RUN="<绝对路径>/hardhat_run" \
  node ./node_modules/hardhat/internal/cli/cli.js test --config revision/hardhat.config.js \
  revision/<target>.test.js
```

| 目标 | 命令中的文件 | 通过数 |
|---|---|---|
| A schema | `stageA_config.test.js` `stageA_record.test.js` | 21 子测试 ok（TAP） |
| B | `security.test.js` `stageB_closure.test.js` | 23 + 9 |
| C | `stageC_recovery.test.js` | 17 |
| D | `stageD_attestation.test.js` | 8 |
| E | `stageE_local.test.js` | 7 |
| F 统计 | `stageF_stats.test.js` | 12 |
| 全量回归 | 上述 B–F 组合 | 53 |

### 3.4 运行测量

```bash
cd evm
# F 全量（13 格 × 3 run）
REVISION_RUN="<abs>/hardhat_run" F_RUN_ID=stageF-local \
  node ./node_modules/hardhat/internal/cli/cli.js run --config revision/hardhat.config.js revision/stageF_perf.js

# F 冒烟（与足量测量分开，仅验证正确性）
STAGEF_SMOKE=1 F_RUN_ID=stageF-smoke ...（同上）

# G 机制微基准
REVISION_RUN="<abs>/hardhat_run" \
  node ./node_modules/hardhat/internal/cli/cli.js run --config revision/hardhat.config.js revision/stageG_mechanism.js
```

### 3.5 从 raw 重建汇总与图表

```bash
node evm/revision/stageF_aggregate.js "<abs>/hardhat_run/stageF"
node evm/revision/stageG_aggregate.js "<abs>/hardhat_run/stageG"
# 输出：summary/*.json|csv、figures/*.svg（纯 SVG，无外部依赖）
```

### 3.6 完整命令集

每个阶段目录下的 `commands.txt` 均为**本机实际执行并验证过**的命令序列（含冻结、测量、聚合、回归），可直接复现。

## 4. 兼容性影响

| 项 | 影响 | 说明 |
|---|---|---|
| 生产合约 ABI / 存储布局 | **无影响** | B/C/D/E 明确 `contractChanges: []`；F 仅新增仪器旋钮；**未修改任何生产合约** |
| A 记录 schema | **无影响** | F 采用"保留旧 schema + 新增独立版本化 window/mechanism 记录"，A 的 21 个子测试全部 ok |
| 既有测试 | **无影响** | 新增 `MechanismBaseline.sol` 后回归 53 passing（F 12 + B 9 + C 17 + D 8 + E 7） |
| `MechanismBaseline.sol` | **新增文件，非生产依赖** | 仅被 `stageG_mechanism.js` 部署用于对照；生产协议不引用、不依赖；**不属于 Arbitrum/Optimism/TeeRollup 任何官方实现** |
| 随机安全证据 | 向后兼容 | 默认 seed 保持 `0x5eed2026`，输出按 seed 命名，原始基线证据未被覆盖 |
| 目录约定 | 无破坏 | 所有输出落在 `outputs/stageX_<UTC>/` 独立目录，互不覆盖 |
| Git | 无提交 | 全程未 commit / push；工作区仍为 `gitDirty=true` |

## 5. 风险点与已知限制

### 5.1 环境类（不可通过本轮工作消除）

| # | 风险/限制 | 影响 | 当前处置 |
|---|---|---|---|
| R1 | Hardhat automining **无真实共识最终性** | 不报告最终性延迟；吞吐不可外推为公网 TPS | 已在 `comparability_contract` 明示 |
| R2 | 每块链钟 +1 秒且出块串行 | 固定 `challengeWindow` 在高负载下被越过 | 已定位并独立归因；建议后续测量显式放大该参数或改用 interval mining |
| R3 | 负载模型为 **closed-loop** | 不能宣称无限到达压力下的容量 | 已明示；开放模型实验列入 P2 |
| R4 | 本机无 SGX/TDX | D-quote 及以上、F-TEE blocked | 已出 runbook，待硬件/授权 |
| R5 | 本机无 Go / foundry | G-official blocked | 已出 runbook，待授权安装 |
| R6 | 无公网 RPC / 测试币 / 广播授权 | E-public-transport、F-Blob、F-full blocked | 未做任何广播 |

### 5.2 协议类（需显式变更才能解除）

| # | 限制 | 证据 | 解除条件 |
|---|---|---|---|
| R7 | `recover` **不做经济接管**（不改 challenger / 收益权 / phase） | C02/C03/C04 标 `limited` | 需说明新增假设与信任影响、取得授权、重跑 B |
| R8 | 核心合约**无 DA 引用/指针字段** | E-binding / E-DA-settlement blocked | 需协议变更并重跑 B/C |
| R9 | `encoderMaxBlobs = 1` | E08 与超容量用例 blocked | 需多 Blob 编码实现 |
| R10 | 未接入 Merkle 单步证明 | 裁决对照 `not_applicable` | 需实现且语义可比 |

### 5.3 结论类（禁止性约束，违反会导致错误主张）

| # | 约束 | 原因 |
|---|---|---|
| C1 | 禁止"比 OP/Arbitrum 快 N 倍" | 端点语义与窗口参数不同 |
| C2 | 禁止"比 TeeRollup 省 X%" | 对方基线是 StarkNet |
| C3 | 禁止"首创第三方接续" | OP FDG 已有时钟继承 + `CLOCK_EXTENSION` |
| C4 | 禁止"恢复降低结算延迟" | 实测相反（12.6 ms vs 8.7 ms） |
| C5 | 禁止跨层（实测/文献/modelled）生成统一百分比 | 分母与语境不同 |
| C6 | 禁止把机制基线称为官方实现 | 基线与官方系统设计差异显著 |
| C7 | 禁止用批内任务数当独立样本量 | cluster 必须是独立 run/批 |

### 5.4 统计不确定性

- 每格 **3 个独立 run**：不报 p99、不输出 bootstrap CI，仅描述性差异。
- **未做图估读**（TeeRollup Fig. 3 曲线值不在正文），不产生估读数字。
- Ablation 与 L1 的样本计划（2 预热 + 10 稳态）小于主矩阵（5 + 30），故障注入因全局时间推进强制串行，已在设计中预先声明原因。

## 6. 待补充清单

以下项本轮**未测/未核实**，明确标注为**待补充**，不得臆造：

| # | 待补充项 | 状态 | 需补充的条件 |
|---|---|---|---|
| T1 | 真实货币费用（法币 / 主网 wei） | 待补充 | E-public-transport 验收 |
| T2 | `blobGasUsed` / `blobGasPrice` 与 Blob 实付成本 | 待补充 | 同上 |
| T3 | TEE 执行/证明时间、真实 Quote 验证延迟 | 待补充 | D-quote 验收 |
| T4 | 共识最终性延迟、p99 尾延迟 | 待补充 | 真实网络 + 更大独立 run 数 |
| T5 | Optimism FDG 生产部署参数（`MAX_GAME_DEPTH` / `SPLIT_DEPTH` / `MAX_CLOCK_DURATION` / `CLOCK_EXTENSION` / `challengePeriod`） | 待补充（当前 `not_verified`） | 查询目标链部署配置或官方部署说明 |
| T6 | TeeRollup 官方实现/artifact | 待补充（当前 **未找到**） | 作者公开仓库或提供 artifact |
| T7 | TeeRollup IEEE TC 期刊版的卷期/页码 | 待补充（仅检索命中，未逐页抓取） | 访问期刊页面 |
| T8 | opML / Dynamic Fraud Proof / LazyLedger 的就近引用来源 | 待补充（本轮未扩大范围） | 明确需要后补充 |
| T9 | BoLD 的 DA 载体与披露义务细节 | 待补充（`not_verified`） | 扩展检索范围至 Nitro/BoLD 完整文档 |
| T10 | 开放模型（open-loop）到达压力下的容量 | 待补充 | 独立 interval mining 模式实验 |
| T11 | 多 Blob 分片下的填充阶梯实测 | 待补充 | `encoderMaxBlobs > 1` |
| T12 | `MechanismBaseline` 之外的其他机制基线（如不同裁决路径组合） | 待补充 | 明确对照维度后扩展 |

---

## 附录 A · 各阶段产物索引

| 阶段 | 目录 | 关键文件 |
|---|---|---|
| A | `outputs/stageA_20260916T162724Z/` | `implementation_report.md`、`stageA_freeze/manifest/run_manifest.json` |
| B | `outputs/stageB_20260916T171758Z/` | `handoff.json`、`report_zh.md`、`commands.txt`、`hardhat_run/stageB/case_matrix.json` |
| C | `outputs/stageC_20260916T174457Z/` | `handoff.json`、`report_zh.md`、`commands.txt`、`hardhat_run/stageC/{case_matrix,state_transition_table,invariants}.json` |
| D | `outputs/stageD_20260916T180557Z/` | `handoff.json`、`report_zh.md`、`commands.txt`、`REMOTE_QUOTE_RUNBOOK.md`、`hardhat_run/stageD/case_matrix.json` |
| E | `outputs/stageE_20260916T181622Z/` | `handoff.json`、`report_zh.md`、`commands.txt`、`hardhat_run/stageE/{case_matrix,trusted_setup}.json` |
| F | `outputs/stageF_20260916T184017Z/` | `handoff.json`、`report_zh.md`、`commands.txt`、`comparability_contract.json`、`hardhat_run/stageF/{design.frozen.json,raw/,summary/,figures/}`、`attribution/` |
| G | `outputs/stageG_20260916T185200Z/` | `handoff.json`、`report_zh.md`、`commands.txt`、`citation_locator.md`、`sources.json`、`mechanism_matrix.json`、`feasibility.json`、`metric_mapping.json`、`comparability_contract.json`、`claim_evidence_matrix.json`、`literature.json`、`official/`、`hardhat_run/stageG/` |

## 附录 B · 新增代码文件清单

| 文件 | 阶段 | 角色 | 是否生产代码 |
|---|---|---|---|
| `evm/revision/stageB_closure.test.js` | B | 资金闭环补充测试 | 否（测试） |
| `evm/revision/stageC_recovery.test.js` | C | 恢复/串谋/DoS 测试 | 否（测试） |
| `evm/revision/random_security.js` | C | 随机安全（扩展） | 否（测试工具） |
| `evm/revision/tee_attestation.js` | D | TEE 后端契约 | 否（库） |
| `evm/revision/stageD_attestation.test.js` | D | D-local 测试与状态登记 | 否（测试） |
| `evm/revision/stageE_binding.js` | E | Blob 绑定与容量度量 | 否（库） |
| `evm/revision/stageE_local.test.js` | E | E-local 测试 | 否（测试） |
| `evm/revision/stageF_stats.js` | F | 纯统计模块（无 IO） | 否（分析） |
| `evm/revision/stageF_stats.test.js` | F | 统计 fixture 测试 | 否（测试） |
| `evm/revision/stageF_perf.js` | F | 测量 runner | 否（测量） |
| `evm/revision/stageF_aggregate.js` | F | raw → 汇总/图表 | 否（分析） |
| `evm/contracts/MechanismBaseline.sol` | G | **机制基线（对照件）** | **否**（对照用，非生产协议） |
| `evm/revision/stageG_mechanism.js` | G | L1 机制微基准 runner | 否（测量） |
| `evm/revision/stageG_aggregate.js` | G | raw → 汇总/图表 | 否（分析） |
