# Hybrid_TEE_Rollup 修改前后差异对照

- 原文件：`project_code\paper_outputs\draft\Hybrid_TEE_Rollup.docx`
- 修改版本：`project_code\paper_outputs\draft\Hybrid_TEE_Rollup_修改版本.docx`
- 不同段落数：`54`

说明：本文档仅列出正文段落文本发生变化的位置；未发生变化的表格、图表标题、公式文本和参考文献不重复列出。

## 1. 段落 4｜Front Matter｜Normal

**修改前：**

高频 DApp，如元宇宙状态同步、去中心化社交交互和链上 AI 推理服务，要求系统同时具备低交互成本、较低延迟和异常情况下的可验证性。全链上执行虽然可验证性强，但难以承受高频负载；完全链下执行虽能降低成本，却削弱了公开可验证与可追责能力；单纯依赖 TEE 又会引入硬件信任与可用性风险。本文不提出一个全新的 Rollup 架构，而是在已有 Hybrid TEE-Rollup 思路下，研究高频 DApp 场景中的可验证低成本交互机制，并将问题明确限定在研究原型和课程论文评估范围内。具体而言，本文设计并实现了一个研究原型，重点推进三项机制：一是 recoverable challenge，将交互式挑战从错误检测扩展为异常场景下可恢复并完成仲裁的状态机；二是 evidence-carrying compact commit，将轻量提交与 DA Merkle root、payload hash、Merkle proof 和 challenge evidence 绑定为最小证据入口；三是 DA-aware cost amortization，从 payload size、batch size 和 DA route 的共同作用下分析成本摊销。实验表明，compact commit 的字节开销近似固定，而 full payload 随负载规模近似线性增长；在高 payload 设置下，compact commit + DA 相对 full-onchain 呈现明显降本趋势；recover 机制将 timeout 场景下的 challenge success 从 0% 提升到 100%；二分定位轮次与 log2(trace steps) 基本一致。同时，本文补充威胁模型、成本公式、实验设置和轻量性质讨论，使实验结果与论文主张形成更清晰的对应关系。本文还给出本地 EVM gasUsed 基线与 Sepolia 部署记录，作为阶段性链上对应物证据。需要强调的是，当前系统仍为研究原型，其中 TEE 为 simulated TEE，DA 为 mock/verifiable DA 原型，本地 EVM 与 Sepolia 结果不能直接外推为主网生产性能结论。

**修改后：**

高频 DApp，如元宇宙状态同步、去中心化社交交互和链上 AI 推理服务，要求系统同时具备低交互成本、较低延迟和异常情况下的可验证性。全链上执行虽然可验证性强，但难以承受高频负载；完全链下执行虽能降低成本，却削弱了公开可验证与可追责能力；单纯依赖 TEE 又会引入硬件信任与可用性风险。围绕这一矛盾，本文并不尝试重新设计一个完整 Rollup 架构，而是在已有 Hybrid TEE-Rollup 思路下，讨论高频 DApp 场景中的可验证低成本交互机制。论文重点考察 recoverable challenge、evidence-carrying compact commit 和 DA-aware cost model 三个环节，并通过 Python prototype、本地 EVM gasUsed 与 Sepolia 部署记录给出阶段性证据。实验显示，compact commit 的平均规模约为 406 bytes；在给定 cost model 与 DA profile 下，compact modular DA sampling 相比 full-onchain calldata 在 payload=8192、prompt length=64、batch size=1000 时可得到 96.33% 的估算降本；recoverable challenge 在 timeout 场景下将 challenge success 从 0% 提升至 100%。上述结果仅对应研究原型条件，不外推为真实 TEE 安全、生产级 DA 或主网性能结论。

---

## 2. 段落 8｜1 Introduction｜Normal

**修改前：**

区块链系统在面向高频 DApp 时面临一个结构性矛盾：应用希望获得接近传统互联网服务的低延迟、高吞吐和低单次交互成本，但底层系统又必须维持公开可验证、去中心化安全和异常可追责能力。对于元宇宙资产交互、去中心化社交状态更新、链上 AI 推理请求等场景而言，单次交互可能价值较低，但请求频率高、状态连续性强。如果每一次交互都以完整链上执行和全量数据上链的方式处理，系统成本会快速放大；如果完全转向链下服务，则执行正确性、数据可用性和异常追责又缺乏足够的公开验证路径。

**修改后：**

高频 DApp 把区块链扩容问题推到了一个不太容易回避的位置。以元宇宙中的连续状态同步、去中心化社交中的频繁互动、链上 AI 推理服务中的多轮请求为例，单次交互往往金额不高，却要求较低延迟、持续状态更新和可追责的执行记录。如果每个请求都完整上链执行，成本会随请求频率迅速放大；如果把执行完全交给链下服务，用户又很难在结果异常时获得公开可验证的证据。实际系统设计因此经常落在两难之间：正常路径希望尽量轻，异常路径又不能失去仲裁能力。

---

## 3. 段落 9｜1 Introduction｜Normal

**修改前：**

Rollup 技术为这一矛盾提供了一类中间路线。ZK-Rollup 通过有效性证明获得较强验证能力，但证明生成和系统实现成本较高；Optimistic Rollup 降低了常规执行路径成本，但挑战窗口和争议处理流程会带来延迟。TEE-Rollup 或 Hybrid TEE-Rollup 则试图利用可信执行环境加速链下执行，并通过链上提交和挑战机制保留异常情况下的仲裁能力。然而，TEE 本身并不应被视为绝对可信：硬件实现、宿主环境、I/O 操控、数据可用性和挑战超时都可能成为系统风险来源。因此，Hybrid TEE-Rollup 的关键问题不只是“如何把执行放到 TEE 中”，而是如何在低成本链下执行之后，仍然保留足够的可验证证据入口和异常恢复能力。

**修改后：**

Rollup 为上述矛盾提供了若干折中路线。ZK-Rollup 依靠有效性证明获得强验证属性，但证明生成、系统工程和电路设计成本并不适合所有高频交互；Optimistic Rollup 将常规路径做轻，却把延迟和复杂性推到挑战窗口与 fraud proof 流程中；TEE-Rollup 或 Hybrid TEE-Rollup 借助可信执行环境加速链下执行，再通过链上提交与挑战机制保留异常处理入口。问题在于，TEE 不能被简单当作绝对可信组件。硬件漏洞、宿主环境、I/O 操控、远程证明失效和服务不可用，都可能让“链下执行很快”与“异常时可验证”之间出现断点。

---

## 4. 段落 10｜1 Introduction｜Normal

