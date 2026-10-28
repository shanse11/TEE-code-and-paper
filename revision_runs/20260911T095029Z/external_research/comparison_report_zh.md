# 外部研究比较报告（中文）

- **run_id**: 20260911T095029Z
- **日期**: 2026-09-11
- **研究者角色**: 仅独立研究与证据写入，**未修改任何合约/测试代码**
- **配套文件**: `sources.json`（结构化来源/URL/版本/摘录/局限）、`tee_precheck_quote.md`（TEE 预检/阻塞 + 官方 Quote 验证续跑建议）

> **证据与版权声明**：以下原文摘录均为短引（fair-use），版权归原作者/发布方。所有「未核实」标记项均无云凭据/库存支持，本环境未购买、未登录、未开通任何云服务。

---

## 1. 研究范围与对象

| 对象 | 一手来源 | 版本/日期 |
|---|---|---|
| TEEROLLUP（异构 TEE Rollup） | arXiv:2409.14647 | v3（最新），v1=2024-09-23，v3=2025-11-30 |
| Arbitrum BoLD 争议协议 | arXiv:2404.10491 | v1，2024-04-16 |
| Optimism Fault Dispute Game | specs.optimism.io（stage-one） | 访问 2026-09-11 |
| EIP-4844（blob 交易） | eips.ethereum.org/EIPS/eip-4844 | Final |
| Sepolia / PeerDAS（Fusaka/EIP-7594） | Arbitrum 公告 + Teku 文档 + viem PR | 访问 2026-09-11 |
| 阿里云 Intel TDX 官方文档 | help.aliyun.com | 更新 2026-09-01 |

---

## 2. 争议解决 / 最终性时延机制比较

### 2.1 信任与威胁模型（各自独立，不可直接横向比「更强」）

- **TEEROLLUP**：依赖**异构 TEE**（SGX/TDX/CSV，实验比例 1:2:2）。安全容忍为至多 `f` 个 sequencer TEE 同时受损，状态转换需 `f+1` 个 TEE 签名（Quorum Certificate）。原文威胁模型：
  > "We assume all sequencers can be malicious by controlling the host of TEEs with at most f sequencers' TEEs are compromised at any time."
  采用**静态腐败**假设；DAP 为**理性**。安全根基是「不同 TEE 平台很难同时被攻破」。
- **Optimism FDG**：基于**交互式二分游戏 + Cannon FPVM（kona-client / MIPS64）**，无许可挑战。安全依赖 L1 最终性与至少一个诚实挑战者；不依赖 TEE。计时参数为部署预设不可变：`CLOCK_EXTENSION`（剩余不足时平铺信用）、`MAX_CLOCK_DURATION`、`SPLIT_DEPTH`、以及 `oracle.challengePeriod()`。扩展规则：标准 `CLOCK_EXTENSION`；预执行轨迹根 `CLOCK_EXTENSION×2`；预单步 `CLOCK_EXTENSION + challengePeriod`。
- **Arbitrum BoLD**：基于**动态协议图 + 本地计时器**，抗延迟攻击。允许**任意数量**腐败方协调，只要现实存在**至少一个诚实方**聚合参与：
  > "at least one honest party participates in the dispute resolution protocol."
  终止时间为 `2·(C_max + D)`，其中 `C_max` 保守取约 1 周（审查累计上限），`D` 为无审查名义延迟（数小时）。

### 2.2 最终性 / 提款时延（各自定义不同，不可比成「快 X%」）

| 协议 | 时延表述（原文） | 上下文 |
|---|---|---|
| TEEROLLUP | "withdrawal delays to a few minutes"（正常情况数分钟） | 仅在系统不可用时触发 τ（数小时）挑战等待；正常不触发 |
| Optimism FDG | 依赖 `challengePeriod()`（常见部署约 7 天，属部署配置非 spec 常量） | 第三方分析给出，需核对部署 |
| Arbitrum BoLD | 最坏 `2·(C_max+D)` ≈ 2 周（有审查）/ 1 周（无审查） | 相对于原 Arbitrum Classic 的延迟攻击（可达 ~2·N 个 challenge period） |

> **不可比说明**：TEEROLLUP 的「数分钟」是 TEE 签名即 finalize 的正常路径；OP/BoLD 的「天级」是欺诈证明挑战窗口。二者安全模型与攻击面不同，**不能计算「TEEROLLUP 比 OP 快 X%」这类领先百分比**。

---

## 3. 成本 / 吞吐实验数字（各自基准不同）

### 3.1 TEEROLLUP（arXiv:2409.14647，测试网 Sepolia 原型）
- 链上验证成本相对 **StarkNet（ZK-rollup）降低约 86%**：原文 "reducing on-chain verification costs by approximately 86%"。batch=2000 时单笔约 **0.006 USD**（StarkNet 对照 0.043 USD）。
- 吞吐：5 sequencer + batch 2000，**LAN ~28 KTPS**，延迟峰值 **119 ms**；离线处理 >**5000 TPS**。20 sequencer WAN 下吞吐 **−15.74%**、延迟 **+20.17%**。
- Table IV gas（汇率 2025-01-01：ETH=$3376.77, 19.26 Gwei）：Deposit 48,551；UpdateState 156,263；StartChallenge 47,118；ResolveChallenge 146,618；SettleRollup 29,078；SettleWithdraw 124,511。

### 3.2 Arbitrum BoLD（arXiv:2404.10491）
- 成本表述为**相对比例**而非绝对金额：参数可设到腐败方总成本（质押+L1 gas）为诚实方的 **10 倍**（"10 times as much"）。
- 摘要称 "without a significant increase in onchain computation costs and with reduced staking costs"；相对原全并发 Arbitrum Classic，诚实方聚合只需质押 **1 次**。
- **未给出具体 ETH/USD 保证金面额**。

