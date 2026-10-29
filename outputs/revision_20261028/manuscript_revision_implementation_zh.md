# Hybrid TEE-Rollup 手稿修订实施指南（2026-10-28）

**修订基准**: `paper_outputs/draft/论文终版/Hybrid_TEE_Rollup_修订稿.docx`  
**依据文档**: `outputs/revision_20261028/expert_response_matrix.md` §4  
**目标输出**: `Hybrid_TEE_Rollup_返修稿_20261028.docx`  
**修订原则**: 严格对齐StageH证据，诚实标注边界，不伪造数据

---

## 0. 修订概览

本次修订响应专家1（2条意见）和专家2（6条意见）的评审意见，基于StageH (2026-10-17) 真实硬件验证成果。主要修订方向：

1. **创新点重定位**: 从"首创恢复机制"改为"有界模型+显式兜底+恢复量化"
2. **证据回填**: StageH真实SGX数据、DA披露罚没、G-L1对照实验
3. **边界标注**: 本地vs真实、blocked项、口径限制
4. **去重**: 删除摘要/引言/结论中的重复贡献段落
5. **引用补全**: opML文献、4处就近标注

---

## 1. 摘要修订

### 1.1 删除内容

❌ **删除重复的贡献段落**（如果摘要中有与引言/结论相同的描述）

❌ **删除以下表述**：
- "恢复机制降低结算延迟"
- "首创第三方争议接续"
- "动态参与机制"
- "完全去信任"

### 1.2 修改创新点表述

将现有的创新点描述改为：

```
本文提出Hybrid TEE-Rollup (HTR)，一种结合可信执行环境（TEE）与乐观验证的有界任务rollup方案。针对"参与者失联时能否保证正确终局"这一核心问题，本文在有界重算模型内引入显式兜底裁决（adjudicate）与可恢复挑战协议，并通过同模型对照实验首次量化恢复机制的收益与代价：在无兜底的机制基线中，提交方离线时正确终局率从30/30跌至0/30；在有兜底的本方案中，所有路径均保持30/30正确终局，但恢复路径gas增加47%（16.1M vs 8.1M）。
```

### 1.3 补充真实验证范围

在摘要中补充：

```
实验验证方面，本文在阿里云SGX实例（Intel Xeon Platinum 8369B）上获取真实DCAP Quote（TCB 0xA003），Enclave内有界哈希链（128步0.497ms）与本地ethers逐字节一致，MRENCLAVE绑定可验证。同时实现DA披露罚没机制（bindDa/fulfillDa/slashDa），闭环解决提交者×DA观察者串谋（C12，罚没1 ether）。
```

### 1.4 标注边界限制

在摘要末尾补充：

```
需明确的边界：本地Hardhat性能指标（162.78 tasks/s）为closed-loop口径，不含DA/TEE成本；真实SGX Quote在链下验证（依赖可信验证服务）；Sepolia Blob广播因缺RPC URL/私钥/beacon API仍blocked；计算模型为有界重算（至多128步），非通用EVM Rollup。
```

---

## 2. §1 引言修订

### 2.1 删除内容

❌ **删除以下创新点表述**：
- "首创第三方争议接续"（OP FDG已有时钟继承）
- "动态延长窗口"（与证据矛盾，C06/C08证明absoluteDeadline不延长）
- "恢复机制加快结算/降低延迟"（F消融证明：recovery 12.6ms > direct-fallback 7.3ms）
- 把哈希、Merkle、摊销本身列为创新的表述

❌ **删除与摘要/结论重复的贡献段落**

### 2.2 重定位创新点

将引言中的贡献段落改为：

```
本文的主要贡献如下：

(1) **有界模型+显式兜底**: 在有界重算模型（至多128步）内提供不依赖交互的终止路径（adjudicate兜底裁决），区别于OP FDG的无界二分+时钟继承。

(2) **恢复机制量化**: 首次通过同模型对照实验（G-L1，210条记录）量化恢复机制的真实收益与代价。发现：无兜底时提交方离线导致正确终局率0/30，有兜底时均30/30；恢复提供不依赖兜底的交互续推路径，代价是gas +47%且延迟未减少（12.6ms vs 7.3ms）。

(3) **真实TEE与DA罚没**: 在真实SGX硬件上获取DCAP Quote（TCB 0xA003），Enclave有界哈希链与本地ethers逐字节一致；实现DA披露罚没（bindDa/fulfillDa/slashDa）闭环解决C12串谋。

(4) **诚实边界标注**: 明确本地vs真实、blocked项、口径限制，不伪造TEE Quote/Blob回执，不把本地Hardhat写成生产主网。
```

### 2.3 补充研究问题

将研究动机改为可证伪形式：

```
本文关注以下可证伪的研究问题：

RQ1: 在有界重算模型内，参与者失联时能否保证正确终局？
RQ2: 恢复机制是否引入延迟放大？
RQ3: 紧凑承诺（traceRoot为有序向量承诺）在恢复后能否支持终局裁决？
RQ4: 真实TEE与DA为系统增加何种成本？
```

### 2.4 明确模型范围

在引言中补充：

```
需明确的模型边界：本方案为有界执行模型（bounded-task），针对可在128步内完成的确定性计算任务，非通用EVM Rollup；traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle单步证明；在单链实例假设下不存在分叉争议场景。
```

