# Hybrid TEE-Rollup 阶段性实验结果报告

生成时间：`2026-05-12`

## 一、研究背景与实验目的

高频 DApp（如元宇宙状态同步、去中心化社交交互和链上 AI 推理服务）对底层执行环境提出了三方面要求：一是需要较低的链上提交成本，二是需要在异常场景下仍保持可验证性，三是需要在工程上具备向链上实现过渡的可行性。传统 full-onchain 提交方式在高负载场景下成本较高，单纯依赖 TEE 的方案又会面临可信执行与去中心化验证之间的张力。

基于上述背景，当前工作并不试图提出一个全新的 TEE-Rollup 基础设施体系，而是在已有 Hybrid TEE-Rollup 思路下，围绕以下两个更具体的问题开展阶段性实验：

1. `compact commit + DA` 是否能够显著降低链上数据提交成本，并在 batch size 增大时保持更好的单笔摊销成本表现；
2. 可恢复交互式挑战机制是否能够解决 timeout 导致的争议流程停滞问题，并在异常场景下完成检测、挑战与 slashing。

为此，本阶段工作围绕 Python 原型、Solidity 映射、本地 EVM gas 实测以及 Sepolia 测试网部署，形成了一条从机制验证到链上对应物验证的连续实验路径。

## 二、系统原型与实验环境

### 2.1 系统原型组成

当前原型包含三层：

- **执行层**：采用 simulated TEE 执行环境，生成输出、状态摘要与模拟 attestation；
- **验证层**：实现 challenge-open、respond、step、recover、replay、resolve 等交互式挑战流程；
- **数据层**：采用 compact commit + DA payload 的提交方式，并通过模拟 Merkle root / proof 组织可验证数据证据。

### 2.2 不同实验层次的边界

为避免实验口径混淆，有必要明确当前报告中的几类“实验环境”含义：

1. **模拟 TEE**  
   当前 TEE 部分为模拟原型，用于验证“可信执行摘要 + challenge 仲裁”的协议路径，不等同于真实 SGX/TDX 环境。

2. **JSON ledger**  
   原型中的状态记录与提交流程使用 JSON ledger 组织，用于快速验证提交、挑战、恢复与 replay 逻辑，不等同于真实链上状态存储。

3. **gas 估算模型**  
   Python 实验中的成本部分主要依赖字节规模与 DA profile 参数进行估算，用于比较 full-onchain 与 compact+DA 的相对趋势，不直接等同于真实主网费用。

4. **本地 EVM 实测**  
   Solidity 合约已在 Hardhat 本地测试链上获得关键路径的 `gasUsed` 基线。这部分结果比纯估算更贴近链上执行，但仍然属于本地测试环境。

5. **Sepolia 公开测试网部署**  
   当前 Solidity 原型已成功部署到 Sepolia，用于证明系统已经具备公开测试网对应物；但其 gas 成本、网络延迟和浏览器验证状态仍不能直接替代主网生产环境结论。

### 2.3 实验运行环境概述

- Python 原型：用于成本实验、挑战实验与失败场景实验；
- Solidity 原型：用于本地 EVM `gasUsed` 实测与公开测试网部署；
- 本地链环境：Hardhat 本地测试链；
- 公开测试网环境：Sepolia；
- 报告依据文件包括：
  - `cost_grid.csv`
  - `challenge_grid.csv`
  - `failure_scenarios.csv`
  - `summary.json`
  - `paper_outputs/evm_gas/measured_gas_report.md`
  - `evm/deployments/sepolia.json`

## 三、实验设计

### 3.1 成本实验设计

成本实验用于比较 full-onchain 提交与 compact commit + DA 提交在不同负载和批处理规模下的成本差异。实验设置如下：

- 每组变量样本数：`100`
- 成本实验总记录数：`3200`
- 核心变量：
  - `payload size`
  - `prompt length`
  - `batch size`
  - `DA profile`

成本实验对照组设计如下：

