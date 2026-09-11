# 面向高频 DApp 的 Hybrid TEE-Rollup 可恢复挑战协议与轻量 DA 成本评估
**英文题目：** Recoverable Challenge Protocol and Lightweight DA Cost Evaluation for Hybrid TEE-Rollups in High-Frequency DApps
**作者：** 杨帆（占位）
**单位：** 待补充

## 摘要

高频 DApp，如元宇宙状态同步、去中心化社交交互和链上 AI 推理服务，要求系统同时具备低交互成本、较低延迟和异常情况下的可验证性。全链上执行虽然可验证性强，但难以承受高频负载；完全链下执行虽能降低成本，却削弱了公开可验证与可追责能力；单纯依赖 TEE 又会引入硬件信任与可用性风险。本文不提出一个全新的 Rollup 架构，而是在已有 Hybrid TEE-Rollup 思路下，研究高频 DApp 场景中的可验证低成本交互机制，并将问题明确限定在研究原型和课程论文评估范围内。具体而言，本文设计并实现了一个研究原型，重点推进三项机制：一是 recoverable challenge，将交互式挑战从错误检测扩展为异常场景下可恢复并完成仲裁的状态机；二是 evidence-carrying compact commit，将轻量提交与 DA Merkle root、payload hash、Merkle proof 和 challenge evidence 绑定为最小证据入口；三是 DA-aware cost amortization，从 payload size、batch size 和 DA route 的共同作用下分析成本摊销。实验表明，compact commit 的字节开销近似固定，而 full payload 随负载规模近似线性增长；在高 payload 设置下，compact commit + DA 相对 full-onchain 呈现明显降本趋势；recover 机制将 timeout 场景下的 challenge success 从 0% 提升到 100%；二分定位轮次与 log2(trace steps) 基本一致。同时，本文补充威胁模型、成本公式、实验设置和轻量性质讨论，使实验结果与论文主张形成更清晰的对应关系。本文还给出本地 EVM gasUsed 基线与 Sepolia 部署记录，作为阶段性链上对应物证据。需要强调的是，当前系统仍为研究原型，其中 TEE 为 simulated TEE，DA 为 mock/verifiable DA 原型，本地 EVM 与 Sepolia 结果不能直接外推为主网生产性能结论。

**关键词：** Hybrid TEE-Rollup；交互式挑战；数据可用性；高频 DApp；成本摊销；故障恢复

## 1 Introduction

区块链系统在面向高频 DApp 时面临一个结构性矛盾：应用希望获得接近传统互联网服务的低延迟、高吞吐和低单次交互成本，但底层系统又必须维持公开可验证、去中心化安全和异常可追责能力。对于元宇宙资产交互、去中心化社交状态更新、链上 AI 推理请求等场景而言，单次交互可能价值较低，但请求频率高、状态连续性强。如果每一次交互都以完整链上执行和全量数据上链的方式处理，系统成本会快速放大；如果完全转向链下服务，则执行正确性、数据可用性和异常追责又缺乏足够的公开验证路径。

Rollup 技术为这一矛盾提供了一类中间路线。ZK-Rollup 通过有效性证明获得较强验证能力，但证明生成和系统实现成本较高；Optimistic Rollup 降低了常规执行路径成本，但挑战窗口和争议处理流程会带来延迟。TEE-Rollup 或 Hybrid TEE-Rollup 则试图利用可信执行环境加速链下执行，并通过链上提交和挑战机制保留异常情况下的仲裁能力。然而，TEE 本身并不应被视为绝对可信：硬件实现、宿主环境、I/O 操控、数据可用性和挑战超时都可能成为系统风险来源。因此，Hybrid TEE-Rollup 的关键问题不只是“如何把执行放到 TEE 中”，而是如何在低成本链下执行之后，仍然保留足够的可验证证据入口和异常恢复能力。

本文基于这一背景，将研究切口收敛为两个具体问题。第一，交互式挑战在异常场景下是否能够恢复推进。传统 challenge 机制通常关注错误是否可被发现，而在 timeout、中断、执行轨迹不一致或数据不可用时，争议流程可能停滞。对于高频 DApp 而言，仅能检测异常并不足够，系统还需要将异常推进到可仲裁、可结算的状态。第二，轻量提交如何在降低链上成本的同时保留验证能力。若 compact commit 只是一个孤立哈希，则虽然节省链上空间，却难以支撑后续挑战；因此，轻量提交需要与 DA root、payload hash、Merkle proof 和 challenge evidence 建立明确关联。

围绕上述问题，本文的课程论文贡献包括：设计可恢复交互式挑战原型，补充 evidence-carrying compact commit 与字段级 DA proof，建立 DA-aware 成本模型与实验网格，并给出 Python 原型、本地 EVM gasUsed 和 Sepolia 部署记录构成的阶段性证据链。本文所有结论均限定为研究原型结果，不声称真实 TEE 安全、生产级 DA 或主网性能。

**表 1  本文机制推进点与研究作用**

| 机制推进 | 核心作用 | 论文定位 |
| --- | --- | --- |
| Recoverable Challenge | 在 timeout 或中断后恢复争议流程 | 提升 challenge liveness |
| Evidence-Carrying Compact Commit | 绑定 state/output/proof/DA root | 形成最小证据入口 |
| Fault Taxonomy | 区分 attestation、DA、timeout、replay 和 trace 故障 | 明确异常责任边界 |
| DA-aware Cost Amortization | 联合 payload、batch 和 DA route 分析成本 | 支撑高频 DApp 成本论证 |

## 2 Background

