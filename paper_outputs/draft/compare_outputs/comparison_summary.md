# DOCX comparison summary

- Original: E:\项目\project_code\paper_outputs\draft\final_balanced_low_aigc_academic.docx
- Revised: D:\微信\WeChat Files\wxid_ggucz7wlbnmo22\FileStorage\Temp\Copy\Hybrid TEE-Rollup-修订版.docx
- Original non-empty paragraphs: 359
- Revised non-empty paragraphs: 383
- Revised tracked insertions: 130
- Revised tracked deletions: 46
- Revised comments: 6

## Comments
- Comment 0 by 赵春艳 on 2026-06-15T00:24:45Z: 英文摘要请对照修改
  Context: Abstract: High-frequency decentralized applications (DApps) require low latency, low on-chain overhead, and publicly verifiable arbitration under abnormal executions. This paper studies the interaction between lightweight on-chain commitments, off-chain data availability (DA) payloads, and timeout challenges in Hybrid TEE-Rollup. It proposes a Recoverable Challenge protocol, an Evidence-Carrying Compact Commit, and a DA-Aware Cost Model. The recoverable challenge path restores timeout sessions to replayable and settleable states; the compact commit binds the state root, output hash, proof hash
- Comment 1 by 赵春艳 on 2026-06-15T00:26:03Z: 参考文献要在正文中合适的位置进行引用
  Context: 1 引言
- Comment 2 by 赵春艳 on 2026-06-15T11:02:41Z: 详见第X章全部去掉
  Context: 
- Comment 3 by 赵春艳 on 2026-06-15T11:05:38Z: 详见第X章全部删掉，顺序写就行，不需要提前预告。
  Context: 在本文原型中，模拟可信执行环境用于建立“链下执行摘要—链上提交—异常挑战”的接口关系；真实 TEE 安全性在第 8 章讨论。
- Comment 4 by 赵春艳 on 2026-06-15T00:31:43Z: 4，5，6章合并为第4章 核心机制与成本评估；然后二级目录分别4.1，4.2，4.3对应原456章
  Context: 4 可恢复挑战协议
- Comment 5 by 赵春艳 on 2026-06-15T00:03:19Z: 参考文献格式不规范，请对照模版要求逐个修改
  Context: 参考文献