| 对照维度 | Baseline | 方案组 | 目的 |
| --- | --- | --- | --- |
| 数据提交 | `full_onchain_calldata` | `compact_external_da / compact_eip4844_like / compact_modular_da_sampling` | 比较 full payload 上链与 compact commit + DA 的降本趋势 |
| 批处理 | `batch_size=1` | `batch_size=10 / 100 / 1000` | 比较单笔摊销成本随批处理规模增大的变化 |
| 负载规模 | `payload size=128` | `payload size=512 / 2048 / 8192` | 比较高频 DApp 负载增大时 compact commit 的压缩收益 |

### 3.2 可恢复挑战实验设计

可恢复挑战实验用于验证交互式挑战在超时与长执行轨迹场景下的可完成性与复杂度表现。实验设置如下：

- 挑战实验总记录数：`600`
- 核心变量：
  - `trace steps`
  - `challenge timeout`
  - `max bisection rounds`
  - `timeout recovery`

挑战实验对照组设计如下：

| 对照维度 | Baseline | 方案组 | 目的 |
| --- | --- | --- | --- |
| 恢复机制 | `challenge_timeout_no_recover` | `challenge_timeout_recover` | 比较 recoverable challenge 对超时场景可完成性的改善 |
| 争议规模 | `trace steps=4` | `trace steps=8 / 16 / 32 / 64 / 128` | 比较二分定位轮次与 replay 路径复杂度 |
| 异常类型 | `normal` | `response_tampered / attestation_invalid / trace_length_mismatch / da_unavailable / da_proof_invalid` | 比较不同故障类型的检测与仲裁结果 |

### 3.3 失败场景实验设计

失败场景实验用于验证系统在不同异常条件下的检测能力、挑战完成能力以及最终 slashing 结果。实验设置如下：

- 失败场景实验总记录数：`800`
- 覆盖场景包括：
  - `normal`
  - `attestation_invalid`
  - `challenge_timeout_no_recover`
  - `challenge_timeout_recover`
  - `da_proof_invalid`
  - `da_unavailable`
  - `response_tampered`
  - `trace_length_mismatch`

### 3.4 本地 EVM Gas 实测设计

本地 EVM 实测用于补充 Python 成本模型，验证关键链上路径的真实状态推进开销。测量环境为 Hardhat 本地测试链，重点关注以下操作：

- `register DA`
- `submit rollup`
- `challenge open`
- `challenge respond`
- `challenge step`
- `challenge recover`
- `challenge replay`
- `challenge resolve`
- `finalize`

样本级实测 payload 取值为 `128 / 512 / 2048`，重点观察在不同 payload 下关键操作 `gasUsed` 的稳定性与差异。

## 四、核心指标定义

为保证实验结论具有可解释性，当前阶段统一采用以下指标：

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

上述指标分别服务于三类判断：  
其一，用于分析 compact commit + DA 的相对降本趋势；其二，用于分析 recoverable challenge 的可完成性；其三，用于分析异常场景下的检测与惩罚结果。

## 五、实验结果与分析

### 5.1 compact commit + DA 成本实验结果

成本实验首先比较 full-onchain 与 compact commit + 多类 DA 路线之间的差异。下表给出代表性实验结果。

| Payload | Prompt | Batch | Full bytes | Compact bytes | Byte降幅 | External DA单笔Gas | EIP4844-like单笔Gas | Modular DA单笔Gas |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 64 | 1 | 1682.84 | 406.00 | 75.33% | 10198.25 | 8010.56 | 7253.28 |
| 128 | 256 | 1 | 1876.84 | 406.00 | 77.98% | 10625.05 | 8185.16 | 7340.58 |
| 512 | 64 | 1 | 3986.84 | 406.00 | 89.39% | 15267.05 | 10084.16 | 8290.08 |
| 512 | 256 | 1 | 4180.84 | 406.00 | 89.92% | 15693.85 | 10258.76 | 8377.38 |
| 2048 | 64 | 1 | 13204.84 | 406.00 | 96.76% | 35546.65 | 18380.36 | 12438.18 |
| 2048 | 256 | 1 | 13398.84 | 406.00 | 96.81% | 35973.45 | 18554.96 | 12525.48 |
| 8192 | 64 | 1 | 50068.84 | 406.00 | 99.14% | 116647.45 | 51557.96 | 29026.98 |
| 8192 | 256 | 1 | 50262.84 | 406.00 | 99.14% | 117074.25 | 51732.56 | 29114.28 |