Rollup 是区块链扩容中的重要路线，其基本思想是将大量执行过程移至链下完成，并将状态承诺、证明或争议入口提交到链上。ZK-Rollup 通过有效性证明保证提交状态的正确性，具有较强的验证属性，但证明生成、验证电路设计和复杂系统实现带来较高成本。Optimistic Rollup 假设链下执行结果默认正确，只有在挑战期内出现争议时才进入 fraud proof 或交互式验证流程，因此常规路径成本较低，但结算延迟和挑战机制复杂度成为关键限制。

TEE attestation 提供了一种链下执行可信性的补充方式。可信执行环境可以在隔离环境中执行程序，并对输入、输出、环境标识和 nonce 生成证明，使外部验证者能够确认某一输出来自指定执行环境。然而，TEE 并非无条件可信。硬件漏洞、实现缺陷、宿主环境操控和可用性问题都可能影响系统安全。因此，TEE 更适合作为降低正常路径验证成本的组件，而不应替代链上挑战、数据可用性和故障追责机制。

Optimistic challenge 是 Rollup 系统中处理异常的重要机制。典型流程包括提交状态承诺、开启挑战、交互式缩小争议范围，并在必要时执行单步重放或链上仲裁。对于长执行轨迹，二分定位能够将争议定位复杂度从线性扫描降低到对数轮次。然而，challenge 本身也可能遭遇 timeout、应答缺失或证据不可用等异常，因此其活性和恢复性同样需要被纳入协议设计。

Data Availability 关注链下或链外数据是否可被需要的验证者获得。模块化区块链和 LazyLedger 等路线强调将数据可用性从执行验证中解耦，使共识层主要负责数据排序和可用性保证。对于 Hybrid TEE-Rollup 而言，DA 的作用不仅是降低存储成本，还要支撑后续 challenge 的证据回溯。因此，compact commit 必须与 DA proof 建立可验证联系。

## 3 Motivation

纯全链上执行并不适合高频 DApp。若将每一次社交状态更新、元宇宙交互或 AI 推理请求都作为完整链上交易执行并存储，则链上 calldata、存储和执行成本会随请求数量快速增长。对于大量小额、高频、状态连续的交互而言，这种成本结构难以长期维持。

纯链下执行同样不足。中心化服务或普通链下节点可以降低成本，但用户和外部观察者难以验证执行结果。一旦执行者篡改 response、隐藏 payload、延迟应答或在争议中失联，系统缺少公开可验证的仲裁路径。对于区块链应用而言，这会削弱去中心化系统最核心的可信边界。

纯 TEE 路线也存在局限。TEE 能够降低链下执行的信任成本，但不能消除所有故障。TEE attestation 可能无效，执行者可能提交与 DA payload 不一致的结果，宿主环境可能影响可用性，挑战过程也可能因 timeout 停滞。因此，将 TEE 作为唯一安全来源并不稳健。更合理的方式是让 TEE 服务于正常路径的低成本执行，同时保留链上提交、DA 证明和 challenge 仲裁作为异常路径。

纯 Optimistic Rollup 机制则面临挑战窗口和异常处理问题。传统 optimistic 机制能够在争议出现时启动验证，但如果 challenge session 因超时或应答中断而停滞，系统可能只能发现异常，却无法完成仲裁。对于高频 DApp，协议活性与可恢复性是实际可用性的组成部分。因此，本文将 recoverable challenge 作为独立研究问题：challenge 不应只是错误检测工具，而应是异常场景下仍可恢复推进的容错状态机。

## 4 Problem Statement and Threat Model

本文关注的问题可以概括为：在高频 DApp 场景中，如何让链下执行结果以较低链上成本提交，同时在异常发生时仍能被公开验证、恢复推进并完成仲裁。该问题同时包含成本、可验证性和活性三个维度。成本维度要求链上提交不随完整 payload 线性增长；可验证性维度要求 compact commit 能指向可检查的 DA payload 与证明；活性维度要求 challenge 在 timeout 后不永久停滞。

本文假设执行者或提交者可能提交错误 response、篡改 DA payload、提供无效 attestation，或在挑战流程中延迟响应。DA 层可能出现 payload 缺失、Merkle proof 损坏或 root 不一致。挑战流程本身也可能因超时、中断或 trace 长度不一致而无法自然进入 resolve 阶段。验证者、挑战者或 watchdog 可以观察链上提交和 DA 证据，并在发现异常时发起或恢复挑战。

本文不覆盖真实硬件 TEE 的侧信道攻击、远程证明供应链、真实 DA 网络的经济安全、主网 MEV 或拥堵环境下的费用波动，也不证明完整 Rollup 安全性。原型中的 TEE 为 simulated TEE，DA 为 mock/verifiable DA registry，Sepolia 部署仅用于说明合约具有公开测试网可部署性。该边界是本文论证成立的前提。

## 5 System Design

本文原型采用三层结构：执行层、数据层和验证层。整体逻辑是链下执行、链上留痕、异常时可恢复验证。该设计不声称实现完整生产级 Rollup，而是用于验证 Hybrid TEE-Rollup 路线下 recoverable challenge 与 verifiable DA 的机制可行性。

![图 1  Hybrid TEE-Rollup 原型系统架构](../figures/system_architecture.png)

**图 1  Hybrid TEE-Rollup 原型系统架构**

如图 1 所示，本文系统由高频 DApp 请求入口、链下执行层、数据可用性层、链上提交层和验证仲裁层组成。执行层在 simulated TEE 中生成 response 与 attestation；数据层保存完整 payload、payload hash、字段级 Merkle proof 与 DA root；链上提交层仅保存 compact commit；验证仲裁层在异常时通过 challenge、recover、replay 和 resolve 推进状态。该结构的关键不是把所有计算都移入链上，而是在正常路径保留低成本提交，在异常路径保留可追溯证据入口。

### 5.1 执行层

