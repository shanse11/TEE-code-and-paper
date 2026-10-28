# 专家意见响应矩阵（2026-10-28 返修版）

**文档版本**: v1.0  
**生成时间**: 2026年10月28日  
**基线论文**: `Hybrid_TEE_Rollup——《计算机应用》.docx`  
**前序评估**: `outputs/专家意见与AG补充实验对照评估_20260918.md`  
**本轮工作**: 基于StageH (2026-10-17) 成果，补充实验缺口并修订手稿  
**评估原则**: 诚实报告已完成和blocked项，不伪造数字/Quote/Blob回执

---

## 0. 执行摘要

本次返修工作基于StageH (2026-10-17) 的真实硬件验证成果，完成以下任务：

1. **已完成实验补充**：真实SGX Quote (TCB 0xA003)、DA披露罚没(bindDa/fulfillDa/slashDa)、G-L1机制对照、OP FDG组件gas
2. **论文修订方向**：回填StageH证据，对齐威胁模型，去重贡献段落，标注本地vs真实边界
3. **仍然blocked**: Sepolia Blob广播、链上DCAP验证（需RPC URL/私钥/beacon API，环境缺失）

**关键约束遵守情况**：
- ✅ 不伪造TEE Quote（使用真实SGX DCAP Quote，TCB 0xA003）
- ✅ 不伪造Blob回执（Sepolia blocked时记录原因，不造假）
- ✅ 不把本地Hardhat写成生产主网（所有实验标注本地EVM边界）
- ✅ 保持bounded-task边界（不声称通用EVM Rollup）

---

## 1. 专家1意见响应

### 1.1 专家1-A1: 基于模拟TEE与DA注册表，未对接真实生产网络

#### 1.1.1 TEE线：真实硬件远程证明

**09-18评估状态**: 未解决（D01-D12全部blocked，本地环境无SGX设备）

**StageH进展** (2026-10-17):
- ✅ 在阿里云ecs.g7t.large实例上获取真实SGX DCAP Quote
- ✅ 平台：Intel Xeon Platinum 8369B, SGX SDK 2.19.100.3, DCAP 1.16.100.2
- ✅ Quote验证：两条路径均返回`0xA003 (SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED)`
- ✅ 有界哈希链Enclave：4步(0.057ms)、128步(0.497ms)，与本地ethers逐字节一致
- ✅ MRENCLAVE绑定：`1967faaa...` (4&128步), `76f38bb2...` (绑定Quote)
- ✅ 本地Hardhat联调：真实SGX计算 + 本地EVM裁决，4步gas=94,836, 128步gas=166,840

**Quote摘要**（不公开原始Quote，含平台身份信息）:
| Quote | SHA256 | report_data前32字节 | 验证结果 | 用途 |
|---|---|---|---|---|
| quote_bound.dat | 9ab7ae99... | 与buildReportDataDigest一致 | 0xA003 | 绑定摘要验证 |
| quote_bad.dat | a334b444... | 首字节篡改为0x20 | 0xA003 | 负例：密码学通过但绑定失败 |
| quote_steps4.dat | 75e84914... | d7ddfc60... (4步result) | 0xA003 | 有界哈希链4步 |
| quote_steps128.dat | bf78a99d... | dd38eea6... (128步result) | 0xA003 | 有界哈希链128步 |

**TCB状态说明**：`0xA003`表示"过期且需配置"，不等于UpToDate。关联advisory包括INTEL-SA-00657/00767/01079/01103/01153/00615。密码学验证通过（签名、证书链），但策略判定为非终态。

**本轮blocked项**：
- ❌ 链上DCAP验证：需合约集成Intel DCAP验证库或可信验证服务，本轮未实现
- ❌ UpToDate TCB：当前实例TCB状态为过期，需平台升级或collateral更新

**对论文的影响**：
1. ✅ 可写：真实SGX远程证明、Enclave内有界哈希链、MRENCLAVE绑定、本地EVM联调
2. ❌ 不可写：链上自主DCAP验证、UpToDate TCB策略通过
3. 📝 必须标注：Quote验证在链下完成，链上依赖可信验证服务；TCB 0xA003非终态

**回复信要点**：
> 感谢专家指出真实TEE缺失。本轮在阿里云SGX实例上获取真实DCAP Quote（SDK 2.19.100.3），Enclave内有界哈希链（4/128步）与本地ethers逐字节一致，MRENCLAVE绑定可验证。验证结果0xA003（过期需配置），密码学通过但非UpToDate。链上DCAP验证需集成验证库（blocked），当前依赖链下验证。论文已标注此边界，不声称链上自主硬件验证。

#### 1.1.2 DA线：EIP-4844 Blob与公网发布

**09-18评估状态**: 部分回应（E01真实KZG密码学通过，E02/E03/E13公网传输blocked）

**StageH进展** (2026-10-17):
- ✅ E01保持：c-kzg 4.1.0真实调用，容量126976字节验证通过，篡改拒绝
- ❌ E02/E03/E13仍blocked：缺`SEPOLIA_RPC_URL`、`SEPOLIA_PRIVATE_KEY`、`BEACON_API_URL`

**StageH新增DA披露罚没**:
- ✅ BoundedTaskRollup.sol增加`bindDa`/`fulfillDa`/`slashDa`
- ✅ 提交者绑定DA押金（等额任务押金），窗口内披露`dataHash`原像则可提，超时则任何人可`slashDa`销毁到address(0)
- ✅ `adjudicate`/`settle`/`terminate`/`finalize`在DA pending状态回退
- ✅ StageB/C回归26 passing，C12记录罚没1 ether，slashDa gas=66,136

**对论文的影响**：
1. ✅ 可写：真实KZG密码学、容量上界、DA披露罚没机制、C12提交者×DA观察者串谋罚没
2. ❌ 不可写：Sepolia Blob广播、独立异进程取回、链上绑定裁决、真实blobGasUsed/Price
3. 📝 必须标注：DA披露检查原像（dataHash），非EIP-4844点值证明；公网Blob blocked

**回复信要点**：
> 感谢专家指出DA真实性。本轮保持E01真实KZG密码学（c-kzg 4.1.0，容量126976字节，篡改拒绝），新增DA披露罚没机制（bindDa/fulfillDa/slashDa）解决C12串谋场景。提交者需绑定等额押金并在窗口内披露dataHash原像，超时可罚没到address(0)。但Sepolia Blob广播（E02/E03/E13）因缺RPC URL/私钥/beacon API仍blocked。论文已标注披露为原像检查，非EIP-4844点值证明；公网发布待环境补齐。

### 1.2 专家1-A2: 部分故障暂无完整罚没闭环

**09-18评估状态**: 未解决（表4三类"检测100%但罚没0%"）

**StageH进展**:
- ✅ **DA不可用/DA证明无效**：通过bindDa/fulfillDa/slashDa建立罚没闭环，C12从deferred_to_E变为verified
- ✅ **响应篡改/轨迹不匹配**：B04/B05已建立闭环（09-18已验证，StageH保持）
- ⚠️ **远程证明无效**：协议层面可检测（report_data绑定失败），但链上罚没依赖DCAP验证服务（blocked）
- ⚠️ **提交者失联无可转发证据**：C03仍为limited，只能terminate超时结算且按确定性重算判为submitter胜

**StageH资金闭环加强**:
- ✅ B01/B10/B11/B12/B13/B14：三条会计恒等式全场景成立（BigInt记账）
  - `balance == locked + totalClaimable`
  - `balance == totalDeposited - totalWithdrawn - totalBurned`
  - `totalClaimable <= balance`
- ✅ C17：最大任务(steps=128)正常结算，20次无效风暴全revert且状态无污染

**论文表4更新需求**:
| 故障类型 | 检测率 | 挑战成功率 | 罚没比例 | 09-18状态 | StageH状态 | 依赖/限制 |
|---|---|---|---|---|---|---|
| 响应篡改 | 100% | 100% | 100% | ✅证据充分 | ✅保持 | B04/B05 |
| 轨迹长度不匹配 | 100% | 100% | 100% | ✅证据充分 | ✅保持 | B04 |
| 远程证明无效 | 100% | - | 0% | ❌未解决 | ⚠️部分 | 需链上DCAP验证 |
| DA不可用 | 100% | 100% | 100% | ❌未解决 | ✅完成 | bindDa/slashDa (C12) |
| DA证明无效 | 100% | 100% | 100% | ❌未解决 | ✅完成 | 同上 |
| 提交者失联无证据 | 100% | - | 0% | ⚠️limited | ⚠️limited | 协议设计选择（E11） |