从字节规模看，`compact commit` 在当前实验中基本稳定在约 `406 bytes`，而 `full payload` 随 payload size 增大近似线性增长。这表明当前轻量提交流程的链上提交规模主要由固定结构组成，而不是随着完整业务负载同比例增长。

从成本角度看，当 `payload=8192` 时：

- `full-onchain` 单笔 Gas 约为 `801101.44 ~ 804205.44`
- `external DA` 单笔 Gas 约为 `116647.45 ~ 117074.25`
- `EIP-4844-like` 单笔 Gas 约为 `51557.96 ~ 51732.56`
- `modular DA` 单笔 Gas 约为 `29026.98 ~ 29114.28`

代表性对照结果如下：

| Payload | Prompt | Full-onchain单笔Gas | External DA单笔Gas | EIP4844-like单笔Gas | Modular DA单笔Gas | 最佳降本比例 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8192 | 64 | 801101.44 | 116647.45 | 51557.96 | 29026.98 | 96.33% |
| 8192 | 256 | 804205.44 | 117074.25 | 51732.56 | 29114.28 | 96.33% |

该结果说明，在高负载场景下，`compact commit + DA` 相比 `full-onchain` 可以显著降低链上数据提交成本，且 `modular DA` 与 `EIP-4844-like` 路线在当前参数设置下表现出更强的降本潜力。

### 5.2 batch size 对单笔摊销 gas 的影响

成本实验还进一步考察了 batch size 增大后单笔摊销 gas 的变化趋势。以若干代表性设置为例：

| Payload | Prompt | Batch | External DA单笔Gas | EIP4844-like单笔Gas | Modular DA单笔Gas |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 64 | 1 | 10198.25 | 8010.56 | 7253.28 |
| 128 | 64 | 10 | 1019.82 | 801.06 | 725.33 |
| 128 | 64 | 100 | 101.98 | 80.11 | 72.53 |
| 128 | 64 | 1000 | 10.20 | 8.01 | 7.25 |
| 8192 | 64 | 1 | 116647.45 | 51557.96 | 29026.98 |
| 8192 | 64 | 10 | 11664.74 | 5155.80 | 2902.70 |
| 8192 | 64 | 100 | 1166.47 | 515.58 | 290.27 |
| 8192 | 64 | 1000 | 116.65 | 51.56 | 29.03 |

从上述结果可以看出，随着 `batch size` 从 `1` 增加到 `1000`，单笔摊销 gas 近似按比例下降。这一趋势说明，当系统面对高频 DApp 的批量交互请求时，批处理能够显著摊薄每笔请求对应的链上提交成本。因此，`compact commit + DA` 不仅在负载规模扩张时有压缩收益，而且在批处理规模增大时也具有更好的单笔成本表现。

### 5.3 可恢复挑战机制实验结果

可恢复挑战实验关注两个核心问题：一是二分定位轮次是否与理论复杂度一致；二是 recover 机制能否解决超时导致的争议流程停滞问题。

首先，在不同 `trace steps` 下观测到的二分轮次如下：

| Trace steps | Timeout | Max rounds | 平均二分轮次 | 理论log2轮次 | 恢复成功率 | 挑战成功率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 2 | 16 | 2.00 | 2.00 | 100.00% | 100.00% |
| 8 | 2 | 16 | 3.00 | 3.00 | 100.00% | 100.00% |
| 16 | 2 | 16 | 4.00 | 4.00 | 100.00% | 100.00% |
| 32 | 2 | 16 | 5.00 | 5.00 | 100.00% | 100.00% |
| 64 | 2 | 16 | 6.00 | 6.00 | 100.00% | 100.00% |
| 128 | 2 | 16 | 7.00 | 7.00 | 100.00% | 100.00% |