执行层负责处理高频 DApp 请求。当前原型采用 deterministic mock model 或可选模型后端生成响应，并使用 simulated TEE attestation 对输入哈希、输出哈希、nonce 和执行环境标识进行绑定。attestation 的作用是为链下执行结果提供最小可信摘要，使后续验证层能够检查提交结果是否与声明的执行过程一致。

需要明确的是，当前 TEE 为模拟实现，并不代表真实 SGX、TDX 或其他硬件 TEE 的安全保证。本文使用 simulated TEE 的目的，是在研究原型中建立“链下执行摘要—链上提交—异常挑战”的接口关系，而不是证明真实硬件安全。

### 5.2 数据层

数据层的核心是 evidence-carrying compact commit。系统不将完整 payload 全量上链，而是在链上提交精简结构：state_root、output_hash、proof_hash、da_pointer 和 da_merkle_root。其中，state_root 表示输入、输出和环境摘要绑定后的状态承诺；output_hash 绑定执行结果；proof_hash 绑定 attestation 证明；da_pointer 指向链外 DA payload；da_merkle_root 则为字段级 DA proof 提供根承诺。

DA entry 中保存完整 payload 及其可验证结构，包括 prompt、response、attestation、payload hash、leaf hashes、Merkle root 和字段级 Merkle proof。这样，compact commit 不再只是为了降低链上字节数的摘要，而成为后续 challenge 的最小证据入口。当验证者需要检查 response、prompt 或 attestation 是否被篡改时，可以通过 DA pointer 获取 payload，并通过 Merkle proof 与链上 da_merkle_root 进行一致性验证。

### 5.3 验证层

验证层负责处理异常路径。当前原型实现了 challenge open、respond、step、recover、replay 和 resolve 等状态推进。其目标不是将所有执行都搬到链上，而是在出现争议时，通过证据加载、二分定位、单步重放和仲裁结算，将异常状态推进为可解释的结果。

验证层同时承担 fault taxonomy 的职责。本文将故障细分为 attestation fault、DA fault、timeout fault、replay fault 和 trace inconsistency。不同故障对应不同的观察和处理路径。例如，DA unavailable 表明数据层无法提供 payload；DA proof invalid 表明 payload 与链上 root 不一致；trace length mismatch 表明执行轨迹与声明结构不一致；response tampering 则可能同时导致 payload hash、attestation 和 state root mismatch。

在 Solidity 映射中，原型包含 MockTEEVerifier、MockDARegistry、MerkleVerifier 和 HybridTEERollup 等合约，用于表达链上状态推进和最小验证逻辑。本地 EVM 合约并非 Python 原型的逐行移植，而是抽取适合链上表达的提交、验证、挑战、恢复和结算路径。

## 6 Recoverable Challenge Protocol

Recoverable Challenge Protocol 的目标，是将 challenge 从一次性错误检测流程扩展为异常场景下可恢复推进的协议状态机。其基本状态包括 PENDING、OPEN、RESPONDED、NARROWING、RECOVERED、READY_FOR_REPLAY、REPLAYED、RESOLVED、SLASHED 和 FINALIZED。

![图 2  Recoverable Challenge 协议流程](../figures/recoverable_challenge_flow.png)

**图 2  Recoverable Challenge 协议流程**

当交易处于 PENDING 状态时，挑战者可以调用 open 进入 OPEN 状态。系统加载 compact commit、DA status 和相关 mismatch evidence。随后，被挑战方进入 respond 阶段，提供其对争议的回应。若争议涉及执行轨迹，协议进入 step 阶段，通过 bisection narrowing 缩小争议区间。对于长度为 n 的 trace，理想情况下定位轮次接近 log2(n)，这避免了线性扫描长执行轨迹。

当争议区间被缩小到单步时，协议进入 single-step replay。replay 阶段比较 expected hash 与 claimed hash，判断局部执行是否一致。如果重放失败，resolve 阶段可以将交易标记为 SLASHED；如果重放通过，则挑战不成立或进入相应结算逻辑。

recover 是本文强调的关键机制。在普通 challenge 中，如果 session 超时，流程可能停滞在中间状态，导致系统只能检测异常而无法完成仲裁。Recoverable challenge 引入 watchdog/operator 恢复路径，使超时 session 能够被恢复并继续 step、replay 和 resolve。该机制的核心价值是 liveness：它使 challenge 能够从“异常被发现”推进到“异常被处理完”。同时，recover 不改变争议事实本身；它既不替换 expected trace，也不覆盖 claimed trace，更不直接决定 slashing，而只是把状态机从 timeout 后的停滞状态恢复到可继续仲裁的状态。因此，本文将 recover 表述为挑战活性补强，而非新的正确性证明。

协议流程可分为三条路径。第一是正常路径：若挑战期内没有有效争议，交易最终进入 FINALIZED。第二是可仲裁异常路径：若 response tampered 或 trace length mismatch 等执行相关故障出现，协议通过 open、respond、step、replay 与 resolve 完成争议定位和结算。第三是 timeout 恢复路径：若挑战过程因超时中断，watchdog 或 operator 可以调用 recover 将会话推进到 RECOVERED，并继续后续 replay 与 resolve。该划分有助于避免将“异常检测”“活性恢复”和“经济惩罚”混写为同一性质。

### 6.1 Correctness and Property Discussion

性质一，DA proof 绑定性质。compact commit 中的 da_merkle_root 与 DA entry 中的字段级 Merkle proof 绑定，因此 prompt、response 或 attestation 字段被替换后，会导致 payload hash、leaf hash 或 Merkle proof 与链上 root 不一致。该性质不依赖真实 DA 网络，只说明当前 verifiable DA 结构能检测字段篡改。

