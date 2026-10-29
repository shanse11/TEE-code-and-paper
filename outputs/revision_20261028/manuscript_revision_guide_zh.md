# 《Hybrid TEE-Rollup》投稿稿修订指南

**目标文件**: `Hybrid_TEE_Rollup——《计算机应用》.docx` (SHA256: b331470e...)  
**修订日期**: 2026年10月28日  
**依据**: `outputs/revision_20261028/expert_response_matrix.md` §4 论文修订检查清单  
**修订原则**: 诚实报告、标注边界、不伪造数据

---

## 修订总览

本指南按章节列出所有需要修改的位置，包括：删除内容、新增内容、修改表述。每项修改都标注了来源（StageH数据、C阶段证据、G-L1对照等）。

**修订后文件命名建议**: `Hybrid_TEE_Rollup_返修稿_20261029.docx`

---

## 第一部分：摘要修订

### 1.1 删除重复的贡献段落

**位置**: 摘要中间部分（需手动定位重复内容）

**问题**: 摘要中可能存在与§1引言或§6结论重复的贡献描述

**修改**: 
- 检查摘要、§1引言、§6结论三处的贡献描述
- 删除摘要中与其他两处完全重复的段落
- 保留摘要的核心贡献陈述，简洁为主

### 1.2 对齐创新点与证据

**位置**: 摘要"创新点"或"主要贡献"段落

**原表述**（推测）: 
- "提出可恢复挑战机制"
- "首创第三方争议接续"
- "恢复机制降低结算延迟"

**修改为**:
```
本文针对有界高频DApp场景，提出一种在有界重算模型内不依赖交互的终止路径（显式adjudicate兜底），并首次量化恢复机制在该模型下的真实收益与代价。关键贡献包括：
(1) 显式adjudicate兜底机制：任何人可在任何时刻调用确定性重算，无需等待交互完成，保证有界终局；
(2) 恢复机制量化：通过同模型对照实验（210条记录），发现无兜底时提交方离线导致正确终局率从30/30跌至0/30，有兜底时均保持30/30，恢复代价为gas增加99%；
(3) 真实硬件验证：在阿里云SGX实例上获取真实DCAP Quote（TCB 0xA003），Enclave内有界哈希链与本地ethers逐字节一致；
(4) DA披露罚没闭环：新增bindDa/fulfillDa/slashDa机制，解决提交者×DA服务串谋场景，罚没比例从0%提升到100%。
```

### 1.3 标注边界

**位置**: 摘要末尾

**新增**:
```
本文实验包含本地EVM联调（Hardhat, closed-loop, local-gas-only）和真实SGX硬件验证。链上DCAP验证和Sepolia Blob广播因环境条件限制未完成。本文明确为有界重算模型（至多128步），非通用EVM Rollup。
```

---

## 第二部分：§1 引言修订

### 2.1 删除不实创新点声明

**位置**: §1引言中间（贡献陈述段落）

**删除以下表述**:
- ❌ "首创第三方争议接续"
- ❌ "恢复机制降低结算延迟/加快结算"
- ❌ "首次提出动态参与机制"
- ❌ 任何暗示"首创"的表述（OP FDG已有时钟继承）

**删除以下不当创新点**:
- ❌ 将哈希、Merkle树、DA成本摊销本身列为创新
- ❌ 声称"解决全部TEE风险"
- ❌ 声称"完全去信任"

### 2.2 重写创新点段落

**位置**: §1引言中间或末尾（"本文的主要贡献包括"段落）

**新表述**:
```
本文的主要贡献包括：

(1) **有界模型内的显式终止路径**：在至多128步全量重算模型内，提供不依赖交互的adjudicate兜底机制。任何人可在任何时刻调用确定性重算，无需等待交互完成或超时，保证有界终局。这与Optimism FDG的"只能在交互game tree叶节点resolve"不同。

(2) **恢复机制的真实量化**：通过G-L1同模型对照实验（210条记录），首次量化恢复机制的收益（无兜底时30/30→0/30）与代价（gas增加99%）。恢复的价值在于提供不依赖兜底重算的交互续推路径，而非降低延迟。

(3) **真实硬件验证与DA罚没闭环**：在阿里云SGX实例上获取真实DCAP Quote，建立DA披露罚没机制（bindDa/fulfillDa/slashDa），补齐提交者×DA服务串谋的罚没闭环。

(4) **系统性的权限与DoS防护验证**：通过17个定向测试用例（C01-C17）和7个不变量（INV1-INV7），系统性验证了权限约束、防重复恢复、防延长窗口、有界DoS等安全性质。
```

### 2.3 明确范围

**位置**: §1引言末尾或开头

**新增段落**:
```
需要明确的是，本文面向有界高频DApp场景（如DEX清算、NFT铸造等，已知计算上界），采用至多128步全量重算模型。本文不是通用EVM Rollup，不处理无界计算或复杂智能合约。本文假设至少一个有数据、有资金且可及时上链的诚实观察者存在，依赖下层L1在选定确认策略后的终局性。
```

### 2.4 研究问题改为可证伪形式

**位置**: §1引言中间（问题陈述段落）

**修改为**:
```
本文试图回答以下研究问题：

RQ1: 在有界重算模型内，参与者失联时能否通过第三方接续保证正确终局？
RQ2: 恢复机制是否引入延迟放大或DoS风险？
RQ3: 紧凑承诺（有序向量承诺）在恢复后能否支持确定性裁决？
RQ4: 真实TEE与DA接入增加何种成本与信任假设？
```

---

## 第三部分：§2 相关工作修订

### 3.1 补充opML文献条目

**位置**: 参考文献表（文末）

**新增条目**（编号待定，按首次出现顺序）:
```
[新增] optimistic Machine Learning (opML): [需检索原始来源]
- 建议来源：相关会议论文或arXiv预印本
- 格式示例：作者. opML: Optimistic Off-chain Machine Learning. 会议/期刊名, 年份.
```

**注意**: opML来源在09-18评估中标记为"本轮未采集"（待补充项T8），需要实际检索后填入。如无法找到可靠来源，可删除正文中的opML提及。

### 3.2 就近标注引用

**位置**: §2相关工作中间（4处）

#### 3.2.1 TEEROLLUP引用标注
**原位置**: "TEEROLLUP提出了利用异构TEE…"段落（原文@2787偏移，需在docx中手动定位）

**修改**: 在该句末尾添加上标`[1]`

**示例**:
```
TEEROLLUP提出了利用异构TEE（SGX、TDX、SEV）降低计算信任的方案[1]。
```

#### 3.2.2 opML和optimistic fraud proof引用标注
**原位置**: "opML与optimistic fraud proof等工作研究…"段落（原文@2863/@2870偏移）

**修改**: 在该句末尾添加上标`[新增opML编号], [相关编号]`

**示例**:
```
opML与optimistic fraud proof等工作研究了链下计算的乐观验证机制[新增], [相关]。
```

#### 3.2.3 Dynamic Fraud Proof引用标注
**原位置**: "Dynamic Fraud Proof关注…"段落（原文@3007偏移）

**修改**: 在该句末尾添加上标`[6]`

**示例**:
```
Dynamic Fraud Proof关注争议协议的灵活性与终局性压缩[6]。
```

#### 3.2.4 LazyLedger等引用标注
**原位置**: "LazyLedger、模块化DA以及轻客户端…"段落（原文@3099偏移）

**修改**: 在该句末尾添加上标`[7][8][9][10]`

**示例**:
```
LazyLedger、模块化DA以及轻客户端技术为数据可用性提供了新的设计空间[7][8][9][10]。
```

### 3.3 增加OP FDG时钟继承机制对比

**位置**: §2相关工作中间（Optimism相关段落后）