该结果表明，当前 challenge-step 确实实现了二分定位过程，而不是线性扫描争议轨迹。随着 `trace steps` 增大，争议定位轮次与理论上的 `log2(trace steps)` 基本一致，这为论文中关于“争议定位复杂度随轨迹长度呈对数增长”的论断提供了实验支撑。

其次，超时场景下 no recover 与 recover 的对照结果如下：

| 场景 | 检测率 | 挑战成功率 | Slashed比例 |
| --- | ---: | ---: | ---: |
| challenge_timeout_no_recover | 100.00% | 0.00% | 0.00% |
| challenge_timeout_recover | 100.00% | 100.00% | 100.00% |

上述对照说明：在无 recover 的情况下，系统虽然能够检测到超时异常，但挑战流程无法完成；在引入 recover 机制后，挑战能够继续推进并最终完成 slashing。因此，recoverable challenge 的作用不仅在于“发现错误”，更在于将“检测到异常但流程停滞”的状态推进为“恢复后继续仲裁并完成惩罚”的状态。

### 5.4 失败场景检测与 slashing 结果

失败场景实验用于验证系统在不同异常条件下的检测能力和惩罚结果。结果如下：

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

从上述结果可以归纳出三类现象：

1. **可检测但未进入成功 challenge/slashing 的场景**  
   例如 `attestation_invalid`、`da_proof_invalid`、`da_unavailable`。这些场景均实现了 `100%` 检测率，但挑战成功率和 slashed 比例为 `0%`，说明当前原型能够稳定识别这些异常，但其后续仲裁路径在现阶段仍主要表现为 challenge failure 或验证失败，而不是完整 slashing。

2. **可恢复并完成仲裁的场景**  
   `challenge_timeout_recover` 在检测率、挑战成功率和 slashed 比例上均达到 `100%`，说明 recover 机制在超时异常下能够有效恢复仲裁流程。

3. **可检测、可 challenge、可 slashing 的异常执行场景**  
   `response_tampered` 和 `trace_length_mismatch` 均达到 `100%` 检测率、`100%` 挑战成功率和 `100%` slashed 比例，说明在响应篡改、轨迹长度不一致等典型异常下，系统能够完成从异常发现到链上惩罚的完整闭环。

因此，从失败场景角度看，当前原型已经能够覆盖多类非 happy-path 条件，并且在关键异常类型下形成完整的“检测 - 挑战 - slashing”路径。

### 5.5 本地 EVM gasUsed 实测结果

Python 原型中的成本分析主要用于说明结构性趋势，而本地 EVM 实测则用于补充链上关键状态推进的真实 `gasUsed` 基线。当前测量环境为 Hardhat 本地测试链，样本级结果如下：

| Payload | register DA | submit | open | respond | step1 | recover | replay | resolve | finalize |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 113530 | 299051 | 283769 | 65886 | 93807 | 156891 | 135632 | 113402 | 33477 |
| 512 | 113530 | 299019 | 283769 | 65886 | 93807 | 156891 | 135632 | 113402 | 33477 |
| 2048 | 113518 | 299031 | 283769 | 65886 | 93807 | 156891 | 135632 | 113402 | 33477 |

进一步汇总后的平均 `gasUsed` 基线如下：

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

这些结果表明：

1. `submit rollup` 在 `payload=128 / 512 / 2048` 下基本保持稳定，说明当前链上提交成本主要对应 compact commit 的固定结构，而不是完整 payload 的线性上链；
2. `challenge open / recover / replay / resolve` 已经形成一组可独立测量的链上状态推进操作，说明交互式争议协议已经具备较明确的 Solidity 对应物；
3. recover 机制虽然引入额外链上开销（如 `challenge recover = 156891.00`），但它换来了异常场景下显著更高的挑战可完成性。