性质二，recover 的活性性质。recover 操作的目标是恢复超时挑战会话，使其继续进入 step、replay 和 resolve；它不修改 expected trace、claimed trace 或 replay mismatch 的事实。因此，recover 不改变争议判断本身，而是避免 timeout 让争议流程永久停在中间状态。

性质三，二分定位性质。对于长度为 n 的执行 trace，challenge-step 每轮缩小争议区间，理想轮次接近 log2(n)。本文实验中 trace steps 为 4、8、16、32、64、128 时，平均二分轮次分别为 2、3、4、5、6、7，与理论对数趋势一致。

## 7 DA Cost Model

本文的成本模型关注 full-onchain 与 compact commit + DA 在高频场景下的结构性差异。full-onchain 路线将完整 payload 作为链上数据提交，其成本随 payload size 增大近似线性增长。compact commit 路线则只将固定摘要结构提交到链上，将完整 payload 放入 DA 层，并通过 DA root 和 Merkle proof 保留验证能力。

本文比较四类 DA route：full-onchain calldata、compact external DA、compact EIP-4844-like 和 compact modular DA sampling。成本分析不是单一变量问题。payload size 决定 full payload 上链成本增长速度；batch size 决定固定提交开销能否被摊薄；DA route 决定 payload 放在不同数据层时的边际成本。为避免将模型趋势误写为真实价格，本文将该模型称为 lightweight DA cost model：它只保留与研究问题直接相关的提交字节、DA profile 和 batch amortization，而不建模实时 gas market、blob base fee、跨域消息费用、主网拥堵或 DA 网络经济安全。

为便于说明，本文采用如下抽象成本表达：C_total = C_commit + C_DA + p_challenge * C_challenge。其中 C_commit 表示链上 compact commit 或 full payload 提交成本，C_DA 表示不同 DA route 下的数据成本，C_challenge 表示发生争议时的挑战、恢复、重放和结算成本，p_challenge 表示争议发生概率。批处理后单笔摊销成本为 C_amortized = C_total / batch_size。当前实验主要比较不同 route 在相同参数下的结构性趋势，而不估计真实业务中的 p_challenge。

在本文实验中，full-onchain calldata 代表将完整 payload 直接计入链上数据成本；compact external DA、compact EIP-4844-like 和 compact modular DA sampling 则代表三类不同 DA profile 下的外部或模块化数据路径。它们共享相同的 compact commit 字节结构，但使用不同的 DA gas per byte 参数。该表达不用于给出主网精确费用，而用于比较不同提交策略在相同参数下的结构性趋势。当前 Python prototype 中的成本实验是配置化估算模型，本地 EVM gasUsed 则用于补充链上状态推进基线，两者在 Evaluation 中需要明确区分。

## 8 Evaluation

本节围绕五个研究问题组织实验结果，而不是仅按结果文件罗列数据：RQ1，evidence-carrying compact commit 是否能够降低链上提交规模；RQ2，batch size 增大后，DA-aware cost model 下的单笔摊销成本是否下降；RQ3，recoverable challenge 是否改善 timeout 场景下的仲裁活性；RQ4，在不同 failure scenario 中，哪些故障只能被检测或拒绝，哪些故障可以进入 challenge + slashing 闭环；RQ5，Solidity 原型、本地 EVM gasUsed 和 Sepolia 部署能否支撑“链上对应物”这一阶段性主张。为避免证据层次混淆，本文将 Python prototype / JSON ledger / simulated TEE 视为机制验证，将 DA-aware cost model 视为配置化估算趋势，将 Hardhat 本地 EVM gasUsed 视为链上状态推进基线，将 Sepolia 部署仅视为 deployability evidence。

本文成本实验使用如下抽象模型：

`C_total = C_commit + C_DA + p_challenge * C_challenge`

`C_amortized = C_total / batch_size`

其中，`C_commit` 表示链上提交 compact commit 或 full payload 的成本，`C_DA` 表示 DA route 对完整 payload 的数据成本，`C_challenge` 表示发生争议时 challenge、recover、replay 与 resolve 的成本，`p_challenge` 表示争议发生概率。当前实验主要比较无争议常规路径下不同提交策略的结构性趋势，因此未估计真实业务中的 `p_challenge`。DA profile 参数来自实验脚本配置：`full_onchain_calldata` 的 on-chain gas per byte 为 16.0，DA gas per byte 为 0；`compact_external_da` 的 on-chain gas per byte 为 16.0，DA gas per byte 为 2.2；`compact_eip4844_like` 的 on-chain gas per byte 为 16.0，DA gas per byte 为 0.9；`compact_modular_da_sampling` 的 on-chain gas per byte 为 16.0，DA gas per byte 为 0.45。这些参数仅用于配置化估算，不代表以太坊主网、blob 市场或任何真实 DA 网络的实时价格。

### 8.1 RQ1: compact commit 是否降低链上提交规模

**Setup.** RQ1 使用 Python prototype 生成提交样本，并比较 full payload 与 compact commit 的 UTF-8 canonical JSON 字节数。实验覆盖 payload size 128、512、2048、8192，prompt length 64、256，每组参数 100 个样本。该实验运行在 JSON ledger 和 simulated TEE 环境中，用于验证提交结构和字节规模趋势。

**Metrics.** 本实验使用 `full_bytes`、`compact_bytes` 和 `byte_reduction_ratio = (full_bytes - compact_bytes) / full_bytes`。其中 `full_bytes` 表示把完整 prompt、response、attestation 和相关字段作为 payload 提交时的字节规模，`compact_bytes` 表示只提交 `state_root`、`output_hash`、`proof_hash`、`da_pointer` 和 `da_merkle_root` 等摘要字段时的字节规模。