**修改前：**

本文基于这一背景，将研究切口收敛为两个具体问题。第一，交互式挑战在异常场景下是否能够恢复推进。传统 challenge 机制通常关注错误是否可被发现，而在 timeout、中断、执行轨迹不一致或数据不可用时，争议流程可能停滞。对于高频 DApp 而言，仅能检测异常并不足够，系统还需要将异常推进到可仲裁、可结算的状态。第二，轻量提交如何在降低链上成本的同时保留验证能力。若 compact commit 只是一个孤立哈希，则虽然节省链上空间，却难以支撑后续挑战；因此，轻量提交需要与 DA root、payload hash、Merkle proof 和 challenge evidence 建立明确关联。

**修改后：**

基于这一观察，论文将研究切口收敛为两个具体问题。第一个问题是 challenge 的恢复性。很多 challenge 机制主要讨论错误能否被发现，但在 timeout、中断、执行轨迹不一致或数据不可用时，争议流程本身可能卡住。对于高频 DApp，仅发现异常并不能完成系统层面的止损，协议还必须把异常推进到可仲裁、可结算的状态。第二个问题是轻量提交的证据边界。compact commit 如果只是一个孤立哈希，确实能减少链上字节数，却不足以支撑后续验证；它需要能够回指 DA payload、字段级 proof 与执行摘要，才能在争议发生时成为证据入口。

---

## 5. 段落 11｜1 Introduction｜Normal

**修改前：**

围绕上述问题，本文的课程论文贡献包括：设计可恢复交互式挑战原型，补充 evidence-carrying compact commit 与字段级 DA proof，建立 DA-aware 成本模型与实验网格，并给出 Python 原型、本地 EVM gasUsed 和 Sepolia 部署记录构成的阶段性证据链。本文所有结论均限定为研究原型结果，不声称真实 TEE 安全、生产级 DA 或主网性能。

**修改后：**

围绕这两个问题，本文将 Hybrid TEE-Rollup 的正常路径与异常路径拆开讨论：正常路径追求低链上提交成本，异常路径要求 challenge 能够恢复推进，并且能够从 DA 结构中取回可检查证据。实验与实现部分由三类证据组成：Python 原型用于验证状态机和成本趋势，本地 EVM gasUsed 用于观察合约关键路径开销，Sepolia 部署记录用于说明核心合约具备公开测试网可部署性。所有结论均限定在研究原型范围内，不把 simulated TEE、mock/verifiable DA registry 或测试网部署解释为生产级安全保证。

---

## 6. 段落 13｜1.1 Contributions（本文贡献）｜Normal

**修改前：**

（1）Recoverable Challenge Protocol。提出可恢复挑战机制（Recoverable Challenge Protocol），将传统 challenge 从错误检测流程扩展为具备异常恢复能力的活性保障机制，使 timeout 或中断后的 challenge session 能够继续推进至 replay 与 resolve 阶段。

**修改后：**

研究目标首先是让 Hybrid TEE-Rollup 在异常场景下不仅能够发现错误，还能继续完成仲裁。因此，Recoverable Challenge Protocol 将传统 challenge 从一次性错误检测流程扩展为具备恢复语义的状态机：当 challenge session 因 timeout 或中断停滞时，watchdog/operator 可以触发 recover，使会话继续推进至 replay 与 resolve 阶段。

---

## 7. 段落 14｜1.1 Contributions（本文贡献）｜Normal

**修改前：**

（2）Evidence-Carrying Compact Commit。提出 evidence-carrying compact commit，将 state root、output hash、proof hash、DA root 与 payload proof 进行绑定，为轻量提交建立最小可验证证据入口。

**修改后：**

围绕轻量提交的可验证性，论文进一步引入 evidence-carrying compact commit。该机制把 state root、output hash、proof hash、DA root 与 payload proof 绑定在同一提交语境中，使 compact commit 不只是节省链上空间的摘要，而是后续验证者能够进入 DA 证据结构的最小入口。

---

## 8. 段落 15｜1.1 Contributions（本文贡献）｜Normal

**修改前：**

（3）DA-Aware Cost Model。构建面向高频 DApp 的 DA-aware cost model，用于分析 payload size、batch size 与 DA route 对成本摊销的联合影响。

**修改后：**

成本侧则通过 DA-aware cost model 描述 payload size、batch size 与 DA route 的联合影响。三项机制合在一起，服务于同一个问题：在高频 DApp 中，怎样用较低链上负担保留异常时的可验证性、可恢复性与成本解释能力。本文推进的是 Hybrid TEE-Rollup 异常路径和轻量 DA 绑定的机制补强，而不是对既有 Rollup 系统的整体替代。

---

## 9. 段落 19｜1.1 Contributions（本文贡献）｜Normal

**修改前：**

需要强调的是，本文创新点并非重新设计 Rollup 系统，而是在已有 Hybrid TEE-Rollup 架构下补强 Recovery、DA Binding 与 Cost Awareness 三项关键能力。上述对比用于说明机制层增强边界，而非声称全面优于既有系统。

**修改后：**

本文的创新位置并非重做 Rollup 系统，而是在已有 Hybrid TEE-Rollup 架构下补强 Recovery、DA Binding 与 Cost Awareness 三项能力。表中对比用于界定机制增强的范围，不应理解为对既有系统的全面优越性声明。

---

## 10. 段落 81｜8 Evaluation｜Normal

**修改前：**

本节围绕五个研究问题组织实验结果，而不是仅按结果文件罗列数据：RQ1，evidence-carrying compact commit 是否能够降低链上提交规模；RQ2，batch size 增大后，DA-aware cost model 下的单笔摊销成本是否下降；RQ3，recoverable challenge 是否改善 timeout 场景下的仲裁活性；RQ4，在不同 failure scenario 中，哪些故障只能被检测或拒绝，哪些故障可以进入 challenge + slashing 闭环；RQ5，Solidity 原型、本地 EVM gasUsed 和 Sepolia 部署能否支撑“链上对应物”这一阶段性主张。为避免证据层次混淆，本文将 Python prototype / JSON ledger / simulated TEE 视为机制验证，将 DA-aware cost model 视为配置化估算趋势，将 Hardhat 本地 EVM gasUsed 视为链上状态推进基线，将 Sepolia 部署仅视为 deployability evidence。

**修改后：**

