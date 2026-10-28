# 【G 阶段】TeeRollup、Arbitrum、Optimism 的公平比较 — 实施报告

- 阶段状态：**G-source = completed；G-feasibility = completed；G-mechanism = completed；G-official = blocked；G-literature = completed；整体 = partial**
- 冻结版本：runId `stageG-freeze-20260916T185200Z`
  - `sourceTreeSha256 = d1aeba5e04c17bb9d03d05a4e764073a19f0227f807f8dd49a6128ae94be8703`
  - `configSha256 = a0fdc46f7cb6b15d967c1d519c3b5bcb5e9257ee93a53341925c8a1f5b9a8f12`
- 前置引用：A `stageA_20260916T162724Z`；F `stageF_20260916T184017Z`（F-local completed，comparability contract 已验收 → **G-mechanism 放行**）
- 未做：未 commit/push、未改论文正文、未执行远程安装脚本、未安装重量级工具链、未做公网交易

---

## 1. G-source：来源与版本锁定（§G1）

| 目标 | 固定版本 | 访问状态 | artifact |
|---|---|---|---|
| TeeRollup | arXiv:2409.14647 **v3**（v1 2024-09-23 / v2 2025-01-04 / v3 2025-11-30） | 已抓取（abstract + HTML 全文） | **未找到公开仓库**（blocked） |
| BoLD | arXiv:2404.10491 **v1**（2024-04-16）+ OffchainLabs/bold @ `30e78f67` | 已抓取 + 已浅克隆（18 MB） | 已克隆**但未执行** |
| Optimism FDG | specs.optimism.io FDG（访问 2026-09-16）+ `FaultDisputeGame.sol` @ ethereum-optimism/optimism `c4a68ab`（2026-09-16T17:40:01Z，MIT，solidity 0.8.15） | 已抓取 spec + 已下载官方源码 | 源码已定位**但未运行** |

**回源核对结果**（对既有项目材料）：
- `audit/citations_zh.md`：三个主目标的版本与 URL 均与一手来源一致 ✓
- `external_research/comparison_report_zh.md`：Table IV gas 与汇率、86%（基线 StarkNet）、28 KTPS/119 ms、τ=several hours、BoLD 2·(Cmax+D)、10×、诚实方 1 次质押 —— **均与 v3/v1 原文一致** ✓
- **本轮补充的既有材料缺口**（见 `sources.json.existingProjectMaterialsCheck.gapsFound`）：
  1. TeeRollup **无公开仓库/artifact**；
  2. TeeRollup **早期版本与 v3 在实验平台与容挫表述上不一致**（早期版本称实验用 AMD SEV、可容忍至多半数 TEE；v3 为 SGX:TDX:CSV = 1:2:2、f 由服务商设定）→ 比较必须固定版本，本轮固定 v3；
  3. OP FDG 的 spec 参数名与生产取值需区分，本轮标 `not_verified`，不填数值。

---

## 2. G2：机制与可比性矩阵（三目标 + 本方案）

`mechanism_matrix.json` 按九个维度填写，字段一律用 `supported / supported_with_source / not_supported_with_source / not_verified / not_applicable` 标记，**没有材料的一律 `not_verified`，不填「不支持」**。

三个必须重点核对的既有机制（避免误称首创）：

1. **OP FDG 的第三方接续确实存在**（`supported_with_source`）
   - spec §Game Clock：claim 继承祖父 claim 的时钟；若继承后剩余不足 `CLOCK_EXTENSION`，补足到 `CLOCK_EXTENSION`（普通）、`CLOCK_EXTENSION × 2`（`SPLIT_DEPTH-1`，留给链下 FPVM 生成轨迹）、`CLOCK_EXTENSION + oracle().challengePeriod()`（`MAX_GAME_DEPTH-1`，含 LPP 挑战期）。
   - 源码定位：`move()` 内 `getChallengerDuration` 与三档延期分支；到期 `revert ClockTimeExceeded()`。
   - spec 明写该机制是为「challenger must inherit a malicious party's clock when countering a freeloader claim」而设。
   - **结论：本方案不得宣称「第三方接续/动态争议参与」为首创。**
2. **BoLD 的动态协议图与本地计时器**（`supported_with_source`）：终止上界 `2·(Cmax+D)`，与参与方数量无关；任意数量腐败方，只需 1 个诚实方。
3. **TeeRollup 的 TEE 不可用兜底**（`supported_with_source`）：challenge 后若 τ（several hours）内无响应，客户端可直接从 TSC 退款。

可检验问题（写成问题而非预设优越）已列入 `mechanism_matrix.json.testableQuestions`：固定争议事实下的接续状态、期限上界与攻击者成本、接续者所需数据/权限、额外开销、受益的故障分布。

---

## 3. G3 · L1：同计算模型机制微基准（**已实测**）