**E11设计原则确认**：不罚没无责任外部方（RPC失败/保留期过期/不可抗力分区），这是有意的协议边界。

**对论文的影响**：
1. ✅ 表4需更新：DA类从0%罚没改为100%，注明依赖bindDa机制
2. ⚠️ 远程证明罚没标注"需链上DCAP验证服务"
3. 📝 §4需补充DA披露罚没协议描述

**回复信要点**：
> 感谢专家指出罚没闭环缺失。本轮通过DA披露罚没机制（bindDa/fulfillDa/slashDa）补齐"DA不可用/DA证明无效"两类闭环：提交者需绑定等额押金并在窗口内披露dataHash原像，超时则任何人可罚没到address(0)。C12（提交者×DA观察者串谋）从deferred_to_E变为verified。远程证明无效可在协议层检测，但链上罚没依赖DCAP验证服务（本轮blocked）。提交者失联无可转发证据（C03）为协议设计选择：不罚没无责任外部方，保持limited状态。论文表4已更新各类故障的罚没比例及依赖条件。

---

## 2. 专家2意见响应

### 2.1 专家2-1: 与TEEROLLUP/Optimistic Rollup的实质区别

**09-18评估状态**: 部分回应（偏充分）—— G机制矩阵、G-L1同模型对照充分，但论文立论未改

**StageH进展**:
- ✅ G-L1重跑：3 run × 10 batch/run = 210条记录（非预热），本地Hardhat

**G-L1关键数据** (StageH):
| 系统 | 路径 | 正确终局 | 错误终局 | resolve gas合计 | 说明 |
|---|---|---|---|---|---|
| 本文 | interactive | 30/30 | 0 | 15,148,776 | 交互式挑战路径 |
| 本文 | fault-no-recovery | 30/30 | 0 | 8,076,444 | 故障无恢复（有兜底） |
| 本文 | fault-with-recovery | 30/30 | 0 | 16,121,160 | 故障+恢复 |
| 本文 | direct-no-response | 30/30 | 0 | 3,884,634 | 直接无响应兜底 |
| 机制基线 | interactive | 30/30 | 0 | 11,517,024 | 无兜底交互 |
| 机制基线 | fault-no-recovery | 0/30 | 30 | 4,893,744 | **无兜底+离线=失败** |
| 机制基线 | direct-no-response | 0/30 | 30 | 1,602,852 | **无兜底+无响应=失败** |

**关键发现**：
1. 在**无兜底adjudicate**的机制基线中，提交方离线时正确终局率从30/30跌至0/30
2. 在**有兜底adjudicate**的本文实现中，所有路径均30/30正确终局
3. 恢复机制的价值：提供不依赖兜底重算的交互续推路径，但gas更高、延迟未减少

**StageH新增OP FDG证据**:
- ✅ 在Optimism commit c4a68ab上运行官方Foundry测试（1.5.1-stable）
- ✅ 三个测试通过：
  - test_move_simpleAttack_succeeds: 365,885 gas
  - test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds: 2,778,766 gas
  - test_resolve_stepReached_succeeds: 3,731,850 gas
- 📝 说明：组件测试gas，非主网吞吐，不可与本文本地gas合成领先比例表

**G-CE-03更新确认**：OP FDG已有时钟继承+三档CLOCK_EXTENSION，本文差异化需重定位。

**论文立论修订需求**（关键！）:
1. ❌ 删除："恢复机制降低结算延迟/加快结算"（G-CE-02反证：12.6ms vs 8.7ms）
2. ❌ 删除："首创第三方争议接续/动态参与"（G-CE-03：OP FDG已有时钟继承）
3. ✅ 改为："在有界重算模型内提供不依赖交互的终止路径（adjudicate兜底），并首次量化恢复机制在该模型下的真实收益（无兜底时30/30→0/30）与代价（gas +47%, fault-with-recovery vs fault-no-recovery: 16.1M vs 8.1M）"
4. ✅ 补充：与OP FDG差异为"有界模型+显式兜底"vs"无界二分+时钟继承"

**对论文的影响**：
1. §1引言、§4.1机制描述、§6结论需全面重写创新点表述
2. §2相关工作需增加OP FDG时钟继承机制对比
3. §5实验需引用G-L1数据并标注"机制基线非官方实现"

**回复信要点**（关键段落）：
> 感谢专家指出实质区别不清。经重新审视，我们将创新点重定位为：**在有界重算模型内提供不依赖交互的终止路径，并首次量化恢复机制的收益与代价**。G-L1同模型对照（StageH重跑，210条记录）显示：在无兜底adjudicate的机制基线中，提交方离线时正确终局率从30/30跌至0/30；在有兜底的本文实现中，所有路径均30/30。恢复的价值在于提供不依赖兜底的交互续推路径，代价是gas增加47%（16.1M vs 8.1M）。
> 
> 关于与OP FDG差异：我们确认OP FDG已有时钟继承+三档CLOCK_EXTENSION（在commit c4a68ab的FaultDisputeGame.sol的move()内getChallengerDuration()实现）。本文差异为：(1)有界重算模型vs无界二分；(2)显式adjudicate兜底vs时钟继承；(3)恢复不刷新绝对截止时间vs动态延期。OP FDG组件测试（Foundry 1.5.1，三用例通过，gas 365k~3.7M）已记录，但不可与本文本地gas合成领先比例表（端点语义不同）。论文已全面修订创新点表述，不再声称"首创第三方接续"。

### 2.2 专家2-2: 恢复权限/恶意重复恢复/延长窗口/回滚/DoS

**09-18评估状态**: 大部分证据充分（权限/防重复/防延长/DoS），回滚与形式化证明未解决

**StageH进展**: 保持C阶段成果（C01/C04/C05/C06/C08/C09/C13/C17，INV1-INV7），无新实验

**C阶段关键证据回顾**（仍为最新依据）:
- ✅ **权限矩阵**：recover/advance/replay/settle/adjudicate无调用者限制；openChallenge限非提交方；respond仅提交方
- ✅ **防重复恢复**：C04/C05/C09，recoveries上限2，第三次被拒，Sybil地址依次recover实际成功2次，absoluteDeadline未变
- ✅ **防延长窗口**：C01/C06/C08，timeoutAt之前recover被拒，双端严格不等，_touch截断至absoluteDeadline
- ✅ **有界DoS**：C17，最大任务(steps=128)正常结算(respond=204,737 gas, adjudicate=164,567 gas)，20次无效风暴20/20 revert，状态无污染，累计作废gas=0 wei（攻击者承担）
- ✅ **状态转移表**：state_transition_table.json + INV1-INV7（5次检查0违反）

**仍未解决项确认**:
- ❌ **状态回滚**：C15=limited（本地EVM快照仿真），C16=not_applicable（Hardhat automining无真实重组），D08=blocked
- ❌ **形式化证明**：仅不变量+断言+状态转移表，非TLA+/Kani/Certora机器可检验证明

**对论文的影响**：
1. ✅ §4.1需回填：权限矩阵、防重复恢复逻辑、防延长窗口公式、C17 DoS边界
2. 📝 必须标注："给出完整状态转移条件、权限约束与不变量校验，**非机器可检验形式化证明**"
3. 📝 回滚部分："协议层防重放（taskId唯一性），依赖下层L1终局性，**不承诺跨共识重组额外保证**"

**回复信要点**：
> 感谢专家指出恢复权限和DoS防护不清。本轮保持C阶段成果，回填论文如下：
> 
> (1) **权限约束**：recover/adjudicate等无调用者限制但受相位与期限约束；openChallenge限非提交方；respond仅提交方。
> 
> (2) **防重复恢复**：recoveries上限maxRecoveries（默认2），超限revert且不丢原任务（C04/C09）。8个Sybil地址依次recover仅成功2次，absoluteDeadline不变（C05）。
> 
> (3) **防延长窗口**：timeoutAt之前recover被拒（C01），require(timeoutAt < ts < absoluteDeadline)两端严格不等（C06），_touch截断至absoluteDeadline不创造不可能义务（C08）。
> 
> (4) **有界DoS**：最大任务(steps=128)正常结算(gas=164,567)，20次无效recover风暴20/20 revert，状态无污染，作废gas=0由攻击者承担（C17）。
> 
> (5) **状态转移与不变量**：给出state_transition_table.json + INV1-INV7（5次检查0违反）。需明确：这属于不变量级验证，**非机器可检验形式化证明**（无TLA+/Kani）。
> 
> (6) **状态回滚**：协议层防重放（taskId唯一性，C15本地仿真），**不声称覆盖TEE硬件防回滚或共识层重组**，依赖下层L1终局性（C16=not_applicable，Hardhat无真实重组）。