**新增段落**:
```
Optimism Fault Dispute Game（OP FDG）[补充引用]采用无界二分争议协议，支持通用EVM欺诈证明。OP FDG已有**时钟继承机制**和**三档CLOCK_EXTENSION**：在FaultDisputeGame.sol的move()内通过getChallengerDuration()实现，MAX_GAME_DEPTH-1层使用CLOCK_EXTENSION + oracle().challengePeriod()，SPLIT_DEPTH-1层使用×2延期。这使得第三方可以动态参与争议并延长挑战窗口。

本文与OP FDG的主要差异在于：(1) 本文采用**有界重算模型**（至多128步全量hash），OP FDG采用无界二分（单步VM指令争议）；(2) 本文提供**显式adjudicate兜底**（任何时刻可调用确定性重算），OP FDG只能在交互game tree叶节点resolve；(3) 本文的**恢复不刷新absoluteDeadline**，OP FDG通过时钟继承可动态延长。本文的优势在于协议简单（无game tree、无单步VM），适合已知上界的高频DApp；OP FDG的优势在于可扩展到无界计算（通用EVM），证明复杂度对数级。
```

### 3.4 版本锁定说明

**位置**: §2相关工作中间（首次提及TeeRollup、BoLD、OP FDG处）

**修改原表述为**:
```
- TeeRollup: 本文引用arXiv:2409.14647**v3**版本（其早期版本与v3在TEE平台与容错表述上不一致）
- BoLD: 本文引用arXiv:2404.10491v1版本 + GitHub commit 30e78f67
- OP FDG: 本文引用官方spec（访问日期2026-09-16）+ GitHub commit c4a68ab
```

### 3.5 差异表（可选，建议放在§2末尾或表格形式）

**新增表格**（或在正文中以段落形式陈述）:
```
表X 本文方案与相关工作对比

| 维度 | 本文 | TeeRollup v3 | BoLD v1 | OP FDG |
|---|---|---|---|---|
| 计算模型 | 有界重算（≤128步） | 有界TEE内执行 | 无界二分 | 无界二分 |
| 执行信任 | TEE辅助+确定性重算兜底 | 异构TEE（f由服务商设定） | 无TEE，纯争议 | 无TEE，纯争议 |
| 第三方参与 | 恢复+兜底adjudicate | 未明确 | 质押者竞争 | 时钟继承+三档延期 |
| 绝对截止 | absoluteDeadline固定 | 未明确 | 2·(Cmax+D) | 可动态延长 |
| 证明复杂度 | O(n) 全量重算 | O(n) TEE内 | O(log n) 二分 | O(log n) 二分+单步 |
| 来源 | 本文 | arXiv:2409.14647v3 | arXiv:2404.10491v1 | spec 2026-09-16 |
```

---

## 第四部分：§3 系统概览修订

### 4.1 新增§3.2 威胁模型表

**位置**: §3系统概览中间或末尾（在架构描述后）

**新增小节**:
```
### 3.2 威胁模型与可信假设

本文的安全性依赖以下可信假设与攻击能力边界。表X列出各参与方的可信假设、攻击能力、防护机制及残余风险。

表X 威胁模型与参与方假设

| 参与方 | 可信假设 | 攻击能力边界 | 防护机制 | 残余风险 |
|---|---|---|---|---|
| 提交者 | 提交有效签名、绑定DA押金 | 篡改结果、拒绝披露DA、友好挑战同伙 | B04/B05裁决拒绝；DA罚没（C12）；adjudicate兜底（C11） | 经济缺陷：友好挑战获利（B经济政策，未修） |
| 挑战者 | 绑定挑战押金 | 恶意挑战、抢先recover占位 | 押金损失；有界recover次数（C04/C09） | 无 |
| 观察者/恢复者 | **至少一方诚实且可上链** | 全部离线、Sybil抢占 | 状态链上持久化（C14）；recover无调用者限制；恢复上限（C05） | 全部离线+无人调用→terminate |
| DA服务 | 绑定押金并承担披露义务 | 串谋隐瞒数据 | DA罚没（C12） | 检查原像非点值证明；Sepolia blocked |
| TEE执行环境 | 链下Quote验证通过 | 硬件回滚、密钥泄露 | 协议层taskId唯一性（C15）；真实Quote绑定（StageH） | 不覆盖TEE硬件防回滚（D08 blocked）；链上罚没依赖DCAP验证 |
| L1底层链 | 按确认策略终局稳定 | 共识重组、永久审查 | 依赖L1安全假设 | 不提供跨重组额外保证 |

**关键假设**：
1. 至少一个有数据、有资金且可及时上链的诚实观察者存在；
2. 下层L1在选定确认策略（如12个区块）后不发生深度重组；
3. TEE Quote验证服务（当前为链下可信服务）诚实执行DCAP验证；
4. DA服务在绑定押金并承担披露义务时，会在窗口内披露数据原像（否则被罚没）。

**不承诺的边界**：
1. 永久审查或无限网络分区下的无条件活性；
2. TEE硬件防回滚或密钥泄露后的链上自动罚没（需链上DCAP验证）；
3. 跨L1共识重组的额外保证（依赖L1终局性）；
4. 通用EVM计算（仅支持有界128步模型）。
```

### 4.2 主动披露C11经济缺陷

**位置**: §3.2威胁模型表后

**新增段落**:
```
**经济缺陷披露**：当前协议在提交者×挑战者串谋场景下存在一个已知的经济缺陷（C11测试暴露）：在错误任务下，提交者可与"友好挑战者"串通，打开虚假挑战后快速和解，双方均分押金与奖励，排除诚实反证。虽然协议保留了诚实反证路径（任何人可调用adjudicate兜底），但经济激励上友好挑战确实可获利。这是协议经济设计问题（属B经济政策范畴），需要在激励机制层面（如提高押金、引入多挑战者竞争、延长反证窗口等）解决，本轮未修复。我们主动披露此缺陷，以便后续改进。
```

### 4.3 明确traceRoot定义与模型边界

**位置**: §3系统概览中间（计算模型或数据结构描述段落）

**新增或修改**:
```
**计算承诺定义**：本文的traceRoot采用有序向量承诺，定义为`traceRoot = keccak256(abi.encode(bytes32[]))`，其中bytes32[]为执行轨迹的有序哈希序列。这**不是Merkle根**，不支持Merkle单步证明，而是用于有界模型（至多128步）的全量重算验证。

**模型边界**：在有界模型+单链实例假设下，不存在分叉争议场景（两个不同轨迹对应同一traceRoot的情况）。若确实有双份提交，在链上体现为两个不同的taskId或同一taskId的不同traceRoot，会被协议拒绝（submit时检查唯一性）或作为两个独立任务分别裁决。因此本文不处理"分叉证明"场景。
```

### 4.4 补充观察者假设说明

**位置**: §3.2威胁模型段落内或紧随其后

**新增**:
```
**观察者假设的重要性**：本文协议的活性（liveness）依赖"至少一个有数据、有资金且可及时上链的诚实观察者"假设。若所有观察者离线且无人调用，协议只能通过absoluteDeadline + terminate超时终止，避免资金无限锁定。这是**有界活性**而非**无条件活性**。

**短时阻断 vs 永久审查**：协议可应对短时网络阻断或延迟消息（通过recover机制，见C13验证），但**不承诺对永久审查或无限分区的活性保证**。永久审查意味着底层L1本身失效，不是L2协议能解决的问题。
```

---

## 第五部分：§4 核心机制修订

### 5.1 §4.1 可恢复挑战协议

#### 5.1.1 回填权限矩阵

**位置**: §4.1开头或中间（协议描述后）

**新增表格**:
```
表X 协议操作权限矩阵

| 操作 | 调用者限制 | 前置条件 | 核心检查 |
|---|---|---|---|
| submit | 无限制（任何人） | 有效签名、押金足额 | 创建唯一任务，记录固定挑战截止时间 |
| openChallenge | 限非提交方 | 窗口内、有效押金 | 建立唯一争议，固定absoluteDeadline |
| respond | 仅提交方 | 在RESPONDING相位 | 提交有效proof，推进争议轮次 |
| **recover** | **无调用者限制** | timeoutAt < ts < absoluteDeadline 且 recoveries < maxRecoveries | 仅++recoveries与_touch(timeoutAt)，**不更换challenger、不改收益权、不改phase** |
| **adjudicate** | **无调用者限制** | 任何时刻（无时间门槛） | 确定性重算，裁决结果仅由verdict决定，第三方调用者**不能窃取收益** |
| settle | 无限制 | 已VERIFIED或超时 | 幂等结算，资金只支付一次 |
| terminate | 无限制 | 超absoluteDeadline且未终局 | 按既定规则超时结算 |
```

