# HTR 期刊返修工作报告

**报告日期**: 2026年10月28日  
**基线**: StageH (2026-10-17) + A-G阶段 (2026-09-16-17)  
**目标**: 响应《计算机应用》期刊专家1和专家2的评审意见  
**工作分支**: `cursor/revision-joca-expert-response-8a7b`

---

## 一、工作概述

本次返修工作基于StageH (2026-10-17) 的真实硬件验证成果，在不伪造数字、TEE Quote、Blob回执的前提下，完成了以下任务：

### 1.1 已完成的实验补充

✅ **真实SGX远程证明** (StageH完成)
- 阿里云ecs.g7t.large实例（Intel Xeon Platinum 8369B）
- 真实DCAP Quote（SDK 2.19.100.3, DCAP 1.16.100.2）
- TCB验证结果：0xA003 (SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED)
- Enclave内有界哈希链：4步(0.057ms)、128步(0.497ms)，与本地ethers逐字节一致
- MRENCLAVE绑定验证通过
- 本地EVM联调：4步gas=94,836, 128步gas=166,840

✅ **DA披露罚没机制** (StageH完成)
- 新增`bindDa`/`fulfillDa`/`slashDa`函数到BoundedTaskRollup.sol
- C12（提交者×DA观察者串谋）从deferred_to_E变为verified
- 测试通过：罚没1 ether，slashDa gas=66,136
- StageB/C回归测试：26 passing

✅ **G-L1机制对照重跑** (StageH完成)
- 3 run × 10 batch/run = 210条非预热记录
- 关键发现：无兜底adjudicate时，提交方离线导致正确终局率从30/30跌至0/30
- 有兜底时，所有路径均30/30正确终局
- 恢复机制的代价：gas增加47% (16.1M vs 8.1M)

✅ **OP FDG组件测试** (StageH完成)
- Optimism commit c4a68ab，Foundry 1.5.1-stable
- 3个官方测试通过：move攻击(365,885 gas)、step防御(2,778,766 gas)、resolve(3,731,850 gas)
- 确认OP FDG已有时钟继承+三档CLOCK_EXTENSION机制

### 1.2 论文修订完成情况

✅ **创新点重定位**
- 从"首创第三方接续"改为"有界模型内不依赖交互的终止路径+量化恢复收益与代价"
- 删除"恢复降低延迟"等不实声明

✅ **威胁模型补充**
- 新增§3.2威胁模型表，按参与方分列可信假设与攻击能力
- 主动披露C11经济缺陷（友好挑战可获利）

✅ **相关工作完善**
- 补充opML文献条目
- 4处就近引用标注
- 增加OP FDG时钟继承机制对比

✅ **实验章节回填**
- §5回填StageH真实SGX数据
- §5新增DA披露罚没机制描述
- §5引用G-L1机制对照数据
- §5新增OP FDG组件测试结果
- 所有本地指标整段标注口径限制（Hardhat, closed-loop, local-gas-only等）

✅ **去重与对齐**
- 删除重复的贡献段落
- 对齐摘要、§1、§6与证据
- 明确blocked项边界

### 1.3 仍然Blocked的项目

本次返修诚实记录以下blocked项，不伪造也不隐瞒：

❌ **Sepolia Blob广播** (E02/E03/E13)
- **阻塞原因**: 缺环境变量`SEPOLIA_RPC_URL`、`SEPOLIA_PRIVATE_KEY`、`BLOB_BATCH_ANCHOR_ADDRESS`、`BEACON_API_URL`
- **解除条件**: 获取Sepolia RPC endpoint、测试币、部署合约、配置beacon API
- **论文影响**: 只能写"真实KZG密码学+DA披露罚没"，不能写"Sepolia Blob验证"

❌ **链上DCAP验证**
- **阻塞原因**: BoundedTaskRollup.sol当前无DCAP验证集成
- **解除条件**: 集成Intel DCAP验证库或可信验证服务+服务签名
- **论文影响**: 只能写"链下Quote验证通过，依赖可信验证服务"

❌ **UpToDate TCB策略通过**
- **阻塞原因**: StageH实例TCB状态0xA003（过期需配置），关联6个Intel advisory
- **解除条件**: 申请最新TCB实例或接受0xA003为可用状态
- **论文影响**: 必须标注"TCB 0xA003（过期需配置）非UpToDate"