本节围绕五个研究问题展开。实验组织并不按结果文件机械罗列，而是分别回答：evidence-carrying compact commit 是否真正降低链上提交规模；batch size 变大后 DA-aware cost model 中的单笔摊销成本是否下降；recoverable challenge 在 timeout 场景下能否改善仲裁活性；不同 failure scenario 中哪些故障只能检测或拒绝，哪些故障可以进入 slashing；以及 Solidity、本地 EVM 与 Sepolia 证据能否支撑“链上对应物”这一有限主张。

---

## 11. 段落 87｜8.1 RQ1: compact commit 是否降低链上提交规模｜Normal

**修改前：**

Setup. RQ1 使用 Python prototype 生成提交样本，并比较 full payload 与 compact commit 的 UTF-8 canonical JSON 字节数。实验覆盖 payload size 128、512、2048、8192，prompt length 64、256，每组参数 100 个样本。该实验运行在 JSON ledger 和 simulated TEE 环境中，用于验证提交结构和字节规模趋势。

**修改后：**

RQ1 的实验从提交结构本身入手。Python prototype 在 JSON ledger 与 simulated TEE 环境中生成提交样本，比较 full payload 与 compact commit 的 UTF-8 canonical JSON 字节数。参数覆盖 payload size 128、512、2048、8192 与 prompt length 64、256，每组参数生成 100 个样本。这里关心的不是主网交易费用，而是提交结构是否已经把链上字节规模从业务 payload 中剥离出来。

---

## 12. 段落 88｜8.1 RQ1: compact commit 是否降低链上提交规模｜Normal

**修改前：**

Metrics. 本实验使用 full_bytes、compact_bytes 和 byte_reduction_ratio = (full_bytes - compact_bytes) / full_bytes。其中 full_bytes 表示把完整 prompt、response、attestation 和相关字段作为 payload 提交时的字节规模，compact_bytes 表示只提交 state_root、output_hash、proof_hash、da_pointer 和 da_merkle_root 等摘要字段时的字节规模。

**修改后：**

度量指标包括 full_bytes、compact_bytes 和 byte_reduction_ratio = (full_bytes - compact_bytes) / full_bytes。full_bytes 表示完整 prompt、response、attestation 及相关字段都作为 payload 提交时的字节规模；compact_bytes 则只统计 state_root、output_hash、proof_hash、da_pointer 与 da_merkle_root 等摘要字段。

---

## 13. 段落 89｜8.1 RQ1: compact commit 是否降低链上提交规模｜Normal

**修改前：**

Results. 在当前实现中，compact commit 的平均规模约为 406 bytes，基本不随 payload size 增长；相对地，full payload bytes 随 payload size 增大近似线性上升。例如，当 payload size 从 128 增至 8192 时，full bytes 从约 1682.84 / 1876.84 增至约 50068.84 / 50262.84，而 compact bytes 仍保持在约 406 bytes。

**修改后：**

实验现象比较直接：compact commit 的平均规模约为 406 bytes，并且基本不随 payload size 增长；full payload bytes 则随着 payload size 增大近似线性上升。当 payload size 从 128 增至 8192 时，full bytes 从约 1682.84 / 1876.84 增至约 50068.84 / 50262.84，而 compact bytes 仍停留在固定摘要结构附近。这个数量级差异来自两类提交的结构差异：full payload 把业务内容本身带入链上提交，compact commit 只保留状态、输出、证明和 DA 指针的绑定关系。

---

## 14. 段落 90｜8.1 RQ1: compact commit 是否降低链上提交规模｜Normal

**修改前：**

Takeaway. 该结果支持一个有限但清晰的结论：在当前原型的数据结构下，evidence-carrying compact commit 能够将链上提交规模从完整业务 payload 中解耦出来，并把链上提交规模主要限制在固定摘要结构附近。

**修改后：**

因此，RQ1 给出的结论是有限但有意义的：在当前原型的数据结构下，evidence-carrying compact commit 能够把链上提交规模与完整业务 payload 解耦。它并没有消除 payload，而是把 payload 移到 DA 层，并通过 root 与 proof 保留后续验证入口。

---

## 15. 段落 91｜8.1 RQ1: compact commit 是否降低链上提交规模｜Normal

**修改前：**

Limitation. 该实验只说明当前 Python prototype 中的数据结构趋势，不等价于真实链上 calldata、storage layout 或 ABI 编码后的完整成本；也不说明真实 TEE attestation 或真实 DA 网络中的证明大小。

**修改后：**

这一结论仍受实验边界约束。上述字节数来自 Python prototype 的 canonical JSON 表达，不能直接等价为真实链上 calldata、storage layout 或 ABI 编码后的完整成本，也没有覆盖真实 TEE attestation 与真实 DA 网络中的证明大小。

---

## 16. 段落 95｜8.2 RQ2: batch size 增大后摊销成本是否下降｜Normal

**修改前：**

Setup. RQ2 使用 DA-aware cost model 比较四类提交路线：full_onchain_calldata、compact_external_da、compact_eip4844_like 和 compact_modular_da_sampling。实验覆盖 payload size 128、512、2048、8192，prompt length 64、256，batch size 1、10、100、1000，每组变量 100 个样本，共生成 3200 条成本记录。

**修改后：**

RQ2 关注批处理后的成本摊销。实验使用 DA-aware cost model 比较 full_onchain_calldata、compact_external_da、compact_eip4844_like 和 compact_modular_da_sampling 四类路线，参数覆盖 payload size 128、512、2048、8192，prompt length 64、256，batch size 1、10、100、1000，每组 100 个样本。与 RQ1 只看字节规模不同，RQ2 把固定提交开销、DA route 和 batch size 放在同一个模型中观察。

---

## 17. 段落 96｜8.2 RQ2: batch size 增大后摊销成本是否下降｜Normal

**修改前：**

Metrics. 主要指标为 amortized_gas = total_gas / batch_size 和 reduction_ratio = (full_onchain_gas - target_gas) / full_onchain_gas。其中 total_gas 由配置化 profile 计算得出，而不是来自主网交易回执。

**修改后：**

主要指标为 amortized_gas = total_gas / batch_size 和 reduction_ratio = (full_onchain_gas - target_gas) / full_onchain_gas。total_gas 来自配置化 profile，而不是主网交易回执；因此这里讨论的是结构性趋势，而不是实时网络价格。

---

## 18. 段落 97｜8.2 RQ2: batch size 增大后摊销成本是否下降｜Normal

**修改前：**

Results. 当 batch size 增大时，各 DA profile 下的单笔摊销成本均明显下降。在 payload=8192、prompt length=64 的配置下，full_onchain_calldata 的单笔估算 gas 从 batch size=1 时的 801101.44 下降到 batch size=1000 时的 801.10；compact_modular_da_sampling 从 29026.98 下降到 29.03。在 payload=8192 时，modular DA profile 相对 full-onchain 的最佳降本约为 96.33%。