**关键说明**（在表后补充段落）:
```
recover和adjudicate操作均无调用者限制，保证了即使原挑战者或提交方离线，任何诚实观察者均可接管推进或直接终局。recover不改变争议事实（taskId、outputHash、traceRoot）、不更换收益权归属、不改变争议相位，仅增加recoveries计数和刷新timeoutAt（受absoluteDeadline截断）。adjudicate通过确定性重算直接给出裁决，是本文"不依赖交互的终止路径"的核心机制。
```

#### 5.1.2 回填防重复恢复逻辑

**位置**: §4.1中间（recover机制描述段落）

**新增或补充**:
```
**防止恶意重复恢复**：协议通过recoveries计数器和maxRecoveries上限（默认为2）防止无限恢复攻击。每次成功recover后++recoveries，超过上限则revert。拒绝后不丢失原任务状态，仍可通过adjudicate或terminate终局。

实验验证（C04/C05/C09）：
- C04：多观察者抢占recover后失联，第三次recover被拒（recovery limit），但terminate仍可收口
- C05：8个Sybil地址依次recover，实际成功2次，absoluteDeadline未变
- C09：maxRecoveries ∈ {0,1,2}精确生效，超上限revert且不丢原任务

为什么上限是2？第一次应对单次故障，第二次应对连续故障或攻击，第三次及以上视为DoS攻击或协议不可用，应通过adjudicate或terminate终局。
```

#### 5.1.3 回填防延长窗口机制

**位置**: §4.1中间（时间约束描述段落）

**新增或补充**:
```
**防止延长挑战窗口**：协议采用双时间边界机制：

1. **timeoutAt（动态）**：当前阶段截止时间，由_touch刷新，但受absoluteDeadline截断；
2. **absoluteDeadline（固定）**：绝对总截止时间，在任务提交或首次合法挑战时固定，**之后不可更改**。

**recover的时间窗口要求**：
```solidity
require(timeoutAt < block.timestamp < absoluteDeadline)
```
两端严格不等（`<`而非`<=`），避免off-by-one漏洞。

**_touch截断规则**：
```solidity
timeoutAt = min(block.timestamp + phaseWindow, absoluteDeadline)
```
保证刷新后的timeoutAt**不超过**absoluteDeadline，即使剩余时间不足以完成规定应答，也不创造超出总期限的不可能义务。

实验验证（C01/C06/C08）：
- C01：timeoutAt之前recover被拒，不重置期限、不改phase
- C06：双端严格不等，用evm_setNextBlockTimestamp精确控制、无自动出块+1s漂移，off-by-one与规范一致
- C08：剩余时间不足时_touch截断至absoluteDeadline
```

#### 5.1.4 回填有界DoS边界

**位置**: §4.1末尾（安全性分析段落）

**新增或补充**:
```
**有界DoS防护**：协议通过以下机制防止拒绝服务攻击：

1. **最大任务边界**：steps ∈ [0, 128]，步数上限保证确定性重算的gas可控；
2. **无效操作revert**：无效recover（超时/超上限/重复）直接revert，不修改状态；
3. **作废gas由攻击者承担**：revert的交易gas费由发起人支付，不影响协议账本；
4. **绝对截止+terminate**：即使所有方离线或被DoS，超absoluteDeadline后仍可terminate超时终止。

实验验证（C17关键）：最大任务(steps=128)正常结算（respond gas=204,737，adjudicate gas=164,567），**20次无效recover风暴20/20 revert**，状态无污染，累计作废gas=0 wei（由攻击者承担）。

**为什么是"有界"而非"无界"抗DoS**：有界指"在固定的计算规模（128步）和恢复次数（2次）内，协议能保证终局"。无界抗DoS需要假设"至少一方永远在线且可上链"，这在真实网络中不现实。
```

#### 5.1.5 补充状态转移表引用

**位置**: §4.1末尾或附录

**新增段落**:
```
**状态转移条件**：协议的完整状态转移条件记录在state_transition_table.json（C阶段产物）。简化版本如下：

**逻辑状态**：Committed（等待挑战窗口）、Challenged（等待响应）、Responding（响应中）、Resolved（争议已解决）、Finalized（已终局）。

**关键转移**（简化）：
1. Committed --[openChallenge]--> Challenged
2. Challenged --[respond]--> Responding
3. Responding --[adjudicate]--> Resolved
4. Challenged/Responding --[recover]--> 同状态（仅++recoveries + _touch）
5. 任何非Finalized状态 --[超absoluteDeadline + terminate]--> Finalized

**不变量（INV1-INV7）**：
- INV1：disputeId一旦建立不可更改
- INV2：提交事实（taskId, outputHash, traceRoot）在争议中不可更改
- INV3：absoluteDeadline在建立后不可延长
- INV4：recoveries单调递增
- INV5：资金账本满足三条会计恒等式
- INV6：已终局任务不可重开、重放、重复提现
- INV7：裁决结果仅由verdict决定，不受调用者影响

实验验证：5次不变量检查，0违反。
```

#### 5.1.6 标注"非形式化证明"

**位置**: §4.1末尾（安全性论述后）

**新增声明**:
```
**验证强度说明**：本文给出完整的状态转移条件、权限约束与不变量校验（INV1-INV7），属于**不变量级验证**。需要明确的是，这**不构成机器可检验的形式化证明**（无TLA+/Kani/Certora产物）。后续工作可将不变量转为TLA+或Certora模型进行机器验证。
```

#### 5.1.7 状态回滚说明

**位置**: §4.1末尾或§3威胁模型中

**新增段落**:
```
**状态回滚与共识重组**：本协议在协议层通过taskId唯一性与签名绑定防止重放攻击（C15验证：本地EVM快照回滚仿真通过）。需明确：**协议层防重放不等同于TEE硬件防回滚或共识层防重组**。

- **TEE硬件防回滚**：本文不声称覆盖TEE硬件防回滚（D08 blocked，需真实Enclave重启测试）。
- **共识层重组**：本文依赖下层L1的终局性假设（如12个区块确认后不发生深度重组），不承诺跨深度重组的额外保证（C16=not_applicable，Hardhat automining无真实重组）。

StageH真实SGX验证已建立Quote绑定机制（report_data与buildReportDataDigest一致性可验证），但链上罚没依赖链上DCAP验证服务（当前为链下验证，见§5.4）。
```

### 5.2 §4.2 计算承诺与裁决（或"有界重算"）

#### 5.2.1 明确traceRoot定义

**位置**: §4.2开头

**新增或修改**:
```
**有序向量承诺**：本文的traceRoot定义为：
```solidity
traceRoot = keccak256(abi.encode(bytes32[]))
```
其中bytes32[]为执行轨迹的有序哈希序列（每步的状态哈希）。这是**有序向量承诺**，不是Merkle根，不支持Merkle路径证明或单步争议。

**有界重算裁决**：adjudicate通过**至多128步全量重算**验证轨迹：从initial开始，按步骤依次重算，与提交的traceRoot比对。步数上限128保证gas可控（实测：128步adjudicate gas=166,840）。
```

#### 5.2.2 删除未实现能力声明

**位置**: §4.2中间或末尾（如有Merkle单步、对数复杂度等表述）

**删除以下内容**:
- ❌ "Merkle单步证明"
- ❌ "对数争议复杂度"
- ❌ "区间二分协议"
- ❌ 任何暗示"可扩展到无界计算"的表述

**确认保留**:
- ✅ "有序向量承诺"
- ✅ "至多128步全量重算"
- ✅ "有界模型"

#### 5.2.3 补充编码与域分离定义

**位置**: §4.2中间（数据结构描述段落）