> **不可比说明**：TEEROLLUP 的「86%」是 vs StarkNet 的绝对成本差；BoLD 的「10×」是腐/诚成本比。二者分母、基准、单位均不同，**不可折算成统一的「领先百分比」**。

---

## 4. 数据可用性层：EIP-4844 → PeerDAS / Fusaka（Sepolia 2026）

- **EIP-4844（Final）**：blob 作为 sidecar 单独传播；每区块目标 3 / 上限 6 blob；`MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS=4096`（约 **18 天**）保留期。blob gas 指数价（更新分数 3338477，每块最大变化 ≈1.125×）。
- **Fusaka 硬分叉时间线**（Arbitrum 官方公告）：Ethereum **Sepolia** Fusaka 于 **2025-10-14 07:36 UTC** 激活；Mainnet 于 **2025-12-03 21:49 UTC** 激活。
- **PeerDAS = EIP-7594**（Fusaka 主特性）：blob 做 1D 擦除码扩展（翻倍、128 列），节点通常只 custody 部分列即可证明 DA。blob 目标数自 **2026-01-07** 起调度为 **14**（Teku 文档）。
- **Sepolia 当前 blob 取回接口注意**：
  - viem PR 备注：Sepolia 链 ID 自动判定使用 **EIP-7594（PeerDAS）** blob 版本（wrapper version byte 0x01，每 blob 128 个 cell proof）。
  - Fusaka 后**完整** blob 数据需超级节点模式或按需下载（Teku `--rest-api-getblobs-sidecars-download-enabled`；Lighthouse `--prune-blobs false`；Prysm `--semi-supernode --enable-backfill`）；普通节点只 custody 部分列。
  - 公开无 key 取回端点：Pinax `GET /eth/v1/beacon/blobs/{block_id}`（支持 Sepolia），可按 `versioned_hashes` 过滤。
- **对 Hybrid TEE-Rollup 的影响**：若数据可用性依赖 Sepolia blob，须确认 L2/归档层节点已订阅全部子网或保留历史 blob，否则超出 ~18 天保留期后无法回放——这与 TEEROLLUP 论文中 DAP 的「链下存储 + 懒惰惩罚」机制是两个不同层，需分别核算。

---

## 5. Intel TDX 短租可行性（500 元内）

### 5.1 官方确认事实（已核实，来自 help.aliyun.com，更新 2026-09-01）
- **实例与区域**：`ecs.g8i.xlarge` 及以上规格支持 TDX；开放于北京可用区 I/L、杭州可用区 J、中国香港 B/C/D、新加坡 B 等**特定 AZ**（TDX 仅部分地域特定 AZ 开放）。
- **Quote 与 DCAP**：
  - Quote 生成接口：`/dev/tdx_guest`（ACL3 内核 5.10.134-16.al8+）或 ConfigFS TSM `/sys/kernel/config/tsm/report`（上游 6.7+）。
  - DCAP 缓存服务（PCCS）：`sgx-dcap-server-vpc.<region_id>.aliyuncs.com`；Quote 验证需拉取 collateral（TCB Info / QE Identity / PCK CRL）。**DCAP 受支持**。
- Intel 官方产品页列出提供 TDX 的云商：阿里巴巴、Google Cloud、Microsoft Azure。

### 5.2 价格 / 库存（**未核实**，需云凭据）
- 本环境**无任何云凭据**（布尔检查全为 false），无法编程核对实时单价、最低计费增量、现货库存。
- 第三方社区快照（gist）给出 `ecs.g8i.xlarge` ≈ **¥1.0885/小时**，为**二手数据、非官方挂牌价**。
- **500 元可行性粗算（仅作量级参考，非采购依据）**：若以 ¥1.0885/小时计，500 元 ≈ **459 小时 ≈ 19 天** 的 g8i.xlarge 短租。但最低计费增量（阿里云 ECS 通常按秒、最低 1 分钟，未经本环境核实）、区域折扣、实际现货均须经控制台确认。
- **结论**：在「仅短期（数天~数周）租一台最低规格 TDX 实例（g8i.xlarge）」场景下，按第三方快照价 **500 元内可行量级成立**；但**确切价格、库存、最低计费一律未核实**，不得作为承诺。

---

## 6. 关键不可比项汇总（避免误导）

1. TEEROLLUP「86% 成本降低」基准是 **StarkNet（ZK）**，不是 OP/Arbitrum；不能转述为「比 OP/Arbitrum 快/省 X%」。
2. BoLD「10×」是**腐/诚成本比**，不是跨协议领先百分比。
3. 三者的「最终性时延」定义不同（TEE 签名即时 vs 欺诈证明挑战窗口），**不可横向求比值**。
4. PeerDAS 后 blob 目标 14 与 EIP-4844 原 3/6 是**同一机制在不同硬分叉下的参数**，非竞争关系。
5. 所有云价格/库存项在本环境**无凭据可核实**，标记为「未核实」。

---

## 7. 来源索引（详见 sources.json）
- TEEROLLUP: https://arxiv.org/abs/2409.14647
- BoLD: https://arxiv.org/abs/2404.10491
- Optimism FDG: https://specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html
- EIP-4844: https://eips.ethereum.org/EIPS/eip-4844
- Fusaka 公告: https://docs.arbitrum.io/notices/fusaka-upgrade-notice
- Teku PeerDAS: https://docs.teku.consensys.io/development/concepts/peer-das
- 阿里云 TDX: https://help.aliyun.com/zh/ecs/user-guide/build-a-tdx-confidential-computing-environment
- Intel TDX: https://www.intel.cn/content/www/cn/zh/products/details/processors/xeon/features/trust-domain-extensions.html