**修改后：**

随着 batch size 增大，各 DA profile 下的单笔摊销成本都会下降。以 payload=8192、prompt length=64 为例，full_onchain_calldata 的单笔估算 gas 从 batch size=1 时的 801101.44 下降到 batch size=1000 时的 801.10；compact_modular_da_sampling 从 29026.98 下降到 29.03。相对于 full_onchain_calldata，compact_modular_da_sampling 在 batch size=1000 时的 reduction_ratio 为 96.33%。这个下降幅度并不神秘：batch size 直接摊薄固定提交成本，而 modular DA sampling profile 又降低了完整 payload 的边际数据成本。

---

## 19. 段落 98｜8.2 RQ2: batch size 增大后摊销成本是否下降｜Normal

**修改前：**

Takeaway. 该结果支持“compact commit + DA 在高 payload 与批处理场景下具有稳定降本趋势”这一阶段性判断。尤其在高频 DApp 中，批处理能够摊薄固定提交成本，使单笔请求承担的估算成本随 batch size 增大而下降。

**修改后：**

从预期关系看，结果与成本模型一致。payload 越大，full-onchain calldata 需要承担的线性数据成本越明显；batch 越大，固定摘要提交越容易被摊薄；DA route 的差异则决定 payload 离开 calldata 后还能节省多少边际成本。对高频 DApp 来说，真正重要的是这三者的组合，而不是单独某一个参数。

---

## 20. 段落 99｜8.2 RQ2: batch size 增大后摊销成本是否下降｜Normal

**修改前：**

Limitation. 96.33% 只是给定 cost model 和 DA profile 参数下的趋势结果，不能写成主网真实降本比例。真实公网费用还受 calldata 定价、blob 价格、交易拥堵、DA 网络实现和业务争议率影响。

**修改后：**

需要保留的边界是，96.33% 只是给定 cost model 与 DA profile 参数下的趋势结果，不能写成主网真实降本比例。真实公网费用还会受到 calldata 定价、blob 价格、交易拥堵、DA 网络实现和业务争议率影响。

---

## 21. 段落 103｜8.3 RQ3: recoverable challenge 是否改善 timeout 场景下的仲裁活性｜Normal

**修改前：**

Setup. RQ3 使用 Python prototype 的 challenge 状态机，覆盖 trace steps 4、8、16、32、64、128，challenge timeout 为 2 秒，max bisection rounds 为 16。实验比较 challenge_timeout_no_recover 与 challenge_timeout_recover 两类场景，并记录 challenge 是否能够继续推进到 replay 与 resolve。

**修改后：**

RQ3 将注意力转到异常路径。实验使用 Python prototype 的 challenge 状态机，覆盖 trace steps 4、8、16、32、64、128，challenge timeout 设为 2 秒，max bisection rounds 设为 16。对照组为 challenge_timeout_no_recover，实验组为 challenge_timeout_recover，核心问题是 timeout 被检测后，challenge 是否还能继续推进到 replay、resolve 与 slashing。

---

## 22. 段落 104｜8.3 RQ3: recoverable challenge 是否改善 timeout 场景下的仲裁活性｜Normal

**修改前：**

Metrics. 主要指标包括 avg_bisection_rounds、avg_expected_log2_rounds、recovery_success_rate、challenge_success_rate 和 slashed_rate。其中 avg_bisection_rounds 用于观察争议定位复杂度，challenge_success_rate 与 slashed_rate 用于观察仲裁是否完成。

**修改后：**

这里记录 avg_bisection_rounds、avg_expected_log2_rounds、recovery_success_rate、challenge_success_rate 和 slashed_rate。avg_bisection_rounds 用来检查争议定位复杂度是否接近理论预期，challenge_success_rate 与 slashed_rate 则反映仲裁是否真正走到完成状态。

---

## 23. 段落 105｜8.3 RQ3: recoverable challenge 是否改善 timeout 场景下的仲裁活性｜Normal

**修改前：**

Results. 在 trace steps 为 4、8、16、32、64、128 时，平均二分轮次分别为 2、3、4、5、6、7，与 log2(trace steps) 基本一致。timeout 对照结果显示，challenge_timeout_no_recover 场景下 detection rate 为 100%，但 challenge success 为 0%，slashed 为 0%；challenge_timeout_recover 场景下 challenge success 和 slashed 均为 100%。

**修改后：**

在 trace steps 为 4、8、16、32、64、128 时，平均二分轮次分别为 2、3、4、5、6、7，与 log2(trace steps) 基本一致。timeout 对照更能说明 recover 的作用：challenge_timeout_no_recover 场景下 detection rate 为 100%，但 challenge success 为 0%，slashed 为 0%；challenge_timeout_recover 场景下 detection rate、recovery success、challenge success 和 slashed 均为 100%。也就是说，没有 recover 时，系统已经知道异常存在，却不能自然完成仲裁；加入 recover 后，同一类异常可以继续进入 step、replay 与 resolve。

---

## 24. 段落 106｜8.3 RQ3: recoverable challenge 是否改善 timeout 场景下的仲裁活性｜Normal

**修改前：**

Takeaway. 该结果说明 recover 的核心价值是 liveness：在 timeout 已被检测但流程无法自然完成时，recover 能够让 challenge session 继续进入后续 step、replay 与 resolve。换言之，recoverable challenge 不只是增加一个接口，而是将“可检测但停滞”的异常状态推进为“可完成仲裁”的状态。

**修改后：**

这一现象说明 recover 的价值主要是活性而非正确性裁决。它没有改变 expected trace、claimed trace 或 replay mismatch 的事实内容，而是为已经停滞的 challenge session 提供继续推进的路径。对高频 DApp 来说，这一区别很关键：异常能被发现只是第一步，异常能被处理完才影响系统是否可用。

---

## 25. 段落 107｜8.3 RQ3: recoverable challenge 是否改善 timeout 场景下的仲裁活性｜Normal

**修改前：**

Limitation. 当前 challenge trace、expected hash、claimed hash 和部分 replay evidence 仍由原型逻辑或链下流程提供。该实验不能证明完整链上 fraud proof、FPVM 或真实 ML/TEE 执行验证的安全性。

**修改后：**

当前实验仍然依赖原型级证据。challenge trace、expected hash、claimed hash 和部分 replay evidence 由原型逻辑或链下流程提供，因此 RQ3 不能证明完整链上 fraud proof、FPVM 或真实 ML/TEE 执行验证的安全性。