## Tracked changes (first 120)
- INS 赵春艳 2026-06-15T00:10:33Z: 同时对
- INS 赵春艳 2026-06-15T00:10:36Z: 系统
- DEL 赵春艳 2026-06-15T00:10:40Z: 要求低
- DEL 赵春艳 2026-06-15T00:10:45Z: 低
- DEL 赵春艳 2026-06-15T00:10:56Z: 与
- INS 赵春艳 2026-06-15T00:10:57Z: 以及
- INS 赵春艳 2026-06-15T00:10:59Z: 一场
- INS 赵春艳 2026-06-15T00:11:03Z: 场景下
- INS 赵春艳 2026-06-15T00:11:06Z: 的
- INS 赵春艳 2026-06-15T00:11:12Z: 能力
- INS 赵春艳 2026-06-15T00:11:14Z: 提出
- INS 赵春艳 2026-06-15T00:11:20Z: 严苛要求
- DEL 赵春艳 2026-06-15T00:11:23Z: 并存
- INS 赵春艳 2026-06-15T00:11:30Z: 针对
- DEL 赵春艳 2026-06-15T00:11:37Z: 本文研究
- INS 赵春艳 2026-06-15T00:11:45Z: 混合
- INS 赵春艳 2026-06-15T00:11:47Z: 可信
- INS 赵春艳 2026-06-15T00:11:48Z: 执行
- INS 赵春艳 2026-06-15T00:11:53Z: 环境
- INS 赵春艳 2026-06-15T00:11:59Z: Rollup
- INS 赵春艳 2026-06-15T00:12:03Z: （
- INS 赵春艳 2026-06-15T00:12:06Z: ）
- INS 赵春艳 2026-06-15T00:12:24Z: 架构
- INS 赵春艳 2026-06-15T00:12:26Z: ，
- INS 赵春艳 2026-06-15T00:12:31Z: 本文
- INS 赵春艳 2026-06-15T00:12:36Z: 围绕
- DEL 赵春艳 2026-06-15T00:12:38Z: 中
- INS 赵春艳 2026-06-15T00:12:43Z: 级
- INS 赵春艳 2026-06-15T00:13:09Z: Data Availability
- INS 赵春艳 2026-06-15T00:13:13Z: ，
- INS 赵春艳 2026-06-15T00:13:23Z: 分发
- DEL 赵春艳 2026-06-15T00:13:27Z: 与
- INS 赵春艳 2026-06-15T00:13:28Z: 和
- DEL 赵春艳 2026-06-15T00:13:32Z: 间
- DEL 赵春艳 2026-06-15T00:13:33Z: 之
- INS 赵春艳 2026-06-15T00:13:36Z: 流程
- INS 赵春艳 2026-06-15T00:13:38Z: 三者
- INS 赵春艳 2026-06-15T00:13:46Z: 运行
- INS 赵春艳 2026-06-15T00:13:49Z: 展开
- INS 赵春艳 2026-06-15T00:13:50Z: 研究
- INS 赵春艳 2026-06-15T00:13:55Z: 依次
- DEL 赵春艳 2026-06-15T00:14:01Z: 机制
- INS 赵春艳 2026-06-15T00:14:03Z: 协议
- INS 赵春艳 2026-06-15T00:14:12Z: 证据
- INS 赵春艳 2026-06-15T00:14:18Z: 绑定型
- DEL 赵春艳 2026-06-15T00:14:23Z: 证据的
- DEL 赵春艳 2026-06-15T00:14:24Z: 携带
- DEL 赵春艳 2026-06-15T00:14:34Z: 以及
- INS 赵春艳 2026-06-15T00:14:54Z: 和
- DEL 赵春艳 2026-06-15T00:14:58Z: 用性感知
- DEL 赵春艳 2026-06-15T00:14:59Z: 数据可
- INS 赵春艳 2026-06-15T00:15:01Z: DA
- INS 赵春艳 2026-06-15T00:15:04Z: 感知
- INS 赵春艳 2026-06-15T00:15:11Z: 摊销
- INS 赵春艳 2026-06-15T00:15:16Z: 三大
- INS 赵春艳 2026-06-15T00:15:17Z: 狠心
- INS 赵春艳 2026-06-15T00:15:19Z: 设计
- INS 赵春艳 2026-06-15T00:15:28Z: 其中
- INS 赵春艳 2026-06-15T00:15:29Z: ，
- DEL 赵春艳 2026-06-15T00:15:41Z: 机制
- INS 赵春艳 2026-06-15T00:15:43Z: 协议
- INS 赵春艳 2026-06-15T00:15:50Z: 能够
- INS 赵春艳 2026-06-15T00:15:56Z: 将
- INS 赵春艳 2026-06-15T00:15:59Z: 因
- INS 赵春艳 2026-06-15T00:16:10Z: 交互
- INS 赵春艳 2026-06-15T00:16:14Z: 超时
- INS 赵春艳 2026-06-15T00:16:16Z: 陷入
- INS 赵春艳 2026-06-15T00:16:19Z: 🤚
- INS 赵春艳 2026-06-15T00:16:20Z: 的
- INS 赵春艳 2026-06-15T00:16:25Z: 挑战
- DEL 赵春艳 2026-06-15T00:16:33Z: 于将超时
- DEL 赵春艳 2026-06-15T00:16:34Z: 用
- DEL 赵春艳 2026-06-15T00:16:41Z: 可
- DEL 赵春艳 2026-06-15T00:16:43Z: 可
- DEL 赵春艳 2026-06-15T00:16:44Z: 、
- INS 赵春艳 2026-06-15T00:16:45Z: 与
- INS 赵春艳 2026-06-15T00:16:49Z: 的
- INS 赵春艳 2026-06-15T00:16:51Z: 正常
- DEL 赵春艳 2026-06-15T00:17:04Z: 带
- DEL 赵春艳 2026-06-15T00:17:05Z: 携
- INS 赵春艳 2026-06-15T00:17:08Z: 绑定型
- DEL 赵春艳 2026-06-15T00:17:14Z: 的
- DEL 赵春艳 2026-06-15T00:17:19Z: 机制
- INS 赵春艳 2026-06-15T00:17:22Z: 将
- DEL 赵春艳 2026-06-15T00:17:27Z: 绑定
- INS 赵春艳 2026-06-15T00:17:50Z: 进行
- INS 赵春艳 2026-06-15T00:17:52Z: 密码学
- INS 赵春艳 2026-06-15T00:17:53Z: 绑定
- INS 赵春艳 2026-06-15T00:17:55Z: ，
- INS 赵春艳 2026-06-15T00:17:57Z: 构建
- INS 赵春艳 2026-06-15T00:17:58Z: 链上
- INS 赵春艳 2026-06-15T00:17:59Z: 最小
- INS 赵春艳 2026-06-15T00:18:03Z: 可信证据
- INS 赵春艳 2026-06-15T00:18:05Z: 集
- DEL 赵春艳 2026-06-15T00:18:19Z: 可用性
- DEL 赵春艳 2026-06-15T00:18:20Z: 数据
- INS 赵春艳 2026-06-15T00:18:25Z: DA
- INS 赵春艳 2026-06-15T00:18:43Z: 量化
- INS 赵春艳 2026-06-15T00:18:56Z: 部署
- INS 赵春艳 2026-06-15T00:19:16Z: 对
- INS 赵春艳 2026-06-15T00:19:18Z: 整体
- INS 赵春艳 2026-06-15T00:19:20Z: 运行
- INS 赵春艳 2026-06-15T00:19:22Z: 成本的
- INS 赵春艳 2026-06-15T00:19:24Z: 影响
- INS 赵春艳 2026-06-15T00:19:26Z: 规律
- DEL 赵春艳 2026-06-15T00:19:31Z: 选择之间的关系
- INS 赵春艳 2026-06-15T00:19:37Z: 本文
- INS 赵春艳 2026-06-15T00:20:42Z: 功能
- DEL 赵春艳 2026-06-15T00:20:48Z: 本地
- INS 赵春艳 2026-06-15T00:20:50Z: 以太坊
- INS 赵春艳 2026-06-15T00:20:55Z: 虚拟机
- INS 赵春艳 2026-06-15T00:20:57Z: （
- INS 赵春艳 2026-06-15T00:20:59Z: ）
- INS 赵春艳 2026-06-15T00:21:02Z: 本地
- INS 赵春艳 2026-06-15T00:21:14Z: 测试网
- INS 赵春艳 2026-06-15T00:21:20Z: 合约
- DEL 赵春艳 2026-06-15T00:21:28Z: 记录
- INS 赵春艳 2026-06-15T00:21:31Z: 完成
- INS 赵春艳 2026-06-15T00:21:33Z: 实验验证
- DEL 赵春艳 2026-06-15T00:21:36Z: ，

