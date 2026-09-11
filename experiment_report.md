# 正式论文实验报告

生成时间：`2026-05-10 03:16:50 UTC`

## 1. 实验规模

- 每组变量样本数：`100`
- 成本实验记录数：`3200`
- 挑战实验记录数：`600`
- 失败场景实验记录数：`800`
- 成本变量：payload size、prompt length、batch size、DA profile
- 挑战变量：trace steps、challenge timeout、max bisection rounds、timeout recovery
- 说明：当前实验使用 simulated TEE、JSON ledger 和 gas 估算模型，只说明原型趋势，不声称真实链上 gas 或真实 TEE 安全。

## 2. 对照组设计

### 2.1 成本对照组

| 对照维度 | Baseline | 方案组 | 目的 |
| --- | --- | --- | --- |
| 数据提交 | full_onchain_calldata | compact_external_da / compact_eip4844_like / compact_modular_da_sampling | 比较 full payload 上链与 compact commit + DA 的降本趋势 |
| 批处理 | batch_size=1 | batch_size=10 / 100 / 1000 | 比较单笔摊销成本随批处理规模增大的变化 |
| 负载规模 | payload size=128 | payload size=512 / 2048 / 8192 | 比较高频 DApp 负载增大时 compact commit 的压缩收益 |

### 2.2 挑战对照组

| 对照维度 | Baseline | 方案组 | 目的 |
| --- | --- | --- | --- |
| 恢复机制 | challenge_timeout_no_recover | challenge_timeout_recover | 比较 recoverable challenge 对超时场景可完成性的改善 |
| 争议规模 | trace steps=4 | trace steps=8 / 16 / 32 / 64 / 128 | 比较二分定位轮次与 replay 路径复杂度 |
| 异常类型 | normal | response_tampered / attestation_invalid / trace_length_mismatch / da_unavailable / da_proof_invalid | 比较不同故障类型的检测与仲裁结果 |

## 3. 指标定义

| 指标 | 定义 | 解释 |
| --- | --- | --- |
| `byte_reduction_ratio` | `(full_bytes - compact_bytes) / full_bytes` | 轻量提交对链上字节的压缩比例 |
| `amortized_gas` | `total_gas / batch_size` | 每笔请求的摊销成本 |
| `reduction_ratio` | `(full_onchain_gas - target_gas) / full_onchain_gas` | 相对 full-onchain 的降本比例 |
| `avg_bisection_rounds` | `mean(dispute.round)` | 争议定位平均轮次 |
| `recovery_success_rate` | `recover_count >= 1` 的样本比例 | 超时后恢复并继续推进的比例 |
| `challenge_success_rate` | `challenge_success=True` 的样本比例 | 争议最终完成仲裁的比例 |
| `detection_rate` | `detected=True` 的样本比例 | 故障是否能被 verify 或 challenge 观测到 |
| `slashed_rate` | `final_status=SLASHED` 的样本比例 | 异常执行最终被罚没的比例 |

## 4. 成本实验摘要