---

## 26. 段落 110｜8.3.1 Recovery Overhead Analysis（恢复开销分析）｜Normal

**修改前：**

该结果表明 Recover 的单次链上开销高于一次 challenge step。然而，Recover 属于低频异常路径操作，其作用是在 timeout 已被检测但流程停滞时恢复 challenge liveness，使会话能够继续进入 replay 与 resolve。对于高频 DApp 的正常吞吐路径，该额外成本通常可接受。

**修改后：**

Recover 的单次链上开销确实高于一次 challenge step，但它处在低频异常路径上。其作用是在 timeout 已被检测、流程却停滞时恢复 challenge liveness，使会话继续进入 replay 与 resolve。对于高频 DApp 的正常吞吐路径，这一额外成本通常不会进入每笔请求的常规开销；更合理的理解是，它用一次较高的异常路径成本换取争议流程不永久卡死。

---

## 27. 段落 111｜8.3.1 Recovery Overhead Analysis（恢复开销分析）｜Normal

**修改前：**

需要再次强调：上述数值仅来自 Hardhat 本地 EVM 原型测量，不代表主网 gas 价格、拥堵条件或生产级合约优化后的成本；本文不将其外推为链上部署的通用性能结论。

**修改后：**

上述数值仅来自 Hardhat 本地 EVM 原型测量，不代表主网 gas 价格、拥堵条件或生产级合约优化后的成本，也不应外推为链上部署的通用性能结论。

---

## 28. 段落 117｜8.4 RQ4: failure scenario 中哪些只能检测，哪些可以 slashing｜Normal

**修改前：**

Setup. RQ4 使用 failure scenario 实验，共覆盖 8 类场景，每类 100 个样本，共 800 条记录。场景包括 normal、attestation_invalid、da_unavailable、da_proof_invalid、response_tampered、trace_length_mismatch、challenge_timeout_no_recover 和 challenge_timeout_recover。

**修改后：**

RQ4 进一步拆开 fault taxonomy。failure scenario 实验覆盖 8 类场景，每类 100 个样本，共 800 条记录，包括 normal、attestation_invalid、da_unavailable、da_proof_invalid、response_tampered、trace_length_mismatch、challenge_timeout_no_recover 和 challenge_timeout_recover。这里不把所有异常都强行归为同一种处理结果，而是观察哪些故障在当前原型中已经进入 challenge + slashing，哪些还停留在检测、拒绝或报告层面。

---

## 29. 段落 118｜8.4 RQ4: failure scenario 中哪些只能检测，哪些可以 slashing｜Normal

**修改前：**

Metrics. 主要指标为 detection_rate、challenge_success_rate 和 slashed_rate。为了避免将不同异常混为一谈，本文将失败场景分为四类：Normal path，Detectable but not unified slashing，Challenge + slashing，以及 Timeout liveness comparison。

**修改后：**

指标为 detection_rate、challenge_success_rate 和 slashed_rate。为了避免把语义不同的异常混在一起，实验分析分为四类：Normal path，Detectable but not unified slashing，Challenge + slashing，以及 Timeout liveness comparison。

---

## 30. 段落 119｜8.4 RQ4: failure scenario 中哪些只能检测，哪些可以 slashing｜Normal

**修改前：**

Results. Normal path 中，normal 不触发异常检测或 slashing。Detectable but not unified slashing 类包括 attestation_invalid、da_unavailable 和 da_proof_invalid，这些场景检测率均为 100%，但 challenge success 与 slashed 均为 0%，说明当前原型主要实现检测或拒绝路径。Challenge + slashing 类包括 response_tampered 和 trace_length_mismatch，二者 detection rate、challenge success 和 slashed rate 均为 100%。Timeout liveness comparison 中，无 recover 时 challenge success 为 0%，recover 后 challenge success 和 slashed 均为 100%。

**修改后：**

Normal path 中，normal 不触发异常检测或 slashing。Detectable but not unified slashing 类包括 attestation_invalid、da_unavailable 和 da_proof_invalid，这些场景检测率均为 100%，但 challenge success 与 slashed 均为 0%，说明当前原型主要实现检测或拒绝路径。Challenge + slashing 类包括 response_tampered 和 trace_length_mismatch，相关场景能够进入挑战与惩罚闭环。Timeout liveness comparison 中，challenge_timeout_no_recover 能检测 timeout，却无法完成 challenge；challenge_timeout_recover 则能够恢复并推进到 slashing。这个分层现象与系统设计相符：响应篡改和 trace 不一致具备可进入 replay/resolve 的争议材料，而 DA unavailable、DA proof invalid 或 attestation invalid 在当前版本中还没有被统一映射为经济惩罚。

---

## 31. 段落 120｜8.4 RQ4: failure scenario 中哪些只能检测，哪些可以 slashing｜Normal

**修改前：**

Takeaway. 该结果支持一个分层结论：当前原型并非对所有 fault 都实现统一 slashing，而是已经对响应篡改、trace 不一致和 timeout recovery 形成较完整闭环；对 attestation fault 和 DA fault，则主要体现为稳定检测、拒绝或报告能力。

**修改后：**

RQ4 的重点不是宣称所有 fault 已经闭环，而是明确当前闭环在哪里。响应篡改、trace 不一致和 timeout recovery 已形成较完整的 challenge + slashing 路径；attestation fault 与 DA fault 则主要体现为稳定检测、拒绝或报告能力。这个区分有助于避免把“能发现异常”误写成“都能惩罚异常”。

---

## 32. 段落 121｜8.4 RQ4: failure scenario 中哪些只能检测，哪些可以 slashing｜Normal

**修改前：**

Limitation. 这类分类说明当前 fault taxonomy 尚未完全闭环。特别是 DA unavailable、DA proof invalid 和 attestation invalid 后续应进一步区分“直接拒绝”“触发恢复”“进入链上仲裁”或“经济惩罚”的条件。

**修改后：**

后续仍需细化 fault taxonomy。特别是 DA unavailable、DA proof invalid 和 attestation invalid，应进一步区分何时直接拒绝、何时触发恢复、何时进入链上仲裁，以及何时应施加经济惩罚。

---

## 33. 段落 127｜8.5 RQ5: Solidity、本地 EVM 与 Sepolia 是否支撑链上对应物主张｜Normal

**修改前：**

Setup. RQ5 使用 Solidity 原型和 Hardhat 本地测试链测量关键操作 gasUsed。Solidity 原型包含 MockTEEVerifier、MockDARegistry、MerkleVerifier 和 HybridTEERollup。测量脚本覆盖 payload size 128、512、2048，并记录 register DA、submit rollup、challenge open、respond、step、recover、replay、resolve 和 finalize 的 gasUsed。同时，项目记录了 Sepolia 部署地址、chain id、构造参数和部署区块。