**Results.** 在当前实现中，compact commit 的平均规模约为 406 bytes，基本不随 payload size 增长；相对地，full payload bytes 随 payload size 增大近似线性上升。例如，当 payload size 从 128 增至 8192 时，full bytes 从约 1682.84 / 1876.84 增至约 50068.84 / 50262.84，而 compact bytes 仍保持在约 406 bytes。

**Takeaway.** 该结果支持一个有限但清晰的结论：在当前原型的数据结构下，evidence-carrying compact commit 能够将链上提交规模从完整业务 payload 中解耦出来，并把链上提交规模主要限制在固定摘要结构附近。

**Limitation.** 该实验只说明当前 Python prototype 中的数据结构趋势，不等价于真实链上 calldata、storage layout 或 ABI 编码后的完整成本；也不说明真实 TEE attestation 或真实 DA 网络中的证明大小。

![图 3  full payload 与 compact commit 的字节规模对比](../figures/cost_payload_full_vs_compact.png)

**图 3  full payload 与 compact commit 的字节规模对比**

### 8.2 RQ2: batch size 增大后摊销成本是否下降

**Setup.** RQ2 使用 DA-aware cost model 比较四类提交路线：`full_onchain_calldata`、`compact_external_da`、`compact_eip4844_like` 和 `compact_modular_da_sampling`。实验覆盖 payload size 128、512、2048、8192，prompt length 64、256，batch size 1、10、100、1000，每组变量 100 个样本，共生成 3200 条成本记录。

**Metrics.** 主要指标为 `amortized_gas = total_gas / batch_size` 和 `reduction_ratio = (full_onchain_gas - target_gas) / full_onchain_gas`。其中 `total_gas` 由配置化 profile 计算得出，而不是来自主网交易回执。

**Results.** 当 batch size 增大时，各 DA profile 下的单笔摊销成本均明显下降。在 payload=8192、prompt length=64 的配置下，`full_onchain_calldata` 的单笔估算 gas 从 batch size=1 时的 801101.44 下降到 batch size=1000 时的 801.10；`compact_modular_da_sampling` 从 29026.98 下降到 29.03。在 payload=8192 时，modular DA profile 相对 full-onchain 的最佳降本约为 96.33%。

**Takeaway.** 该结果支持“compact commit + DA 在高 payload 与批处理场景下具有稳定降本趋势”这一阶段性判断。尤其在高频 DApp 中，批处理能够摊薄固定提交成本，使单笔请求承担的估算成本随 batch size 增大而下降。

**Limitation.** 96.33% 只是给定 cost model 和 DA profile 参数下的趋势结果，不能写成主网真实降本比例。真实公网费用还受 calldata 定价、blob 价格、交易拥堵、DA 网络实现和业务争议率影响。

![图 4  不同 DA profile 下的摊销 gas 趋势](../figures/da_profile_amortized_gas.png)

**图 4  不同 DA profile 下的摊销 gas 趋势**

### 8.3 RQ3: recoverable challenge 是否改善 timeout 场景下的仲裁活性

**Setup.** RQ3 使用 Python prototype 的 challenge 状态机，覆盖 trace steps 4、8、16、32、64、128，challenge timeout 为 2 秒，max bisection rounds 为 16。实验比较 `challenge_timeout_no_recover` 与 `challenge_timeout_recover` 两类场景，并记录 challenge 是否能够继续推进到 replay 与 resolve。

**Metrics.** 主要指标包括 `avg_bisection_rounds`、`avg_expected_log2_rounds`、`recovery_success_rate`、`challenge_success_rate` 和 `slashed_rate`。其中 `avg_bisection_rounds` 用于观察争议定位复杂度，`challenge_success_rate` 与 `slashed_rate` 用于观察仲裁是否完成。

**Results.** 在 trace steps 为 4、8、16、32、64、128 时，平均二分轮次分别为 2、3、4、5、6、7，与 `log2(trace steps)` 基本一致。timeout 对照结果显示，`challenge_timeout_no_recover` 场景下 detection rate 为 100%，但 challenge success 为 0%，slashed 为 0%；`challenge_timeout_recover` 场景下 challenge success 和 slashed 均为 100%。

**Takeaway.** 该结果说明 recover 的核心价值是 liveness：在 timeout 已被检测但流程无法自然完成时，recover 能够让 challenge session 继续进入后续 step、replay 与 resolve。换言之，recoverable challenge 不只是增加一个接口，而是将“可检测但停滞”的异常状态推进为“可完成仲裁”的状态。

**Limitation.** 当前 challenge trace、expected hash、claimed hash 和部分 replay evidence 仍由原型逻辑或链下流程提供。该实验不能证明完整链上 fraud proof、FPVM 或真实 ML/TEE 执行验证的安全性。

![图 5  二分挑战轮次与 trace steps 的关系](../figures/challenge_rounds.png)

**图 5  二分挑战轮次与 trace steps 的关系**

![图 6  timeout recover 对挑战完成率的影响](../figures/recovery_success.png)

**图 6  timeout recover 对挑战完成率的影响**

### 8.4 RQ4: failure scenario 中哪些只能检测，哪些可以 slashing

**Setup.** RQ4 使用 failure scenario 实验，共覆盖 8 类场景，每类 100 个样本，共 800 条记录。场景包括 `normal`、`attestation_invalid`、`da_unavailable`、`da_proof_invalid`、`response_tampered`、`trace_length_mismatch`、`challenge_timeout_no_recover` 和 `challenge_timeout_recover`。

**Metrics.** 主要指标为 `detection_rate`、`challenge_success_rate` 和 `slashed_rate`。为了避免将不同异常混为一谈，本文将失败场景分为四类：Normal path，Detectable but not unified slashing，Challenge + slashing，以及 Timeout liveness comparison。

