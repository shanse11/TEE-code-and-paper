# 主张与证据边界矩阵

| 主张/问题 | 当前结论 | 证据层级 | 证据文件 | 可否对外表述 |
|---|---|---|---|---|
| 修订合约限制未授权 response、非法 steps/version、重复结算和提现重入 | 已验证 | local_evm | `security/security_report.json` | 可以，但应注明本地 EVM |
| 恶意 challenge、超时和双方离线时仍可公开裁决 | 已验证 | local_evm | `security/security_report.json` | 可以，限定为测试模型 |
| 资金守恒、罚没和提现后余额关系成立 | 已验证 | local_evm | `security/security_report.json` | 可以，限定为测试模型 |
| 1000 条固定种子对抗序列无状态不变量破坏 | 已验证 | local_evm | `security/random_report.json` | 可以，注明 27401 次操作 |
| 旧实现的 10 类不安全行为可复现 | 已验证 | local_evm | `legacy/report.json` | 可以，明确是旧合约 |
| 本地主性能矩阵通过 | 已验证 | local_evm | `performance/summary.json` | 可以，不能等同公网吞吐 |
| 本地 calldata 对照数据存在 | 已验证 | local_evm | `performance/summary.json` | 可以，不能推导 Blob 节省 |
| 真实 EIP-4844 KZG 编码/承诺/证明/解码可工作 | 已验证 | offline_kzg | `blob_offline/*/meta.json` | 可以，不能等同链上发布 |
| 内容篡改和 Blob 字节篡改被拒绝 | 已验证 | offline_kzg | `blob_offline/NEGATIVE_EXAMPLE/meta.json` | 可以，限定为离线密码学实验 |
| 真实 Blob 已进入 Sepolia | 未完成 | public_testnet | 无交易 receipt | 不可表述为已完成 |
| Blob versioned hash 已被链上锚定 | 未完成 | public_testnet | 无 `BlobBatchAnchored` 事件 | 不可表述为已完成 |
| Blob 已从 Beacon API 独立取回 | 未运行 | public_testnet | 无 `blob_fetch` 成功状态 | 不可表述为已完成 |
| 链上锚定值与独立取回 Blob 一致 | 未完成 | public_testnet | 无 on-chain verify 结果 | 不可表述为已完成 |
| 真实 Blob gas 费用或 Blob 节省 | 未测量 | public_testnet | 无 type-3 receipt | 不可表述为已完成 |
| TDX 提供商、规格、Quote/DCAP 流程存在 | 文档级已核实 | documentary | `external_research/sources.json` | 可以，注明文档级 |
| 实时 TDX 价格、库存、配额、最低计费 | 未核实 | documentary | `tee_precheck_quote.md` | 不可作采购承诺 |
| 真实 TDX Quote 已采集和验证 | 未完成 | real_tee | 无 Quote evidence | 不可表述为已完成 |
| TEE 测量值与部署 sequencer 一致 | 未完成 | real_tee | 无真实 Quote/collateral | 不可表述为已完成 |

## 使用规则

- “通过”只针对对应证据层级，不自动向更高层级外推。
- `offline_kzg` 不等价于 `public_testnet`。
- `documentary` 不等价于 `real_tee`。
- 性能结果中的 p50/p95 是本地实验描述统计；不能写成主网 TPS、共识最终性或真实云成本。