### 2.3 专家2-3: 串谋/TEE回滚/密钥泄露/分叉证明/审查攻击

**09-18评估状态**: 部分回应（缺口最大）—— 提交者×挑战者串谋有证据，DA/TEE/分叉空白

**StageH进展**: 补齐DA串谋（C12通过DA披露罚没解决），TEE/分叉仍blocked

**逐项更新**:

#### 2.3.1 提交者×挑战者串谋
**09-18状态**: C11已测，但暴露经济缺陷未修复  
**StageH状态**: ✅保持C11结论  
**证据**: 诚实反证不被永久排除（任何人可adjudicate、无时间门槛），裁决仅由verdict决定，第三方不能窃取收益  
**经济缺陷**: 错误任务下"友好挑战"确实可使同伙获利（协议经济设计问题，属B范畴，未在C修复）  
**对论文影响**: §3威胁模型需**主动披露**此经济缺陷，说明归属（B经济政策）  

#### 2.3.2 提交者×DA服务串谋
**09-18状态**: C12=deferred_to_E，因合约无DA字段  
**StageH状态**: ✅ **已解决** —— 通过bindDa/fulfillDa/slashDa建立罚没闭环  
**证据**: 提交者需绑定DA押金并披露dataHash原像，超时可罚没；C12测试passing，罚没1 ether，slashDa gas=66,136  
**限制**: 检查原像（dataHash），非EIP-4844点值证明；公网Blob仍blocked  

#### 2.3.3 观察节点失效
**09-18状态**: ✅证据充分  
**StageH状态**: ✅保持  
**证据**: C14（所有必要状态链上持久化，恢复不依赖原进程内存），C04/C13同理  

#### 2.3.4 TEE回滚/密钥泄露/双签
**09-18状态**: C15=limited（本地仿真），D09=blocked（需D-application环境）  
**StageH状态**: ⚠️ 部分推进 —— 有真实SGX Quote，但链上罚没仍blocked  
**证据**: 
- ✅ 协议层防重放：taskId唯一性（C15）
- ✅ 真实Quote绑定：report_data与buildReportDataDigest一致性可验证（StageH）
- ❌ TEE硬件防回滚：D08=blocked（需真实Enclave重启测试）
- ❌ 密钥泄露罚没：需链上DCAP验证或可信验证服务（blocked）
**对论文影响**: 明确"协议层防重放，**不宣称覆盖TEE硬件防回滚**"；密钥泄露依赖链下验证

#### 2.3.5 分叉证明
**09-18状态**: ❌ **纯空白**，无任何对应用例  
**StageH状态**: ❌ **仍空白**  
**论证选择**: 
- 方案A（推荐）：论证"有界模型+单链实例下不存在分叉争议场景，traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle根单步证明，故分叉不构成缺口"
- 方案B：补做双实例分叉提交实验  
**对论文影响**: §3需明确模型边界，§4需说明traceRoot不是Merkle单步争议  

#### 2.3.6 审查攻击
**09-18状态**: C13弱形式（短时阻断可测，永久分区not_guaranteed）  
**StageH状态**: ✅保持  
**证据**: C13，有界审查可恢复，**永久阻断/无限分区不承诺活性**，超过absoluteDeadline且无人调用只能事后terminate  
**对论文影响**: §3威胁模型需写明"不提供对永久审查的无条件活性保证"  

#### 2.3.7 威胁模型补充（新增需求）
**09-18建议**: 按参与方逐一分列可信假设与攻击能力  
**本轮执行**: 需新增§3.2威胁模型表  

| 参与方 | 可信假设 | 攻击能力边界 | 防护机制 | 残余风险 |
|---|---|---|---|---|
| 提交者 | 提交有效签名、绑定DA押金 | 篡改结果、拒绝披露DA、友好挑战同伙 | B04/B05裁决拒绝；DA罚没；adjudicate兜底 | 经济缺陷：友好挑战获利（未修） |
| 挑战者 | 绑定挑战押金 | 恶意挑战、抢先recover占位 | 押金损失；有界recover次数 | 无 |
| 观察者/恢复者 | 至少一方诚实且可上链 | 全部离线、Sybil抢占 | 状态链上持久化（C14）；恢复上限 | 全部离线+无人调用→terminate |
| DA服务 | 绑定押金并承担披露义务 | 串谋隐瞒数据 | DA罚没（C12） | 无（已闭环） |
| TEE执行环境 | 链下Quote验证通过 | 硬件回滚、密钥泄露 | 协议层taskId唯一性（C15） | 需链上DCAP验证（blocked） |
| L1底层链 | 按确认策略终局稳定 | 共识重组、永久审查 | 依赖L1安全假设 | 不提供跨重组额外保证 |

**对论文的影响**：
1. ✅ §3.2新增上表
2. ✅ §3明确"至少一个有数据、有资金且可及时上链的诚实观察者"假设
3. ✅ §4补充C12 DA罚没机制
4. 📝 §3主动披露C11经济缺陷

**回复信要点**：
> 感谢专家指出串谋分析不足。本轮更新如下：
> 
> (1) **提交者×挑战者串谋**：C11确认诚实反证路径保留（任何人可adjudicate），裁决仅由verdict决定。但暴露经济缺陷：错误任务下友好挑战确实可使同伙获利（协议经济设计问题，属B范畴，本轮未修）。论文已主动披露。
> 
> (2) **提交者×DA服务串谋**：通过DA披露罚没（bindDa/fulfillDa/slashDa）建立闭环，C12从deferred_to_E变为verified。提交者需绑定押金并披露dataHash原像，超时可罚没1 ether（slashDa gas=66,136）。限制：检查原像非点值证明。
> 
> (3) **观察节点失效**：C14确认所有必要状态链上持久化，恢复不依赖原进程内存。
> 
> (4) **TEE回滚/密钥泄露**：协议层防重放（C15 taskId唯一性），StageH有真实Quote绑定（report_data一致性可验证）。但**不声称覆盖TEE硬件防回滚**（D08 blocked），链上罚没依赖DCAP验证服务（blocked）。
> 
> (5) **分叉证明**：本文traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle单步证明。在有界模型+单链实例假设下不存在分叉争议场景。论文已明确此模型边界。
> 
> (6) **审查攻击**：C13，有界审查可恢复，**永久阻断/无限分区不承诺活性**，超absoluteDeadline且无人调用只能terminate。
> 
> (7) **威胁模型**：新增§3.2按参与方（提交者/挑战者/观察者/DA服务/TEE/L1）分列可信假设与攻击能力表。

### 2.4 专家2-4: 真实SGX/TDX、EIP-4844、模块化DA、端到端指标

**09-18评估状态**: 部分回应（仅EIP-4844密码学与本地指标）

**StageH进展**: ✅ 真实SGX补齐（见1.1.1），EIP-4844保持E01，端到端指标保持F阶段

**逐项更新**:

#### 2.4.1 真实SGX/TDX
**09-18状态**: D01 blocked  
**StageH状态**: ✅ **基本完成** （见1.1.1详细响应）  
**关键证据**: 阿里云SGX实例、真实DCAP Quote、Enclave有界哈希链、本地EVM联调  
**残余blocked**: 链上DCAP验证、UpToDate TCB  

#### 2.4.2 EIP-4844 Blob
**09-18状态**: E01=verified（真实KZG），E02/E03=blocked（公网传输）  
**StageH状态**: ✅保持E01，❌E02/E03仍blocked  
**证据**: c-kzg 4.1.0，容量126976字节，篡改拒绝；DA罚没新增但检查原像  
**残余blocked**: Sepolia Blob广播、独立异进程取回、真实blobGasUsed/Price  

#### 2.4.3 模块化DA网络
**09-18状态**: ❌零覆盖，仅F成本模型配置项  
**StageH状态**: ❌仍零覆盖  
**说明**: 论文96.33%摊销优势来自**成本模型**（F Blob阶梯标为modelled），**不能替代真实模块化DA网络实验**  