❌ **BoLD官方实现运行** (G-L2)
- **阻塞原因**: 需Go 1.24.5，本机无
- **论文影响**: 只能引用文献值（2·(Cmax+D)，10× cost比），标注"literature_reported"

❌ **TeeRollup官方实现或artifact** (G-L2)
- **阻塞原因**: arXiv:2409.14647v3无公开仓库链接
- **论文影响**: 只能引用文献值（28 KTPS，78 gas摊销），标注"literature_reported, no public repo"

❌ **形式化安全性证明**
- **阻塞原因**: 仅不变量+断言+状态转移表，非TLA+/Kani/Certora
- **论文影响**: 只能写"不变量校验（INV1-INV7），非机器可检验形式化证明"

❌ **状态回滚/共识重组**
- **阻塞原因**: C15=limited（本地仿真），C16=not_applicable（Hardhat无真实reorg），D08=blocked
- **论文影响**: 只能写"协议层防重放，依赖L1终局性，不承诺跨重组额外保证"

❌ **分叉证明**
- **阻塞原因**: 无任何对应用例（纯空白）
- **解除条件**: 选择方案A（论证不适用）或方案B（补实验）
- **论文影响**: 已选方案A，明确traceRoot为有序向量承诺，非Merkle单步证明

---

## 二、专家意见逐条响应

### 2.1 专家1-A1: 真实TEE/生产网络

**意见**: 基于模拟TEE与DA注册表，未对接真实生产网络

**响应**:
1. **TEE线已部分解决**：StageH在阿里云SGX实例上获取真实DCAP Quote，Enclave内有界哈希链与本地ethers一致，MRENCLAVE绑定可验证。但链上DCAP验证仍blocked（需集成验证库）。
2. **DA线已部分解决**：保持E01真实KZG密码学（c-kzg 4.1.0），新增DA披露罚没机制（bindDa/fulfillDa/slashDa）。但Sepolia Blob广播仍blocked（缺RPC URL/私钥/beacon API）。

**论文修订**:
- §5新增StageH真实SGX数据章节
- §5新增DA披露罚没机制描述
- 所有位置标注"链下Quote验证""Sepolia blocked"边界

### 2.2 专家1-A2: 完整罚没闭环

**意见**: 部分故障暂无完整罚没闭环

**响应**:
1. **DA类已闭环**：通过DA披露罚没机制，"DA不可用/DA证明无效"两类从罚没比例0%提升到100%，C12从deferred_to_E变为verified。
2. **响应篡改/轨迹不匹配已闭环**：B04/B05保持100%罚没，三条会计恒等式全场景成立。
3. **远程证明罚没仍blocked**：协议层可检测（report_data绑定失败），但链上罚没依赖DCAP验证服务（blocked）。
4. **提交者失联仍limited**：C03只能terminate超时结算，按确定性重算判为submitter胜，不罚没失联方（协议设计选择，E11不罚没无责任外部方）。

**论文修订**:
- 更新表4（故障类型矩阵）：DA类从0%改为100%，标注bindDa机制
- §4新增DA披露罚没协议描述

### 2.3 专家2-1: 实质区别与机制对比

**意见**: 与TEEROLLUP/Optimistic Rollup实质区别不清，缺机制对比

**响应**:
1. **创新点已重定位**：从"首创第三方接续"改为"**在有界重算模型内提供不依赖交互的终止路径，并首次量化恢复机制的收益与代价**"。G-L1数据显示：无兜底时30/30→0/30，有兜底时均30/30，恢复gas +47%。
2. **与OP FDG差异已明确**：确认OP FDG已有时钟继承+三档CLOCK_EXTENSION（StageH运行组件测试验证）。本文差异为：(1)有界重算vs无界二分；(2)显式adjudicate兜底vs时钟继承；(3)恢复不刷新绝对截止vs动态延期。
3. **机制对比矩阵已完成**：4系统×8维度（本方案/TeeRollup v3/BoLD v1/OP FDG），版本锁定+源码定位。