---

## 3. §2 相关工作修订

### 3.1 补充缺失的引用标注

**位置1**: "TEEROLLUP提出了利用异构TEE…"（原文@2787，无标注）

修改为：
```
TEEROLLUP[1]提出了利用异构TEE…
```

**位置2**: "opML与optimistic fraud proof等工作研究…"（原文@2863/@2870，无标注且opML无条目）

修改为：
```
opML[新增编号]与optimistic fraud proof等工作研究…
```

**位置3**: "Dynamic Fraud Proof关注…"（原文@3007，无标注）

修改为：
```
Dynamic Fraud Proof[6]关注…
```

**位置4**: "LazyLedger、模块化DA以及轻客户端…"（原文@3099，无标注）

修改为：
```
LazyLedger[7]、模块化DA[8][9]以及轻客户端[10]…
```

### 3.2 补充opML文献条目

在参考文献表新增（需检索原始来源，临时格式如下）：

```
[新增编号] AUTHOR. opML: Optimistic Machine Learning[EB/OL]. [访问日期]. URL.
```

### 3.3 增加OP FDG时钟继承对比

在相关工作中新增一段：

```
Optimism的Fault Dispute Game (FDG)[已有编号]在move()函数内通过getChallengerDuration()实现三档CLOCK_EXTENSION时钟继承机制，允许挑战方在提交响应时动态延长游戏期限。本文与OP FDG的差异在于：(1)有界重算模型vs无界二分；(2)显式adjudicate兜底vs时钟继承；(3)恢复不刷新绝对截止时间vs动态延期。本文通过G-L1同模型对照（210条记录）量化了有兜底adjudicate在提交方离线场景下的价值（正确终局率从0/30提升至30/30），而OP FDG的时钟继承为无界模型提供了不同的活性保证。
```

### 3.4 版本锁定

修改所有相关文献引用：

- **TeeRollup**: "arXiv:2409.14647**v3**"（强调v3版本）
- **BoLD**: "commit 30e78f67"
- **OP FDG**: "规范访问日期2026-09-16，源码commit c4a68ab"

### 3.5 差异对比表

在相关工作末尾新增表格：

```
表1 本方案与相关工作的机制差异

| 维度 | 本方案 | TeeRollup v3 | BoLD v1 | OP FDG |
|---|---|---|---|---|
| 计算模型 | 有界重算（≤128步） | 异构TEE并行 | 无界二分 | 无界二分 |
| 执行信任 | 链下Quote验证 | TEE远程证明 | 零信任 | 零信任 |
| 争议接续 | recover+adjudicate兜底 | 未明确 | 新质押者继续 | 时钟继承+move |
| 恢复量化 | G-L1: 0/30→30/30 | 未量化 | 未量化 | 未量化 |
| 数据来源 | 本文实验 | 文献报告 | 文献报告 | 组件测试 |
```

---

## 4. §3 系统概览修订

### 4.1 新增§3.2威胁模型表

在系统概览中新增一节"§3.2 威胁模型与信任假设"，包含以下表格：

```
表2 威胁模型与防护机制

| 参与方 | 可信假设 | 攻击能力边界 | 防护机制 | 残余风险 |
|---|---|---|---|---|
| 提交者 | 提交有效签名、绑定DA押金 | 篡改结果、拒绝披露DA、友好挑战同伙 | B04/B05裁决拒绝；DA罚没；adjudicate兜底 | 经济缺陷：友好挑战获利（C11，未修） |
| 挑战者 | 绑定挑战押金 | 恶意挑战、抢先recover占位 | 押金损失；有界recover次数（maxRecoveries=2） | 无 |
| 观察者/恢复者 | 至少一方诚实且可上链 | 全部离线、Sybil抢占 | 状态链上持久化（C14）；恢复上限 | 全部离线+无人调用→terminate |
| DA服务 | 绑定押金并承担披露义务 | 串谋隐瞒数据 | DA罚没（bindDa/slashDa，C12） | 无（已闭环） |
| TEE执行环境 | 链下Quote验证通过 | 硬件回滚、密钥泄露 | 协议层taskId唯一性（C15） | 需链上DCAP验证（blocked） |
| L1底层链 | 按确认策略终局稳定 | 共识重组、永久审查 | 依赖L1安全假设 | 不提供跨重组额外保证 |
```

### 4.2 明确观察者假设

在§3.2中补充一段：

```
本方案假设至少存在一个有数据、有资金且可及时上链的诚实观察者。在此假设下，任何参与者失联（submitter拒绝respond、challenger放弃、原恢复者离线）均可由其他观察者通过recover接续，最终由adjudicate兜底裁决保证正确终局。若所有观察者同时离线且无人调用，则任务超过absoluteDeadline后只能由任何人terminate结算。
```

### 4.3 主动披露C11经济缺陷

在§3.2中补充：

```
需主动披露的经济缺陷：在错误任务下，提交者与挑战者可通过"友好挑战"使同伙获利（C11测试揭示）。这属于协议经济设计问题（B阶段范畴），本轮未修复。诚实反证路径保留（任何人可adjudicate），裁决仅由verdict决定，第三方不能窃取收益。
```

### 4.4 明确审查与活性边界

在§3.2中补充：