**Results.** Normal path 中，`normal` 不触发异常检测或 slashing。Detectable but not unified slashing 类包括 `attestation_invalid`、`da_unavailable` 和 `da_proof_invalid`，这些场景检测率均为 100%，但 challenge success 与 slashed 均为 0%，说明当前原型主要实现检测或拒绝路径。Challenge + slashing 类包括 `response_tampered` 和 `trace_length_mismatch`，二者 detection rate、challenge success 和 slashed rate 均为 100%。Timeout liveness comparison 中，无 recover 时 challenge success 为 0%，recover 后 challenge success 和 slashed 均为 100%。

**Takeaway.** 该结果支持一个分层结论：当前原型并非对所有 fault 都实现统一 slashing，而是已经对响应篡改、trace 不一致和 timeout recovery 形成较完整闭环；对 attestation fault 和 DA fault，则主要体现为稳定检测、拒绝或报告能力。

**Limitation.** 这类分类说明当前 fault taxonomy 尚未完全闭环。特别是 DA unavailable、DA proof invalid 和 attestation invalid 后续应进一步区分“直接拒绝”“触发恢复”“进入链上仲裁”或“经济惩罚”的条件。

![图 7  失败场景检测与仲裁结果](../figures/failure_detection.png)

**图 7  失败场景检测与仲裁结果**

**表 2  失败场景分类与当前证据边界**

| 类别 | 场景 | 当前结果 | 证据边界 |
| --- | --- | --- | --- |
| Normal path | normal | 不触发检测或 slashing | 说明正常路径不误报 |
| Detectable but not unified slashing | attestation_invalid, da_unavailable, da_proof_invalid | 检测率 100%，challenge success/slashed 为 0% | 说明可检测或拒绝，不说明已统一惩罚 |
| Challenge + slashing | response_tampered, trace_length_mismatch | detection/challenge success/slashed 均为 100% | 说明典型执行异常可进入闭环 |
| Timeout liveness comparison | challenge_timeout_no_recover vs challenge_timeout_recover | no recover 为 0%，recover 后为 100% | 说明 recover 改善仲裁活性 |

### 8.5 RQ5: Solidity、本地 EVM 与 Sepolia 是否支撑链上对应物主张

**Setup.** RQ5 使用 Solidity 原型和 Hardhat 本地测试链测量关键操作 gasUsed。Solidity 原型包含 MockTEEVerifier、MockDARegistry、MerkleVerifier 和 HybridTEERollup。测量脚本覆盖 payload size 128、512、2048，并记录 register DA、submit rollup、challenge open、respond、step、recover、replay、resolve 和 finalize 的 gasUsed。同时，项目记录了 Sepolia 部署地址、chain id、构造参数和部署区块。

**Metrics.** 本地 EVM 指标为各关键函数调用的 gasUsed。Sepolia 证据包括 chain id、部署区块、合约地址和 ABI/address index。二者分别对应“本地链上状态推进基线”和“公开测试网可部署性证据”。

**Results.** 本地 EVM 平均 gasUsed 包括：register DA 113526.00，submit rollup 299033.67，challenge open 283769.00，challenge respond 65886.00，challenge step 93807.00，challenge recover 156891.00，challenge replay 135632.00，challenge resolve 113402.00，finalize 33477.00。Sepolia 部署记录显示 network 为 Sepolia，chain id 为 11155111，部署区块为 10825904；MockTEEVerifier、MockDARegistry 和 HybridTEERollup 分别已记录部署地址。源码验证曾因 block explorer connect timeout 未完成。

**Takeaway.** 这些结果支持“当前机制具有链上对应物”的阶段性主张：Python prototype 中的提交、挑战、恢复、重放和结算路径已被抽取为 Solidity 合约中的状态推进操作，并可在 Hardhat 本地链上得到 gasUsed 基线；同一组核心合约也已部署到 Sepolia。

**Limitation.** 本地 EVM gasUsed 不能等价为公网费用，Sepolia 部署也不能说明生产可用性、主网性能或经济安全。当前 Sepolia 证据仅支持 deployability evidence，不支持“已在真实生产网络中验证”的结论。

**表 3  本地 EVM 关键路径平均 gasUsed**

| 操作 | 平均 gasUsed | 解释 |
| --- | ---: | --- |
| register DA | 113526.00 | MockDARegistry 记录 payload hash 与 DA root |
| submit rollup | 299033.67 | compact commit 提交路径 |
| challenge open | 283769.00 | 打开争议并加载证据 |
| challenge respond | 65886.00 | 被挑战方响应 |
| challenge step | 93807.00 | 二分定位的单轮推进 |
| challenge recover | 156891.00 | 恢复超时挑战会话 |
| challenge replay | 135632.00 | 单步重放仲裁 |
| challenge resolve | 113402.00 | 结算争议结果 |
| finalize | 33477.00 | 挑战期后最终确认 |

**表 4  Sepolia 部署信息**

| 项目 | 数值 |
| --- | --- |
| Network / Chain ID | Sepolia / 11155111 |
| 部署区块 | 10825904 |
| MockTEEVerifier | 0xC42CB0Cf0D112Bd59E0f212F2DB2002ca50a8b6A |
| MockDARegistry | 0xc42C64a7De05bf3ad4f1c75CbD8E0506F7De99Ff |
| HybridTEERollup | 0xB9B72f10bB8aBC1ed090f1B0443Fe57189c497Fd |

### 8.6 Reproducibility and Evidence Types

Python 原型位于 `project_code/tee_rollup_demo`，正式实验脚本为 `project_code/scripts/run_paper_experiments.py`，输出 `cost_grid.csv`、`challenge_grid.csv`、`failure_scenarios.csv`、`summary.json` 和 figures 目录。本地 EVM gas 脚本为 `project_code/evm/scripts/measure_gas.js`，输出 `paper_outputs/evm_gas/measured_gas_report.md` 与 `measured_gas_summary.json`。Sepolia 部署记录位于 `project_code/evm/deployments/sepolia.json`。