需要强调的是，这部分数据应被视为“本地合约实测基线”，而不能直接视为主网最终费用。真实主网部署成本仍会受到 calldata 定价、blob 价格、链上拥堵状态和网络环境等因素影响。

### 5.6 Sepolia 公开测试网部署结果

在本地 EVM 实测之外，当前 Solidity 原型已进一步部署到 Sepolia，表明系统已经从 Python 原型与本地链测试推进到公开测试网阶段。

部署参数如下：

| 参数 | 数值 |
| --- | --- |
| Network | `Sepolia` |
| Chain ID | `11155111` |
| disputeWindowSeconds | `60` |
| challengeTimeoutSeconds | `2` |
| maxBisectionRounds | `16` |
| 部署区块 | `10825904` |

Sepolia 合约地址如下：

| 合约 | Sepolia 地址 | 角色 |
| --- | --- | --- |
| MockTEEVerifier | `0xC42CB0Cf0D112Bd59E0f212F2DB2002ca50a8b6A` | 模拟 TEE attestation 链上验证 |
| MockDARegistry | `0xc42C64a7De05bf3ad4f1c75CbD8E0506F7De99Ff` | DA 根与可用性记录 |
| HybridTEERollup | `0xB9B72f10bB8aBC1ed090f1B0443Fe57189c497Fd` | compact commit、challenge、recover、replay、resolve |

该结果说明，当前项目已经具备以下证据链：

1. Python 原型验证了提交、挑战、恢复与 replay 的协议趋势；
2. Solidity 合约给出了关键链上路径的对应实现；
3. Hardhat 本地测试链提供了真实 `gasUsed` 基线；
4. Sepolia 部署证明该原型已经具备公开测试网对应物，而不再只是纯本地模拟。

关于源码验证状态，当前 `verify:sepolia` 已执行两次，但均返回 block explorer 侧的 `Connect Timeout Error`。这意味着部署和构造参数记录本身已经成功，不影响当前将部署区块、地址与 ABI 索引作为公开测试网部署证据使用；后续可在网络条件更稳定时继续重试验证流程。

## 六、阶段性结论

基于当前阶段实验，可以形成以下较为稳健的阶段性结论：

1. **`compact commit + DA` 能够显著降低链上数据提交成本。**  
   在高 payload 组（如 `payload=8192`）中，相比 full-onchain 路线，当前方案最佳降本比例达到 `96.33%`，说明轻量提交在高负载场景下具有明显优势。

2. **batch size 增大后，单笔摊销 gas 明显下降。**  
   该趋势说明当前方案更适合高频 DApp 的批量交互场景，批处理能够有效摊薄单笔提交成本。

3. **可恢复挑战机制能够解决 timeout 导致的争议流程停滞问题。**  
   对照结果显示，无 recover 时挑战成功率为 `0%`；引入 recover 后，挑战成功率与 slashed 比例均提升至 `100%`。

4. **在响应篡改、轨迹长度不一致等关键异常场景下，系统能够完成检测、挑战与 slashing。**  
   `response_tampered` 与 `trace_length_mismatch` 均实现了 `100%` 检测率、`100%` 挑战成功率和 `100%` slashed 比例，说明系统已具备处理典型异常执行行为的完整仲裁路径。

5. **原型已具备 Solidity 合约实现、本地 EVM `gasUsed` 实测和 Sepolia 部署证据。**  
   这说明当前工作已经超出纯 Python 模拟阶段，开始形成“原型趋势 - 链上基线 - 公开测试网对应物”的连续验证链路。

总体来看，当前实验结果已经能够支撑论文中的三条阶段性主张：  
其一，可恢复挑战协议增强了异常场景下的争议流程鲁棒性；其二，`compact commit + DA` 在高频 DApp 批量交互中表现出稳定的降本趋势；其三，当前原型已经具备向链上实现过渡的直接工程证据。

## 七、实验局限性

尽管当前阶段结果已经较为完整，但仍需明确以下局限性：