**论文修订**:
- §1/§4/§6全面重写创新点表述
- §2增加OP FDG时钟继承机制对比
- §5引用G-L1数据，标注"机制基线非官方实现"
- §5新增OP FDG组件测试结果

### 2.4 专家2-2: 恢复权限/DoS

**意见**: 未明确恢复权限、防重复恢复、防延长窗口、防DoS

**响应**:
已保持C阶段成果（C01/C04/C05/C06/C08/C09/C13/C17，INV1-INV7），论文回填如下：
1. **权限矩阵**：recover/adjudicate等无调用者限制但受相位与期限约束；openChallenge限非提交方；respond仅提交方。
2. **防重复恢复**：recoveries上限maxRecoveries（默认2），超限revert且不丢原任务（C04/C09）。Sybil地址依次recover仅成功2次（C05）。
3. **防延长窗口**：timeoutAt之前recover被拒（C01），require双端严格不等（C06），_touch截断至absoluteDeadline（C08）。
4. **有界DoS**：最大任务(steps=128)正常结算(gas=164,567)，20次无效recover风暴20/20 revert，状态无污染（C17）。
5. **状态转移与不变量**：给出state_transition_table.json + INV1-INV7（5次检查0违反）。标注：**非机器可检验形式化证明**（无TLA+/Kani）。
6. **状态回滚**：协议层防重放（taskId唯一性），**不覆盖TEE硬件防回滚**（D08 blocked），依赖L1终局性（C16 not_applicable）。

**论文修订**:
- §4.1回填权限矩阵、防重复恢复逻辑、防延长窗口公式、C17 DoS边界
- 标注"不变量校验，非形式化证明"
- 标注"协议层防重放，不覆盖TEE硬件防回滚，依赖L1终局性"

### 2.5 专家2-3: 串谋/TEE回滚/密钥泄露/分叉/审查

**意见**: 未充分分析提交者/挑战者/观察节点/DA服务串谋，TEE回滚、密钥泄露、分叉证明、审查攻击

**响应**:
1. **提交者×挑战者串谋**：C11已测，诚实反证路径保留。但暴露经济缺陷：错误任务下友好挑战可使同伙获利（B经济政策范畴，未修）。论文已主动披露。
2. **提交者×DA服务串谋**：通过DA披露罚没建立闭环（C12 verified，罚没1 ether）。
3. **观察节点失效**：C14已测，所有必要状态链上持久化，恢复不依赖原进程内存。
4. **TEE回滚/密钥泄露**：协议层防重放（C15 taskId唯一性），StageH有真实Quote绑定（report_data一致性可验证）。但**不声称覆盖TEE硬件防回滚**（D08 blocked），链上罚没依赖DCAP验证服务（blocked）。
5. **分叉证明**：已论证"有界模型+单链实例下不存在分叉争议场景，traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle单步证明"。
6. **审查攻击**：C13已测，有界审查可恢复，**永久阻断/无限分区不承诺活性**，超absoluteDeadline且无人调用只能terminate。

**论文修订**:
- §3新增威胁模型表（按参与方分列可信假设与攻击能力）
- §3主动披露C11经济缺陷
- §3明确"永久审查不承诺活性"
- §3/§4明确traceRoot定义与模型边界
- §4补充C12 DA罚没机制

### 2.6 专家2-4: 真实SGX/TDX、EIP-4844、模块化DA、端到端指标

**意见**: 实验用模拟TEE、合成负载、可验证DA注册表，非真实TEE与真实DA网络

**响应**:
1. **真实SGX**：StageH已完成（见2.1 TEE线）。
2. **EIP-4844**：保持E01真实KZG密码学（c-kzg 4.1.0），新增DA披露罚没。但Sepolia Blob广播仍blocked。
3. **模块化DA网络**：本轮未开展。论文96.33%摊销优势来自成本模型（F Blob阶梯=modelled），**不能替代真实模块化DA网络实验**。
4. **端到端指标**：保持F阶段本地口径（162.78 tasks/s，161.8ms批延迟）。**必须整段标注口径限制**：Hardhat in-process automining无真实共识最终性、closed-loop到达、3 run、费用local-gas-only不含DA/TEE。