复现实验可使用以下命令：`python -m unittest discover -s tests -v`；`python scripts/run_paper_experiments.py --clean --samples 100 --payload-sizes 128,512,2048,8192 --batch-sizes 1,10,100,1000 --trace-steps 4,8,16,32,64,128`；在 `project_code/evm` 目录下运行 `npm.cmd test` 和 `npm.cmd run measure:gas`。上述命令分别对应机制验证、配置化成本趋势和本地 EVM 状态推进基线，不能相互替代。

## 9 Discussion and Limitations

本文工作仍有明确边界。第一，当前 TEE 为 simulated TEE。原型中的 attestation 使用模拟方式绑定输入、输出、nonce 和执行环境标识，其目的在于验证“链下执行摘要 - 链上提交 - 异常挑战”的协议接口，而不是证明真实 SGX、TDX、CSV 或其他硬件 TEE 的安全性。真实 TEE 部署还需要处理远程证明格式、硬件漏洞、侧信道攻击、宿主 I/O 操控和多厂商 TEE 信任假设。

第二，当前 DA 为 mock/verifiable DA 原型。系统实现了 DA root、payload hash、字段级 Merkle proof 和可用性状态记录，但并未接入 Celestia、EigenDA 或其他真实 DA 网络。因此，本文只能说明 compact commit 与 verifiable DA structure 能形成可检查的证据入口，不能声称已经实现生产级 DA availability。

第三，Python cost model 是配置化估算。DA profile 中的 gas per byte 参数用于构造可比较的趋势模型，而不是主网 calldata、blob 或真实 DA 服务的实时价格。由此得到的 96.33% 降本只应表述为“给定 cost model 下的趋势结果”，不能外推为主网级或生产级费用结论。

第四，Hardhat gasUsed 是本地 EVM 基线。它说明 Solidity 原型中的 submit、challenge open、recover、replay、resolve 和 finalize 等关键路径具有链上状态推进对应物，并能被本地测试链测量；但它不等价于 Sepolia 或主网费用，也不覆盖公网拥堵、交易排序、blob 价格和跨合约部署环境差异。

第五，Sepolia 部署是公开测试网 deployability evidence。部署区块、合约地址和 ABI 索引说明当前合约可以部署到公开测试网，但源码验证曾受 block explorer connect timeout 影响，且尚未记录大规模 Sepolia 交互交易样本。因此，Sepolia 结果不能被解释为生产成熟度、主网性能或完整安全性的证明。

第六，fault taxonomy 尚未形成完全统一的 slashing 闭环。当前 response_tampered、trace_length_mismatch 和 challenge_timeout_recover 可以进入 challenge + slashing 路径；attestation_invalid、da_unavailable 和 da_proof_invalid 主要体现为检测、拒绝或报告能力。后续需要进一步明确不同 fault 的仲裁策略，例如哪些故障应直接拒绝，哪些故障需要 watchdog recovery，哪些故障需要链上 replay，哪些故障应触发经济惩罚。

第七，challenge replay 中部分 evidence 仍由链下提供。当前原型通过 expected hash、claimed hash、trace evidence 和 mismatch bits 支持 replay arbitration，但并未实现完整链上可验证执行环境、FPVM 或真实模型推理单步证明。因此，后续工作需要加强 evidence 的链上可验证性、形式化安全论证和跨实现一致性测试，避免 replay 结果过度依赖链下诚实生成的证据。

总体而言，本文结论应被理解为阶段性研究原型结论：它说明 recoverable challenge、evidence-carrying compact commit 和 DA-aware cost model 在当前实验条件下具有可行性和趋势支撑；它不说明系统已经成为完整生产级 Rollup，也不说明其具备真实 TEE 安全证明、真实 DA 网络安全或主网级性能保证。

## 10 Related Work

TEEROLLUP 提出了利用异构 TEE 降低 Rollup 验证成本并缩短提现延迟的系统设计，其核心包括 TEE 委员会、链上状态合约、挑战机制和数据可用性惩罚。本文受到 Hybrid TEE-Rollup 思路启发，但并不重做完整 TEEROLLUP 系统，而是聚焦异常场景下 challenge 的恢复性，以及 compact commit 与 verifiable DA 的成本和证据结构。换言之，本文的贡献位置不是替代既有 TEE-Rollup 架构，而是在其“TEE 快速路径 + 链上异常路径”的思想下，补充 timeout 后争议会话如何恢复推进、轻量提交如何保留 DA 证据入口、以及成本趋势如何以可复现实验方式表达。

OTR 和 Optimistic TEE-Rollups 关注如何将 TEE 与 optimistic verification 结合，尤其适用于链上生成式 AI 或模型推理结果验证。这类工作表明 TEE 可以作为快速路径，而 optimistic challenge 可作为异常路径。本文与其相近之处在于同样关注 TEE 与 challenge 的结合，差异在于本文强调 recoverable challenge 的 liveness，以及 DA payload 与 compact commit 之间的证据绑定。

opML 等工作研究如何通过 optimistic fraud proof 支持机器学习或大模型计算，通常包含二分定位、单步仲裁和链上虚拟机验证。本文借鉴交互式争议定位思想，但没有实现完整 FPVM 或真实 ML 执行证明，而是将 bisection replay 用于 Hybrid TEE-Rollup 原型中的异常仲裁。

Dynamic Fraud Proof 关注如何缩短无争议场景下的最终性，并在发现争议时动态延迟结算。该方向强调 challenge window 和验证者参与机制的动态调整。本文不提出完整动态最终性协议，而是在更小范围内研究 timeout 后 challenge session 如何恢复推进。

