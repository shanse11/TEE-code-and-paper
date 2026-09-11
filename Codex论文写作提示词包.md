# Codex 论文写作提示词包

适用对象：当前项目《Hybrid TEE-Rollup 高可验证低成本交互机制》  
适用目标：生成**中文完整初稿**，表达风格按**正式会议论文**约束，但保持对当前阶段性原型边界的克制描述。  
使用方式：建议按“**总控提示词 -> 分章节提示词 -> 回审提示词**”三步使用，而不是一次性依赖单个超长提示词。

---

## 一、使用说明

### 1. 推荐使用顺序

1. 先使用 **总控提示词** 生成一版完整论文初稿；
2. 再分别使用 **Prompt A-E** 对关键章节进行重写和增强；
3. 最后使用 **回审提示词** 从审稿人视角检查夸大表述、逻辑漏洞和边界问题。

### 2. 建议提供给 Codex 的本地材料

在使用以下提示词时，建议同时将这些材料作为事实基础提供给 Codex：

- `E:/项目/project_code/paper_outputs/paper_outline.md`
- `E:/项目/project_code/paper_outputs/Hybrid_TEE_Rollup_高可验证低成本交互机制的阶段性理论总结与创新提炼.md`
- `E:/项目/project_code/paper_outputs/理论创新点说明.md`
- `E:/项目/project_code/paper_outputs/Hybrid_TEE_Rollup_阶段性实验结果报告.md`
- `E:/项目/project_code/paper_outputs/related_work_table.md`
- `E:/项目/project_code/paper_outputs/system_design.md`

### 3. 统一写作约束

无论使用哪一个提示词，都建议保留以下统一约束：

- 角色：区块链系统 / 分布式系统 / Rollup 方向论文作者
- 输出语言：中文
- 风格：正式、学术、克制、逻辑清晰，不营销、不夸大
- 论文定位：
  - **不是提出一个全新的 Rollup 体系**
  - 而是在已有 Hybrid TEE-Rollup 路线下推进：
    - `recoverable challenge`
    - `evidence-carrying compact commit`
    - `verifiable DA`
    - 高频 DApp 场景下的可验证低成本交互
- 必须明确边界：
  - simulated TEE
  - mock DA
  - Python prototype
  - 本地 EVM 不等于主网
  - Sepolia 仅为阶段性部署

---

## 二、总控提示词

以下提示词用于**第一次生成完整中文论文初稿**。