- 对照双方：**本方案 `BoundedTaskRollup`** vs **机制基线 `MechanismBaseline`**（明确命名为 mechanism baseline，**不是** Arbitrum/Optimism/TeeRollup，也不属生产协议）。
- 基线设计：与本项目相同的有界 hash 链模型与 submit/openChallenge/respond/advance 流程，但**去掉 `adjudicate` 兜底重算**，改为「定位后单步证明 `step()`」，超时只能 `terminate()`（判挑战方获胜 → 正确提交方被罚没）。
- 同口径：steps=64、batchSize=1、concurrency=1、同部署参数（bond=1e15 wei、stepTimeout=10、challengeWindow=100000 以消除 F 已归因的链钟窗口假象）、同一进程内配对、3 独立 run ×（2 预热 + 10 稳态）。

| 系统 | 臂 | 正确终局 | 错误终局 | 总 gas（3 run） | L1 交易数 |
|---|---|---|---|---|---|
| 本方案 | interactive | **30/30** | 0/30 | 25,918,326 | 360 |
| 本方案 | fault-no-recovery | **30/30** | 0/30 | 18,857,820 | 150 |
| 本方案 | fault-with-recovery | **30/30** | 0/30 | 26,889,540 | 390 |
| 本方案 | direct-no-response | **30/30** | 0/30 | 14,668,132 | 120 |
| 机制基线 | interactive | **30/30** | 0/30 | 20,404,304 | 330 |
| 机制基线 | fault-no-recovery | **0/30** | 30/30 | 13,781,198 | 150 |
| 机制基线 | direct-no-response | **0/30** | 30/30 | 10,490,070 | 120 |

- 配对延迟差（baseline − ours，独立 run 为 cluster）：interactive −1.20 ms、fault-no-recovery −0.47 ms；**3 个 cluster 不给 CI**（`only_3_independent_runs`）。
- 校验：252 条记录（210 稳态）、重复 sampleId = 0、各臂 totalGas = per-run 之和 ✅。
- **结论（含代价，非单边优势）**：兜底重算的价值被量化为「提交方离线时正确终局率 30/30 → 0/30」；代价是交互路径 gas 更高（25.92M vs 20.40M）。这是一次明确的**成本 / 可用性权衡**，不是「本方案更省」。

---

## 4. G3 · L2：官方实现或 artifact 复现 — **blocked**

| 目标 | 缺口 | 本地可行性 | 状态 |
|---|---|---|---|
| TeeRollup | 无公开仓库 | — | blocked（artifact not_found） |
| BoLD | 需 **Go 1.24.5**（本机 `go: command not found`）+ bazel；端到端还需 devnet；许可为 **BSL 1.1**（非完全开源） | 克隆成功（18 MB），未构建 | blocked |
| Optimism FDG | 需 **foundry/forge**（本机无）；安装通常需执行远程脚本 `foundryup` | 官方源码已下载并逐行定位 | blocked |

- 本轮**未执行任何远程安装脚本、未安装重量级工具链**（属重量级依赖，本轮未获授权）。
- 已取得的**非运行**证据：BoLD 的许可/依赖/测试入口清单；FDG 的关键机制源码定位（时钟继承、三档延期、单步、结算、预映像）。
- `feasibility.json` 给出每个目标在工具链可用后的**完整 runbook 命令**；并明确：仅跑单元 fixture 必须标 `component benchmark`，不代表整条 Rollup TPS。
- **不写「已复现」。**

---

## 5. G3 · L3：文献定量表

`literature.json` 全部标 `literature_reported`，保留原始环境、网络、任务模型、指标定义、单位、章节/表号：

- TeeRollup v3：Table IV（Deposit 48,551 / UpdateState 156,263 / StartChallenge 47,118 / ResolveChallenge 146,618 / SettleRollup 29,078 / SettleWithdraw 124,511 gas；折算价 ETH/USD 3376.77、19.26 Gwei、2025-01-01）；28 KTPS、119 ms、>5000 TPS、WAN −15.74%/+20.17%；86%（**基线 StarkNet**）；τ=several hours。未报字段（样本量、尾延迟、失败率、DA 实际字节与成本、保证金面额）一律 `not_reported`。
- BoLD v1：`2·(Cmax+D)`（Cmax≈1 周、D 数小时）、10× 腐/诚成本比、诚实方 1 次质押；gas 与质押面额 `not_reported`。
- OP FDG：四个 immutable 参数与三档延期**规则**（源码核实），生产取值 `not_verified`；常见「7 天挑战期」属部署配置/第三方分析，本轮**未核实不填**。
- **未做图估读**（Fig. 3 曲线值不在正文），不产生估读数字。

---

## 6. G4：四类主比较指标的口径冻结

`metric_mapping.json` 已冻结定义，关键是**禁止不同单位的行自动合并**：