**修改后：**

RQ5 回到链上对应物。实验使用 Solidity 原型和 Hardhat 本地测试链测量关键操作 gasUsed。Solidity 原型包含 MockTEEVerifier、MockDARegistry、MerkleVerifier 和 HybridTEERollup；测量脚本覆盖 payload size 128、512、2048，并记录 register DA、submit rollup、challenge open、respond、step、recover、replay、resolve 和 finalize 的 gasUsed。

---

## 34. 段落 128｜8.5 RQ5: Solidity、本地 EVM 与 Sepolia 是否支撑链上对应物主张｜Normal

**修改前：**

Metrics. 本地 EVM 指标为各关键函数调用的 gasUsed。Sepolia 证据包括 chain id、部署区块、合约地址和 ABI/address index。二者分别对应“本地链上状态推进基线”和“公开测试网可部署性证据”。

**修改后：**

本地 EVM 指标是各关键函数调用的 gasUsed。Sepolia 证据包括 chain id、部署区块、合约地址和 ABI/address index。前者用于观察链上状态推进路径的基线开销，后者用于说明同一组核心合约已经具备公开测试网 deployability evidence。

---

## 35. 段落 129｜8.5 RQ5: Solidity、本地 EVM 与 Sepolia 是否支撑链上对应物主张｜Normal

**修改前：**

Results. 本地 EVM 平均 gasUsed 包括：register DA 113526.00，submit rollup 299033.67，challenge open 283769.00，challenge respond 65886.00，challenge step 93807.00，challenge recover 156891.00，challenge replay 135632.00，challenge resolve 113402.00，finalize 33477.00。Sepolia 部署记录显示 network 为 Sepolia，chain id 为 11155111，部署区块为 10825904；MockTEEVerifier、MockDARegistry 和 HybridTEERollup 分别已记录部署地址。源码验证曾因 block explorer connect timeout 未完成。

**修改后：**

本地 EVM 平均 gasUsed 包括：register DA 113526.00，submit rollup 299033.67，challenge open 283769.00，challenge respond 65886.00，challenge step 93807.00，challenge recover 156891.00，challenge replay 135632.00，challenge resolve 113402.00，finalize 33477.00。Sepolia 部署记录则给出了公开测试网链上地址与 ABI/address index。将这两类证据放在一起看，可以说明 Python prototype 中的提交、挑战、恢复、重放和结算路径已经被抽取成 Solidity 状态推进操作，但还不能说明它们已经经历生产网络压力测试。

---

## 36. 段落 130｜8.5 RQ5: Solidity、本地 EVM 与 Sepolia 是否支撑链上对应物主张｜Normal

**修改前：**

Takeaway. 这些结果支持“当前机制具有链上对应物”的阶段性主张：Python prototype 中的提交、挑战、恢复、重放和结算路径已被抽取为 Solidity 合约中的状态推进操作，并可在 Hardhat 本地链上得到 gasUsed 基线；同一组核心合约也已部署到 Sepolia。

**修改后：**

因此，RQ5 支撑的是一个阶段性主张：当前机制具有链上对应物。本地 Hardhat 测量给出了关键路径 gasUsed 基线，Sepolia 部署说明核心合约可以部署到公开测试网。这个主张的范围很窄，但对于课程论文原型而言，它补上了从 Python 状态机到链上合约表达之间的一步。

---

## 37. 段落 131｜8.5 RQ5: Solidity、本地 EVM 与 Sepolia 是否支撑链上对应物主张｜Normal

**修改前：**

Limitation. 本地 EVM gasUsed 不能等价为公网费用，Sepolia 部署也不能说明生产可用性、主网性能或经济安全。当前 Sepolia 证据仅支持 deployability evidence，不支持“已在真实生产网络中验证”的结论。

**修改后：**

本地 EVM gasUsed 不能等价为公网费用，Sepolia 部署也不能说明生产可用性、主网性能或经济安全。当前 Sepolia 证据仅支持 deployability evidence，不支持“已在真实生产网络中验证”的结论。

---

## 38. 段落 141｜9 Threats to Validity（效度威胁与局限）｜Normal

**修改前：**

为避免将原型结果误解为生产系统结论，本文将原有讨论整理为三类效度威胁：Internal Validity、External Validity 与 Construct Validity。

**修改后：**

为避免把原型实验解读成生产系统结论，本节从 Internal Validity、External Validity 与 Construct Validity 三个角度说明边界，并将具体限制合并讨论。

---

## 39. 段落 143｜Internal Validity（内部效度）｜Normal

**修改前：**

内部效度主要受 simulated TEE、mock/verifiable DA registry、Python 原型逻辑与 Hardhat 本地 EVM 测量方式影响。原型中的 attestation 仅建模输入/输出绑定，DA 层未接入真实采样与经济安全机制，因此机制验证与实现细节耦合。本地 gasUsed 也可能因合约简化、测试数据规模固定而与真实部署存在偏差。

**修改后：**

内部效度主要受 simulated TEE、mock/verifiable DA registry、Python 原型逻辑与 Hardhat 本地 EVM 测量方式影响。原型中的 attestation 只建模输入/输出绑定，DA 层也没有接入真实采样与经济安全机制，因此实验验证的是机制接口是否能跑通，而不是硬件安全或 DA 经济安全。本地 gasUsed 还可能受到合约简化、测试数据规模固定和本地链环境的影响。

---

## 40. 段落 145｜External Validity（外部效度）｜Normal

**修改前：**

外部效度限制来自实验环境到主网/生产网络的泛化边界。本文未覆盖主网 MEV、拥堵费率波动、真实 TEE 供应链攻击与真实 DA 网络运营风险。Sepolia 部署仅提供 deployability evidence，不能支持主网性能或安全强度外推。

**修改后：**

外部效度的限制来自实验环境到主网或生产网络之间的差距。主网 MEV、拥堵费率波动、blob 价格变化、真实 TEE 供应链攻击、侧信道风险、宿主 I/O 操控与真实 DA 网络运营风险，均未在当前实验中覆盖。Sepolia 部署只能说明核心合约具有公开测试网可部署性，不能据此外推主网性能或安全强度。

---

## 41. 段落 147｜Construct Validity（构念效度）｜Normal

**修改前：**