```text
你是一名区块链系统与分布式系统方向的论文作者，请基于我当前项目的本地材料，帮我写一篇可投稿风格的中文完整论文初稿。

写作要求如下：

1. 论文定位
- 这篇论文不是提出一个全新的 Rollup 体系；
- 而是在已有 Hybrid TEE-Rollup 思路下，研究高频 DApp 场景中的可验证低成本交互机制；
- 重点分析：
  - recoverable challenge
  - compact commit + verifiable DA
  - 以及其原型、实验和链上部署支撑。

2. 风格要求
- 使用正式、学术、克制的中文；
- 不要写成产品介绍，不要营销化；
- 不要过度声称创新；
- 不要将阶段性原型结果写成生产系统结论；
- 不要把 mock DA、simulated TEE、本地 EVM 或 Sepolia 写成主网级结论。

3. 必须使用的事实基础
请以我提供的以下本地文档为事实基础：
- paper_outline.md
- Hybrid_TEE_Rollup_高可验证低成本交互机制的阶段性理论总结与创新提炼.md
- 理论创新点说明.md
- Hybrid_TEE_Rollup_阶段性实验结果报告.md
- related_work_table.md
- system_design.md

4. 必须明确的研究边界
- 当前系统使用 simulated TEE，而不是真实 SGX/TDX；
- 当前 DA 为 mock DA / verifiable DA 原型，而不是生产级 DA 网络；
- Python prototype 与 gas 估算模型用于说明趋势；
- 本地 EVM gasUsed 提供链上基线；
- Sepolia 部署提供公开测试网证据；
- 这些结果不能直接等同于主网性能结论。

5. 必须体现的六个创新点
- Recoverable Challenge
- Evidence-Carrying Compact Commit
- Fault Taxonomy
- DA-aware Cost Amortization
- 高频 DApp 的可验证性能分析
- Python -> 本地 EVM -> Sepolia 的渐进式验证路径

6. 实验结果必须支撑的理论主张
- compact commit 的固定成本特征
- payload 增大后收益扩大
- batch 增大后 amortized gas 降低
- recover 改善 liveness
- bisection 轮次符合 log2(trace steps) 趋势

7. 输出结构固定为
- 摘要
- 1 Introduction
- 2 Background
- 3 Motivation
- 4 System Design
- 5 Recoverable Challenge Protocol
- 6 DA Cost Model
- 7 Evaluation
- 8 Discussion
- 9 Related Work
- 10 Conclusion

8. 章节写作要求
- Introduction 要明确高频 DApp 的问题、Hybrid TEE-Rollup 的必要性、本文研究切口和贡献；
- Background 需要解释 Rollup、TEE attestation、optimistic challenge、data availability；
- Motivation 要回答为什么不是纯 TEE、纯 OP、纯全量上链；
- System Design 必须围绕执行层、数据层、验证层；
- Recoverable Challenge Protocol 必须把状态机、timeout recovery、bisection、single-step replay 写清楚；
- DA Cost Model 必须讨论 full-onchain、compact commit、DA profile、batch amortization；
- Evaluation 不能只是列数据，必须写成“实验如何支撑理论命题”；
- Discussion 必须主动承认局限性；
- Related Work 必须强调“推进已有路线”，而非“重新发明体系”。

请直接输出完整中文论文初稿。
```

---

## 三、分章节提示词

以下提示词用于在完整初稿生成后，对关键章节分别重写。

### Prompt A：摘要 + 引言

```text
你是一名区块链系统论文作者。请基于我现有项目材料，重写这篇论文的“摘要 + 引言”部分。

要求：
- 输出中文；
- 风格按正式会议论文；
- 不夸大，不营销；
- 摘要必须在一段内讲清：
  - 问题
  - 方法
  - 贡献
  - 实验支撑
  - 边界
- 引言必须明确：
  - 高频 DApp 的核心矛盾
  - Hybrid TEE-Rollup 的必要性
  - 当前研究切口不是提出新 Rollup，而是推进 recoverable challenge 与 compact commit + verifiable DA
  - 本文贡献点

特别要求：
- 引言不能写成泛泛而谈的“区块链很重要”；
- 必须突出“高频 DApp 的可验证低成本交互”；
- 必须强调当前系统仍是阶段性研究原型。

请只输出：
1. 摘要
2. 1 Introduction
```

### Prompt B：背景 + 动机

```text
请帮我重写论文中的“2 Background”与“3 Motivation”两节。

要求：
- 输出中文；
- 风格为正式、学术、克制的会议论文表达；
- Background 需要解释：
  - Rollup 的基本思想
  - TEE attestation 的作用与局限
  - optimistic challenge 的基本机制
  - data availability 的角色
- Motivation 必须回答：
  - 为什么高频 DApp 不能依赖全链上执行
  - 为什么纯链下执行会带来不可验证问题
  - 为什么不是纯 TEE、纯 OP、纯全量上链
  - 为什么 recoverable challenge 是合理的研究切口

特别要求：
- 不要写成教科书式冗长背景；
- 背景必须服务于后文系统设计；
- Motivation 必须明显体现“问题收敛”，而不是泛泛谈挑战。

请只输出：
2 Background
3 Motivation
```

### Prompt C：系统设计 + Recoverable Challenge