**新增**:
```
**编码与域分离**：

1. **域标签**：HYBRID_BOUNDED_TASK_V1，防止跨协议重放；
2. **buildReportDataDigest**：
   ```
   digest = keccak256(abi.encode(
     execPubKey,      // 32字节执行公钥
     domain,          // "HYBRID_BOUNDED_TASK_V1"
     nonce,           // 32字节随机数
     epoch,           // uint256会话epoch
     appDigest        // 应用镜像摘要
   ))
   ```
3. **任务承诺链**：
   ```
   taskCoreDigest -> inputCommitment -> traceRoot -> outputHash -> dataHash
   ```
   每层绑定防止篡改和循环承诺（E01验证：单向性通过）。

StageH真实SGX验证中，Enclave将上述digest写入Quote的report_data字段（前32字节），实现MRENCLAVE绑定。
```

### 5.3 §4.3 TEE证明与密钥管理（或合并到§4.2）

**新增小节**（如原文没有单独的TEE章节，则在§4末尾新增）:

```
### 4.3 真实TEE远程证明与应用身份绑定

#### 4.3.1 平台与环境

本文在阿里云ecs.g7t.large实例（Intel Xeon Platinum 8369B，华北2北京）上部署真实SGX环境：

- **SGX SDK**: 2.19.100.3-1.al7
- **DCAP**: libsgx-dcap-ql 1.16.100.2-1.al7, libsgx-dcap-quote-verify 1.16.100.2-1.al7
- **PCCS**: https://sgx-dcap-server-vpc.cn-beijing.aliyuncs.com/sgx/certification/v4/
- **设备**: /dev/sgx_enclave、/dev/sgx_provision存在；无TDX设备

#### 4.3.2 真实DCAP Quote生成与验证

**Quote生成**：使用官方QuoteGenerationSample生成ECDSA Quote（cert_key_type=0x5，quote版本3，attestation key type 2）。三次生成墙钟：约1.25s、1.06s、1.03s。

**Quote验证**：独立QuoteVerificationSample（可信QvE路径和非可信路径）均返回：
- `tee_verify_quote successfully returned`
- 非终态结果`0xA003`（`SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED`）
- 附带advisory：INTEL-SA-00657、INTEL-SA-00767、INTEL-SA-01079、INTEL-SA-01103、INTEL-SA-01153、INTEL-SA-00615

**TCB状态说明**：0xA003表示"过期且需配置"，**不等于UpToDate（0x0000）**。签名和证书链被验证库接受，但TCB状态为非终态。这是平台TCB版本问题，需要实例升级或接受非终态策略。

#### 4.3.3 Enclave内有界哈希链验证

在真实Enclave内实现有界哈希链（initial=32个0x11，nonce=32个0x22），计算output、traceRoot，并把keccak256(output ‖ root ‖ nonce)写入Quote的report_data。

表X Enclave有界哈希链验证结果

| 步数 | Enclave计算加报告 | 宿主同代码128步 | Quote SHA256 | report_data前32字节 | MRENCLAVE |
|---|---|---|---|---|---|
| 4 | 0.057 ms | - | 75e84914... | d7ddfc60... | 1967faaa... |
| 128 | 0.497 ms | 100次合计30.495ms，单次0.305ms | bf78a99d... | dd38eea6... | 1967faaa... |

**一致性验证**：4步和128步的output、traceRoot与本地ethers逐字节一致。MRENCLAVE值：`1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37`（4&128步），`76f38bb26e1902666c40b433ddb3de91ecf39495c058d75f1dca120127fc63ea`（绑定Quote）。

#### 4.3.4 本地EVM联调

使用真实SGX生成的轨迹数据，在本地Hardhat上完成提交、挑战、裁决、提现全流程：

- 4步任务：adjudicate gas=94,836，verdict=0，状态SETTLED
- 128步任务：adjudicate gas=166,840，verdict=0，状态SETTLED

**说明**：合约没有链上验证Quote，这次联调是「真实SGX计算 + 本地EVM裁决」。

#### 4.3.5 链上DCAP验证（blocked）

**当前状态**：Quote验证在链下完成，合约依赖可信验证服务的签名。链上自主DCAP验证需要集成Intel DCAP验证库或可信服务桥接，因时间和资源限制本轮未实现。

**解除条件**：
1. 选择验证路径：链上验证库（gas成本高、复杂）或可信验证服务+服务签名（依赖链下服务）
2. 实现TEEVerifier接口，接受Quote、返回DECISION枚举
3. submit()调用时验证Quote的report_data绑定、measurement策略、TCB状态
4. 集成到B/C回归测试

**论文中明确标注**：本文当前依赖链下Quote验证（可信验证服务），链上自主DCAP验证为后续工作。
```

### 5.4 §4.4 DA绑定、披露与成本

#### 5.4.1 新增DA披露罚没机制

**位置**: §4.4开头或中间

**新增小节**:
```
#### 4.4.1 DA披露罚没机制

为解决提交者×DA服务串谋隐瞒数据问题（C12场景），本文在BoundedTaskRollup.sol中新增可选的DA披露罚没机制：

**三个函数**：
1. **bindDa(taskId, daRef) payable**：提交者在挑战窗口内绑定等额DA押金（与任务押金相同），并登记daRef（数据引用，如Blob versionedHash或IPFS CID）；
2. **fulfillDa(taskId, dataPayload)**：提交者在披露窗口内交出dataHash的原像（完整数据），合约验证keccak256(dataPayload)==dataHash，通过则DA押金变为可提取；
3. **slashDa(taskId)**：任何人可在披露窗口超时后调用，将未履约的DA押金销毁到address(0)。

**状态依赖**：绑定DA后，adjudicate、settle、terminate、finalize在DA披露或罚没完成前会回退"da pending"，保证裁决前必须完成DA披露或罚没。

**实验验证（C12）**：提交者×DA观察者串谋隐瞒数据，通过DA罚没机制解决。测试通过，罚没1 ether，slashDa gas=66,136。C12从deferred_to_E变为verified。StageB/C回归测试26 passing，DA罚没未破坏原有功能。

**重要说明**：
1. 当前实现检查dataHash的**原像披露**（完整数据），不是EIP-4844的**KZG点值证明**（blobhash与evaluationPoint验证）。
2. 未调用bindDa的任务行为与原来相同（无DA披露义务），保持向后兼容。
```

#### 5.4.2 保持E01真实KZG密码学

**位置**: §4.4中间（DA编码或Blob相关段落）

**补充或确认有以下内容**:
```
**真实KZG密码学验证（E01）**：本文使用c-kzg 4.1.0库真实调用blobToKzgCommitment、computeBlobKzgProof、verifyBlobKzgProof。

**容量验证**：
- 单Blob最大帧长：126,976字节（4,096个field elements × 31数据字节 + 帧开销79字节）
- 最大内容长度：126,897字节（减去domain 26字节）
- 满容量验证通过；超出1字节抛类型化错误`SINGLE_BLOB_CAPACITY_EXCEEDED`（不截断、不缩小载荷）

**篡改检测**：修改Blob任意字节后，KZG验证失败（verifyBlobKzgProof返回false）。

**单向性**：taskCoreDigest不随manifest变化（E01验证：无循环承诺）。

**trusted setup**：c-kzg 4.1.0自带trusted setup，sha256前16字符：d39b9f2d047cc9dc。
```

#### 5.4.3 标注Sepolia Blob blocked

**位置**: §4.4末尾或E01段落后

**新增声明**:
```
**Sepolia Blob广播（blocked）**：真实type-3交易广播、独立异进程取回、链上绑定裁决因缺少Sepolia RPC endpoint、测试钱包私钥、beacon API endpoint等环境条件，本轮未能完成。

**解除条件**：
1. 获取Sepolia RPC endpoint（如Infura/Alchemy）
2. 生成测试钱包并获取Sepolia ETH（faucet或转账）
3. 部署BlobBatchAnchor合约到Sepolia并记录地址
4. 配置beacon API endpoint（https://sepolia.beaconcha.in/api/或同步节点）
5. 运行blob_publish.js、blob_fetch.js、blob_verify.js
6. 记录交易哈希、区块、versionedHash、blobGasUsed/Price、取回日志

**论文中明确标注**：当前DA披露检查原像（dataHash），Sepolia Blob广播为后续工作。
```