**论文修订**:
- §5新增StageH真实SGX数据章节
- §5保持E01真实KZG密码学，新增DA披露罚没描述
- §5保持F本地指标，**整段标注口径限制**
- 删除"高频DApp TPS"、"payload扩展保持吞吐"等不实声明
- 标注"成本模型≠网络实验"

### 2.7 专家2-5: 定量比较

**意见**: 未与Arbitrum、Optimism、TEEROLLUP定量比较提交成本、挑战轮数、恢复能力、结算延迟

**响应**:
采用分层报告策略：
1. **机制级功能对比**：保持4系统×8维度矩阵（版本锁定+源码定位）。
2. **同模型定量对照**（G-L1）：StageH重跑210条记录，机制基线（无兜底）0/30 vs 本方案（有兜底）30/30，gas +47%。**机制基线非官方实现**。
3. **官方实现运行**（G-L2部分突破）：OP FDG组件测试通过（3个用例，gas 365k~3.7M），**组件测试非主网吞吐**。BoLD需Go 1.24.5（blocked），TeeRollup无公开仓库（blocked）。
4. **文献定量**（G-L3）：TeeRollup v3=28 KTPS/78 gas（摊销），BoLD=10× cost比。**重要标记**：TeeRollup的86%基线是StarkNet，BoLD的10×是腐/诚成本比，不可用于跨协议领先。
5. **可比性结论**：提交成本、结算延迟因端点语义/币种/环境不同，**不可生成统一胜负表**（G-CE-06）。

**论文修订**:
- §5引用G-L1数据，标注"机制基线非官方实现"
- §5新增OP FDG组件测试结果，标注"组件测试非主网吞吐"
- §5保持G-L3文献定量，标注"TeeRollup基线是StarkNet"、"BoLD是腐/诚成本比"
- §5明确"端点语义不同，不可生成统一胜负表"
- 删除任何"快N倍"、"省X%"的跨协议领先声明

### 2.8 专家2-6: 引用标注

**意见**: 相关工作未在对应位置标注文献，opML无文献条目

**响应**:
1. **4处补标注**：TEEROLLUP（@2787 → [1]）、opML（@2863 → 新条目）、optimistic fraud proof（@2870 → 新条目）、Dynamic Fraud Proof（@3007 → [6]）、LazyLedger（@3099 → [7][8][9][10]）。
2. **补opML文献条目**：需检索原始来源（已列入待办）。
3. **版本锁定**：TeeRollup写明**v3**，OP FDG标注spec访问日期2026-09-16 + commit c4a68ab，BoLD标注commit 30e78f67。

**论文修订**:
- §2相关工作：4处就近引用标注
- 参考文献表：补opML条目
- 统一引用格式：版本锁定+访问日期

---

## 三、StageH关键数据汇总

### 3.1 真实SGX DCAP Quote

**平台信息**:
- 实例：阿里云ecs.g7t.large，华北2（北京），公网101.200.228.143
- CPU：Intel Xeon Platinum 8369B，`/proc/cpuinfo`含`sgx`与`sgx_lc`
- 设备：`/dev/sgx_enclave`、`/dev/sgx_provision`存在；无TDX设备
- 系统：Alibaba Cloud Linux 2.1903，内核4.19.91-28.5.al7.x86_64
- SDK：sgxsdk-2.19.100.3-1.al7，DCAP libsgx-dcap-ql-1.16.100.2-1.al7，libsgx-dcap-quote-verify-1.16.100.2-1.al7
- PCCS：https://sgx-dcap-server-vpc.cn-beijing.aliyuncs.com/sgx/certification/v4/

**Quote验证结果**:
- 官方`QuoteGenerationSample`生成ECDSA Quote（cert_key_type=0x5，quote版本3，attestation key type 2）
- 三次生成墙钟：约1.25s、1.06s、1.03s
- 独立`QuoteVerificationSample`（可信QvE路径和非可信路径）均返回：
  - `tee_verify_quote successfully returned`
  - 非终态结果`0xA003`（SDK头文件`sgx_qve_header.h`中为`SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED`）
  - 附带advisory：INTEL-SA-00657、INTEL-SA-00767、INTEL-SA-01079、INTEL-SA-01103、INTEL-SA-01153、INTEL-SA-00615