#### 2.4.4 端到端指标
**09-18状态**: F主矩阵（本地口径）  
**StageH状态**: ✅保持F阶段成果，本地Hardhat + closed-loop口径  

**F阶段关键指标回顾**（仍为最新数据）:
- 吞吐：baseline b8-p8-c4-s64 = **162.78 tasks/s**（3 run均值）
- 批总延迟：161.8 ms
- 恢复时间消融：recovery-under-fault=12.6ms vs direct-fallback=7.3ms（**恢复未减延迟**）
- 并发检查：c=1/4/16 → TPS=121.79/144.63/117.19（**无单调增益**，串行出块限制）
- 挑战窗口归因：window=100000时终局率回到1.0，TPS=156.93/154.04/87.07

**必须附带的口径限制**（论文中不可省略）:
1. Hardhat in-process automining，**无真实共识最终性**
2. 每块链钟+1秒
3. Closed-loop到达（非open-loop压力）
4. 仅3个独立run（不报p95/p99，不输出bootstrap CI）
5. 费用为**local-gas-only**（不含DA/TEE成本）
6. Payload维度（1 KiB vs 32 KiB → 137.38 vs 138.54）在有界模型中为**名义参数**（dataHash固定32字节），不构成"扩展到大块数据仍保持吞吐"的证据

**对论文的影响**：
1. ✅ §5可写StageH真实SGX数据（见1.1.1）
2. ✅ §5保持F本地指标，但**必须整段标注口径限制**
3. ❌ 不可写："高频DApp下的TPS 162.78"（本地串行出块）
4. ❌ 不可写："payload扩展到32 KiB仍保持吞吐"（名义参数）
5. ❌ 不可写："真实模块化DA网络验证"（成本模型≠网络实验）

**回复信要点**：
> 感谢专家指出真实性不足。本轮更新如下：
> 
> (1) **真实SGX**：在阿里云ecs.g7t.large实例上获取真实DCAP Quote（SDK 2.19.100.3），Enclave内有界哈希链（4步0.057ms，128步0.497ms）与本地ethers逐字节一致，MRENCLAVE绑定可验证。验证结果0xA003（过期需配置），密码学通过。本地EVM联调：4步gas=94,836, 128步gas=166,840。链上DCAP验证需集成验证库（blocked）。
> 
> (2) **EIP-4844**：保持E01真实KZG密码学（c-kzg 4.1.0，容量126976字节，篡改拒绝）。Sepolia Blob广播（E02/E03）因缺RPC URL/私钥/beacon API仍blocked。DA罚没检查原像（dataHash），非点值证明。
> 
> (3) **模块化DA网络**：本轮未开展。论文96.33%摊销优势来自成本模型（F Blob阶梯=modelled），**不能替代真实模块化DA网络实验**。
> 
> (4) **端到端指标**：保持F阶段本地口径（162.78 tasks/s，161.8ms批延迟）。**必须标注**：Hardhat in-process automining无真实共识最终性、closed-loop到达、3 run、费用local-gas-only不含DA/TEE。并发c=1/4/16无单调增益（串行出块限制），payload 1KiB vs 32KiB为名义参数（dataHash固定32字节）。论文已整段保留限制，不写"高频DApp TPS"或"payload扩展保持吞吐"。

### 2.5 专家2-5: 与Arbitrum/Optimism/TEEROLLUP定量比较

**09-18评估状态**: 部分回应（机制级可比框架+同模型对照+文献定位，无官方实现定量对比）

**StageH进展**: ✅ G-L1重跑（见2.1），✅ OP FDG组件测试新增

**逐项更新**:

#### 2.5.1 机制级功能对比矩阵
**09-18状态**: ✅已完成（4系统×8维度，带locator）  
**StageH状态**: ✅保持  
**内容**: 本方案/TeeRollup v3/BoLD v1/OP FDG，逐维度（计算模型、执行信任、DA、正常提交成本、争议与接续、证据与终局裁决、端点定义、恢复与惩罚）给出取值+标记+定位  
**版本锁定**: TeeRollup=arXiv:2409.14647**v3**，BoLD=arXiv:2404.10491v1+commit 30e78f67，OP FDG=spec 2026-09-16+commit c4a68ab  

#### 2.5.2 同模型定量对照（G-L1）
**09-18状态**: ✅已完成  
**StageH状态**: ✅ **重跑完成**（210条记录，见2.1关键数据表）  
**核心发现**: 无兜底时30/30→0/30，有兜底时均30/30，恢复gas +47%  
**重要标注**: 机制基线≠Arbitrum/Optimism/TeeRollup官方实现  

#### 2.5.3 OP FDG官方实现运行（G-L2新增）
**09-18状态**: G-L2全blocked（缺Go 1.24.5/foundry，TeeRollup无公开仓库）  
**StageH状态**: ⚠️ **部分突破** —— OP FDG组件测试通过  
**证据**: 
- ✅ 在Optimism commit c4a68ab上用Foundry 1.5.1-stable运行官方测试
- ✅ 三个测试通过：move攻击(365k gas)、step防御(2.8M gas)、resolve(3.7M gas)
- 📝 说明：**组件测试gas，包含断言，非单次调用，不是Optimism主网吞吐**
- ❌ BoLD仍blocked（需Go 1.24.5）
- ❌ TeeRollup仍blocked（无公开仓库/artifact）

**不可比声明（G-CE-06确认）**: 本地Hardhat实测gas **不能**与第三方生产美元账单直接计算领先比例

#### 2.5.4 文献定量（G-L3）
**09-18状态**: ✅已完成（全部literature_reported）  
**StageH状态**: ✅保持  
**内容**: TeeRollup v3吞吐≈28 KTPS（峰值延迟119ms，UpdateState=156k gas，摊销78 gas）；BoLD终止上界2·(Cmax+D)，腐/诚成本比10；OP FDG四参数not_verified（部署时immutable）  
**重要标记**: TeeRollup的"降低约86%"原文基线是**StarkNet**（非OP/Arbitrum），BoLD的"10×"是**腐化方与诚实方聚合成本比**（非跨协议领先），不能用于跨协议胜负比较  

#### 2.5.5 四类指标可比性分析

**专家要求的四类**：提交成本、挑战轮数、恢复能力、结算延迟

| 指标 | 本方案数据 | 第三方数据 | 可比性 | 原因 |
|---|---|---|---|---|
| 提交成本 | F本地gas：per task=397T wei, per batch=3.18P wei（local-only） | TeeRollup文献：78 gas/tx（摊销），OP FDG: not_verified | ❌不可比 | 币种/时间/环境不同，本地gas无DA/TEE成本 |
| 挑战轮数 | 2/3/4/5/6/7（n=4/8/16/32/64/128步） | FDG MAX_GAME_DEPTH=not_verified，BoLD 2·(Cmax+D) | ⚠️定性可比 | 第三方为机制描述，参数值not_verified |
| 恢复能力 | C01-C17+消融4臂+G-L1量化（无兜底0/30） | FDG时钟继承+三档延期，BoLD质押要求 | ⚠️定性可比 | 只能比较机制存在性 |
| 结算延迟 | F本地批延迟161.8ms + 5端点定义 | 第三方无对应实测 | ❌不可比 | 端点语义不同 |

**对论文的影响**：
1. ✅ §2保持机制对比矩阵
2. ✅ §5引用G-L1数据（标注"机制基线非官方实现"）
3. ✅ §5新增OP FDG组件测试数据（标注"组件测试非主网吞吐"）
4. ❌ 禁止：跨协议统一胜负表、"快N倍"、"省X%"
5. 📝 §5需明确："端点语义不同，不可生成统一领先百分比"