```text
请帮我重写论文中的“4 System Design”和“5 Recoverable Challenge Protocol”。

要求：
- 输出中文；
- 风格为正式会议论文；
- 必须围绕三层结构展开：
  - 执行层
  - 数据层
  - 验证层
- 必须解释以下概念在系统中的作用：
  - simulated TEE attestation
  - compact commit
  - verifiable DA
  - Merkle proof
  - challenge replay
  - timeout recovery
  - replay arbitration

Recoverable Challenge 一节必须：
- 明确 challenge 的状态推进逻辑；
- 明确 recoverable challenge 与普通 challenge 的区别；
- 强调它研究的是 liveness、recoverability、fault-tolerant dispute state machine；
- 不能只写接口流程，要写理论逻辑。

特别要求：
- 不能写成代码说明书；
- 要写成系统机制设计；
- 要让读者感到这是“链下执行 + 链上留痕 + 异常时可恢复验证”的完整闭环。

请只输出：
4 System Design
5 Recoverable Challenge Protocol
```

### Prompt D：DA Cost Model + Evaluation

```text
请帮我重写论文中的“6 DA Cost Model”和“7 Evaluation”。

要求：
- 输出中文；
- 风格为正式会议论文；
- DA Cost Model 必须围绕：
  - full-onchain
  - compact commit
  - DA profile
  - batch amortization
  - payload size
  - batch size
展开；
- Evaluation 不能只列实验数据，必须解释“这些数据支持什么理论命题”。

必须讨论的结果包括：
- compact commit 的固定成本特征
- payload 增大后降本收益扩大
- batch 增大后 amortized gas 降低
- recoverable challenge 改善 timeout 场景下的 liveness
- bisection rounds 与 log2(trace steps) 趋势一致
- response_tampered、trace_length_mismatch 等场景中的 detection / challenge / slashing 结果
- 本地 EVM gasUsed 的意义
- Sepolia 部署的意义

特别要求：
- 清楚区分：
  - 趋势估算
  - 本地 EVM 实测
  - Sepolia 部署证据
- 不要把阶段性实验写成主网级结论。

请只输出：
6 DA Cost Model
7 Evaluation
```

### Prompt E：Discussion + Related Work + Conclusion

```text
请帮我重写论文中的“8 Discussion”“9 Related Work”“10 Conclusion”。

要求：
- 输出中文；
- 风格为正式会议论文；
- Discussion 必须主动写局限性，包括：
  - simulated TEE
  - mock DA
  - Python prototype
  - 本地 EVM 不等于主网
  - Sepolia 仅为阶段性部署
  - 当前仍是研究原型
- Related Work 必须比较：
  - TEEROLLUP
  - OTR
  - opML
  - Dynamic Fraud Proof
  - LazyLedger / DA 相关路线
- Related Work 的表达要强调：
  - 本文不是重新发明体系
  - 而是在已有 Hybrid TEE-Rollup 路线下推进 recoverable challenge、证据化轻量提交和 DA-aware 成本分析

Conclusion 必须：
- 总结研究问题
- 总结本文机制推进
- 总结实验与部署支撑
- 保持克制，不夸大

请只输出：
8 Discussion
9 Related Work
10 Conclusion
```

---

## 四、回审提示词

以下提示词用于初稿完成后的“审稿人视角”检查。

```text
你现在扮演区块链系统与分布式系统领域的严格审稿人。请从会议论文评审视角，对我当前这篇中文论文初稿进行学术质量回审。

请重点检查以下问题：

1. 是否把“原型结果”写成了“生产结论”；
2. 是否过度声称创新；
3. 是否把实验结果和理论命题对应起来；
4. 是否清楚区分：
   - 趋势估算
   - 本地 EVM 实测
   - Sepolia 部署证据
5. 是否符合正式会议论文风格；
6. 引言是否清楚说明研究切口；
7. System Design 是否真正围绕执行层、数据层、验证层；
8. Evaluation 是否不仅列数据，还分析数据支持的理论主张；
9. Discussion 是否主动承认局限性；
10. Related Work 是否强调“推进已有路线”，而不是“重新发明体系”。

输出格式要求：
- 先给出总体评价；
- 再列出最重要的 5-10 个问题；
- 对每个问题说明：
  - 问题是什么
  - 为什么会影响论文质量
  - 应如何修改
- 最后给出一版“这篇论文当前最需要优先修改的 3 件事”。

请保持正式、严格、专业，不要客套。
```