```
审查攻击边界（C13）：有界审查可恢复（多个观察者轮流上链），但永久阻断/无限分区不承诺活性。若任务超过absoluteDeadline且无人调用，只能事后terminate。
```

### 4.5 明确traceRoot定义

在系统概览或§4中补充：

```
traceRoot采用有序向量承诺：keccak256(abi.encode(bytes32[]))，即对完整轨迹数组的紧凑哈希，非Merkle单步证明。在有界模型（至多128步全量重算）+单链实例假设下，不存在分叉争议场景，故分叉证明不构成协议缺口。
```

### 4.6 区分TEE信任层次

在§3系统架构中补充：

```
TEE信任分两层：(1)硬件信任：依赖Intel SGX平台提供的Enclave隔离与远程证明；(2)验证服务信任：当前链上DCAP验证blocked（需集成验证库），依赖链下Quote验证服务确认TCB状态（本方案TCB 0xA003）。
```

---

## 5. §4 核心机制修订

### 5.1 §4.1 可恢复挑战协议

#### 5.1.1 回填权限矩阵

新增一小节或表格：

```
表3 操作权限矩阵

| 操作 | 调用者限制 | 相位限制 | 期限限制 |
|---|---|---|---|
| submit | 无 | IDLE | - |
| openChallenge | 非提交方 | SUBMITTED | timestamp < responseDeadline |
| respond | 仅提交方 | CHALLENGED | timestamp < responseDeadline |
| recover | 无 | CHALLENGED或RECOVERED | timeoutAt < timestamp < absoluteDeadline，且recoveries < maxRecoveries |
| advance | 无 | RECOVERED | timestamp < absoluteDeadline |
| replay | 无 | RECOVERED | timestamp < absoluteDeadline |
| settle | 无 | CHALLENGED或RECOVERED | timestamp >= deadline |
| adjudicate | 无 | CHALLENGED或RECOVERED | timestamp >= deadline，verdict冲突 |
| terminate | 无 | 任意 | timestamp > absoluteDeadline |
| finalize | 无 | SETTLED | timestamp > finality window |
```

#### 5.1.2 防重复恢复逻辑

补充一段：

```
防重复恢复机制（C04/C09/C05）：recoveries上限maxRecoveries（默认2）。require(taskData.recoveries < maxRecoveries, "RecoveriesExhausted")拒绝第三次恢复，且不丢原任务状态。8个Sybil地址依次recover仅成功2次，absoluteDeadline不变（C05）。
```

#### 5.1.3 防延长窗口公式

补充一段：

```
防延长窗口机制（C01/C06/C08）：recover要求timeoutAt < timestamp < absoluteDeadline双端严格不等（C06），timeoutAt之前recover被拒（C01）。_touch()函数截断新期限至absoluteDeadline：newDeadline = min(timestamp + timeout, absoluteDeadline)，不创造不可能义务（C08）。
```

#### 5.1.4 有界DoS防护

补充一段：

```
有界DoS防护（C17）：最大任务（steps=128）正常结算（respond=204,737 gas, adjudicate=164,567 gas）。20次无效recover风暴20/20 revert，状态无污染，作废gas=0由攻击者承担（gas refund机制）。
```

#### 5.1.5 状态转移与不变量

补充一段：

```
状态转移完整性：给出state_transition_table.json（附录或在线资源），覆盖8种相位×10种操作的条件约束。不变量校验（INV1-INV7）在5次独立检查中0违反：
- INV1: balance == locked + totalClaimable
- INV2: balance == totalDeposited - totalWithdrawn - totalBurned
- INV3: totalClaimable <= balance
- INV4: challengeDeadline only forward
- INV5: absoluteDeadline monotonic
- INV6: phase transition valid
- INV7: claimable non-negative

需明确：这属于不变量级验证，非机器可检验形式化证明（无TLA+/Kani/Certora）。
```

#### 5.1.6 回滚与终局性

补充一段：

```
状态回滚边界：协议层通过taskId唯一性防重放（C15本地仿真），不声称覆盖TEE硬件防回滚（D08 blocked，需真实Enclave重启测试）或共识层重组（C16 not_applicable，Hardhat automining无真实重组）。本方案依赖下层L1终局性，不提供跨共识重组额外保证。
```

---

### 5.2 §4.2 计算承诺与裁决

#### 5.2.1 明确traceRoot定义

修改或补充：

```
traceRoot采用有序向量承诺：keccak256(abi.encode(bytes32[]))，对完整轨迹数组（至多128个bytes32元素）的紧凑哈希。这与Merkle单步证明的区间争议协议不同，本方案在挑战阶段由submitter披露完整trace数组，adjudicate进行全量重算（至多128步）验证verdict。
```

#### 5.2.2 删除未实现能力

❌ **删除以下表述**（如果存在）：
- "单步验证"
- "对数复杂度争议"
- "Merkle区间证明"

#### 5.2.3 补充编码定义

新增一小节：

```
编码与绑定链条：
- input: 用户提供的输入数据（本地环境为keccak256(input_json)）
- programHash: 链上注册的确定性程序摘要
- trace: 执行轨迹bytes32[]（每步状态哈希或中间承诺）
- result: 最终输出（bytes32）
- dataHash: DA数据承诺（keccak256(data)）
- traceRoot = keccak256(abi.encode(trace))
- reportDataDigest = buildReportDataDigest(taskId, input, programHash, result, dataHash, traceRoot)（域分离：HYBRID_BOUNDED_TASK_V1）

TEE内验证：report_data前32字节与reportDataDigest一致性。
```