构念效度关注指标是否准确刻画论文主张。challenge success、recovery_success 与 slashed_rate 衡量的是原型状态机下的仲裁推进，而非完整 Rollup 经济安全；DA-aware cost model 为配置化趋势模型，不等价于真实 calldata/blob 定价；fault taxonomy 亦尚未形成统一 slashing 闭环。因此，本文结论应被理解为机制层研究原型结论，而非生产系统审计结果。

**修改后：**

构念效度关注指标与论文主张之间是否匹配。challenge success、recovery_success 与 slashed_rate 衡量的是原型状态机下的仲裁推进，而不是完整 Rollup 经济安全；DA-aware cost model 是配置化趋势模型，不等价于真实 calldata/blob 定价；fault taxonomy 也尚未形成统一 slashing 闭环。因此，论文结论应理解为机制层研究原型结论，而非生产系统审计结果。

---

## 42. 段落 148｜Construct Validity（构念效度）｜Normal

**修改前：**

本文工作仍有明确边界。第一，当前 TEE 为 simulated TEE。原型中的 attestation 使用模拟方式绑定输入、输出、nonce 和执行环境标识，其目的在于验证“链下执行摘要 - 链上提交 - 异常挑战”的协议接口，而不是证明真实 SGX、TDX、CSV 或其他硬件 TEE 的安全性。真实 TEE 部署还需要处理远程证明格式、硬件漏洞、侧信道攻击、宿主 I/O 操控和多厂商 TEE 信任假设。

**修改后：**

具体而言，TEE 部分仍停留在模拟层。attestation 用于绑定输入、输出、nonce 和执行环境标识，目的在于验证“链下执行摘要 - 链上提交 - 异常挑战”的协议接口；真实 SGX、TDX、CSV 或其他硬件 TEE 还需要处理远程证明格式、硬件漏洞、侧信道攻击、宿主 I/O 操控和多厂商信任假设。

---

## 43. 段落 149｜Construct Validity（构念效度）｜Normal

**修改前：**

第二，当前 DA 为 mock/verifiable DA 原型。系统实现了 DA root、payload hash、字段级 Merkle proof 和可用性状态记录，但并未接入 Celestia、EigenDA 或其他真实 DA 网络。因此，本文只能说明 compact commit 与 verifiable DA structure 能形成可检查的证据入口，不能声称已经实现生产级 DA availability。

**修改后：**

DA 部分同样是 mock/verifiable DA 原型。系统实现了 DA root、payload hash、字段级 Merkle proof 和可用性状态记录，但没有接入 Celestia、EigenDA 或其他真实 DA 网络。因而，compact commit 与 verifiable DA structure 在本文中只能说明可检查证据入口的形成方式，不能等同于生产级 DA availability。

---

## 44. 段落 150｜Construct Validity（构念效度）｜Normal

**修改前：**

第三，Python cost model 是配置化估算。DA profile 中的 gas per byte 参数用于构造可比较的趋势模型，而不是主网 calldata、blob 或真实 DA 服务的实时价格。由此得到的 96.33% 降本只应表述为“给定 cost model 下的趋势结果”，不能外推为主网级或生产级费用结论。

**修改后：**

成本模型也应按配置化估算理解。DA profile 中的 gas per byte 参数用于构造可比较的趋势模型，而不是主网 calldata、blob 或真实 DA 服务的实时价格。由此得到的 96.33% 降本只对应给定 cost model 下的趋势结果，不能外推为主网级或生产级费用结论。

---

## 45. 段落 151｜Construct Validity（构念效度）｜Normal

**修改前：**

第四，Hardhat gasUsed 是本地 EVM 基线。它说明 Solidity 原型中的 submit、challenge open、recover、replay、resolve 和 finalize 等关键路径具有链上状态推进对应物，并能被本地测试链测量；但它不等价于 Sepolia 或主网费用，也不覆盖公网拥堵、交易排序、blob 价格和跨合约部署环境差异。

**修改后：**

Hardhat gasUsed 提供的是本地 EVM 基线。它说明 Solidity 原型中的 submit、challenge open、recover、replay、resolve 和 finalize 等关键路径具有链上状态推进对应物，并能被本地测试链测量；但它不等价于 Sepolia 或主网费用，也没有覆盖公网拥堵、交易排序、blob 价格和跨合约部署环境差异。

---

## 46. 段落 152｜Construct Validity（构念效度）｜Normal

**修改前：**

第五，Sepolia 部署是公开测试网 deployability evidence。部署区块、合约地址和 ABI 索引说明当前合约可以部署到公开测试网，但源码验证曾受 block explorer connect timeout 影响，且尚未记录大规模 Sepolia 交互交易样本。因此，Sepolia 结果不能被解释为生产成熟度、主网性能或完整安全性的证明。

**修改后：**

Sepolia 部署记录属于公开测试网 deployability evidence。部署区块、合约地址和 ABI 索引说明当前合约可以部署到公开测试网；同时，源码验证曾受 block explorer connect timeout 影响，也尚未记录大规模 Sepolia 交互交易样本。该证据不应被解释为生产成熟度、主网性能或完整安全性的证明。

---

## 47. 段落 153｜Construct Validity（构念效度）｜Normal

**修改前：**

第六，fault taxonomy 尚未形成完全统一的 slashing 闭环。当前 response_tampered、trace_length_mismatch 和 challenge_timeout_recover 可以进入 challenge + slashing 路径；attestation_invalid、da_unavailable 和 da_proof_invalid 主要体现为检测、拒绝或报告能力。后续需要进一步明确不同 fault 的仲裁策略，例如哪些故障应直接拒绝，哪些故障需要 watchdog recovery，哪些故障需要链上 replay，哪些故障应触发经济惩罚。

**修改后：**

fault taxonomy 仍需继续收敛。当前 response_tampered、trace_length_mismatch 和 challenge_timeout_recover 可以进入 challenge + slashing 路径；attestation_invalid、da_unavailable 和 da_proof_invalid 主要体现为检测、拒绝或报告能力。后续需要明确不同 fault 的仲裁策略，例如哪些故障应直接拒绝，哪些故障需要 watchdog 恢复，哪些故障应进入链上仲裁或经济惩罚。

---

## 48. 段落 154｜Construct Validity（构念效度）｜Normal

**修改前：**

第七，challenge replay 中部分 evidence 仍由链下提供。当前原型通过 expected hash、claimed hash、trace evidence 和 mismatch bits 支持 replay arbitration，但并未实现完整链上可验证执行环境、FPVM 或真实模型推理单步证明。因此，后续工作需要加强 evidence 的链上可验证性、形式化安全论证和跨实现一致性测试，避免 replay 结果过度依赖链下诚实生成的证据。