LazyLedger 和 Light Clients for Lazy Blockchains 等工作强调将数据可用性从执行验证中解耦，并通过数据可用性抽样支持模块化扩容。本文没有实现真实 DAS 网络，而是使用 mock DA 和 DA profile 建模 compact commit + verifiable DA 的成本与证据结构。本文的重点不是替代 DA 层，而是说明 Hybrid TEE-Rollup 中链上轻量提交必须与 DA 证明建立可验证联系。

EIP-4844 将 blob-carrying transaction 引入以太坊扩容路线，为 Rollup 数据发布提供了区别于传统 calldata 的成本结构。本文中的 compact EIP-4844-like profile 只抽象了“数据发布成本低于 full calldata”的趋势，并未模拟真实 blob base fee、blob 生命周期或主网交易调度。因此，EIP-4844 在本文中是成本建模参照，而不是已经接入的真实数据通道。

**表 5  Related Work 与本文工作的对照**

| 方向 / 工作 | 核心关注 | 与本文关系 | 本文不声称覆盖的部分 |
| --- | --- | --- | --- |
| TEEROLLUP / Hybrid TEE-Rollup | 利用异构 TEE 降低 Rollup 验证成本，并保留挑战和 DA 处罚机制 | 本文沿用 Hybrid TEE-Rollup 的研究方向，聚焦 recoverable challenge 与 evidence-carrying compact commit | 不实现完整 TEE 委员会、生产级提现流程或完整经济安全 |
| Optimistic TEE-Rollups / OTR | 将 TEE 快速执行与 optimistic verification 结合 | 本文同样采用“正常路径低成本、异常路径挑战”的思想 | 不证明真实 TEE 远程证明安全或链上生成式 AI 生产服务可用性 |
| opML / optimistic ML fraud proof | 通过二分定位和单步证明验证 ML 或复杂计算 | 本文借鉴 bisection replay 的争议定位结构 | 不实现完整 FPVM、真实模型推理单步证明或链上 ML 执行环境 |
| Dynamic Fraud Proof | 动态调整争议窗口和最终性，以缩短无争议路径延迟 | 本文关注 timeout 后会话恢复，是更窄的 challenge liveness 问题 | 不提出完整动态最终性协议 |
| LazyLedger / 模块化 DA | 将 DA 与执行验证解耦，支持数据可用性抽样 | 本文用 mock/verifiable DA 与 DA profile 说明 compact commit 需要绑定 DA 证据 | 不接入真实 DA 网络，也不证明 DAS 经济安全 |
| Light Clients for Lazy Blockchains | 面向轻客户端的数据可用性抽样与验证 | 本文借鉴“轻量验证者需要可检查数据承诺”的思想 | 不实现真实轻客户端协议 |
| EIP-4844 / blob data | 降低 Rollup 数据发布成本，提供 blob 数据市场 | 本文将 EIP-4844-like 作为配置化成本 profile | 不模拟真实 blob base fee、主网拥堵或 blob 生命周期 |

从对照可以看出，本文与现有工作的关系是“局部机制补强”而不是“完整系统替代”。已有工作提供了 TEE-Rollup、optimistic fraud proof 和 modular DA 的主要路线；本文的课程论文贡献在于把 recoverable challenge、DA-bound compact commit 和轻量成本模型放到同一个可运行研究原型中，并通过 Python、Hardhat 与 Sepolia 证据分别说明机制、链上对应物和可部署性边界。

## 11 Conclusion

本文面向高频 DApp 场景，在已有 Hybrid TEE-Rollup 思路下研究可验证低成本交互机制。本文没有提出一个全新的 Rollup 体系，而是聚焦 recoverable challenge、evidence-carrying compact commit 和 DA-aware cost amortization 三个具体问题。

通过 Python prototype，本文验证了提交、DA proof、挑战、恢复、重放和结算的基本闭环；通过实验，本文观察到 compact commit 的固定成本特征、payload 增大后的 DA 路线收益、batch size 对 amortized gas 的摊薄作用、recover 对 challenge liveness 的改善，以及 bisection 轮次与理论对数复杂度的一致性；通过本地 EVM 和 Sepolia 部署，本文进一步给出链上关键路径基线和公开测试网对应物。

当前工作仍是阶段性研究原型，不能被解释为真实 TEE 安全证明、生产级 DA 系统或主网性能结论。后续工作应继续推进真实 TEE attestation、真实 DA 网络接入、更完整的链上交易样本、源码验证、形式化安全分析和更统一的 fault arbitration 策略。总体而言，本文为 Hybrid TEE-Rollup 在高频 DApp 中的可验证低成本交互提供了一个克制但可继续扩展的研究基础。

## 参考文献

[1] WEN X, FENG Q, LYU H, et al. TEEROLLUP: Efficient Rollup Design Using Heterogeneous TEE[EB/OL]. arXiv:2409.14647, 2024.

[2] PICCO G, FORTUGNO A. Dynamic Fraud Proof[EB/OL]. arXiv:2502.10321, 2025.

[3] AL-BASSAM M. LazyLedger: A Distributed Data Availability Ledger with Client-Side Smart Contracts[EB/OL]. arXiv:1905.09274, 2019.

[4] TAS E N, TSE D, YANG L, et al. Light Clients for Lazy Blockchains[EB/OL]. arXiv:2203.15968, 2022.

[5] Ethereum Foundation. EIP-4844: Shard Blob Transactions[EB/OL]. 2024.

[6] Ethereum Foundation. Optimistic Rollups[EB/OL]. Ethereum Documentation, 2024.

[7] Buterin V. An Incomplete Guide to Rollups[EB/OL]. 2021.