1. **TEE 部分为模拟原型。**  
   当前 attestation 与执行流程用于验证协议路径，不直接代表真实硬件 TEE 的安全边界。

2. **成本实验中的大部分结果来自 gas 估算模型。**  
   Python 成本实验主要用于比较结构性趋势，而非直接给出真实主网费用。

3. **本地 EVM 实测仍属于局部链上基线。**  
   虽然本地 EVM `gasUsed` 已比纯字节估算更进一步，但仍然是在 Hardhat 本地测试链中得到的，不等同于 Sepolia 或主网最终成本。

4. **Sepolia 部署证明的是可部署性，而非主网性能。**  
   公开测试网部署说明合约路径已经可上链，但真实公网环境下的网络状态、交易费用、区块拥堵和浏览器验证状态仍会影响最终表现。

5. **部分异常场景虽可稳定检测，但尚未全部进入完整 slashing 路径。**  
   例如 `attestation_invalid`、`da_unavailable`、`da_proof_invalid` 等场景当前更多体现为稳定检测与 challenge failure 路径，而不是统一的链上罚没闭环。

因此，当前阶段更适合将实验结果表述为：**用于验证趋势、协议合理性和原型可行性**，而不应过度外推为主网级性能结论。

## 八、后续工作计划

基于当前阶段结果，下一步工作将重点围绕以下几个方向展开：

1. **继续补充更多 payload、batch size、DA profile 的实验组合。**  
   在当前 `128 / 512 / 2048 / 8192` 的基础上，进一步扩展负载规模与参数组合，以增强成本实验的覆盖面和稳定性。

2. **将 gas 估算模型与本地 EVM 实测结果进一步对齐。**  
   在 Python 成本模型与 Solidity 本地实测之间建立更细的映射关系，使“趋势估算”与“链上基线”之间的口径更加统一。

3. **重试 Sepolia 合约源码验证。**  
   在网络状态更稳定时重新执行 `verify:sepolia`，补齐公开测试网浏览器侧的源码验证证据。

4. **增加真实链上交易样本。**  
   在 Sepolia 上进一步记录提交、挑战、恢复与 replay 等关键路径的公开测试网交易样本，为后续论文和答辩提供更直接的链上回执支持。

5. **完善论文中的实验章节和图表说明。**  
   将当前 `experiment_report`、本地 EVM gas 实测结果与 Sepolia 部署信息进一步转写为论文 `Evaluation` 与 `Discussion` 的正式段落，并优化图表说明文字。

6. **补充与相关扩容路线的对比分析。**  
   在 Hybrid TEE-Rollup 主线下，进一步与 Optimistic Rollup、ZK Rollup、State Channel 等方案进行机制与成本层面的对照分析，明确当前工作的适用边界与差异化价值。

## 附录：结果文件与部署信息

### A.1 核心结果文件

- `cost_grid.csv`
- `challenge_grid.csv`
- `failure_scenarios.csv`
- `summary.json`

### A.2 图表文件

- `figures/cost_payload_full_vs_compact.png`
- `figures/challenge_rounds.png`
- `figures/recovery_success.png`
- `figures/da_profile_amortized_gas.png`
- `figures/failure_detection.png`

### A.3 EVM 与部署记录

- `paper_outputs/evm_gas/measured_gas_report.md`
- `paper_outputs/evm_gas/measured_gas_summary.json`
- `evm/deployments/sepolia.json`
- `evm/deployments/sepolia_abis/address_index.json`

### A.4 关键部署信息摘要

| 项目 | 内容 |
| --- | --- |
| 部署网络 | `Sepolia` |
| 部署区块 | `10825904` |
| MockTEEVerifier | `0xC42CB0Cf0D112Bd59E0f212F2DB2002ca50a8b6A` |
| MockDARegistry | `0xc42C64a7De05bf3ad4f1c75CbD8E0506F7De99Ff` |
| HybridTEERollup | `0xB9B72f10bB8aBC1ed090f1B0443Fe57189c497Fd` |