| Payload | Prompt | Batch | Full bytes | Compact bytes | Byte降幅 | External DA单笔Gas | EIP4844-like单笔Gas | Modular DA单笔Gas |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 64 | 1 | 1682.84 | 406.00 | 75.33% | 10198.25 | 8010.56 | 7253.28 |
| 128 | 64 | 10 | 1682.84 | 406.00 | 75.33% | 1019.82 | 801.06 | 725.33 |
| 128 | 64 | 100 | 1682.84 | 406.00 | 75.33% | 101.98 | 80.11 | 72.53 |
| 128 | 64 | 1000 | 1682.84 | 406.00 | 75.33% | 10.20 | 8.01 | 7.25 |
| 128 | 256 | 1 | 1876.84 | 406.00 | 77.98% | 10625.05 | 8185.16 | 7340.58 |
| 128 | 256 | 10 | 1876.84 | 406.00 | 77.98% | 1062.50 | 818.52 | 734.06 |
| 128 | 256 | 100 | 1876.84 | 406.00 | 77.98% | 106.25 | 81.85 | 73.41 |
| 128 | 256 | 1000 | 1876.84 | 406.00 | 77.98% | 10.63 | 8.19 | 7.34 |
| 512 | 64 | 1 | 3986.84 | 406.00 | 89.39% | 15267.05 | 10084.16 | 8290.08 |
| 512 | 64 | 10 | 3986.84 | 406.00 | 89.39% | 1526.70 | 1008.42 | 829.01 |
| 512 | 64 | 100 | 3986.84 | 406.00 | 89.39% | 152.67 | 100.84 | 82.90 |
| 512 | 64 | 1000 | 3986.84 | 406.00 | 89.39% | 15.27 | 10.08 | 8.29 |
| 512 | 256 | 1 | 4180.84 | 406.00 | 89.92% | 15693.85 | 10258.76 | 8377.38 |
| 512 | 256 | 10 | 4180.84 | 406.00 | 89.92% | 1569.38 | 1025.88 | 837.74 |
| 512 | 256 | 100 | 4180.84 | 406.00 | 89.92% | 156.94 | 102.59 | 83.77 |
| 512 | 256 | 1000 | 4180.84 | 406.00 | 89.92% | 15.69 | 10.26 | 8.38 |
| 2048 | 64 | 1 | 13204.84 | 406.00 | 96.76% | 35546.65 | 18380.36 | 12438.18 |
| 2048 | 64 | 10 | 13204.84 | 406.00 | 96.76% | 3554.66 | 1838.04 | 1243.82 |
| 2048 | 64 | 100 | 13204.84 | 406.00 | 96.76% | 355.47 | 183.80 | 124.38 |
| 2048 | 64 | 1000 | 13204.84 | 406.00 | 96.76% | 35.55 | 18.38 | 12.44 |
| 2048 | 256 | 1 | 13398.84 | 406.00 | 96.81% | 35973.45 | 18554.96 | 12525.48 |
| 2048 | 256 | 10 | 13398.84 | 406.00 | 96.81% | 3597.34 | 1855.50 | 1252.55 |
| 2048 | 256 | 100 | 13398.84 | 406.00 | 96.81% | 359.73 | 185.55 | 125.25 |
| 2048 | 256 | 1000 | 13398.84 | 406.00 | 96.81% | 35.97 | 18.55 | 12.53 |
| 8192 | 64 | 1 | 50068.84 | 406.00 | 99.14% | 116647.45 | 51557.96 | 29026.98 |
| 8192 | 64 | 10 | 50068.84 | 406.00 | 99.14% | 11664.74 | 5155.80 | 2902.70 |
| 8192 | 64 | 100 | 50068.84 | 406.00 | 99.14% | 1166.47 | 515.58 | 290.27 |
| 8192 | 64 | 1000 | 50068.84 | 406.00 | 99.14% | 116.65 | 51.56 | 29.03 |
| 8192 | 256 | 1 | 50262.84 | 406.00 | 99.14% | 117074.25 | 51732.56 | 29114.28 |
| 8192 | 256 | 10 | 50262.84 | 406.00 | 99.14% | 11707.42 | 5173.26 | 2911.43 |
| 8192 | 256 | 100 | 50262.84 | 406.00 | 99.14% | 1170.74 | 517.33 | 291.14 |
| 8192 | 256 | 1000 | 50262.84 | 406.00 | 99.14% | 117.07 | 51.73 | 29.11 |

## 5. 可恢复挑战实验摘要

| Trace steps | Timeout | Max rounds | 平均二分轮次 | 理论log2轮次 | 恢复成功率 | 挑战成功率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 2 | 16 | 2.00 | 2.00 | 100.00% | 100.00% |
| 8 | 2 | 16 | 3.00 | 3.00 | 100.00% | 100.00% |
| 16 | 2 | 16 | 4.00 | 4.00 | 100.00% | 100.00% |
| 32 | 2 | 16 | 5.00 | 5.00 | 100.00% | 100.00% |
| 64 | 2 | 16 | 6.00 | 6.00 | 100.00% | 100.00% |
| 128 | 2 | 16 | 7.00 | 7.00 | 100.00% | 100.00% |

## 6. 失败场景实验摘要

| 场景 | 样本数 | 检测率 | 挑战成功率 | Slashed比例 | 示例 mismatch |
| --- | ---: | ---: | ---: | ---: | --- |
| attestation_invalid | 100 | 100.00% | 0.00% | 0.00% | da_payload_hash_mismatch;attestation_invalid;proof_hash_mismatch |
| challenge_timeout_no_recover | 100 | 100.00% | 0.00% | 0.00% | - |
| challenge_timeout_recover | 100 | 100.00% | 100.00% | 100.00% | - |
| da_proof_invalid | 100 | 100.00% | 0.00% | 0.00% | da_proof_invalid |
| da_unavailable | 100 | 100.00% | 0.00% | 0.00% | da_unavailable |
| normal | 100 | 0.00% | 0.00% | 0.00% | - |
| response_tampered | 100 | 100.00% | 100.00% | 100.00% | da_payload_hash_mismatch;da_proof_invalid;attestation_invalid;state_root_mismatch |
| trace_length_mismatch | 100 | 100.00% | 100.00% | 100.00% | da_payload_hash_mismatch;da_proof_invalid;attestation_invalid;state_root_mismatch |

## 7. 核心对照结论

### 7.1 full-onchain vs compact+DA

| Payload | Prompt | Full-onchain单笔Gas | External DA单笔Gas | EIP4844-like单笔Gas | Modular DA单笔Gas | 最佳降本比例 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8192 | 64 | 801101.44 | 116647.45 | 51557.96 | 29026.98 | 96.33% |
| 8192 | 256 | 804205.44 | 117074.25 | 51732.56 | 29114.28 | 96.33% |

### 7.2 no recover vs recover