**修改后：**

challenge replay 中的部分 evidence 仍由链下提供。原型通过 expected hash、claimed hash、trace evidence 和 mismatch bits 支持 replay arbitration，但没有实现完整链上可验证执行环境、FPVM 或真实模型推理单步证明。下一步需要加强 evidence 的链上可验证性、形式化安全论证和跨实现一致性测试，减少 replay 结果对链下诚实生成证据的依赖。

---

## 49. 段落 155｜Construct Validity（构念效度）｜Normal

**修改前：**

总体而言，本文结论应被理解为阶段性研究原型结论：它说明 recoverable challenge、evidence-carrying compact commit 和 DA-aware cost model 在当前实验条件下具有可行性和趋势支撑；它不说明系统已经成为完整生产级 Rollup，也不说明其具备真实 TEE 安全证明、真实 DA 网络安全或主网级性能保证。

**修改后：**

综合这些边界，论文结论应被限定为阶段性研究原型结论：recoverable challenge、evidence-carrying compact commit 和 DA-aware cost model 在当前实验条件下具有可行性和趋势支撑；系统距离完整生产级 Rollup、真实 TEE 安全证明、真实 DA 网络安全和主网级性能保证仍有明显距离。

---

## 50. 段落 166｜10 Related Work｜Normal

**修改前：**

从对照可以看出，本文与现有工作的关系是“局部机制补强”而不是“完整系统替代”。已有工作提供了 TEE-Rollup、optimistic fraud proof 和 modular DA 的主要路线；本文的课程论文贡献在于把 recoverable challenge、DA-bound compact commit 和轻量成本模型放到同一个可运行研究原型中，并通过 Python、Hardhat 与 Sepolia 证据分别说明机制、链上对应物和可部署性边界。

**修改后：**

从对照可以看出，本文与现有工作的关系是“局部机制补强”而不是“完整系统替代”。已有工作已经提供 TEE-Rollup、optimistic fraud proof 和 modular DA 的主要路线；本文的课程论文工作把 recoverable challenge、DA-bound compact commit 和轻量成本模型放入同一个可运行研究原型中，并分别用 Python、Hardhat 与 Sepolia 证据说明机制可行性、链上对应物和可部署性边界。

---

## 51. 段落 168｜11 Conclusion｜Normal

**修改前：**

本文面向高频 DApp 场景，在已有 Hybrid TEE-Rollup 思路下研究可验证低成本交互机制。本文没有提出一个全新的 Rollup 体系，而是聚焦 recoverable challenge、evidence-carrying compact commit 和 DA-aware cost amortization 三个具体问题。

**修改后：**

高频 DApp 的核心困难不只是吞吐量不足，还在于低成本交互与异常可验证之间经常互相拉扯。完全上链会把大量低价值高频请求转化为高昂链上成本；完全链下或单纯依赖 TEE 又会削弱异常时的公开仲裁能力。本文在已有 Hybrid TEE-Rollup 思路下回答的是一个更窄的问题：能否在不重做完整 Rollup 系统的前提下，让轻量提交、DA 证据和可恢复 challenge 形成可运行的研究原型。

---

## 52. 段落 169｜11 Conclusion｜Normal

**修改前：**

通过 Python prototype，本文验证了提交、DA proof、挑战、恢复、重放和结算的基本闭环；通过实验，本文观察到 compact commit 的固定成本特征、payload 增大后的 DA 路线收益、batch size 对 amortized gas 的摊薄作用、recover 对 challenge liveness 的改善，以及 bisection 轮次与理论对数复杂度的一致性；通过本地 EVM 和 Sepolia 部署，本文进一步给出链上关键路径基线和公开测试网对应物。

**修改后：**

实验给出的回答是谨慎肯定的。Python prototype 跑通了提交、DA proof、挑战、恢复、重放和结算的基本闭环；结果中可以观察到 compact commit 的固定成本特征、payload 增大后 DA 路线的收益、batch size 对 amortized gas 的摊薄作用、recover 对 challenge liveness 的改善，以及 bisection 轮次与理论对数复杂度的一致性。本地 EVM 和 Sepolia 部署进一步说明，原型中的关键路径已经能够被抽取为 Solidity 合约操作，并具有公开测试网部署记录。

---

## 53. 段落 170｜11 Conclusion｜Normal

**修改前：**

当前工作仍是阶段性研究原型，不能被解释为真实 TEE 安全证明、生产级 DA 系统或主网性能结论。后续工作应继续推进真实 TEE attestation、真实 DA 网络接入、更完整的链上交易样本、源码验证、形式化安全分析和更统一的 fault arbitration 策略。总体而言，本文为 Hybrid TEE-Rollup 在高频 DApp 中的可验证低成本交互提供了一个克制但可继续扩展的研究基础。

**修改后：**

仍未解决的问题同样清楚：真实 TEE attestation、真实 DA 网络接入、大规模链上交互样本、源码验证、形式化安全分析和统一 fault arbitration 策略，都超出了当前版本的证据范围。后续研究可以沿两个方向推进：一是把 evidence 的链上可验证性做得更强，减少 replay 对链下证据生成的依赖；二是在真实 DA 与 TEE 环境中重新测量成本、活性和异常处理边界。这样，Hybrid TEE-Rollup 面向高频 DApp 的可验证低成本交互，才可能从研究原型继续走向更完整的系统评估。

---

## 54. 段落 172｜11.1 Theoretical Implication（理论启示）｜Normal

**修改前：**

本文最大的贡献并非提出新的 Rollup 系统，而是将 Challenge Recovery 从工程实现细节提升为具有协议语义的独立机制。通过 Recoverable Challenge、Evidence-Carrying Commit 与 DA-Aware Cost Model 的结合，本文为 Hybrid TEE-Rollup 在高频 DApp 场景下的异常处理与低成本验证提供了一种可讨论的研究视角。需要保持克制的是：该视角建立在研究原型与阶段性证据之上，尚不能替代完整系统安全证明或生产级性能评估。

**修改后：**

从理论层面看，本文更有价值的部分不是提出新的 Rollup 系统，而是把 Challenge Recovery 从工程补丁提升为具有协议语义的独立机制。Recoverable Challenge、Evidence-Carrying Commit 与 DA-Aware Cost Model 的组合，为 Hybrid TEE-Rollup 在高频 DApp 场景下的异常处理与低成本验证提供了一个可讨论的研究视角。这个视角仍建立在研究原型与阶段性证据之上，不能替代完整系统安全证明或生产级性能评估。

---