- **提交成本**：拆 normalSubmitGas / DA gas+bytes / verificationGas / 链下 TEE 时间 / 货币费用；分母（批 / task / transaction）不混用；本轮 DA 与货币费用为 `null + reason`（E/F blocked），**不填 0**。
- **挑战轮数**：逻辑交互轮（`ceil(log2(steps+1))`，64 步=7、128 步=8）/ 单方 move（`interactiveMoves`）/ L1 交易数（`txCount`）/ DAG edge（本方案 `not_applicable`）**互不等价，不得相除**。
- **恢复能力**：按 C 故障模型字段（谁失联、在哪一步、第三方证据、能否接管、保留状态、最大恢复次数、最大延迟、最后责任方、资金结果），禁止用单一 yes/no 排名。
- **结算延迟**：六个端点分列；自定义短挑战窗口**不得**与生产挑战期比「快 N 倍」，短参数 devnet 与部署参数上界分表。

---

## 7. G5：结论、证据与统计

`claim_evidence_matrix.json` 共 11 条，含**负面与修正性结论**：

| ID | 结论 | 极性 | 可比级别 |
|---|---|---|---|
| G-CE-01 | 去掉兜底重算后，提交方离线时正确终局率 30/30 → 0/30 | 正面 | comparable（L1） |
| G-CE-02 | **recover 不改善正确终局时间**（12.6 ms vs 兜底 8.7 ms，gas 更高） | **负面** | comparable |
| G-CE-03 | **不得宣称「第三方接续」首创**（OP FDG 已有时钟继承+延期） | **修正** | not_applicable（机制存在性） |
| G-CE-04 | TeeRollup 86% 基线是 StarkNet | 修正 | not_directly_comparable |
| G-CE-05 | BoLD 10× 是腐/诚成本比 | 修正 | not_directly_comparable |
| G-CE-06 | 本地 gas 不能与生产美元账单算领先比例 | 修正 | partially_comparable |
| G-CE-07 | payload 是名义参数（137.38 vs 138.54 tasks/s） | 负面 | comparable |
| G-CE-08 | 并发 1/4/16 无单调增益（121.79/144.63/117.19） | 负面 | comparable |
| G-CE-09 | Blob 填充阶梯为 codec 计算 | 中性 | **modelled** |
| G-CE-10 | 未复现任何官方实现 | blocked | not_applicable |
| G-CE-11 | TeeRollup 版本间表述不一致 | 注意 | not_applicable |

`unsupportedClaimsFlagged` 明确列出 4 条禁止使用的表述（比 OP/Arbitrum 快 N 倍、比 TeeRollup 省 X%、首创第三方接续、恢复降低延迟）。

统计口径与 F 完全一致：cluster = 独立 run/批，nearest-rank 分位，n<20 不报 p95，3 run 不输出 CI，删失与失败全部保留。

---

## 8. 产出清单

```
outputs/stageG_20260916T185200Z/
├── handoff.json  report_zh.md  commands.txt  citation_locator.md
├── sources.json  mechanism_matrix.json  feasibility.json
├── metric_mapping.json  comparability_contract.json
├── claim_evidence_matrix.json  literature.json
├── stageG_freeze/                        # 冻结清单 + 机制运行日志
├── official/
│   ├── bold@30e78f67…                   # 官方仓库浅克隆（未执行）
│   └── optimism_src/FaultDisputeGame.sol # @ c4a68ab（未运行）
└── hardhat_run/stageG/
    ├── mechanism_design.frozen.json
    ├── raw/mechanism/mechanism_records.jsonl
    ├── summary/{mechanism_summary.json|csv, mechanism_validation.json}
    └── figures/{fig_g_correct_finality.svg, fig_g_gas.svg}
```

新增代码：`evm/contracts/MechanismBaseline.sol`（机制基线，**非生产协议**）、`evm/revision/stageG_mechanism.js`（L1 runner）、`evm/revision/stageG_aggregate.js`（raw→汇总/图表）。

---

## 9. 本阶段没有做到/没有测到的项

1. **G-official = blocked**：三个官方目标均未运行（TeeRollup 无仓库；BoLD 缺 Go 1.24.5；FDG 缺 foundry）。
2. 无真实货币费用、无 blobGas、无 TEE 执行时间（D/E 未验收）。
3. 未做公网交易、未请求付费资源、未执行远程安装脚本。
4. 未把机制基线冒充任何官方系统；基线仅覆盖「无兜底重算 + 单步证明」这一个维度，不代表 BoLD/FDG 的完整设计。

## 10. 给作者的引文定位建议

见 `citation_locator.md`：三个一手来源的建议引用格式与可用数字/定位、六条建议修正的本文表述、自证实验的引用位置与必须标注的限制，以及应保留为「未核实/缺口」的表述。**未直接修改论文正文。**