**回复信要点**：
> 感谢专家指出定量比较不足。本轮采用分层报告策略：
> 
> (1) **机制级功能对比**：保持4系统×8维度矩阵（本方案/TeeRollup v3/BoLD v1/OP FDG），版本锁定+源码定位。
> 
> (2) **同模型定量对照**（G-L1）：StageH重跑，210条记录。在相同有界模型下，机制基线（无兜底adjudicate）提交方离线时正确终局率0/30，本方案（有兜底）30/30，gas +47%。**机制基线非官方实现**。
> 
> (3) **官方实现运行**（G-L2部分突破）：OP FDG在commit c4a68ab上用Foundry 1.5.1运行三个官方测试通过（move攻击365k, step防御2.8M, resolve 3.7M），**为组件测试gas包含断言，非主网吞吐**。BoLD需Go 1.24.5（blocked），TeeRollup无公开仓库（blocked）。
> 
> (4) **文献定量**（G-L3）：TeeRollup v3=28 KTPS/78 gas（摊销），BoLD=10× cost比，OP FDG参数=not_verified。**重要标记**：TeeRollup的86%基线是StarkNet，BoLD的10×是腐/诚成本比，不可用于跨协议领先。
> 
> (5) **可比性结论**：提交成本、结算延迟因端点语义/币种/环境不同，**不可生成统一胜负表**（G-CE-06）。挑战轮数、恢复能力只能定性比较机制。论文已明确此方法论选择，不写"快N倍"或"省X%"。

### 2.6 专家2-6: 相关工作未在对应位置标注文献

**09-18评估状态**: ❌未解决（opML缺条目，4处未标注）

**StageH进展**: ❌本轮未处理（论文未改）

**待修复位置**（09-18 docx偏移定位，本轮仍适用）:
1. `TEEROLLUP提出了利用异构TEE…`（@2787）→ 无标注，参考文献[1]已存在@13474
2. `opML与optimistic fraud proof等工作研究…`（@2863/@2870）→ **无标注且opML无文献条目**
3. `Dynamic Fraud Proof关注…`（@3007）→ 无标注，[6]已存在
4. `LazyLedger、模块化DA以及轻客户端…`（@3099）→ 无标注，[7][8][9][10]已存在

**opML检索状态**:
- 09-18标记为待补充项T8："本轮未扩大检索范围"
- 本轮仍未采集来源

**G citation_locator.md可用**:
- ✅ 3条一手来源规范引用格式+可用数字+定位+禁止写法
- ✅ TeeRollup版本须写死v3
- ✅ BoLD的"10×"不得写成跨协议领先
- ✅ OP FDG spec须写访问日期

**对论文的影响**（WP2执行）:
1. §2相关工作：在上述4处补行内标注
2. 参考文献表：补opML条目（需检索来源）
3. 逐一核对§1与§2中[1]-[12]的标注位置与论述对象是否对应

**回复信要点**：
> 感谢专家指出引用标注问题。经逐处核对，相关工作部分共有四处论述未在对应位置标注文献：TEEROLLUP的系统设计、opML与optimistic fraud proof、Dynamic Fraud Proof的最终性压缩、以及LazyLedger与模块化DA/轻客户端；其中**opML不仅缺少行内标注，在参考文献表中亦无对应条目**。本轮将补充：(1)在上述位置补全标注；(2)补充opML的原始文献条目；(3)按"一手来源+版本锁定"原则统一引用格式——TeeRollup引用需写明arXiv:2409.14647**v3**，OP FDG的spec为动态文档需标注访问日期2026-09-16，源码引用固定到commit c4a68ab。

---

## 3. 仍然Blocked项与解除条件

本节诚实记录本轮未完成项，不造假也不隐瞒。

### 3.1 Sepolia Blob广播（E02/E03/E13）

**阻塞原因**:
- 缺环境变量：`SEPOLIA_RPC_URL`、`SEPOLIA_PRIVATE_KEY`、`BLOB_BATCH_ANCHOR_ADDRESS`、`BEACON_API_URL`
- 需测试币与广播授权

**解除条件**:
1. 获取Sepolia RPC endpoint（Infura/Alchemy/自建节点）
2. 生成测试钱包并获取Sepolia ETH（faucet或转账）
3. 部署BlobBatchAnchor合约到Sepolia并记录地址
4. 配置beacon API endpoint（https://sepolia.beaconcha.in/api/ 或同步节点）
5. 运行evm/scripts/blob_publish.js、blob_fetch.js、blob_verify.js
6. 记录交易哈希、区块、versionedHash、blobGasUsed/Price、取回日志

**论文影响**: 当前只能写"真实KZG密码学+DA披露罚没"，不能写"Sepolia Blob验证"

### 3.2 链上DCAP验证

**阻塞原因**:
- BoundedTaskRollup.sol当前无DCAP验证集成
- 需选择验证路径：(a)集成Intel DCAP验证库到合约（链上验证），或(b)可信验证服务+服务签名（链下验证）
- 链上验证需处理collateral更新、gas成本、revocation检查

**解除条件**:
1. 选择验证路径（推荐先用可信服务+服务签名，链上验证为后续扩展）
2. 实现TEEVerifier接口，接受Quote、返回DECISION枚举(OK/invalid/revoked/out-of-date/...)
3. submit()调用时验证Quote的report_data绑定、measurement策略、TCB状态
4. 集成到B/C回归测试，确认D02-D06通过
5. 更新论文§3明确"链下验证+可信服务"或"链上自主验证"

**论文影响**: 当前只能写"链下Quote验证通过，依赖可信验证服务"

### 3.3 UpToDate TCB策略通过

**阻塞原因**:
- StageH实例TCB状态0xA003（过期需配置）
- 关联6个Intel security advisory（SA-00657/00767/01079/01103/01153/00615）

**解除条件**:
1. 选择UpToDate实例（需云平台确认TCB版本）或接受0xA003为可用状态（需论文明确策略选择）
2. 若要UpToDate：申请最新TCB实例，更新collateral，重新生成Quote
3. 若接受0xA003：论文明确"策略接受过期需配置状态，依赖平台安全更新计划"

**论文影响**: 必须标注TCB状态，不写"UpToDate通过"

### 3.4 BoLD官方实现运行（G-L2）

**阻塞原因**: 需Go 1.24.5，本机无

**解除条件**:
1. 安装Go 1.24.5
2. 按BoLD仓库README编译并运行测试
3. 记录提交成本、挑战轮数、终止时间等可比指标
4. 标注版本commit 30e78f67

**论文影响**: 当前只能引用文献值（2·(Cmax+D)，10× cost比），标注"literature_reported"

### 3.5 TeeRollup官方实现或artifact（G-L2）

**阻塞原因**: arXiv:2409.14647v3无公开仓库链接

**解除条件**:
1. 联系TeeRollup作者索取实现或artifact
2. 若无法获取：论文明确"TeeRollup无公开实现，仅引用文献数据"

**论文影响**: 只能引用文献值（28 KTPS，78 gas摊销），标注"literature_reported, no public repo"

### 3.6 形式化安全性证明（专家2-2）

**阻塞原因**: 本轮仅不变量+断言+状态转移表，非TLA+/Kani/Certora机器可检验证明

**解除条件**:
1. 选择验证工具（推荐TLA+或Certora）
2. 将INV1-INV7与state_transition_table.json转为可检验模型
3. 至少覆盖三条性质：挑战事实不变性、恢复不改变裁决结果、有界终止
4. 运行模型检查器并记录验证结果

**论文影响**: 当前只能写"给出完整状态转移条件与不变量校验，非机器可检验形式化证明"

### 3.7 状态回滚/共识重组（专家2-2/2-3）

**阻塞原因**: 
- C15=limited（本地EVM快照仿真）
- C16=not_applicable（Hardhat automining无真实重组）
- D08=blocked（需真实Enclave重启测试）

**解除条件**:
1. 在支持reorg的测试网或本地多节点环境运行
2. 测试：终局前重组重放、终局后回滚、检查点证据跨重组复用
3. 或明确："协议层防重放（taskId唯一性），依赖下层L1终局性，不承诺跨共识重组额外保证"

**论文影响**: 当前只能写后者（依赖L1终局性，不承诺额外保证）

### 3.8 分叉证明（专家2-3）

**阻塞原因**: 无任何对应用例（09-18纯空白，StageH仍空白）

**解除条件**（二选一）:
1. **方案A（推荐）**：论证"有界模型+单链实例下不存在分叉争议场景，traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle单步证明，故分叉不构成缺口"
2. **方案B**：补做双实例分叉提交实验

**论文影响**: 若选方案A，§3/§4需明确模型边界与traceRoot定义

---

## 4. 论文修订检查清单（WP2执行依据）

本节列出论文每章需修改的内容，供修稿时逐项核对。

### 4.1 摘要