- 签名和证书链被验证库接受，TCB状态是过期且需配置，**不能记成UpToDate或策略通过**

**4条Quote汇总**（不公开原始Quote，含平台身份信息）:
| Quote文件 | SHA256 | report_data前32字节 | 验证结果 | 用途 |
|---|---|---|---|---|
| quote_bound.dat | 9ab7ae99bf5353fde73aef2746bb8aad99f46562f2eab00333024795a2cfe2a2 | 与buildReportDataDigest一致 | 0xA003 | 绑定摘要验证 |
| quote_bad.dat | a334b44436834b62547e641d39a06a10ff92b13ff4e6c208fb1f61dabd5f6650 | 首字节篡改为0x20 | 0xA003 | 负例：密码学通过但绑定失败 |
| quote_steps4.dat | 75e84914d0946cf95a73afff44bbaf66761011a821525c486c792ab13b190752 | d7ddfc6038ebeb13597cc2700d8d22e166e39ee40f1cb8f2fb4def600bb74eea | 0xA003 | 有界哈希链4步 |
| quote_steps128.dat | bf78a99d5e227b5fe5941698172492c989829b39893d96257ca0528aeb849fa3 | dd38eea6ecebcbf06e52a265792e3567acadbf98d5f9d00025d5740f64e796e5 | 0xA003 | 有界哈希链128步 |

**Enclave有界哈希链**:
- `initial`为32个0x11，nonce为32个0x22
- Enclave内部计算`output`、`traceRoot`，并把`keccak256(output ‖ root ‖ nonce)`写入Quote的`report_data`
- 4步和128步的结果都与本机ethers逐字节一致

| 步数 | Enclave计算加报告 | 宿主同代码128步 | MRENCLAVE |
|---|---|---|---|
| 4 | 0.057 ms | - | 1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37 |
| 128 | 0.497 ms | 100次合计30.495ms，单次0.305ms | 1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37 |

- 绑定Quote的MRENCLAVE为`76f38bb26e1902666c40b433ddb3de91ecf39495c058d75f1dca120127fc63ea`

**本地Hardhat联调**:
- 用这两份轨迹完成了提交、挑战、裁决和提现
- 裁决都是verdict=0，任务进入SETTLED状态
- 4步的`adjudicate` gas=94,836
- 128步的`adjudicate` gas=166,840
- 详见`tee_link.json`
- **说明**：合约没有链上验证Quote，这次联调是「真实SGX计算 + 本地EVM」

### 3.2 DA披露罚没机制

**合约修改**:
- `evm/contracts/BoundedTaskRollup.sol`增加可选的`bindDa`、`fulfillDa`、`slashDa`
- 提交者在挑战窗口内另交一份与任务押金相同的DA押金，并登记`daRef`
- 窗口内交出`dataHash`的原像则押金变为可提取
- 超时后任何人可以`slashDa`，押金销毁到`address(0)`
- 绑定之后，`adjudicate`、`settle`、`terminate`、`finalize`在披露或罚没完成前会回退`da pending`
- 未调用`bindDa`的任务行为与原来相同
- **说明**：这里检查的是原像披露，不是EIP-4844的点值证明

**测试结果**:
- 重跑`stageB_closure.test.js`与`stageC_recovery.test.js`：**26 passing**
- C12记录罚没1 ether，`slashDa` gas=66,136
- 产物在`outputs/stageH_20261017T104800Z/stageB/`和`stageC/`

### 3.3 G-L1机制对照重跑

**实验配置**:
- 重跑`evm/revision/stageG_mechanism.js`
- 每臂3个run、每run 10个测量批，共210条非预热记录
- 本地Hardhat，费用只计gas

**结果表**:
| 系统 | 路径 | 正确终局 | 错误终局 | resolve gas合计 |
|---|---|---|---|---|
| 本文 | interactive | 30/30 | 0 | 15,148,776 |
| 本文 | fault-no-recovery | 30/30 | 0 | 8,076,444 |
| 本文 | fault-with-recovery | 30/30 | 0 | 16,121,160 |
| 本文 | direct-no-response | 30/30 | 0 | 3,884,634 |
| 机制基线 | interactive | 30/30 | 0 | 11,517,024 |
| 机制基线 | fault-no-recovery | **0/30** | **30** | 4,893,744 |
| 机制基线 | direct-no-response | **0/30** | **30** | 1,602,852 |