## Paragraph-level changed blocks
### Block 1: replace original paras 2-4, revised paras 2-3
OLD:
- 作者：杨帆
- 摘要
- 高频去中心化应用（DApp）要求低延迟、低链上开销与公开可验证仲裁并存。本文研究 Hybrid TEE-Rollup 中轻量链上承诺、链外数据可用性（DA）负载与超时挑战之间的协同机制，提出可恢复挑战机制、携带证据的紧凑提交机制以及数据可用性感知成本模型。可恢复挑战机制用于将超时会话恢复至可重放、可结算状态；携带证据的紧凑提交机制绑定状态根、输出哈希、证明哈希、DA 指针与 DA 根；数据可用性感知成本模型用于分析负载规模、批处理摊销与 DA 路径选择之间的关系。基于 Python 原型、本地 EVM gas 测量与 Sepolia 部署记录，实验结果表明：紧凑提交平均约为 406 字节；在负载 8192、批大小 1000 的配置下，模块化 DA 采样路径的摊销成本估算较全链上调用数据下降 96.33%；在合成超时场景中，恢复路径可将挑战成功率由 0% 提升至 100%。本文结论基于模拟 TEE、可验证 DA 注册表与配置化成本模型。
NEW:
- 杨帆
- 摘 要：高频去中心化应用（DApp）同时对系统延迟、链上开销以及一场场景下的公开可验证仲裁能力提出严苛要求。针对混合可信执行环境Rollup（Hybrid TEE-Rollup）架构，本文围绕轻量级链上承诺、链外数据可用性（Data Availability，DA）负载分发和超时挑战流程三者的协同运行机制展开研究，依次提出可恢复挑战协议、证据绑定型紧凑提交机制和DA感知成本摊销模型三大狠心设计。其中，可恢复挑战协议能够将因交互超时陷入🤚的挑战会话恢复至重放与结算的正常状态；证据绑定型紧凑提交将状态根、输出哈希、证明哈希、DA 指针与 DA 根进行密码学绑定，构建链上最小可信证据集；DA感知成本模型用于量化分析负载规模、批处理摊销与 DA部署路径对整体运行成本的影响规律。本文基于 Python 功能原型、以太坊虚拟机（EVM ）本地gas 测量与 Sepolia 测试网合约部署完成实验验证。结果表明：紧凑提交平均约为 406 字节；在负载 8192、批大小 1000 的配置下，模块化 DA 采样路径的摊销成本估算较全链上调用数据下降 96.33%；在模拟超时场景下，本文恢复机制可将挑战完成成功率从 0% 提升至 100%。本文所有结论均基于模拟 TEE、可验证 DA 注册表与配置化成本模型得出，实验边界清晰可控。