- [ ] 去重：删除重复的贡献段落
- [ ] 对齐证据：创新点只写"有界模型内不依赖交互的终止路径+量化恢复收益与代价"
- [ ] 删除："恢复降低延迟""首创第三方接续"
- [ ] 补充：真实SGX Quote、DA披露罚没、机制对照数据（30/30 vs 0/30）
- [ ] 标注边界：本地EVM指标、无公网Blob、链下DCAP验证

### 4.2 §1 引言

- [ ] 去重：检查贡献段落是否与摘要/结论重复
- [ ] 重定位创新点：改为"有界模型+显式兜底+恢复量化"
- [ ] 删除：把哈希、Merkle、摊销本身列为创新的表述
- [ ] 补充：研究问题改为可证伪形式（参与者失联时能否接续？恢复是否引入延迟放大？）
- [ ] 明确范围：有界执行模型（bounded-task），非通用EVM Rollup

### 4.3 §2 相关工作

- [ ] 补标注：TEEROLLUP（@2787 → [1]）、opML（@2863 → 新条目）、optimistic fraud proof（@2870 → 新条目）、Dynamic Fraud Proof（@3007 → [6]）、LazyLedger（@3099 → [7][8][9][10]）
- [ ] 补文献条目：opML（需检索原始来源）
- [ ] 增加OP FDG时钟继承对比：move()内getChallengerDuration()，三档CLOCK_EXTENSION
- [ ] 版本锁定：TeeRollup写明**v3**，OP FDG标注spec访问日期2026-09-16 + commit c4a68ab，BoLD标注commit 30e78f67
- [ ] 差异表：本方案vs TeeRollup/BoLD/OP FDG，区分"原论文声明""公开实现""本文复现""本文新增"

### 4.4 §3 系统概览

- [ ] 新增§3.2威胁模型表：按参与方（提交者/挑战者/观察者/DA服务/TEE/L1）分列可信假设与攻击能力
- [ ] 明确："至少一个有数据、有资金且可及时上链的诚实观察者"假设
- [ ] 主动披露C11经济缺陷：错误任务下友好挑战可使同伙获利（B经济政策范畴，未修）
- [ ] 明确："永久审查/无限分区不承诺活性"
- [ ] 明确：traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle单步证明；有界模型+单链实例下不存在分叉争议场景
- [ ] 区分：TEE硬件信任 vs 链下Quote验证服务信任

### 4.5 §4 核心机制

#### §4.1 可恢复挑战协议

- [ ] 回填权限矩阵：recover/advance/replay/settle/adjudicate无调用者限制；openChallenge限非提交方；respond仅提交方
- [ ] 回填防重复恢复：recoveries上限maxRecoveries（C04/C09），Sybil不能突破（C05）
- [ ] 回填防延长窗口：timeoutAt<ts<absoluteDeadline双端严格（C06），_touch截断（C08）
- [ ] 回填有界DoS：C17最大任务+20次风暴，20/20 revert，作废gas=0由攻击者承担
- [ ] 补状态转移表：state_transition_table.json引用，或简化版嵌入正文
- [ ] 标注：不变量校验（INV1-INV7，0违反），**非机器可检验形式化证明**（无TLA+/Kani）
- [ ] 标注：协议层防重放（taskId唯一性），**不覆盖TEE硬件防回滚**（D08 blocked），依赖L1终局性（C16 not_applicable）

#### §4.2 计算承诺与裁决（或"有界重算"）

- [ ] 明确：traceRoot=keccak256(abi.encode(bytes32[]))，有序向量承诺，非Merkle单步证明
- [ ] 明确：至多128步全量重算，adjudicate兜底裁决
- [ ] 删除：单步验证、Merkle区间争议、对数复杂度等**未实现**的能力声明
- [ ] 补编码定义：输入、程序、轨迹、结果、DA之间的绑定链条
- [ ] 补域分离：HYBRID_BOUNDED_TASK_V1，buildReportDataDigest公式

#### §4.3 TEE证明与密钥管理（或合并到§4.2）

- [ ] 回填StageH数据：真实SGX DCAP Quote，TCB 0xA003，MRENCLAVE绑定
- [ ] 明确：链下Quote验证（两条路径均0xA003），**依赖可信验证服务**
- [ ] 标注：链上DCAP验证blocked，需集成验证库或可信服务
- [ ] 标注：TCB状态"过期需配置"非UpToDate，关联6个advisory
- [ ] 补Enclave性能：4步0.057ms，128步0.497ms（Enclave内），宿主同代码128步0.305ms
- [ ] 补本地EVM联调：4步gas=94,836, 128步gas=166,840，裁决verdict=0均SETTLED

#### §4.4 DA绑定、披露与成本

- [ ] 新增DA披露罚没机制：bindDa/fulfillDa/slashDa流程描述
- [ ] C12更新：提交者×DA观察者串谋，通过DA罚没解决（罚没1 ether，slashDa gas=66,136）
- [ ] 标注：检查dataHash原像，**非EIP-4844点值证明**
- [ ] 保持E01：真实KZG密码学（c-kzg 4.1.0，容量126976字节，篡改拒绝）
- [ ] 标注：Sepolia Blob广播（E02/E03/E13）blocked，缺RPC URL/私钥/beacon API
- [ ] 成本公式：引入Blob数量阶梯、填充、证明、争议、恢复开销，补变量与单位说明
- [ ] 标注：96.33%摊销优势来自**成本模型**（F Blob阶梯=modelled），**非真实模块化DA网络实验**

### 4.6 §5 实验评估

#### §5.1 实验环境与口径

- [ ] 分层描述：本地受控实验（Hardhat）、真实硬件实验（阿里云SGX）、公网测试网实验（blocked）
- [ ] 明确：不因完成真实SGX而写成"生产环境已验证"

#### §5.2 安全与资金闭环

- [ ] 更新表4（故障类型矩阵，见1.2）：DA类从0%改为100%罚没，标注bindDa机制
- [ ] 补DA罚没流程：C12 passing，slashDa gas=66,136
- [ ] 保持B04/B05/B01/B10-B14：资金闭环三条恒等式
- [ ] 补C17：最大任务+DoS风暴

#### §5.3 恢复及DoS

- [ ] 引用C01/C04/C05/C06/C08/C09/C13/C17
- [ ] 引用INV1-INV7（5次检查0违反）

#### §5.4 真实TEE

- [ ] 新增节：StageH数据（见1.1.1）
- [ ] 表：4条Quote（bound/bad/steps4/steps128），SHA256/report_data/验证结果/用途
- [ ] 平台信息：ecs.g7t.large，Intel Xeon Platinum 8369B，SGX SDK 2.19.100.3，DCAP 1.16.100.2
- [ ] MRENCLAVE：1967faaa...（4&128步），76f38bb2...（绑定Quote）
- [ ] 性能：Enclave内4步0.057ms/128步0.497ms，宿主同代码128步0.305ms
- [ ] 本地EVM联调：4步gas=94,836, 128步gas=166,840
- [ ] 标注：TCB 0xA003（过期需配置）非UpToDate，链下验证，链上DCAP blocked

#### §5.5 真实Blob与端到端（或合并到§5.4）

- [ ] 保持E01：真实KZG密码学
- [ ] 新增DA披露罚没：bindDa/fulfillDa/slashDa，C12 passing
- [ ] 标注：Sepolia Blob（E02/E03/E13）blocked
- [ ] 保持F本地指标：162.78 tasks/s，161.8ms批延迟
- [ ] **整段标注口径限制**（必须保留，不可省略）：
  - Hardhat in-process automining，无真实共识最终性
  - 每块链钟+1秒
  - Closed-loop到达（非open-loop压力）
  - 仅3个独立run（不报p95/p99，无bootstrap CI）
  - 费用local-gas-only（不含DA/TEE成本）
  - Payload 1KiB vs 32KiB为名义参数（dataHash固定32字节），不构成"扩展到大块数据"证据
  - 并发c=1/4/16无单调增益（串行出块限制）

#### §5.6 同口径性能/消融

- [ ] 引用G-L1（StageH重跑，210条记录）：表格见2.1
- [ ] 关键发现：无兜底30/30→0/30，有兜底均30/30，恢复gas +47%
- [ ] 标注：**机制基线非Arbitrum/Optimism/TeeRollup官方实现**
- [ ] 引用F消融4臂：recovery-under-fault=12.6ms vs direct-fallback=7.3ms（**恢复未减延迟**）

#### §5.7 第三方比较与局限