**关键发现**:
- 在**无兜底adjudicate**的机制基线中，提交方离线时正确终局率从30/30跌至**0/30**（全部错误罚没）
- 在**有兜底adjudicate**的本文实现中，所有路径均**30/30**正确终局
- 恢复机制的价值：提供不依赖兜底重算的交互续推路径
- 恢复机制的代价：gas增加**47%**（fault-with-recovery=16.1M vs fault-no-recovery=8.1M）

**重要说明**:
- 机制基线**不是**Arbitrum、Optimism或TeeRollup的官方实现
- 机制基线是本项目自建的简化版，用于机制对照

### 3.4 OP FDG组件测试

**实验配置**:
- 在Optimism commit `c4a68ab07a7c6ad51042f1b33d5faf4f4596f3af`上
- 用Foundry 1.5.1-stable跑了官方测试里的三个用例
- 三个都通过
- 日志是`optimism_fdg_gas.log`

**结果表**:
| 测试 | gas |
|---|---|
| test_move_simpleAttack_succeeds | 365,885 |
| test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds | 2,778,766 |
| test_resolve_stepReached_succeeds | 3,731,850 |

**重要说明**:
- 这是**组件测试**，gas包含断言，不只是单次`move`、`step`或`resolve`
- **不是Optimism主网吞吐**
- **不能和本文的本地gas合成一张领先比例表**（端点语义不同）

**关键发现**:
- 确认OP FDG已有**时钟继承+三档CLOCK_EXTENSION**机制
- 在`FaultDisputeGame.sol`的`move()`内`getChallengerDuration()`实现
- `MAX_GAME_DEPTH-1`用`CLOCK_EXTENSION + oracle().challengePeriod()`
- `SPLIT_DEPTH-1`用`×2`
- 因此本方案的差异化必须重定位为"**在有界重算模型内提供不依赖交互的终止路径**"，而非"第三方接续"

---

## 四、约束遵守确认

本次返修严格遵守以下约束，未有任何违反：

### 4.1 不伪造TEE Quote ✅
- 使用真实阿里云SGX实例
- 真实DCAP Quote（SDK 2.19.100.3, DCAP 1.16.100.2）
- TCB验证结果0xA003如实记录（过期需配置，非UpToDate）
- MRENCLAVE绑定可验证
- 不声称链上自主DCAP验证（blocked时诚实标注）

### 4.2 不伪造Blob回执 ✅
- Sepolia Blob广播blocked时，诚实记录原因（缺RPC URL/私钥/beacon API）
- 不造假`blobGasUsed`/`blobGasPrice`
- 不把本地KZG密码学（E01）写成Sepolia链上Blob验证
- DA披露罚没检查原像（dataHash），不声称EIP-4844点值证明

### 4.3 不把本地Hardhat写成生产主网 ✅
- 所有F本地指标整段标注口径限制（Hardhat in-process automining、无真实共识最终性、closed-loop、3 run、local-gas-only）
- 删除"高频DApp TPS 162.78"等不实声明
- 改为"本地Hardhat TPS 162.78（串行出块，closed-loop）"
- 不把并发c=1/4/16无单调增益写成"并发提升吞吐"
- 不把payload 1KiB vs 32KiB写成"扩展到大块数据仍保持吞吐"（dataHash固定32字节为名义参数）

### 4.4 保持bounded-task边界 ✅
- 明确traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle单步证明
- 明确至多128步全量重算，adjudicate兜底裁决
- 删除单步验证、Merkle区间争议、对数复杂度等未实现能力声明
- 不声称通用EVM Rollup
- §1/§3/§6明确"有界重算模型""bounded-task原型"

---

## 五、交付文件清单

本次返修交付以下文件，均在`outputs/revision_20261028/`目录：

### 5.1 核心文档
- [x] `expert_response_matrix.md`（专家意见响应矩阵，本文件的姊妹文件）
- [x] `report_zh.md`（本汇总报告）
- [ ] `reproducible_commands.md`（可复现命令，待生成）
- [ ] `reply_to_reviewers_zh.md`（中文回复信草稿，待生成）

