# 供作者回填的引文定位建议（**不直接修改论文正文**）

> 原则：每条建议给出「可在论文哪个位置引用 / 应写成什么 / 证据在哪」。
> 所有数字必须带来源与单位；literature 与 measured 分层，不得混写。

---

## 1. 建议新增/修正的引用

### R1 — TeeRollup（一手来源，版本必须写死）

- 建议引用格式：
  > X. Wen, Q. Feng, H. Lyu, J. Niu, Y. Zhang, C. Feng, “TeeRollup: Efficient Rollup Design Using Heterogeneous TEE,” arXiv:2409.14647 **v3**, Nov. 30, 2025.
- 可用数字与定位（**均为 literature_reported**）：
  - 实验设置：20 节点，SGX:TDX:CSV = 1:2:2，阿里云 ECS g7t/8i/g7h；LAN RTT 0.5±0.03 ms、WAN RTT 25±0.1 ms — Sec. VI-A、Table III
  - 吞吐 ≈28 KTPS、峰值延迟 119 ms（5 sequencer、batch=2000、LAN）— Sec. VI-C
  - Table IV gas：UpdateState 156,263；StartChallenge 47,118；ResolveChallenge 146,618；SettleRollup 29,078；SettleWithdraw 124,511（按 ETH/USD 3376.77、19.26 Gwei、2025-01-01 折算）
  - 摊销后 78 gas（0.005 USD）/笔；平均 0.006 USD/笔（batch=2000）— Sec. VI-B / VI-D
  - 「86%」的完整表述：**相比 StarkNet（0.043 USD → 0.006 USD）** — Sec. VI-D
- **必须避免**：写成「比 Optimism/Arbitrum 快/省 X%」；把 v1 的「容忍半数 TEE / AMD SEV」与 v3 混用。

### R2 — BoLD（一手来源）

- 建议引用格式：
  > M. Alvarez et al., “BoLD: Fast and Cheap Dispute Resolution,” arXiv:2404.10491, Apr. 16, 2024.
- 可用数字与定位：
  - 终止上界 `2·(Cmax + D)`，Cmax ≈ 1 周、D = 数小时 — Sec. 2.2.1 / 2.1.1
  - 腐败方聚合成本可达诚实方 10 倍（质押 + L1 gas）— Sec. 2.2.3
  - 诚实方聚合只需 1 次质押断言（对比 Arbitrum Classic 的 M 次）— Sec. 2.2.1 / 2.1.2
  - 假设「至少一个诚实方参与」；腐败方数量无上限 — Sec. 1、Sec. 3
- **必须避免**：把「10×」写成跨协议领先百分比；凭空补 gas 或质押面额（原文未报）。

### R3 — Optimism Fault Dispute Game（官方 spec + 源码）

- 建议引用格式（spec 为动态文档，建议写访问日期）：
  > “Fault Dispute Game,” OP Stack Specification, specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html, accessed Sep. 16, 2026.
  > （如需固定版本）`FaultDisputeGame.sol`, ethereum-optimism/optimism, commit `c4a68ab`, MIT.
- 可用的**源码级**证据（本轮已逐行核实，非运行）：
  - `MAX_GAME_DEPTH`（L128）、`SPLIT_DEPTH`（L132）、`MAX_CLOCK_DURATION`（L135）、`CLOCK_EXTENSION`（L139）均为部署时 immutable
  - 时钟继承：`getChallengerDuration`（move() 内）
  - 三档延期：`CLOCK_EXTENSION + oracle().challengePeriod()` / `CLOCK_EXTENSION × 2` / `CLOCK_EXTENSION`
  - 时钟到期：`revert ClockTimeExceeded()`
  - 单步 `step()` L362、预映像 `addLocalData()` L581、结算 `resolve()` L709 / `resolveClaim()` L735 / `claimCredit()` L984
- **必须避免**：给 spec 参数填具体生产数值（本轮 not_verified）。

---

## 2. 建议修正的本文表述

| 现有风险表述 | 建议改为 | 依据 |
|---|---|---|
| 「恢复机制降低结算延迟」 | 「恢复机制使第三方可在提交方离线后继续**交互**路径；在本有界模型中不改善正确终局时间（12.6 ms vs 兜底 8.7 ms）」 | G-CE-02 |
| 「首创第三方争议接续 / 动态参与」 | 「在有界重算模型内提供**不依赖交互**的终止路径（adjudicate）；OP FDG 已有时钟继承与延期机制」 | G-CE-03 |
| 「比 OP/Arbitrum 快 N 倍」 | 删除或改为端点定义分表（提交确认/乐观可用/挑战关闭/协议终局/提款） | G4、claim_evidence_matrix.unsupportedClaimsFlagged |
| 「比 TeeRollup 省 X%」 | 删除（对方基线为 StarkNet） | G-CE-04 |
| 「payload 扩展到大块数据仍保持吞吐」 | 「payload 在本有界模型中为名义参数（dataHash 固定 32 字节），不改变链上负载」 | G-CE-07 |
| 「并发提升带来吞吐线性增长」 | 「在串行出块的本地环境中并发无单调增益（121.79 / 144.63 / 117.19）」 | G-CE-08 |

---

## 3. 建议新增的自证实验引用（本文 own data）

- 同模型机制微基准（本方案 vs mechanism baseline）：
  - 正确终局率：本方案 4 臂均 30/30；基线在提交方离线臂 0/30（30/30 为错误罚没）
  - gas：本方案 interactive 25.92M vs 基线 20.40M；本方案 direct 兜底 14.67M vs 基线 terminate 10.49M
  - 定位：`outputs/stageG_20260916T185200Z/hardhat_run/stageG/summary/mechanism_summary.csv`
- F 消融四臂（恢复/兜底）：`outputs/stageF_20260916T184017Z/hardhat_run/stageF/summary/ablation_summary.csv`

> 引用本文自测数据时，必须同时给出：本地 Hardhat 环境、feeSource=local-gas-only、3 个独立 run、无 CI、不含 DA/TEE 成本。

---

## 4. 建议保留为「未核实/缺口」的表述

- TeeRollup：无公开实现仓库，本轮未复现其原型。
- BoLD：官方仓库已获取（commit `30e78f67`，BSL 1.1），本机无 Go 工具链，未运行。
- Optimism FDG：官方合约源码已获取（commit `c4a68ab`），本机无 foundry，未运行单测。
- 真实 TEE（D）与真实 Blob（E）未验收，故不含 TEE/DA 的定量对照。