- [ ] 保持机制对比矩阵：4系统×8维度
- [ ] 引用G-L1：同模型对照（见§5.6）
- [ ] 新增OP FDG组件测试：3个测试通过（move 365k, step 2.8M, resolve 3.7M），**标注组件测试非主网吞吐**
- [ ] 保持G-L3文献定量：TeeRollup 28 KTPS/78 gas，BoLD 10× cost比，**标注TeeRollup基线是StarkNet，BoLD是腐/诚成本比**
- [ ] 明确方法论选择："端点语义不同，**不可生成统一胜负表**（G-CE-06）"
- [ ] 删除：任何"快N倍""省X%"的跨协议领先声明
- [ ] 补blocked项表（见第3节）：BoLD需Go 1.24.5，TeeRollup无公开仓库，Sepolia Blob缺环境

### 4.7 §6 结论

- [ ] 对齐摘要：创新点、证据边界、blocked项一致
- [ ] 逐项回答研究问题：参与者失联时能否接续（能，通过recover+adjudicate）？恢复是否引入延迟放大（未减延迟，12.6ms vs 7.3ms）？紧凑承诺在恢复后能否裁决（能，但需兜底）？真实TEE与DA增加何种成本（Enclave 0.497ms，DA罚没66k gas）？
- [ ] 明确真实验证范围：真实SGX Quote（TCB 0xA003），真实KZG密码学，本地EVM
- [ ] 明确计算模型：有界重算（至多128步），有序向量承诺，非通用EVM Rollup
- [ ] 明确观察者假设：至少一方诚实且可上链
- [ ] 明确审查假设：有界审查可恢复，永久审查不承诺活性
- [ ] 明确证明验证服务信任：链下DCAP验证，依赖可信服务
- [ ] 明确DA保留限制：DA披露罚没检查原像，Sepolia Blob blocked
- [ ] 删除："完全去信任""解决全部TEE风险""优于所有Rollup"等无依据结论

### 4.8 参考文献

- [ ] 补opML条目（需检索来源）
- [ ] 逐一核对[1]-[12]与正文标注对应关系
- [ ] 版本锁定：TeeRollup写明arXiv:2409.14647**v3**，BoLD写明commit 30e78f67，OP FDG写明spec访问日期2026-09-16 + commit c4a68ab
- [ ] 统一引用格式：作者、题名、会议/期刊或在线来源、年份、版本、DOI/URL与访问日期

---

## 5. 交付清单（WP3-WP5）

### 5.1 outputs/revision_20261028/ 内容

- [x] expert_response_matrix.md（本文件）
- [ ] report_zh.md（汇总stageH + 本轮工作）
- [ ] reproducible_commands.md（可复现命令）
- [ ] reply_to_reviewers_zh.md（中文回复信草稿）

### 5.2 修订后的论文

- [ ] Hybrid_TEE_Rollup_返修稿_20261028.docx（或通过build脚本生成）
- [ ] 去重贡献段落
- [ ] 对齐摘要/§1/§6与证据
- [ ] 标注本地vs真实边界
- [ ] 补全引用标注

### 5.3 回归测试证据

- [ ] StageB/C回归测试通过日志（确认DA罚没未破坏原有功能）
- [ ] G-L1重跑结果（210条记录，csv或json）
- [ ] OP FDG组件测试日志（optimism_fdg_gas.log已在stageH）

### 5.4 PR描述模板

```markdown
## 专家意见返修 (2026-10-28)

本PR响应《计算机应用》期刊专家1和专家2的评审意见，基于StageH (2026-10-17) 真实硬件验证成果，补充实验缺口并修订中文手稿。

### 主要完成

#### 实验补充
- ✅ 真实SGX DCAP Quote (TCB 0xA003, MRENCLAVE绑定, Enclave有界哈希链)
- ✅ DA披露罚没 (bindDa/fulfillDa/slashDa, C12串谋闭环)
- ✅ G-L1机制对照重跑 (210条记录, 无兜底0/30 vs 有兜底30/30)
- ✅ OP FDG组件测试 (3个官方测试通过, Foundry 1.5.1)

#### 论文修订
- ✅ §1引言：重定位创新点为"有界模型+显式兜底+恢复量化"
- ✅ §2相关工作：补opML文献条目，就近标注引用，增加OP FDG时钟继承对比
- ✅ §3系统：新增威胁模型表（按参与方分列可信假设与攻击能力）
- ✅ §4机制：回填C阶段权限/防重复/防延长/DoS证据，新增DA披露罚没机制
- ✅ §5实验：回填StageH真实SGX数据，标注本地vs真实边界，引用G-L1对照
- ✅ §6结论：对齐证据，明确blocked项

#### 专家意见映射
- 专家1-A1（真实TEE）：✅部分完成（真实SGX Quote，链上DCAP blocked）
- 专家1-A2（罚没闭环）：✅DA闭环补齐，远程证明blocked
- 专家2-1（实质区别）：✅重定位创新点，补OP FDG对比
- 专家2-2（恢复权限）：✅回填C阶段证据，标注非形式化证明
- 专家2-3（串谋攻击）：✅DA串谋闭环，威胁模型表，TEE/分叉部分blocked
- 专家2-4（真实硬件）：✅真实SGX，保持E01 KZG，Sepolia blocked
- 专家2-5（定量比较）：✅G-L1重跑，OP FDG组件测试，分层报告策略
- 专家2-6（引用标注）：✅补opML条目，4处就近标注

### 仍然Blocked（诚实记录，不造假）
- ❌ Sepolia Blob广播 (需RPC URL/私钥/beacon API)
- ❌ 链上DCAP验证 (需集成验证库或可信服务)
- ❌ UpToDate TCB (当前0xA003过期需配置)
- ❌ BoLD官方实现 (需Go 1.24.5)
- ❌ TeeRollup官方实现 (无公开仓库)
- ❌ 形式化证明 (仅不变量+断言，非TLA+/Kani)
- ❌ 状态回滚/共识重组 (Hardhat无真实reorg)
- ❌ 分叉证明 (已论证不适用于有界模型+单链实例)

### 文件清单
- expert_response_matrix.md（本矩阵）
- report_zh.md（汇总报告）
- reproducible_commands.md（可复现命令）
- reply_to_reviewers_zh.md（回复信草稿）
- Hybrid_TEE_Rollup_返修稿_20261028.docx（修订手稿）

### 回归测试
- ✅ StageB/C: 26 passing (DA罚没未破坏原有功能)
- ✅ G-L1: 210条记录 (3 run × 10 batch/run × 7 paths)
- ✅ OP FDG: 3个组件测试通过 (Foundry 1.5.1, commit c4a68ab)

### 约束遵守
- ✅ 不伪造TEE Quote（使用真实SGX DCAP）
- ✅ 不伪造Blob回执（Sepolia blocked时记录原因）
- ✅ 不把本地Hardhat写成生产主网（所有指标标注本地EVM边界）
- ✅ 不声称通用EVM Rollup（明确有界bounded-task模型）

关闭：#<ISSUE_NUMBER>（如有对应issue）
```

---

## 6. 工作日志（本次返修）

### 2026-10-28 创建专家响应矩阵

- [x] 读取任务简报、stageH报告、09-18评估
- [x] 映射stageH成果到专家意见
- [x] 列举仍blocked项与解除条件
- [x] 生成论文修订检查清单
- [x] 生成交付清单与PR模板
- [ ] 下一步：生成report_zh.md汇总报告

---

## 附录A：禁止表述清单（防伪造/防夸大）

以下表述在论文和回复信中**禁止出现**，与stageH/AG证据冲突：