---

### 5.3 §4.3 TEE证明与密钥管理

#### 5.3.1 回填StageH真实SGX数据

新增一节"§4.3.1 真实SGX DCAP验证"：

```
本方案在阿里云ecs.g7t.large实例（Intel Xeon Platinum 8369B，北京可用区）上获取真实SGX DCAP Quote。软件栈：sgxsdk-2.19.100.3, libsgx-dcap-ql-1.16.100.2, libsgx-dcap-default-qpl-1.16.100.2。

Quote验证结果：两条路径（Intel QvE + Azure Attestation）均返回0xA003 (SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED)。TCB状态"过期需配置"非UpToDate，关联6个Intel security advisory：INTEL-SA-00657/00767/01079/01103/01153/00615。密码学验证通过（签名、证书链），但策略判定为非终态。

表4 真实SGX Quote验证摘要

| Quote | SHA256 | report_data前32字节 | 验证结果 | 用途 |
|---|---|---|---|---|
| quote_bound.dat | 9ab7ae99... | 与buildReportDataDigest一致 | 0xA003 | 绑定摘要验证 |
| quote_bad.dat | a334b444... | 首字节篡改为0x20 | 0xA003 | 负例：密码学通过但绑定失败 |
| quote_steps4.dat | 75e84914... | d7ddfc60... (4步result) | 0xA003 | 有界哈希链4步 |
| quote_steps128.dat | bf78a99d... | dd38eea6... (128步result) | 0xA003 | 有界哈希链128步 |

MRENCLAVE：
- 有界哈希链4步与128步：1967faaa...
- 绑定Quote场景：76f38bb2...

说明：不公开原始Quote二进制文件（含平台身份信息）。
```

#### 5.3.2 补充Enclave性能

补充一段：

```
Enclave性能：有界哈希链4步0.057ms（Enclave内），128步0.497ms（Enclave内）。同代码宿主环境128步0.305ms，Enclave开销约63%（Enclave上下文切换+内存加密）。Enclave输出与本地ethers.solidityKeccak256逐字节一致，证明确定性计算。
```

#### 5.3.3 本地EVM联调

补充一段：

```
本地EVM联调：真实SGX计算+本地Hardhat裁决。4步任务respond gas=94,836, adjudicate gas=94,812（verdict=0），SETTLED。128步任务respond gas=166,840, adjudicate gas=164,567（verdict=0），SETTLED。
```

#### 5.3.4 标注链下验证边界

补充一段（重要）：

```
验证边界：当前Quote验证在链下完成（两条路径：Intel QvE + Azure API），链上DCAP验证blocked（需合约集成Intel DCAP验证库或可信验证服务）。本方案依赖链下可信验证服务确认Quote有效性。TCB状态0xA003非UpToDate，需平台升级或collateral更新方可通过严格策略。链上罚没依赖DCAP验证集成（未实现），当前协议层仅检测report_data绑定失败。
```

---

### 5.4 §4.4 DA绑定、披露与成本

#### 5.4.1 新增DA披露罚没机制

新增一小节"§4.4.1 DA披露罚没协议"：

```
为解决提交者×DA观察者串谋（C12），本方案实现DA披露罚没机制：

- **bindDa(taskId)**: submitter提交任务时绑定DA押金（等额任务押金），并承诺在披露窗口（默认600区块）内披露dataHash原像。
- **fulfillDa(taskId, dataBytes)**: 在窗口内，submitter调用fulfillDa披露dataBytes，合约验证keccak256(dataBytes) == taskData.dataHash，通过后返还押金。
- **slashDa(taskId)**: 超过披露窗口，任何人可调用slashDa销毁押金到address(0)。任务状态回退至IDLE或前一相位（取决于履约状态），防止依赖未披露DA的裁决。

C12测试：submitter拒绝披露DA，观察者调用slashDa罚没1 ether（slashDa gas=66,136），任务状态从DA_PENDING回退。adjudicate/settle/terminate/finalize在DA pending状态拒绝执行。

StageB/C回归：26 passing（DA罚没未破坏原有功能）。
```

#### 5.4.2 标注披露非点值证明

补充一段：

```
重要标注：DA披露检查dataHash原像（keccak256(dataBytes)），非EIP-4844点值证明（blob.verify_kzg_proof）。本方案保持E01真实KZG密码学（c-kzg 4.1.0，容量126976字节，篡改拒绝），但Sepolia Blob广播（E02/E03/E13）因缺SEPOLIA_RPC_URL、SEPOLIA_PRIVATE_KEY、BEACON_API_URL仍blocked。
```

#### 5.4.3 成本公式补充

补充变量说明：

```
成本模型（F阶段）：
- Per-task成本 = submitGas + challengeGas + resolveGas + daGas + teeGas
- DA成本 = blobCount × blobBaseFee + kzgProofGas（本地=modelled，真实网络blocked）
- TEE成本 = enclaveTime × teeRate（Enclave 128步0.497ms，费率modelled）
- 摊销优势96.33%来自成本模型，非真实模块化DA网络实验

变量单位：gas in wei, time in ms, blobBaseFee in wei/blob（Blob阶梯为modelled参数）
```