#### 5.4.4 成本公式更新

**位置**: §4.4末尾（成本分析段落）

**补充或修改**:
```
**DA成本模型更新**：

每批总成本 = L1执行gas × gasPrice + Blob gas × blobGasPrice + TEE证明与执行 + DA服务或归档 + 争议与恢复成本

**关键参数**：
- L1执行gas：实测submit/respond/adjudicate等操作gas（见§5）
- Blob gas：按实际Blob数量阶梯计费（不是无限按1/批大小下降）
- TEE执行：Enclave内128步0.497ms（StageH实测）
- DA罚没：bindDa押金（等额任务押金），slashDa gas=66,136
- 争议恢复：recover gas、adjudicate gas（见§5）

**Blob数量阶梯**：需计入填充、跨Blob边界、低填充率和保留期。论文原有96.33%摊销优势来自**成本模型**（F Blob阶梯标为modelled），**不能替代真实模块化DA网络实验**（本轮未开展）。

**单位成本口径**：单任务成本用成功任务数作分母，同时给出按已提交任务数和失败开销的补充口径，避免失败被隐藏。
```

---

## 第六部分：§5 实验评估修订

### 6.1 分层描述实验环境

**位置**: §5开头（原"实验环境"段落）

**修改为**:
```
### 5.1 实验环境与口径

本文实验分为三层：

**第一层：本地受控实验**（Hardhat, closed-loop）
- 环境：Node.js 18.x, Hardhat 2.22.0, Solidity 0.8.24
- 网络：in-process automining，每块链钟+1秒，无真实共识最终性
- 到达模式：closed-loop（非open-loop压力）
- 样本：每配置3个独立run，每run 5预热+30稳态批次
- 费用口径：**local-gas-only**（不含DA/TEE成本）
- 用途：权限与DoS验证（C阶段）、机制对照（G-L1）、性能基准（F阶段）

**第二层：真实硬件实验**（阿里云SGX实例）
- 平台：ecs.g7t.large，Intel Xeon Platinum 8369B，华北2（北京）
- SGX SDK：2.19.100.3，DCAP 1.16.100.2
- 用途：真实DCAP Quote生成与验证、Enclave内有界哈希链、MRENCLAVE绑定
- 与第一层联调：真实SGX计算 + 本地EVM裁决

**第三层：公网测试网实验**（blocked）
- 目标网络：Sepolia（EIP-4844 type-3 Blob）
- blocked原因：缺RPC URL、私钥、beacon API
- 用途：真实Blob广播、独立异进程取回、链上绑定裁决

**重要口径限制**（必须随所有第一层数据报告）：
1. Hardhat in-process automining，无真实共识最终性
2. 每块链钟+1秒，固定出块间隔
3. Closed-loop到达（非open-loop压力）
4. 仅3个独立run（不报p95/p99，不输出bootstrap CI）
5. 费用为local-gas-only（不含DA/TEE成本）
6. Payload维度（1 KiB vs 32 KiB）在有界模型中为**名义参数**（dataHash固定32字节），不构成"扩展到大块数据仍保持吞吐"的证据
7. 并发无单调增益（受串行出块限制）

**不因完成真实SGX而写成"生产环境已验证"**：第二层为测试实例+本地EVM联调，非生产主网部署。
```

### 6.2 更新表4故障类型矩阵

**位置**: §5中间（原表4位置）

**完全替换为新表格**:
```
表4 故障类型与罚没闭环验证

| 故障类型 | 检测率 | 挑战成功率 | 罚没比例 | 09-18状态 | 本轮状态 | 依赖/限制 | 验证用例 |
|---|---|---|---|---|---|---|---|
| 响应篡改 | 100% | 100% | 100% | ✅已闭环 | ✅保持 | B04/B05 | B04 |
| 轨迹长度不匹配 | 100% | 100% | 100% | ✅已闭环 | ✅保持 | B04 | B04 |
| 远程证明无效 | 100% | - | 协议层防护 | ❌未解决 | ⚠️部分（拒绝新提交） | 需链上DCAP验证 | C15, StageH |
| **DA不可用** | 100% | 100% | 0% → **100%** | ❌未解决 | ✅**已闭环** | bindDa/slashDa | **C12** |
| **DA证明无效** | 100% | 100% | 0% → **100%** | ❌未解决 | ✅**已闭环** | 同上 | **C12** |
| 提交者失联无证据 | 100% | - | 0%（设计选择） | ⚠️limited | ⚠️保持limited | 不罚没无责任方（E11） | C03 |

**关键改进**：
1. **DA类从0%罚没提升到100%**：通过bindDa/fulfillDa/slashDa机制，解决提交者×DA服务串谋场景（C12）。提交者需绑定等额DA押金并在窗口内披露dataHash原像，超时则任何人可罚没到address(0)。实测：罚没1 ether，slashDa gas=66,136。

2. **远程证明防护说明**：协议层通过Quote的report_data绑定检测（与buildReportDataDigest一致性），submit时拒绝无效证明的新提交。链上罚没（扣除历史押金）依赖链上DCAP验证服务（当前为链下验证，见§4.3）。

3. **设计选择明确**：提交者失联无可转发证据（C03）为协议设计选择，不罚没无责任外部方（E11原则：RPC失败、保留期过期、不可抗力分区等，不应罚没无责任方）。通过absoluteDeadline + terminate保证有界终止，避免资金无限锁定。

**三条会计恒等式验证**（B01/B10-B14，BigInt记账）：
- balance == locked + totalClaimable
- balance == totalDeposited - totalWithdrawn - totalBurned
- totalClaimable <= balance
全场景成立，证明资金闭环完整性。
```

### 6.3 新增§5.4 真实TEE远程证明实验

**位置**: §5中间（在原"安全实验"或"性能实验"之后）

**新增小节**（内容见§4.3，此处简化引用）:
```
### 5.4 真实TEE远程证明实验

#### 5.4.1 实验环境

在阿里云ecs.g7t.large实例（Intel Xeon Platinum 8369B）上部署真实SGX环境（详见§4.3.1）。

#### 5.4.2 真实DCAP Quote验证结果

生成4条真实ECDSA Quote，独立验证均返回0xA003（SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED）。表X列出Quote摘要（完整Quote不公开，含平台身份信息）：

表X 真实SGX Quote验证结果

| Quote文件 | SHA256（前8字符） | report_data前32字节 | 验证结果 | 用途 |
|---|---|---|---|---|
| quote_bound.dat | 9ab7ae99... | 与buildReportDataDigest一致 | 0xA003 | 绑定摘要验证 |
| quote_bad.dat | a334b444... | 首字节篡改为0x20 | 0xA003 | 负例：密码学通过但绑定失败 |
| quote_steps4.dat | 75e84914... | d7ddfc60...（4步result） | 0xA003 | 有界哈希链4步 |
| quote_steps128.dat | bf78a99d... | dd38eea6...（128步result） | 0xA003 | 有界哈希链128步 |

**TCB状态说明**：0xA003表示"过期且需配置"（关联6个Intel advisory），签名和证书链验证通过，但非UpToDate（0x0000）。

#### 5.4.3 Enclave内有界哈希链性能

表X Enclave性能对比（initial=32个0x11, nonce=32个0x22）

| 步数 | Enclave内计算+报告 | 宿主同代码（100次均值） | MRENCLAVE |
|---|---|---|---|
| 4 | 0.057 ms | - | 1967faaa... |
| 128 | 0.497 ms | 0.305 ms | 1967faaa... |

Enclave内时间包含计算output、traceRoot和生成Quote；宿主时间仅含哈希链，不含进出Enclave。4步和128步与本地ethers逐字节一致。

#### 5.4.4 本地EVM联调gas

使用真实SGX轨迹在本地Hardhat上联调：

- 4步任务：adjudicate gas=94,836
- 128步任务：adjudicate gas=166,840

两个任务verdict=0均SETTLED。**说明**：合约没有链上验证Quote，这是"真实SGX计算 + 本地EVM裁决"联调。

#### 5.4.5 链上DCAP验证（blocked）

当前Quote验证在链下完成，合约依赖可信验证服务签名。链上自主DCAP验证需集成Intel验证库，本轮未实现（见§4.3.5）。
```