---

## 五、推荐的实际使用流程

### 第一步：先生成总稿

把以下材料一并交给 Codex：

- `paper_outline.md`
- `Hybrid_TEE_Rollup_高可验证低成本交互机制的阶段性理论总结与创新提炼.md`
- `理论创新点说明.md`
- `Hybrid_TEE_Rollup_阶段性实验结果报告.md`
- `related_work_table.md`
- `system_design.md`

然后使用“总控提示词”生成完整中文初稿。

### 第二步：逐节重写

按下面顺序逐节重写：

1. `Prompt A`：摘要 + 引言
2. `Prompt B`：背景 + 动机
3. `Prompt C`：系统设计 + Recoverable Challenge
4. `Prompt D`：DA Cost Model + Evaluation
5. `Prompt E`：Discussion + Related Work + Conclusion

### 第三步：回审

将修订后的整篇论文再次交给 Codex，并使用“回审提示词”，从审稿人视角筛掉：

- 过度夸大
- 逻辑跳跃
- 理论与实验脱节
- 边界不清
- 会议风格不稳

---

## 六、最短可复制版本

如果你现在只想先跑一版初稿，可以直接复制下面这段：

```text
你是一名区块链系统与分布式系统方向的论文作者。请基于我当前项目的本地材料，帮我写一篇中文完整论文初稿，风格按正式会议论文约束。

论文定位不是提出一个新的 Rollup，而是在已有 Hybrid TEE-Rollup 思路下，研究高频 DApp 场景中的可验证低成本交互机制，重点分析 recoverable challenge、compact commit + verifiable DA，以及其原型、实验和链上部署支撑。

请使用以下材料作为事实基础：
- paper_outline.md
- Hybrid_TEE_Rollup_高可验证低成本交互机制的阶段性理论总结与创新提炼.md
- 理论创新点说明.md
- Hybrid_TEE_Rollup_阶段性实验结果报告.md
- related_work_table.md
- system_design.md

必须满足以下约束：
- 使用正式、学术、克制的中文；
- 不要夸大，不要营销化；
- 不要把当前工作写成生产系统；
- 必须明确 simulated TEE、mock DA、Python prototype、本地 EVM 和 Sepolia 的边界；
- 必须体现六个创新点：
  - Recoverable Challenge
  - Evidence-Carrying Compact Commit
  - Fault Taxonomy
  - DA-aware Cost Amortization
  - 高频 DApp 的可验证性能分析
  - Python -> 本地 EVM -> Sepolia 的渐进式验证路径
- 实验分析必须解释数据支撑什么理论命题，而不是只列实验结果。

输出结构固定为：
- 摘要
- 1 Introduction
- 2 Background
- 3 Motivation
- 4 System Design
- 5 Recoverable Challenge Protocol
- 6 DA Cost Model
- 7 Evaluation
- 8 Discussion
- 9 Related Work
- 10 Conclusion

请直接输出完整中文论文初稿。
```

---

## 七、使用建议

如果这周目标是尽快进入“论文正文可改”状态，建议你优先做两件事：

1. 先用“最短可复制版本”或“总控提示词”生成一版完整初稿；
2. 再用 `Prompt D` 和“回审提示词”重点打磨实验章节，因为这通常是最容易写成“流水账”的部分。

这套提示词包的目的，不是让 Codex 替你“自动写完论文”，而是让它在你已经有主线、实验和理论材料的基础上，稳定地产出更像论文、而不是更像项目说明书的文本。