---

## 6. §5 实验评估修订

### 6.1 §5.1 实验环境与口径

#### 6.1.1 分层描述

修改实验环境节为分层描述：

```
本文实验分三层：

(1) **本地受控实验（Hardhat）**: 性能基准（F阶段162.78 tasks/s）、安全测试（B/C阶段26 passing）、机制对照（G-L1）。环境：Node.js 18.16.0, Hardhat 2.19.0, in-process automining。

(2) **真实硬件实验（阿里云SGX）**: TEE远程证明（StageH）。环境：ecs.g7t.large, Intel Xeon Platinum 8369B, sgxsdk-2.19.100.3, DCAP 1.16.100.2。

(3) **公网测试网实验（blocked）**: Sepolia Blob广播（E02/E03/E13）因缺RPC URL/私钥/beacon API未完成。
```

#### 6.1.2 不写"生产环境已验证"

补充一段：

```
重要说明：虽完成真实SGX Quote获取，但不因此写成"生产环境已验证"。本地Hardhat无真实共识最终性，真实SGX在链下验证，Sepolia Blob blocked。本方案为研究原型（prototype），生产部署需补齐：链上DCAP验证、公网Blob广播、正式审计。
```

---

### 6.2 §5.2 安全与资金闭环

#### 6.2.1 更新表4故障类型矩阵

修改表4（如果存在），或新增：

```
表5 故障类型检测与罚没

| 故障类型 | 检测率 | 挑战成功率 | 罚没比例 | 依赖机制 | StageH状态 |
|---|---|---|---|---|---|
| 响应篡改 | 100% | 100% | 100% | B04/B05裁决拒绝 | ✅证据充分 |
| 轨迹长度不匹配 | 100% | 100% | 100% | B04 | ✅证据充分 |
| 远程证明无效 | 100% | - | 0% | 需链上DCAP验证 | ⚠️部分（协议层检测，链上罚没blocked） |
| DA不可用 | 100% | 100% | 100% | bindDa/slashDa（C12） | ✅完成 |
| DA证明无效 | 100% | 100% | 100% | 同上 | ✅完成 |
| 提交者失联无证据 | 100% | - | 0% | 协议设计选择（E11） | ⚠️limited（不罚没无责任外部方） |
```

#### 6.2.2 补充DA罚没流程

新增一段：

```
DA披露罚没实验（C12）：submitter拒绝披露dataHash原像，观察者在披露窗口结束后调用slashDa，罚没1 ether押金到address(0)（slashDa gas=66,136）。任务状态从DA_PENDING回退，adjudicate拒绝执行。StageB/C回归26 passing，确认DA罚没未破坏原有功能。
```

#### 6.2.3 保持资金闭环

补充一段：

```
资金闭环三条恒等式（B01/B10-B14，BigInt记账）：
- balance == locked + totalClaimable
- balance == totalDeposited - totalWithdrawn - totalBurned
- totalClaimable <= balance

C17：最大任务（steps=128）正常结算（respond=204,737 gas, adjudicate=164,567 gas），20次无效风暴20/20 revert，状态无污染，作废gas=0由攻击者承担。
```

---

### 6.3 §5.3 恢复及DoS

补充或修改：

```
恢复与DoS实验（C阶段）：

- **C01/C06**: timeoutAt之前recover被拒（C01），双端严格不等（C06）
- **C04/C09**: recoveries上限2，第三次被拒且不丢原任务
- **C05**: 8个Sybil地址依次recover仅成功2次，absoluteDeadline不变
- **C08**: _touch截断至absoluteDeadline，不创造不可能义务
- **C13**: 有界审查可恢复，永久阻断不承诺活性
- **C17**: 最大任务+20次风暴，20/20 revert，作废gas=0

不变量校验（INV1-INV7）：5次检查0违反。
```

---

### 6.4 §5.4 真实TEE

新增一节"§5.4 真实SGX DCAP验证"（与§4.3.1内容一致，但实验节详细展示数据）：

复制§4.3.1的内容到实验节，并补充：

```
图X 真实SGX Quote验证流程

[流程图：Enclave计算 → 生成Quote → Intel QvE验证 → 返回0xA003 → 检查report_data绑定]

实验结论：
- ✅ 真实SGX DCAP Quote获取成功
- ✅ Enclave有界哈希链与本地ethers逐字节一致
- ✅ MRENCLAVE绑定可验证
- ✅ 本地EVM联调通过（4步gas=94,836, 128步gas=166,840）
- ⚠️ TCB 0xA003非UpToDate，链下验证
- ❌ 链上DCAP验证blocked
```

---

### 6.5 §5.5 真实Blob与端到端

#### 6.5.1 保持E01真实KZG

补充一段：

```
EIP-4844 KZG密码学（E01）：c-kzg 4.1.0, loadTrustedSetup(kzg_trusted_setup_g1.json)。容量上界126976字节（4096 field elements × 31字节 + 帧开销79字节）。验证测试：正常blob通过verifyKzgProof，篡改1字节抛VerificationFailed，超容量1字节抛SINGLE_BLOB_CAPACITY_EXCEEDED。trusted setup sha256: d39b9f2d047cc9dc...
```

#### 6.5.2 标注Sepolia Blob blocked

补充一段：