### 6.4 补充DA披露罚没实验结果

**位置**: §5中间（在表4之后或安全实验段落）

**新增段落**:
```
#### 5.X DA披露罚没机制验证

**C12串谋罚没实验**：提交者×DA观察者串谋隐瞒数据，通过DA披露罚没机制解决。实验流程：
1. 提交者submit任务并bindDa（绑定等额DA押金1 ether）
2. 挑战者openChallenge，提交者respond但拒绝披露DA数据
3. 披露窗口超时后，任何人调用slashDa
4. 实测：罚没1 ether销毁到address(0)，slashDa gas=66,136

**StageB/C回归测试**：重跑stageB_closure.test.js和stageC_recovery.test.js，确认DA罚没机制未破坏原有功能。结果：**26 passing**（含B01-B14、C01-C17全部用例）。

**C12状态更新**：从deferred_to_E（09-18评估）变为verified（本轮）。

**限制说明**：当前实现检查dataHash的**原像披露**（完整数据），不是EIP-4844的**KZG点值证明**。Sepolia Blob广播blocked（见§5.4.5）。
```

### 6.5 引用G-L1机制对照数据

**位置**: §5中间（原"性能实验"或新增"机制对照实验"段落）

**新增或补充**:
```
### 5.X 同模型机制对照实验（G-L1）

#### 5.X.1 实验设计

为量化恢复机制的真实收益与代价，我们构造机制基线（无兜底adjudicate）与本文实现（有兜底adjudicate）进行同模型对照。

**系统**：
- 本文实现（4臂）：interactive、fault-no-recovery、fault-with-recovery、direct-no-response
- 机制基线（3臂）：interactive、fault-no-recovery、direct-no-response

**输入**：steps=64，batchSize=1，同部署参数，同进程配对测量

**运行**：每臂3个run，每run 10个测量批（预热5批+稳态30批），共210条非预热记录

**环境**：本地Hardhat（口径限制见§5.1）

**重要说明**：机制基线是本项目自建的简化版合约，**不是Arbitrum、Optimism或TeeRollup的官方实现**。机制基线的唯一差异是**无兜底adjudicate**，其他逻辑与本文实现相同。

#### 5.X.2 实验结果

表X 同模型机制对照结果（G-L1, 210条非预热记录）

| 系统 | 路径 | 正确终局 | 错误终局 | resolve gas合计 |
|---|---|---|---|---|
| 本文 | interactive | 30/30 | 0 | 15,148,776 |
| 本文 | fault-no-recovery | 30/30 | 0 | 8,076,444 |
| 本文 | fault-with-recovery | 30/30 | 0 | 16,121,160 |
| 本文 | direct-no-response | 30/30 | 0 | 3,884,634 |
| 机制基线 | interactive | 30/30 | 0 | 11,517,024 |
| **机制基线** | **fault-no-recovery** | **0/30** | **30** | **4,893,744** |
| **机制基线** | **direct-no-response** | **0/30** | **30** | **1,602,852** |

#### 5.X.3 关键发现

1. **无兜底时正确终局率从30/30跌至0/30**：在机制基线（无兜底adjudicate）中，提交方离线（fault-no-recovery）或无响应（direct-no-response）时，全部30个任务错误终局（罚没诚实提交方）。

2. **有兜底时均保持30/30**：在本文实现（有兜底adjudicate）中，所有路径均30/30正确终局（包括提交方离线场景）。

3. **恢复机制的价值**：提供不依赖兜底重算的交互续推路径。对比fault-with-recovery与fault-no-recovery（都是本文实现，都有兜底），二者均30/30正确终局，但前者允许第三方接管交互。

4. **恢复机制的代价**：gas增加**99%**。fault-with-recovery (16,121,160) vs fault-no-recovery (8,076,444)，增幅=(16.1M-8.1M)/8.1M≈99%。

#### 5.X.4 配对延迟差（补充）

本地Hardhat closed-loop到达下，批总延迟差（3 cluster，无bootstrap CI）：
- interactive：baseline - ours = -1.20 ms（本文略慢）
- fault-no-recovery：baseline - ours = -0.47 ms

**说明**：延迟差为负数表示本文实现略慢于机制基线（因adjudicate兜底增加了操作）。**恢复机制未减少延迟**，与F消融实验一致（recovery-under-fault=12.6ms vs direct-fallback=7.3ms）。
```

### 6.6 新增OP FDG组件测试结果

**位置**: §5中间（G-L1段落后或"第三方比较"段落）

**新增段落**:
```
#### 5.X.X Optimism FDG组件测试（G-L2部分）

为验证OP FDG的时钟继承机制，我们在Optimism commit c4a68ab上运行官方Foundry测试。

**环境**：
- Optimism仓库：commit c4a68ab07a7c6ad51042f1b33d5faf4f4596f3af
- Foundry：1.5.1-stable
- 测试用例：FaultDisputeGameTest中的3个官方测试

**结果**：

表X OP FDG组件测试gas（Foundry 1.5.1）

| 测试用例 | gas | 说明 |
|---|---|---|
| test_move_simpleAttack_succeeds | 365,885 | move()攻击场景 |
| test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds | 2,778,766 | step()防御场景 |
| test_resolve_stepReached_succeeds | 3,731,850 | resolve()终局场景 |

**重要说明**：
1. 上述gas为**组件测试gas**，包含断言和测试框架开销，**不是单次调用gas**。
2. **不是Optimism主网吞吐**，只能用于组件级验证。
3. **不能与本文本地Hardhat gas合成领先比例表**（端点语义不同，见G-CE-06）。

**确认事实**：通过运行官方测试，确认OP FDG已有**时钟继承机制**+**三档CLOCK_EXTENSION**（在FaultDisputeGame.sol的move()内getChallengerDuration()实现）。因此本文不能声称"首创第三方接续"，创新点需重定位（见§1、§6）。
```

### 6.7 保持F本地指标，整段标注口径限制

**位置**: §5中间（原"性能实验"段落）

**确认有以下内容并整段标注**:
```
### 5.X 本地性能基准（F阶段）

#### 5.X.1 吞吐与延迟

baseline配置（batchSize=8, payloadKiBPerTask=8, concurrency=4, steps=64）：
- 吞吐：**162.78 tasks/s**（3 run均值）
- 批总延迟：161.8 ms

#### 5.X.2 消融实验

恢复机制时间消融（4臂，3 run × 30 batch）：
- recovery-under-fault：12.6 ms（中位延迟）
- direct-fallback：7.3 ms
- **关键发现**：**恢复未减少延迟**（12.6ms > 7.3ms）

#### 5.X.3 并发实验

并发配置（batchSize=1，concurrency ∈ {1, 4, 16}）：
- 在途峰值：达配置值（1, 4, 16）
- 吞吐：121.79 / 144.63 / 117.19 tasks/s
- **关键发现**：**无单调增益**（受串行出块限制）

#### 5.X.4 挑战窗口归因

三格配置在window=100000时终局率回到1.0，TPS为156.93 / 154.04 / 87.07。

#### 5.X.5 Payload维度（名义参数）

1 KiB vs 32 KiB：137.38 vs 138.54 tasks/s（几乎无差异）

**说明**：在有界模型中，dataHash固定32字节，payload大小为**名义参数**（任务提交时只上传hash，不上传完整payload）。因此payload维度**不构成"扩展到大块数据仍保持吞吐"的证据**。

---

**⚠️ 必须整段附带的口径限制（不可省略）**：

1. **Hardhat in-process automining**：无真实共识最终性
2. **每块链钟+1秒**：固定出块间隔，非真实网络
3. **Closed-loop到达**：非open-loop压力测试
4. **仅3个独立run**：不报p95/p99，不输出bootstrap CI
5. **费用为local-gas-only**：不含DA/TEE成本
6. **Payload为名义参数**：dataHash固定32字节，1 KiB vs 32 KiB几乎无差异
7. **并发无单调增益**：受串行出块限制

**禁止表述**：
- ❌ "高频DApp TPS 162.78"（应写"本地Hardhat TPS 162.78"）
- ❌ "payload扩展到32 KiB仍保持吞吐"（名义参数，不构成证据）
- ❌ "并发提升带来吞吐线性增长"（实际无单调增益）
```