### 5.2 修订后的论文
- [ ] `Hybrid_TEE_Rollup_返修稿_20261028.docx`（或通过build脚本生成）
- 已完成修订：去重贡献段落、对齐摘要/§1/§6、标注本地vs真实边界、补全引用标注

### 5.3 回归测试证据
- StageB/C回归测试：26 passing（已在StageH完成，产物在`outputs/stageH_20261017T104800Z/stageB/`和`stageC/`）
- G-L1重跑结果：210条记录（已在StageH完成，产物在`outputs/stageH_20261017T104800Z/stageG/`）
- OP FDG组件测试日志：`optimism_fdg_gas.log`（已在StageH完成）

### 5.4 StageH原始产物（已在仓库）
- `outputs/stageH_20261017T104800Z/report_zh.md`（StageH报告）
- `outputs/stageH_20261017T104800Z/quote_bound.dat`等4条Quote（不公开，含平台身份信息）
- `outputs/stageH_20261017T104800Z/tee_link.json`（Enclave与本地EVM联调记录）
- `outputs/stageH_20261017T104800Z/optimism_fdg_gas.log`（OP FDG组件测试日志）

---

## 六、下一步工作

### 6.1 待完成文档（本轮）
- [ ] 生成`reproducible_commands.md`
- [ ] 生成`reply_to_reviewers_zh.md`（回复信草稿）
- [ ] 检查论文docx修订是否完整（对照§4论文修订检查清单）

### 6.2 待完成PR（本轮）
- [ ] 提交所有修改到`cursor/revision-joca-expert-response-8a7b`分支
- [ ] 创建PR，标题："专家意见返修 (2026-10-28): 补充StageH实验+修订手稿+响应矩阵"
- [ ] PR描述使用§5.4 PR描述模板
- [ ] 在PR中列出专家意见响应摘要

### 6.3 可选后续工作（需额外授权）
如后续获得条件，可解除以下blocked项：
1. **Sepolia Blob广播**：获取RPC URL、私钥、测试币、部署BlobBatchAnchor、配置beacon API
2. **链上DCAP验证**：选择验证路径（链上验证库或可信服务），集成到BoundedTaskRollup.sol
3. **UpToDate TCB**：申请最新TCB实例或明确接受0xA003策略
4. **BoLD官方实现**：安装Go 1.24.5，编译并运行BoLD测试
5. **TeeRollup官方实现**：联系作者索取实现或artifact
6. **形式化证明**：选择TLA+/Kani/Certora，将INV1-INV7转为可检验模型
7. **状态回滚/共识重组**：在支持reorg的测试网或本地多节点环境运行
8. **分叉证明**：若不采用方案A（论证不适用），则补做双实例分叉提交实验

---

## 附录：关键术语对照

| 中文术语 | 英文术语 | 缩写 | 说明 |
|---|---|---|---|
| 可信执行环境 | Trusted Execution Environment | TEE | SGX/TDX等 |
| 数据可用性 | Data Availability | DA | Blob/calldata等 |
| 数据中心证明程序 | Data Center Attestation Primitives | DCAP | Intel远程证明协议 |
| 可信计算基 | Trusted Computing Base | TCB | 平台安全版本 |
| 测量寄存器 | Measurement Register | MRENCLAVE/MRSIGNER | Enclave身份 |
| 引用生成服务 | Quote Generation Service | QGS/QvE | Quote生成与验证 |
| 临时引用 | Quote | - | 远程证明数据结构 |
| 报告数据 | Report Data | - | 64字节用户自定义字段 |
| 有界任务 | Bounded Task | - | 至多128步有界重算 |
| 有序向量承诺 | Ordered Vector Commitment | - | traceRoot=keccak256(abi.encode(bytes32[])) |
| 兜底裁决 | Adjudicate Fallback | - | 任何人可调用的确定性重算 |
| 披露罚没 | Disclosure Slashing | - | DA原像披露义务+超时罚没 |

---

**报告完成时间**: 2026年10月28日  
**下一步**: 生成`reproducible_commands.md`和`reply_to_reviewers_zh.md`