### Block 2: insert original paras 6-5, revised paras 5-9
NEW:
- 中图分类号：TP311 文献标志码：A
- Recoverable Challenge Protocol and Lightweight DA Cost Evaluation for
Hybrid TEE-Rollup in High-Frequency DApps
- YANG Fan
- Abstract: High-frequency decentralized applications (DApps) require low latency, low on-chain overhead, and publicly verifiable arbitration under abnormal executions. This paper studies the interaction between lightweight on-chain commitments, off-chain data availability (DA) payloads, and timeout challenges in Hybrid TEE-Rollup. It proposes a Recoverable Challenge protocol, an Evidence-Carrying Compact Commit, and a DA-Aware Cost Model. The recoverable challenge path restores timeout sessions to replayable and settleable states; the compact commit binds the state root, output hash, proof hash, DA pointer, and DA root; the cost model characterizes the effects of payload size, batching, and DA path selection. Experiments based on a Python prototype, local EVM gas measurements, and Sepolia d

### Block 3: replace original paras 10-14, revised paras 14-17
OLD:
- 实验部分采用合成负载、模拟 TEE、可验证 DA 注册表、本地 EVM gas 实测与 Sepolia 可部署性证据。实验设计与证据边界将在第 7 章和第 8 章集中说明。
- 1.1 本文贡献
- 第一个贡献是可恢复挑战机制。传统挑战流程中，超时可能使争议停留在未解决状态；即使系统已经检测到异常，也无法自然推进到重放与结算。本文将恢复操作从普通工程恢复提升为保持协议活性的状态转移机制：恢复不修改争议事实，而是在挑战事实不变的条件下，使停滞会话回到可重放、可仲裁路径，目标是保证协议的仲裁连续性。详见第 4 章。
- 第二个贡献是携带证据的紧凑提交。该提交将状态根、输出哈希、证明哈希、数据可用性指针与数据可用性根绑定在同一上下文中，使链上对象具备重放准备性、证据可追溯性和面向验证的属性。详见第 5 章。
NEW:
- 本文主要贡献如下。
- （1）提出可恢复挑战协议。传统挑战机制无法处理交互超时问题，异常即便被检测也难以推进至重放与结算阶段。本文将会话恢复从单纯的工程补救手段，升级为保障协议活性的标准化状态转移机制。该机制在不篡改争议事实的前提下，将停滞的挑战会话切换至可重放、可仲裁的正常链路，从协议层面保障仲裁连续性。
- （2）设计证据绑定型紧凑提交机制。该结构将状态根、输出哈希、证明哈希、DA 指针与 DA 根进行密码学绑定，使链上精简凭证具备重放前置能力、证据可追溯能力与可验证属性。
- （3）构建DA 感知成本摊销模型。该模型量化分析负载规模伸缩、批处理策略、DA 部署路径三类因素对系统成本的影响，为不同业务负载下的 DA 方案选型与成本管控提供理论依据。

### Block 4: insert original paras 16-15, revised paras 19-19
NEW:
- Table 1 Mechanism advances and roles

### Block 5: insert original paras 31-30, revised paras 35-35
NEW:
- 表 2 用于界定本文机制与既有系统的关系：已有系统通常已经具备挑战机制或 TEE 快速路径，本文关注的增量在于超时后的挑战活性、紧凑提交到数据可用性字段级证明的绑定关系，以及面向高频工作负载的成本解释。