```
Sepolia Blob广播（E02/E03/E13）：blocked，缺SEPOLIA_RPC_URL、SEPOLIA_PRIVATE_KEY、BEACON_API_URL。无法记录真实blobGasUsed/Price、versionedHash、beacon取回日志。
```

#### 6.5.3 保持F本地指标+整段口径限制

修改或补充（**必须保留，不可省略**）：

```
端到端性能（F阶段）：

baseline配置（b8-p8-c4-s64）：162.78 tasks/s（3 run均值），批总延迟161.8 ms。

消融实验（4臂）：
- recovery-under-fault: 12.6 ms
- direct-fallback: 7.3 ms
- no-recovery-baseline: 8.7 ms
- full-interaction: 15.2 ms

结论：**恢复未减延迟**（recovery 12.6ms > direct-fallback 7.3ms）。

并发测试（c=1/4/16）：121.79/144.63/117.19 tasks/s，**无单调增益**（串行出块限制）。

挑战窗口测试：window=100000时终局率回到1.0，TPS=156.93/154.04/87.07。

**口径限制（必须完整标注）**：
1. Hardhat in-process automining，无真实共识最终性
2. 每块链钟+1秒（block.timestamp += 1s per block）
3. Closed-loop到达（每批等待前批完成，非open-loop压力）
4. 仅3个独立run（不报p95/p99，无bootstrap CI）
5. 费用local-gas-only（不含DA/TEE成本，仅链上EVM gas）
6. Payload 1KiB vs 32KiB为名义参数（dataHash固定32字节），不构成"扩展到大块数据仍保持吞吐"的证据
7. 并发c=1/4/16无单调增益，受串行出块限制

不可写：
- ❌ "高频DApp TPS 162.78"
- ❌ "生产环境吞吐"
- ❌ "payload扩展保持吞吐"
```

---

### 6.6 §5.6 同口径性能/消融（G-L1）

新增一节"§5.6 机制对照实验"：

```
为量化恢复机制的真实收益与代价，本文设计G-L1同模型对照实验：在相同有界重算模型下，对比"有兜底adjudicate的本方案"vs"无兜底adjudicate的机制基线"在提交方离线场景的表现。

实验配置：3 run × 10 batch/run = 210条记录（非预热），本地Hardhat。

表6 G-L1机制对照结果

| 系统 | 路径 | 正确终局 | 错误终局 | resolve gas合计 | 说明 |
|---|---|---|---|---|---|
| 本文 | interactive | 30/30 | 0 | 15,148,776 | 交互式挑战路径 |
| 本文 | fault-no-recovery | 30/30 | 0 | 8,076,444 | 故障无恢复（有兜底） |
| 本文 | fault-with-recovery | 30/30 | 0 | 16,121,160 | 故障+恢复 |
| 本文 | direct-no-response | 30/30 | 0 | 3,884,634 | 直接无响应兜底 |
| 机制基线 | interactive | 30/30 | 0 | 11,517,024 | 无兜底交互 |
| 机制基线 | fault-no-recovery | **0/30** | **30** | 4,893,744 | **无兜底+离线=失败** |
| 机制基线 | direct-no-response | **0/30** | **30** | 1,602,852 | **无兜底+无响应=失败** |

关键发现：
1. 在无兜底adjudicate的机制基线中，提交方离线时正确终局率从30/30跌至0/30
2. 在有兜底adjudicate的本文实现中，所有路径均30/30正确终局
3. 恢复机制的价值：提供不依赖兜底重算的交互续推路径
4. 恢复机制的代价：gas增加47%（fault-with-recovery 16.1M vs fault-no-recovery 8.1M），且延迟未减少（12.6ms vs 7.3ms）

重要标注：**机制基线为本项目自建，非Arbitrum/Optimism/TeeRollup官方实现**。
```

#### 6.6.1 引用F消融

在§5.6中补充：

```
与F消融4臂对应：recovery-under-fault 12.6ms vs direct-fallback 7.3ms，证明**恢复未减延迟**。恢复的价值在于保留交互续推路径（适用于有能力respond的场景），而非缩短结算时间。
```

---

### 6.7 §5.7 第三方比较与局限

#### 6.7.1 保持机制对比矩阵

保持表1（或新增表7）：

```
表7 本方案与相关工作的机制对比

（同§2的表1，4系统×8维度，版本锁定）
```

#### 6.7.2 引用G-L1同模型对照

补充一段：

```
同模型对照（G-L1）：在相同有界模型下，机制基线（无兜底adjudicate）提交方离线时正确终局率0/30，本方案（有兜底）30/30，gas +47%。**机制基线非官方实现**，不可直接推广至Arbitrum/Optimism/TeeRollup官方系统的表现。
```

#### 6.7.3 新增OP FDG组件测试

新增一段：

```
OP FDG官方实现组件测试（G-L2部分突破）：在Optimism commit c4a68ab上用Foundry 1.5.1-stable运行三个官方测试通过：
- test_move_simpleAttack_succeeds: 365,885 gas
- test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds: 2,778,766 gas
- test_resolve_stepReached_succeeds: 3,731,850 gas

重要说明：**这些为组件测试gas，包含断言与辅助逻辑，非Optimism主网吞吐**。端点语义不同，不可与本文本地gas合成领先比例表。
```

#### 6.7.4 保持G-L3文献定量

补充一段：