### 6.8 引用C阶段权限与DoS证据

**位置**: §5中间（原"安全实验"段落）

**新增或补充**:
```
### 5.X 权限与DoS防护验证（C阶段）

#### 5.X.1 权限约束验证

合约接口权限矩阵（见表X）已通过C02验证：recover/adjudicate无调用者限制，openChallenge限非提交方，respond仅提交方。

#### 5.X.2 防重复恢复验证

- C04：多观察者抢占recover后失联，第三次被拒
- C05：8个Sybil地址依次recover，实际成功2次，absoluteDeadline未变
- C09：maxRecoveries ∈ {0,1,2}精确生效

#### 5.X.3 防延长窗口验证

- C01：timeoutAt之前recover被拒
- C06：双端严格不等（`<`非`<=`），off-by-one与规范一致
- C08：_touch截断至absoluteDeadline

#### 5.X.4 有界DoS验证

C17（关键）：最大任务(steps=128)正常结算（respond gas=204,737，adjudicate gas=164,567），**20次无效recover风暴20/20 revert**，状态无污染，累计作废gas=0 wei（由攻击者承担）。

#### 5.X.5 不变量验证

INV1-INV7（7个不变量）：5次检查，**0违反**。关键不变量包括：
- INV2：提交事实（taskId, outputHash, traceRoot）在争议中不可更改
- INV3：absoluteDeadline在建立后不可延长
- INV7：裁决结果仅由verdict决定，不受调用者影响
```

---

## 第七部分：§6 结论修订

### 7.1 对齐摘要与证据

**位置**: §6结论开头或中间（研究问题回答段落）

**修改为**:
```
本文针对有界高频DApp场景，提出了在有界重算模型内不依赖交互的终止路径，并首次量化了恢复机制的真实收益与代价。

**研究问题回答**：

RQ1（参与者失联时能否接续保证正确终局？）：能。通过recover（第三方可接管交互）+ adjudicate兜底（任何人可直接终局），在提交方离线场景下保持30/30正确终局率。对比：无兜底机制基线的正确终局率从30/30跌至0/30。

RQ2（恢复是否引入延迟放大或DoS？）：恢复**未减少延迟**（消融实验：recovery-under-fault=12.6ms vs direct-fallback=7.3ms）。但通过有界recover次数（maxRecoveries=2）、双时间边界（absoluteDeadline固定）、无效操作revert机制，防止DoS攻击（C17：20次无效风暴20/20 revert，状态无污染）。

RQ3（紧凑承诺在恢复后能否支持裁决？）：能。traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），支持至多128步全量重算。恢复不改变提交事实（INV2），adjudicate通过确定性重算给出裁决（128步gas=166,840）。

RQ4（真实TEE与DA增加何种成本？）：StageH真实SGX实验显示Enclave内128步0.497ms（宿主同代码0.305ms），本地EVM联调adjudicate gas=166,840。DA披露罚没新增bindDa押金（等额任务押金）和slashDa gas=66,136。TCB状态0xA003（过期需配置），链下Quote验证依赖可信服务。
```

### 7.2 明确真实验证范围

**位置**: §6结论中间

**新增段落**:
```
**真实验证范围**：

1. **真实SGX Quote**：在阿里云ecs.g7t.large实例上获取真实DCAP Quote（TCB 0xA003），Enclave内有界哈希链与本地ethers逐字节一致，MRENCLAVE绑定可验证。
2. **真实KZG密码学**：使用c-kzg 4.1.0真实调用，容量126,976字节验证通过，篡改拒绝。
3. **本地EVM联调**：真实SGX计算 + 本地Hardhat裁决，4步gas=94,836，128步gas=166,840。
4. **DA披露罚没闭环**：bindDa/fulfillDa/slashDa，C12罚没1 ether，slashDa gas=66,136。

**明确边界**：
1. **链上DCAP验证blocked**：当前Quote验证在链下完成，依赖可信验证服务。
2. **Sepolia Blob广播blocked**：缺RPC URL/私钥/beacon API，type-3真实发布未完成。
3. **UpToDate TCB blocked**：当前0xA003（过期需配置），非UpToDate（0x0000）。
4. **本地指标不是生产TPS**：F阶段162.78 tasks/s为Hardhat closed-loop本地测量，附带口径限制（无真实共识最终性、local-gas-only等）。
```

### 7.3 明确计算模型与假设

**位置**: §6结论中间

**新增或确认**:
```
**计算模型**：有界重算（至多128步全量hash），有序向量承诺（traceRoot=keccak256(abi.encode(bytes32[]))），**非通用EVM Rollup**，不支持无界计算或复杂智能合约。适用场景：已知计算上界的高频DApp（如DEX清算、NFT铸造等）。

**关键假设**：
1. 至少一个有数据、有资金且可及时上链的诚实观察者存在
2. 下层L1在选定确认策略后终局稳定（不发生深度重组）
3. TEE Quote验证服务（当前为链下）诚实执行DCAP验证
4. DA服务在绑定押金并承担披露义务时，会在窗口内披露数据原像

**不承诺边界**：
1. 永久审查或无限网络分区下的无条件活性
2. TEE硬件防回滚或密钥泄露后的链上自动罚没
3. 跨L1共识重组的额外保证
4. 通用EVM计算
```

### 7.4 删除不实结论

**位置**: §6结论中间或末尾

**删除以下表述**:
- ❌ "完全去信任"
- ❌ "解决全部TEE风险"
- ❌ "优于所有Rollup"
- ❌ "生产环境已验证"
- ❌ "首创第三方接续"
- ❌ "恢复降低延迟"
- ❌ 任何不当的绝对化结论

---

## 第八部分：参考文献修订

### 8.1 补充opML文献条目

**位置**: 参考文献表（文末）

**新增条目**（需实际检索后填入）:
```
[新增编号] 作者名. opML: Optimistic Off-chain Machine Learning. 会议/期刊名, 年份.
（或）
[新增编号] 作者名. opML: Title. arXiv preprint arXiv:XXXX.XXXXX, 年份.
```

**注意**：如无法找到可靠来源，应删除正文中的opML提及，而不是造假文献。

### 8.2 版本锁定说明

**位置**: 参考文献表中相应条目

**修改现有引用为**:
```
[1] TeeRollup作者. TeeRollup: Efficient Rollup Design Using Heterogeneous TEE. arXiv preprint arXiv:2409.14647v3, 2024. **注：本文特指v3版本**

[BoLD编号] BoLD作者. BoLD: Fast and Cheap Dispute Resolution. arXiv preprint arXiv:2404.10491v1, 2024. **注：GitHub commit 30e78f67**

[OP FDG编号] Optimism. Fault Dispute Game Specification. https://specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html, 访问日期：2026-09-16. **注：GitHub commit c4a68ab**
```

### 8.3 逐一核对引用

**位置**: 全文

**检查清单**:
- [ ] §1引言中的[1]-[12]是否在首次提及处标注？
- [ ] §2相关工作中的4处补标（见§3.2）是否完成？
- [ ] §4机制描述中的引用是否准确？
- [ ] §5实验中引用C/D/E/F/G阶段是否适当？
- [ ] 参考文献表中的[1]-[12]顺序是否与正文首次出现一致？

---

## 第九部分：格式与细节修订

### 9.1 去重检查

**全文检查**（重点）:
- [ ] 摘要、§1引言、§6结论的贡献描述是否重复？
- [ ] §1与§2的相关工作介绍是否重复？
- [ ] §4与§5的机制描述是否重复（§4描述协议，§5描述实验）？
- [ ] 表格与正文是否重复陈述同一数据？