### Block 6: replace original paras 32-32, revised paras 37-37
OLD:
- 表 2 用于界定本文机制与既有系统的关系：已有系统通常已经具备挑战机制或 TEE 快速路径，本文关注的增量在于超时后的挑战活性、紧凑提交到数据可用性字段级证明的绑定关系，以及面向高频工作负载的成本解释。
NEW:
- Table 2 Semantic comparison of mechanisms

### Block 7: replace original paras 72-72, revised paras 77-77
OLD:
- 3 系统概览
NEW:
- 3 系统架构与总体设计

### Block 8: insert original paras 75-74, revised paras 80-80
NEW:
- Fig.1 Prototype architecture of Hybrid TEE-Rollup

### Block 9: insert original paras 103-102, revised paras 109-109
NEW:
- Fig.2 Workflow of the recoverable challenge protocol

### Block 10: replace original paras 111-111, revised paras 118-118
OLD:
- 4.4 协议性质分析
NEW:
- 4.4 协议性质

### Block 11: replace original paras 113-113, revised paras 120-120
OLD:
- （一）挑战事实不变性
NEW:
- 4.4.1 挑战事实不变性

### Block 12: replace original paras 115-115, revised paras 122-127
OLD:
- • 状态根（State Root）：约束输入与输出哈希的绑定关系；
• 数据可用性根（DA Merkle Root）：约束 DA 层中完整负载的字段级承诺；
• 负载哈希（Payload Hash）：标识 DA 层中完整的原始负载；
• 执行轨迹（Execution Trace）：挑战方与被挑战方各自提交的执行步骤序列；
• 重放证据：二分缩小后定位到的目标步骤与对应的预期哈希和声明哈希；
• 不一致证据：验证、响应和 DA 字段检查中观测到的字段级不一致记录。
NEW:
- • 状态根（State Root）：约束输入与输出哈希的绑定关系；
- • 数据可用性根（DA Merkle Root）：约束 DA 层中完整负载的字段级承诺；
- • 负载哈希（Payload Hash）：标识 DA 层中完整的原始负载；
- • 执行轨迹（Execution Trace）：挑战方与被挑战方各自提交的执行步骤序列；

### Block 13: replace original paras 118-118, revised paras 130-130
OLD:
- （二）安全性与活性的分离
NEW:
- 4.4.2 安全性与活性分离

### Block 14: replace original paras 122-122, revised paras 134-134
OLD:
- （三）仲裁连续性
NEW:
- 4.4.3 仲裁连续性

### Block 15: replace original paras 126-126, revised paras 138-138
OLD:
- （四）恢复操作正确性与抗滥用边界
NEW:
- 4.4.4 恢复操作正确性与抗滥用边界

### Block 16: insert original paras 133-132, revised paras 145-145
NEW:
- Table 3 Protocol invariants and preserved properties

### Block 17: insert original paras 170-169, revised paras 183-183
NEW:
- Fig.3 Byte-size comparison between full payloads and compact commits

### Block 18: insert original paras 174-173, revised paras 188-188
NEW:
- Fig.4 Amortized gas trends under different DA configurations

### Block 19: insert original paras 181-180, revised paras 196-196
NEW:
- Fig.5 Relationship between bisection rounds and trace steps

### Block 20: insert original paras 182-181, revised paras 198-198
NEW:
- Fig.6 Impact of timeout recovery on challenge completion rate

### Block 21: insert original paras 186-185, revised paras 203-203
NEW:
- Fig.7 Detection and arbitration outcomes under failure scenarios

### Block 22: insert original paras 187-186, revised paras 205-205
NEW:
- Table 4 Failure scenarios and evidence boundaries

### Block 23: insert original paras 210-209, revised paras 229-229
NEW:
- Table 5 Average gasUsed of local EVM key paths

### Block 24: insert original paras 241-240, revised paras 261-261
NEW:
- Table 6 Sepolia deployment information

### Block 25: replace original paras 257-257, revised paras 278-278
OLD:
- 7.7 对比实验小结
NEW:
- 7.7 实验小结

### Block 26: insert original paras 260-259, revised paras 281-281
NEW:
- Table 7 Summary of comparison experiments

### Block 27: insert original paras 303-302, revised paras 325-325
NEW:
- Table 8 Comparison with related work

### Block 28: insert original paras 340-339, revised paras 363-363
NEW:
- 参考文献