```
文献定量（G-L3）：
- TeeRollup v3: 28 KTPS（峰值延迟119ms），UpdateState=156k gas（摊销78 gas）[1]
- BoLD v1: 终止上界2·(Cmax+D)，腐化方与诚实方聚合成本比10×[已有编号]
- OP FDG: MAX_GAME_DEPTH等参数为not_verified（部署时immutable）[已有编号]

重要标记：
- TeeRollup的"降低约86%"原文基线是**StarkNet**，非OP/Arbitrum
- BoLD的"10×"是**腐化方与诚实方聚合成本比**，非跨协议领先
- 均标注"literature_reported"
```

#### 6.7.5 明确方法论选择

新增一段：

```
可比性分析（G-CE-06）：本文端到端指标为本地Hardhat closed-loop口径，第三方为生产账单或机制描述。端点语义不同（submit-to-finalize vs transaction-confirmed），币种不同（local wei vs USD），时间不同（2026实验 vs 文献报告时间），环境不同（in-process vs 公网）。**不可生成统一胜负表**，不写"快N倍"或"省X%"。

可比维度：
- 提交成本：仅定性比较机制（本地gas vs 文献gas，币种/时间不同）
- 挑战轮数：定性可比（本文2-7轮 vs FDG MAX_GAME_DEPTH vs BoLD 2·(Cmax+D)）
- 恢复能力：定性可比（本文recover+adjudicate vs FDG时钟继承 vs BoLD新质押者）
- 结算延迟：不可比（端点语义不同）
```

#### 6.7.6 删除跨协议领先声明

❌ **删除以下表述**（如果存在）：
- "比Optimism快N倍"
- "比Arbitrum省X%"
- "优于TeeRollup Y%"
- 任何统一胜负表

#### 6.7.7 补充blocked项表

新增表8：

```
表8 仍然Blocked的对比项（诚实记录）

| 项目 | 阻塞原因 | 解除条件 |
|---|---|---|
| BoLD官方实现 | 需Go 1.24.5 | 安装Go 1.24.5并编译运行 |
| TeeRollup官方实现 | arXiv:2409.14647v3无公开仓库 | 联系作者索取或标注"无公开实现" |
| Sepolia Blob广播 | 缺RPC URL/私钥/beacon API | 配置环境变量并运行blob_publish.js |
| 链上DCAP验证 | 需集成验证库 | 实现TEEVerifier接口或可信验证服务 |
| UpToDate TCB | 实例TCB 0xA003过期 | 申请最新TCB实例或接受0xA003策略 |
```

---

## 7. §6 结论修订

### 7.1 对齐摘要与引言

确保结论中的创新点、证据边界、blocked项与摘要/引言一致。

### 7.2 逐项回答研究问题

修改或补充：

```
本文回答了以下研究问题：

RQ1: 在有界重算模型内，参与者失联时能否保证正确终局？
- **是的**。通过recover+adjudicate兜底机制，G-L1实验显示：无兜底时正确终局率0/30，有兜底时30/30。

RQ2: 恢复机制是否引入延迟放大？
- **未减延迟**。F消融实验：recovery-under-fault 12.6ms > direct-fallback 7.3ms。恢复的价值在于保留交互续推路径，而非缩短结算时间。

RQ3: 紧凑承诺在恢复后能否支持终局裁决？
- **能**。traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），adjudicate全量重算（至多128步）验证verdict，但需兜底重算能力。

RQ4: 真实TEE与DA为系统增加何种成本？
- **Enclave**: 128步0.497ms（vs宿主0.305ms，开销63%）
- **DA罚没**: slashDa gas=66,136
- **链下验证**: 依赖可信Quote验证服务
```

### 7.3 明确真实验证范围

补充一段：

```
本文真实验证范围：
- ✅ 真实SGX DCAP Quote（TCB 0xA003，链下验证）
- ✅ Enclave有界哈希链与本地ethers逐字节一致
- ✅ 真实KZG密码学（c-kzg 4.1.0，容量126976字节）
- ✅ DA披露罚没（C12罚没1 ether）
- ✅ G-L1同模型对照（210条记录）
- ✅ OP FDG组件测试（3个通过）
```

### 7.4 明确模型与假设

补充一段：

```
本文模型边界：
- **计算模型**: 有界重算（至多128步），有序向量承诺，非通用EVM Rollup
- **观察者假设**: 至少一个有数据、有资金且可及时上链的诚实观察者
- **审查假设**: 有界审查可恢复，永久审查不承诺活性
- **TEE信任**: 链下Quote验证，依赖可信验证服务
- **DA限制**: DA披露检查dataHash原像，Sepolia Blob blocked
```

### 7.5 明确残余风险

补充一段：

```
残余风险与blocked项：
- 链上DCAP验证blocked（需集成验证库）
- TCB 0xA003非UpToDate（需平台升级）
- Sepolia Blob blocked（缺RPC/私钥/beacon API）
- 形式化证明为不变量级验证（非TLA+/Kani）
- 状态回滚依赖L1终局性（不提供跨重组额外保证）
- C11经济缺陷：友好挑战可使同伙获利（未修）
```

### 7.6 删除无依据结论

❌ **删除以下表述**（如果存在）：
- "完全去信任"
- "解决全部TEE风险"
- "优于所有Rollup"
- "恢复降低延迟"
- "首创第三方接续"

