# 引用与使用边界清单

## 核心来源

1. Wen et al., *TeeRollup: Efficient Rollup Design Using Heterogeneous TEE*, arXiv:2409.14647, v3.
   - URL: https://arxiv.org/abs/2409.14647
   - 用途：异构 TEE、QC、挑战等待、DAP、论文原型实验数字。
   - 边界：论文实验为测试网原型；不能替代本项目真实 TDX Quote 或公网复测。

2. Alvarez et al., *BoLD: Fast and Cheap Dispute Resolution*, arXiv:2404.10491.
   - URL: https://arxiv.org/abs/2404.10491
   - 用途：动态争议协议图、诚实参与者假设、相对成本讨论。
   - 边界：文中成本和终止时间与本项目模型不同，不转换为统一领先百分比。

3. Optimism, *Fault Dispute Game specification*.
   - URL: https://specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html
   - 用途：Fault Dispute Game 的参数和计时规则。
   - 边界：部署参数需要按具体链配置核对，不把 spec 中的参数名当成固定数值。

4. Ethereum Improvement Proposal 4844, *Shard Blob Transactions*.
   - URL: https://eips.ethereum.org/EIPS/eip-4844
   - 用途：type-3 transaction、Blob versioned hash、KZG 和 Blob sidecar 规则。
   - 边界：Blob 为短期 DA 载体，不能未经归档策略假设永久可取回。

5. Arbitrum, *Fusaka upgrade notice*；Teku, *PeerDAS*；Pinax, *Blobs API*.
   - URLs:
     - https://docs.arbitrum.io/notices/fusaka-upgrade-notice
     - https://docs.teku.consensys.io/development/concepts/peer-das
     - https://app.pinax.network/docs/blobs
   - 用途：Sepolia/Fusaka/PeerDAS 状态与完整 Blob 取回条件。
   - 边界：普通节点可能不 custody 完整 Blob；本次没有实际调用 Beacon API。

6. 阿里云，*构建 TDX 机密计算环境*；Intel，*Trust Domain Extensions*。
   - URLs:
     - https://help.aliyun.com/zh/ecs/user-guide/build-a-tdx-confidential-computing-environment
     - https://www.intel.cn/content/www/cn/zh/products/details/processors/xeon/features/trust-domain-extensions.html
   - 用途：TDX 规格、支持 AZ、Quote 接口、PCCS/DCAP 流程和提供商存在性。
   - 边界：实时价格、库存、配额、最低计费和真实 Quote 未在本环境核实。

## 项目内证据

- `../external_status.json`：公网 Blob、真实 TEE、离线 KZG、费用独立性和续跑条件的结构化状态。
- `security/security_report.json`：23 项定向安全回归。
- `security/random_report.json`：1000 条随机序列与状态检查。
- `performance/summary.json`：本地性能、calldata、恢复矩阵。
- `legacy/report.json`：旧实现 10 个反例复现。
- `blob_offline/*/meta.json`：离线真实 KZG 正例和负例。

## 引用原则

- 论文/官方文档中的数字保留原始语境，不改写为本项目实测数字。
- 本地实验只标记为 `local_evm`；离线 KZG 只标记为 `offline_kzg`。
- 未有交易 receipt、Beacon 取回结果或 TDX Quote 时，不写“已上链”“已独立取回”或“真实 TEE 已验证”。