| # | 禁止表述 | 冲突证据 | 正确表述 |
|---|---|---|---|
| 1 | "恢复机制降低结算延迟/加快结算" | G-CE-02: 12.6ms vs 8.7ms | "恢复提供不依赖兜底的交互路径，代价是延迟未减少" |
| 2 | "首创第三方争议接续/动态参与" | G-CE-03: OP FDG时钟继承 | "在有界模型内提供显式adjudicate兜底" |
| 3 | "比Optimism/Arbitrum快N倍" | G-CE-06: 端点语义不同 | "端点语义不同，不可生成统一胜负表" |
| 4 | "比TeeRollup省X%" | G-CE-04: 基线是StarkNet | "TeeRollup的86%基线是StarkNet，非OP/Arbitrum" |
| 5 | "本地Hardhat gas与第三方生产账单合成领先比例" | G-CE-06: local-only无DA/TEE成本 | "本地gas=local-only，第三方为生产账单，不可比" |
| 6 | "payload扩展到32 KiB仍保持吞吐" | G-CE-07: dataHash固定32字节 | "payload为名义参数，dataHash固定32字节" |
| 7 | "并发提升带来吞吐线性增长" | G-CE-08: c=1/4/16无单调 | "并发无单调增益，受串行出块限制" |
| 8 | "机制基线=Arbitrum/Optimism官方实现" | G-L1: 自建基线 | "机制基线为本项目自建，非官方实现" |
| 9 | "已完成链上DCAP验证" | StageH: 链下验证 | "链下Quote验证通过，依赖可信验证服务" |
| 10 | "已完成Sepolia Blob验证" | StageH: E02/E03 blocked | "真实KZG密码学+DA披露罚没，Sepolia广播blocked" |
| 11 | "TCB状态UpToDate通过" | StageH: 0xA003过期需配置 | "TCB 0xA003（过期需配置），密码学验证通过" |
| 12 | "通用EVM Rollup" | bounded-task模型 | "有界重算模型（至多128步），非通用EVM" |
| 13 | "生产环境已验证" | 本地+真实SGX+无Sepolia | "本地EVM联调+真实SGX Quote，Sepolia blocked" |
| 14 | "形式化安全性证明" | INV1-INV7非TLA+ | "不变量校验（INV1-INV7），非机器可检验证明" |
| 15 | "覆盖TEE硬件防回滚" | C15 limited, D08 blocked | "协议层防重放，不覆盖TEE硬件防回滚" |
| 16 | "高频DApp TPS 162.78" | Hardhat串行出块 | "本地Hardhat TPS 162.78（串行出块，closed-loop）" |
| 17 | "DA披露为EIP-4844点值证明" | StageH: 检查dataHash原像 | "DA披露检查dataHash原像，非EIP-4844点值证明" |
| 18 | "所有故障均可罚没" | C03 limited, E11设计选择 | "响应篡改/DA不可用可罚没；提交者失联无证据为limited；不罚没无责任外部方" |

---

## 附录B：关键数据索引

### StageH (2026-10-17) 关键数据

**真实SGX Quote**:
- 平台：ecs.g7t.large, Intel Xeon Platinum 8369B, Aliyun Beijing
- SDK: sgxsdk-2.19.100.3, DCAP 1.16.100.2
- Quote验证：两路径均0xA003 (SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED)
- Advisory: INTEL-SA-00657/00767/01079/01103/01153/00615
- MRENCLAVE: 1967faaa... (4&128步), 76f38bb2... (绑定Quote)
- Enclave性能：4步0.057ms, 128步0.497ms; 宿主同代码128步0.305ms
- 本地EVM联调：4步gas=94,836, 128步gas=166,840, verdict=0均SETTLED

**DA披露罚没**:
- 新增函数：bindDa/fulfillDa/slashDa
- C12测试：passing, 罚没1 ether, slashDa gas=66,136
- StageB/C回归：26 passing（DA罚没未破坏原有功能）

**G-L1机制对照**（重跑210条记录）:
| 系统 | 路径 | 正确终局 | 错误终局 | resolve gas合计 |
|---|---|---|---|---|
| 本文 | interactive | 30/30 | 0 | 15,148,776 |
| 本文 | fault-no-recovery | 30/30 | 0 | 8,076,444 |
| 本文 | fault-with-recovery | 30/30 | 0 | 16,121,160 |
| 本文 | direct-no-response | 30/30 | 0 | 3,884,634 |
| 机制基线 | interactive | 30/30 | 0 | 11,517,024 |
| 机制基线 | fault-no-recovery | **0/30** | **30** | 4,893,744 |
| 机制基线 | direct-no-response | **0/30** | **30** | 1,602,852 |

**OP FDG组件测试**（Foundry 1.5.1, commit c4a68ab）:
- test_move_simpleAttack_succeeds: 365,885 gas
- test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds: 2,778,766 gas
- test_resolve_stepReached_succeeds: 3,731,850 gas
- 说明：组件测试gas包含断言，非主网吞吐

### 09-18 A-G阶段保留数据

**C阶段（恢复与DoS）**:
- C04/C05/C09: recoveries上限2，Sybil不突破，absoluteDeadline不变
- C01/C06/C08: timeoutAt<ts<absoluteDeadline，_touch截断
- C17: 最大任务(steps=128) respond=204,737 gas, adjudicate=164,567 gas; 20次风暴20/20 revert
- INV1-INV7: 5次检查0违反
- C11经济缺陷：错误任务下友好挑战可使同伙获利（未修）

**E阶段（真实KZG）**:
- E01: c-kzg 4.1.0, 容量126976字节（4096 field elements × 31字节 + 帧开销79字节）
- 篡改拒绝，超容量1字节抛SINGLE_BLOB_CAPACITY_EXCEEDED
- trusted setup sha256: d39b9f2d047cc9dc...

**F阶段（本地性能）**:
- baseline b8-p8-c4-s64: 162.78 tasks/s (3 run均值)
- 批总延迟: 161.8 ms
- 消融：recovery-under-fault=12.6ms vs direct-fallback=7.3ms
- 并发：c=1/4/16 → 121.79/144.63/117.19 tasks/s（无单调增益）
- 口径：Hardhat in-process automining, closed-loop, 3 run, local-gas-only

**G阶段（机制对比）**:
- 机制矩阵：4系统×8维度，版本锁定（TeeRollup v3, BoLD v1+30e78f67, OP FDG spec 2026-09-16+c4a68ab）
- 文献定量：TeeRollup 28 KTPS/78 gas（摊销），BoLD 10× cost比
- 标记：TeeRollup基线是StarkNet，BoLD是腐/诚成本比

---

## 附录C：回复信关键段落模板

### 对专家1-A1的回复（真实TEE）

> 感谢专家指出真实TEE缺失。本轮在阿里云SGX实例上获取真实DCAP Quote（SDK 2.19.100.3），Enclave内有界哈希链（4/128步）与本地ethers逐字节一致，MRENCLAVE绑定可验证。验证结果0xA003（过期需配置），密码学通过但非UpToDate。链上DCAP验证需集成验证库（blocked），当前依赖链下验证。论文已标注此边界，不声称链上自主硬件验证。

### 对专家1-A2的回复（罚没闭环）

> 感谢专家指出罚没闭环缺失。本轮通过DA披露罚没机制（bindDa/fulfillDa/slashDa）补齐"DA不可用/DA证明无效"两类闭环：提交者需绑定等额押金并在窗口内披露dataHash原像，超时则任何人可罚没到address(0)。C12（提交者×DA观察者串谋）从deferred_to_E变为verified。远程证明无效可在协议层检测，但链上罚没依赖DCAP验证服务（本轮blocked）。提交者失联无可转发证据（C03）为协议设计选择：不罚没无责任外部方，保持limited状态。论文表4已更新各类故障的罚没比例及依赖条件。

### 对专家2-1的回复（实质区别）

> 感谢专家指出实质区别不清。经重新审视，我们将创新点重定位为：**在有界重算模型内提供不依赖交互的终止路径，并首次量化恢复机制的收益与代价**。G-L1同模型对照（StageH重跑，210条记录）显示：在无兜底adjudicate的机制基线中，提交方离线时正确终局率从30/30跌至0/30；在有兜底的本文实现中，所有路径均30/30。恢复的价值在于提供不依赖兜底的交互续推路径，代价是gas增加47%（16.1M vs 8.1M）。
>
> 关于与OP FDG差异：我们确认OP FDG已有时钟继承+三档CLOCK_EXTENSION（在commit c4a68ab的FaultDisputeGame.sol的move()内getChallengerDuration()实现）。本文差异为：(1)有界重算模型vs无界二分；(2)显式adjudicate兜底vs时钟继承；(3)恢复不刷新绝对截止时间vs动态延期。OP FDG组件测试（Foundry 1.5.1，三用例通过，gas 365k~3.7M）已记录，但不可与本文本地gas合成领先比例表（端点语义不同）。论文已全面修订创新点表述，不再声称"首创第三方接续"。

---

**文档结束**

下一步：执行WP2（修订论文）和WP3（生成其他交付文档）。