---

## 8. 参考文献修订

### 8.1 补充opML条目

新增（需检索原始来源，临时格式）：

```
[新增编号] AUTHOR. opML: Optimistic Machine Learning[EB/OL]. [访问日期]. URL.
```

检索来源：arXiv, GitHub, 官方白皮书。

### 8.2 逐一核对引用标注

检查每个[1]-[12]在正文中的标注位置是否正确，论述对象是否对应。

### 8.3 版本锁定

修改相关文献条目：

- **TeeRollup**: "arXiv:2409.14647**v3**. 2024."
- **BoLD**: "Arbitrum Foundation. BoLD: Bounded Liquidity Delay[EB/OL]. (2024-04-15)[访问日期]. https://arxiv.org/abs/2404.10491v1. commit 30e78f67."
- **OP FDG**: "Optimism Foundation. Fault Dispute Game Specification[EB/OL]. (2026-09-16)[2026-09-16]. https://specs.optimism.io/. commit c4a68ab."

### 8.4 统一引用格式

所有文献条目遵循：

```
作者. 题名[文献类型标识]. (发表日期)[访问日期]. DOI/URL. 版本/Commit.
```

---

## 9. 全文检查清单（提交前核对）

### 9.1 内容完整性

- [ ] 摘要：创新点重定位，删除禁止表述，补充真实验证范围，标注边界
- [ ] §1引言：去重，重定位创新点，补充研究问题，明确模型范围
- [ ] §2相关工作：4处补标注，补opML条目，增加OP FDG对比，版本锁定
- [ ] §3系统：新增威胁模型表，明确观察者/审查/traceRoot/TEE信任假设，披露C11缺陷
- [ ] §4机制：回填权限/防重复/防延长/DoS/状态转移/不变量，标注非形式化证明，回填StageH SGX数据，新增DA罚没机制
- [ ] §5实验：分层环境描述，更新表4故障矩阵，新增§5.4真实TEE节，标注口径限制，新增§5.6 G-L1对照，新增OP FDG组件测试，明确方法论，删除跨协议领先声明
- [ ] §6结论：对齐摘要，逐项回答研究问题，明确模型/假设/残余风险，删除无依据结论
- [ ] 参考文献：补opML，版本锁定，统一格式

### 9.2 证据对齐

- [ ] 所有创新点声明均有StageH证据支撑
- [ ] 所有性能数字标注口径限制
- [ ] 所有TEE数据标注TCB 0xA003+链下验证
- [ ] 所有DA数据标注dataHash原像检查，非点值证明
- [ ] 所有第三方比较标注"机制基线非官方实现""组件测试非主网吞吐""端点语义不同"

### 9.3 禁止表述检查

- [ ] 无"恢复降低延迟""首创第三方接续"
- [ ] 无"完全去信任""解决全部TEE风险""优于所有Rollup"
- [ ] 无"快N倍""省X%"跨协议领先声明
- [ ] 无"生产环境已验证""高频DApp TPS""payload扩展保持吞吐"
- [ ] 无"TeeRollup基线是OP/Arbitrum""BoLD 10×是跨协议领先"

### 9.4 边界标注检查

- [ ] 本地Hardhat口径限制（7条）完整标注
- [ ] TCB 0xA003非UpToDate标注
- [ ] 链下Quote验证标注
- [ ] Sepolia Blob blocked标注
- [ ] DA披露非点值证明标注
- [ ] 链上DCAP验证blocked标注
- [ ] 协议层防重放不覆盖TEE硬件防回滚标注
- [ ] 依赖L1终局性不提供跨重组额外保证标注
- [ ] 有界模型（至多128步）非通用EVM Rollup标注

### 9.5 去重检查

- [ ] 摘要/引言/结论中的贡献段落无重复
- [ ] 摘要/引言/结论中的创新点表述一致

### 9.6 引用完整性

- [ ] TEEROLLUP[1]标注@2787
- [ ] opML[新增]标注@2863
- [ ] optimistic fraud proof标注@2870
- [ ] Dynamic Fraud Proof[6]标注@3007
- [ ] LazyLedger[7][8][9][10]标注@3099
- [ ] 所有[1]-[12]与正文对应

---

## 10. 修订后的交付清单

完成本指南所有修订后，应生成以下文件：

### 10.1 修订后的论文

- `Hybrid_TEE_Rollup_返修稿_20261028.docx`

### 10.2 修订说明

- `manuscript_revision_log_20261028.md`（记录每章修改摘要）

### 10.3 检查清单

- 打印本指南§9，逐项核对并标记完成

---

## 11. 后续工作（本轮不要求，供参考）

1. **补齐blocked项**：Sepolia Blob、链上DCAP、UpToDate TCB、BoLD/TeeRollup运行
2. **形式化证明**：TLA+/Kani/Certora模型检查
3. **生产部署**：安全审计、主网测试、监控告警
4. **经济修复**：解决C11友好挑战经济缺陷

---

**文档结束**

修订工作执行顺序建议：
1. 先读原稿，标注需修改位置
2. 按章节顺序逐段修改（摘要→§1→§2→§3→§4→§5→§6→参考文献）
3. 每章修改后核对§9检查清单
4. 最后通读全文，确保一致性与流畅性
5. 提交前再次核对禁止表述清单（附录A）