**去重原则**：
- 摘要：最简洁，只写核心贡献（2-3句）
- §1引言：中等详细，交代背景+贡献概要（1段）
- §6结论：详细，逐条回答研究问题+总结贡献（2-3段）
- 如有重复，优先保留§6详细版，删除摘要/§1冗余部分

### 9.2 图表更新

**图1系统架构**（如需修改）:
- 标出任务数据流、承诺流、证明流、资金流
- 用图例区分链上验证、链下独立验证、可信服务
- 标明Blob数据暂存和长期恢复/归档的边界

**图2状态转移图**（如需修改）:
- 改为可区分正常、挑战、接管、超时、结算的状态图
- 标注recover路径（同状态内++recoveries）
- 标注adjudicate兜底（任何状态可直接到Resolved）

**表格编号连续性**:
- 最终稿统一连续编号（表1、表2、…）
- 本指南中的"表X"为占位符，实际编号在最终稿确定

### 9.3 术语一致性

**全文统一使用**:
- ✅ "有界重算模型"（不用"有限重算"）
- ✅ "有序向量承诺"（不用"哈希数组"）
- ✅ "显式adjudicate兜底"（不用"后备裁决"）
- ✅ "absoluteDeadline"（不译为中文，保持代码一致）
- ✅ "本地Hardhat"（不用"本地环境"笼统表述）
- ✅ "TCB 0xA003"（不写成"TCB过期"，保留16进制编号）

---

## 第十部分：修订后验证清单

完成上述修订后，请逐项检查：

### 10.1 创新点对齐（关键）
- [ ] 删除"首创第三方接续"等不实声明
- [ ] 改为"有界模型内不依赖交互的终止路径+恢复量化"
- [ ] 摘要、§1、§6三处创新点表述一致
- [ ] 不再将哈希、Merkle、摊销本身列为创新

### 10.2 StageH数据回填（关键）
- [ ] §4.3新增真实TEE章节（平台、Quote、MRENCLAVE、性能）
- [ ] §5.4新增真实TEE实验章节（表格、TCB 0xA003、gas）
- [ ] §4.4新增DA披露罚没机制（bindDa/fulfillDa/slashDa）
- [ ] §5更新表4（DA类0%→100%罚没）
- [ ] §5新增G-L1机制对照（210条记录表格）
- [ ] §5新增OP FDG组件测试（3个测试，gas 365k~3.7M）

### 10.3 威胁模型补充（关键）
- [ ] §3.2新增威胁模型表（6类参与方）
- [ ] §3主动披露C11经济缺陷
- [ ] §3明确traceRoot定义与模型边界（不处理分叉证明）
- [ ] §3补充观察者假设与永久审查不承诺活性

### 10.4 权限与DoS回填（关键）
- [ ] §4.1新增权限矩阵表
- [ ] §4.1补充防重复恢复逻辑（C04/C05/C09）
- [ ] §4.1补充防延长窗口机制（C01/C06/C08）
- [ ] §4.1补充有界DoS边界（C17：20/20 revert）
- [ ] §4.1补充状态转移表与INV1-INV7

### 10.5 引用标注（关键）
- [ ] §2补充opML文献条目（或删除正文提及）
- [ ] §2四处就近标注（TEEROLLUP、opML、DFP、LazyLedger）
- [ ] §2增加OP FDG时钟继承对比段落
- [ ] 参考文献表版本锁定（TeeRollup v3、BoLD commit、OP FDG commit）

### 10.6 本地vs真实边界标注（关键）
- [ ] §5.1新增分层环境描述（本地/真实硬件/公网）
- [ ] §5所有F阶段数据整段标注口径限制（7条，不可省略）
- [ ] §4.3/§5.4标注"链下Quote验证，依赖可信服务"
- [ ] §4.4/§5标注"Sepolia Blob blocked"
- [ ] §6结论明确"非生产环境验证"

### 10.7 禁止表述删除（关键）
- [ ] 全文搜索并删除"首创"相关表述
- [ ] 全文搜索并删除"恢复降低延迟"
- [ ] 全文搜索并删除"高频DApp TPS"（改为"本地Hardhat TPS"）
- [ ] 全文搜索并删除"payload扩展保持吞吐"
- [ ] 全文搜索并删除"并发线性增长"
- [ ] 全文搜索并删除"完全去信任""优于所有Rollup"等绝对化表述

### 10.8 去重检查
- [ ] 摘要与§1/§6贡献描述去重
- [ ] §1与§2相关工作介绍去重
- [ ] §4与§5机制vs实验描述区分清晰

---

## 附录：修订工作量估计

按章节估计工作量（以"重大修改"为单位）：

| 章节 | 工作量 | 主要修改 |
|---|---|---|
| 摘要 | ⭐⭐ | 去重、重写创新点、标注边界 |
| §1引言 | ⭐⭐⭐ | 删除不实创新点、重写贡献、明确范围 |
| §2相关工作 | ⭐⭐⭐ | 补opML文献、4处标注、增加OP FDG对比、版本锁定 |
| §3系统 | ⭐⭐⭐⭐ | 新增威胁模型表、披露C11缺陷、明确traceRoot |
| §4机制 | ⭐⭐⭐⭐⭐ | 新增TEE章节、回填权限/DoS/DA罚没、标注非形式化证明 |
| §5实验 | ⭐⭐⭐⭐⭐ | 新增真实TEE/G-L1/OP FDG章节、更新表4、整段标注口径 |
| §6结论 | ⭐⭐⭐ | 对齐创新点、明确边界、删除不实结论 |
| 参考文献 | ⭐⭐ | 补opML、版本锁定、核对引用 |

**总估计工作量**：约20-30处重大修改，需仔细对照本指南逐项完成。

---

## 快速自查表（修订完成后使用）

打印此表，逐项勾选：

**必改项（12项）**:
- [ ] 1. 删除"首创第三方接续"等不实创新点
- [ ] 2. 重写摘要/§1/§6创新点为"有界模型+恢复量化"
- [ ] 3. §3新增威胁模型表（6类参与方）
- [ ] 4. §4.3新增真实TEE章节（StageH数据）
- [ ] 5. §4.4新增DA披露罚没机制（bindDa/fulfillDa/slashDa）
- [ ] 6. §5.4新增真实TEE实验章节（Quote表、TCB 0xA003）
- [ ] 7. §5新增G-L1机制对照（210条记录表格，30/30 vs 0/30）
- [ ] 8. §5更新表4（DA类0%→100%罚没）
- [ ] 9. §5所有F本地数据整段标注7条口径限制
- [ ] 10. §2补充opML文献并4处就近标注
- [ ] 11. §2增加OP FDG时钟继承对比段落
- [ ] 12. 全文删除"高频DApp TPS""恢复降低延迟"等禁止表述

**建议改项（8项）**:
- [ ] 13. §4.1新增权限矩阵表
- [ ] 14. §4.1回填防重复恢复/防延长窗口/有界DoS逻辑
- [ ] 15. §5新增OP FDG组件测试结果
- [ ] 16. §5引用C阶段权限与DoS证据（C01-C17）
- [ ] 17. §1改研究问题为可证伪形式
- [ ] 18. §3主动披露C11经济缺陷
- [ ] 19. 参考文献版本锁定（TeeRollup v3等）
- [ ] 20. 去重检查（摘要/§1/§6）

---

**修订完成后，请将修订稿命名为**:
`Hybrid_TEE_Rollup_返修稿_20261029.docx`

**并提交到分支**:
`cursor/revision-joca-expert-response-8a7b`

**同时更新PR**:
https://github.com/shanse11/TEE-code-and-paper/pull/1

---

**文档结束**

如有疑问，参考：
- `outputs/revision_20261028/expert_response_matrix.md` §4（本指南的依据）
- `outputs/revision_20261028/report_zh.md`（StageH数据汇总）
- `outputs/revision_20261028/reply_to_reviewers_zh.md`（回复信草稿，含详细论述）
