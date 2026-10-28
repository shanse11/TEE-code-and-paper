# Hybrid TEE-Rollup 修订分支审计交付

- **run_id**: `20260911T095029Z`
- **生成日期**: 2026-09-11
- **证据根目录**: `revision_runs/20260911T095029Z/`
- **独立审计副本**: `revision_runs/20260911T095029Z/audit/`
- **综合状态**: `revision_runs/20260911T095029Z/external_status.json`

## 1. 结论摘要

本次修订分支已完成本地安全、随机状态机、性能、旧实现反例和离线真实 KZG 验证。公网 Sepolia Blob 发布/独立取回/链上绑定验证，以及真实 TDX Quote 采集仍未完成，原因是环境没有 RPC、签名私钥、已部署锚定合约地址、Beacon API 或云凭据/运行中的 TDX 实例。相关脚本均为 fail-closed，不会用本地工件冒充公网结果。

## 2. 已完成证据

| 证据项 | 结果 | 主要文件 |
|---|---:|---|
| 定向安全回归 | 23/23 通过，0 失败 | `security/security_report.json` |
| 固定种子随机序列 | 1000/1000 完成；27401 次操作；22686 次回退状态检查 | `security/random_report.json` |
| 性能主矩阵 | 27 个单元，通过 | `performance/summary.json` |
| calldata 矩阵 | 9 个单元，通过 | `performance/summary.json` |
| 恢复矩阵 | 48 个单元，通过 | `performance/summary.json` |
| 旧实现反例 | 10/10 复现 | `legacy/report.json` |
| 离线真实 KZG | 9 个矩阵批次 + 1 个负例，全部通过 | `blob_offline/` |
| 外部文献/官方文档核实 | 文档级完成 | `external_research/` |

离线 KZG 使用真实 Ethereum 主网 EIP-4844 SRS，固定 Blob 长度为 131072 字节，commitment 和 proof 各为 48 字节。负例覆盖内容篡改、Blob 字节篡改、payload hash 变化和解码语义检查。

## 3. 明确未完成项

### 3.1 公网 Sepolia

- 未广播 type-3 交易。
- 未部署或读取公网 `BlobBatchAnchor`。
- 未获得 `BlobBatchAnchored` 事件、anchor id、交易 receipt 或公网 block number。
- 未从 Beacon API 独立取回 Blob。
- 未进行链上 versioned hash、payload hash、task count 的最终比对。

续跑需要：`SEPOLIA_RPC_URL`、`SEPOLIA_PRIVATE_KEY`、已部署的 `BLOB_BATCH_ANCHOR_ADDRESS`、有余额的 Sepolia signer，以及可取回完整 Blob 的 `BEACON_API_URL`。详见 `external_status.json` 和 `external_research/tee_precheck_quote.md`。

### 3.2 真实 TEE

- 未开通或运行 TDX 实例。
- 未采集真实 TD Report/Quote。
- 未取得 PCK 证书链和 DCAP collateral。
- 未完成 Quote 签名、证书链、TCB 状态和测量值核验。
- 实时价格、库存、区域配额和最低计费增量未核实。

未使用样例 Quote，也未代用户购买、登录或开通云服务。

### 3.3 Blob 费用独立性

性能文件中的 calldata 数据只用于本地对照，不能推出真实 EIP-4844 Blob 节省。真实费用比较需要公网 type-3 receipt 中的 Blob gas 字段和同条件 calldata 交易数据；当前状态标记为 `not_measured`。

## 4. 证据层级

1. **local_evm**：Hardhat Cancun、chainId 31337、自动挖矿，仅支持合约行为和恢复逻辑的本地验证。
2. **offline_kzg**：真实 EIP-4844 SRS 下的编码、承诺、证明、解码和篡改检测，不支持公网交易绑定结论。
3. **public_testnet**：需要 Sepolia 交易、Beacon 取回和链上读取，目前未完成。
4. **real_tee**：需要真实 TDX 实例、Quote、collateral 和独立 DCAP 验证，目前未完成。

## 5. 审计副本内容

- `blob_offline/`：9 个矩阵批次和 `NEGATIVE_EXAMPLE` 的 Blob、commitment、proof、frame、篡改工件及 `meta.json`。
- `performance/`：性能原始数据和汇总。
- `security/`：定向安全报告和随机状态机报告。
- `legacy/`：旧实现 10 个反例的汇总。
- `external_research/`：中文比较报告、TEE 预检续跑说明和结构化来源。
- `*_run.log`：主要实验日志。
- `evidence_matrix_zh.md`：主张与证据边界矩阵。
- `reviewer_response_zh.md`：面向评审的限制和证据回应。
- `citations_zh.md`：引用与使用边界清单。
- `performance_overview.svg`：本地性能概览图，含范围警示。
- `sha256sums.txt`：关键审计文件 SHA-256。

## 6. 复核入口

```text
external_status.json
 audit/README_审计交付.md
 audit/evidence_matrix_zh.md
 audit/reviewer_response_zh.md
 audit/performance_overview.svg
 audit/sha256sums.txt
 audit/blob_offline/
 audit/security/
 audit/performance/
 audit/external_research/
```

原始 `artifacts/`、`security/`、`performance/`、`legacy/` 和实验日志均保留；`audit/` 是独立副本，不替换原始证据。