| 场景 | 检测率 | 挑战成功率 | Slashed比例 |
| --- | ---: | ---: | ---: |
| challenge_timeout_no_recover | 100.00% | 0.00% | 0.00% |
| challenge_timeout_recover | 100.00% | 100.00% | 100.00% |

## 8. 图表与结论

- `figures/cost_payload_full_vs_compact.png`：payload 增大时，full payload 字节数随数据增长，compact commit 保持近似固定。
- `figures/challenge_rounds.png`：trace steps 增长时，二分定位轮次接近 log2(trace steps)。
- `figures/recovery_success.png`：无 recover 的超时流程会停滞，有 recover 的流程可继续推进。
- `figures/da_profile_amortized_gas.png`：不同 DA profile 的单笔摊销 gas 随 batch size 增大下降。
- `figures/failure_detection.png`：篡改、attestation 失效、trace length mismatch 和 DA 异常均可被记录为 mismatch 或 challenge failure。

## 9. 本地 EVM Gas 实测补充

当前项目已将关键链上路径映射为 Solidity 合约，并在 Hardhat 本地测试链上得到 `gasUsed` 基线。这部分结果用于补充 Python 成本模型，说明关键提交和争议路径在链上执行时的真实状态推进开销。

| 操作 | 平均 gasUsed |
| --- | ---: |
| register DA | 113526.00 |
| submit rollup | 299033.67 |
| challenge open | 283769.00 |
| challenge respond | 65886.00 |
| challenge step | 93807.00 |
| challenge recover | 156891.00 |
| challenge replay | 135632.00 |
| challenge resolve | 113402.00 |
| finalize | 33477.00 |

这组本地 EVM 数据应被看作“链上实测基线”，而不是 Sepolia 或主网费用的直接替代；真实公网环境下的费用还会受到 calldata 定价、blob 价格和网络状态影响。

## 10. Sepolia 公开测试网部署结果

当前项目已将同一套 Solidity 合约成功部署到 Sepolia，部署记录位于 [`evm/deployments/sepolia.json`](</E:/项目/project_code/evm/deployments/sepolia.json>)，ABI 与地址索引位于 [`evm/deployments/sepolia_abis/address_index.json`](</E:/项目/project_code/evm/deployments/sepolia_abis/address_index.json>)。

### 10.1 部署参数

| 参数 | 数值 |
| --- | --- |
| Network | `Sepolia` |
| Chain ID | `11155111` |
| disputeWindowSeconds | `60` |
| challengeTimeoutSeconds | `2` |
| maxBisectionRounds | `16` |
| 部署区块 | `10825904` |

### 10.2 合约地址

| 合约 | Sepolia 地址 | 角色 |
| --- | --- | --- |
| MockTEEVerifier | `0xC42CB0Cf0D112Bd59E0f212F2DB2002ca50a8b6A` | 模拟 TEE attestation 链上验证 |
| MockDARegistry | `0xc42C64a7De05bf3ad4f1c75CbD8E0506F7De99Ff` | DA 根与可用性记录 |
| HybridTEERollup | `0xB9B72f10bB8aBC1ed090f1B0443Fe57189c497Fd` | compact commit、challenge、recover、replay、resolve |

### 10.3 验证状态

`verify:sepolia` 已执行两次，但当前返回的是 block explorer 侧的 `Connect Timeout Error`。这说明：

1. 合约部署和构造参数记录已经成功完成；
2. 当前未通过 Etherscan 侧请求超时完成源码验证；
3. 该问题不影响 Sepolia 地址、部署区块和 ABI 索引作为论文中的公开测试网部署证据使用；
4. 后续可以在网络状态更稳定时再次重试 `npm.cmd run verify:sepolia`。

## 11. 可贴组会结论

本周将论文主线收敛为“Hybrid TEE-Rollup 下的可恢复交互式挑战 + 轻量 DA 成本评估”，并新增批量实验脚本。
成本实验已从 5 组样本扩展为 `3200` 条记录，覆盖 payload size、batch size 与多类 DA profile。
在最大 payload `8192` 的实验组中，compact commit 相比 full payload 仍保持明显字节压缩；batch 增大后，单笔摊销 Gas 继续下降。
挑战实验覆盖最高 `128` 个 trace steps，恢复成功率为 `100.00%`，挑战成功率为 `100.00%`，说明 timeout recovery 后争议流程仍能继续推进并完成 slashing。
对照组结果进一步说明：无 recover 的超时流程无法完成仲裁，而有 recover 的流程可恢复并推进到 slashing；full-onchain 与 compact+DA 的差距会随着 payload 增大而被放大。
当前实验结果可以支撑论文中的三条阶段性主张：一是可恢复挑战协议增强异常场景鲁棒性；二是 compact commit + DA 在高频 DApp 批量交互中具有稳定降本趋势；三是该原型已经具备 Solidity 对应物、本地 EVM 实测基线以及 Sepolia 公开测试网部署证据。

## 12. 结果文件

- `cost_grid.csv`
- `challenge_grid.csv`
- `failure_scenarios.csv`
- `summary.json`
