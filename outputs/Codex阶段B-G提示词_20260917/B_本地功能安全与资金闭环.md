# 阶段 B｜给 Codex：本地功能、安全与资金闭环

请直接实施本阶段，不只给计划。先读同目录`00_总控与阶段A交接.md`；以下内容也可单独复制执行。

## 1. 任务与边界

工作区：`/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup`。

用户已完成阶段A，交接起点为`outputs/stageA_20260916T162724Z/stageA_freeze/manifest/run_manifest.json`。请重新读取当前文件确认。复用`evm/revision/experiment_config.js`、`freeze_experiment.js`、`experiment_record.js`及schemas，不另造不兼容记录器，不覆盖A或历史run。

本阶段目标：在本地Hardhat上确认或补齐“提交→挑战→响应→确定性裁决→资金结算→提现”的可验证闭环；列明哪些错误在提交前拒绝、哪些可客观反证、哪些只能按超时归责。允许针对发现的缺陷作最小合约/测试修复，但不得改测试来迎合漏洞。

不要实现真实TEE、广播交易、接入实际DA或全新通用VM。默认沿用至多128步确定性重算模型；traceRoot若仍是有序向量承诺，不能称Merkle单步证明。DA/真实TEE未实现的专属case应移交D/E，而不是伪造通过。

禁止reset/clean、覆盖用户成果、自行commit/push、写出秘密。所有故障只在本地授权环境。每次代码变更后重新冻结用于测量的源文件及配置，不能沿用A旧哈希。

## 2. 开始前：识别权威实现和继承接口

只读检查当前Git状态、A manifest/config/schema和以下实际存在的文件：

- `evm/contracts/BoundedTaskRollup.sol`：主实验入口候选，核对constructor、状态、权限、挑战、裁决、deposit/withdraw。
- `evm/contracts/HybridTEERollup.sol`：如为legacy仅用于旧反例，不能混入新结果。
- `MockTEEVerifier.sol`、`MockDARegistry.sol`：只作受控后端。
- `evm/revision/hardhat.config.js`、`security.test.js`、`random_security.js`、`legacy_counterexamples.js`。
- A的record函数与CLI帮助，确认真实签名和REVISION_RUN规则。

写出authority inventory：合约、程序模型、接口、生产/实验角色、源码hash、信任假设、哪些结果已存在且不重造。必须从接口生成case，禁止臆造已有`challenge()/settle()`方法。

已读当前有界实现的特别基线：respond为optional diagnostic；已OPEN且未SETTLED时，adjudicate无时间门槛地确定性重算并结算；terminate超时仍按计算结果判责；未挑战SUBMITTED走挑战窗口后的finalize，错误任务已有转零地址及totalBurned记账。recover只更新受限计数和timeout，不改变challenger/收益人。先确认当前源码仍如此，不把可选回应当作离线即可罚没的义务，不以实验目的修改收益权或新增burn。

如果当前代码与A源树不同，记录差异，保留A基线，建立新stage-B run。扩展字段须新schema/profile，旧A样本继续能用旧验证器验证。

## 3. 实现步骤

### B1：统一测试fixture与独立参考模型

建立或扩展本地fixture：诚实提交者、诚实挑战者、接管者、未授权地址、恶意接收者合约。账户使用Hardhat开发账户，不导出私钥。

写独立参考计算/资金模型：输入相同但不直接复用待测合约输出作为expected。固定seed、任务nonce、输入、程序版本和预期轨迹；标注mock证明与真实签名的差别。

逐事件保存taskId、争议标识、状态、调用者角色、转移前后余额和交易receipt。对revert保存error selector、调用参数摘要及状态未变断言；错误堆栈脱敏。

### B2：先跑旧回归，再修复再重跑

先执行已有相关测试作为before基线；记录commit/sourceTree、测试命令和退出码。对失败给最小反例，定位源文件/函数。

允许修复：域分离、任务唯一性、验证顺序、权限、终局幂等、托管账本、提现重入、错误裁决条件等最小缺陷。涉及经济分配或timeout胜负规则时先列旧规则、改动依据与影响；有两个不等价协议选项而用户未选择时暂停该项，不静默改变信任模型。

每项修复须新增会在旧实现失败的回归。禁止跳过断言、统一返回成功、以观察者自报错误直接罚没、使用管理员任意指定赢家。

### B3：客观裁决与责任映射

建立机器可读case matrix，至少包含：caseId、前置状态、注入动作、expectedOutcome、expectedFaultOwner、expectedAccounting、evidenceKind、实际断言、证据路径。

分组：

1. 提交前无效签名/编码/证明→拒绝，不创建活跃任务；不要求已有押金被罚没。
2. 已接受的错误计算承诺→可验证反证→确定责任与经济结果。
3. 承担应答义务的一方在期限内不回应→客观超时→协议指定结果。
4. 挑战无效/挑战者失联→按明确保证金规则结算；不能锁住诚实提交者。
5. 尚无协议内DA义务→标记deferred_to_E；不能拿Mock setter改变available字段当DA罚没已经实现。

### B4：资金闭环与经济合理性

明确定义locked、claimable、已支付、协议留存/费用、罚没分配各自是不重叠账户还是视图。按任务和全局两层对账：

- 累计受控入金 − 累计外付 = 该测试范围内合约资产净变化。
- 内部负债总额不超过可用合约资产；正常fixture里应精确相等，强制转入等额外资产单独归类。
- 单任务抵押不能被其他任务扣除/重复使用。
- slash改变责任方权利，随后受益人实际withdraw才算资金支付完成。

外部EOA余额变化需扣除实际测试交易gas或转用合约账本作为主要断言；押金退款、罚没赔付不是系统资源费用。保留integer wei，BigInt序列化为十进制字符串，不用JS浮点。

检查自挑战和提交者/挑战者同控制人：只在两个自有地址间转移押金可能不是经济惩罚。报告净收益与协议允许条件；不要强制引入未定义burn，也不能将任意转账宣称抗串谋惩罚。修复仅限预先定义的经济政策。

### B5：产物与阶段C交接

输出API/状态表，列出每个操作、调用者、前置条件、时间条件、状态变化、资金变化、可复用证据。协议原生超时在B测试正确性，复杂恢复/对抗调度交C。

提供一条可重跑本地完整B套件的实际命令。先核实Node/Hardhat版本和参数，不把新脚本文件名当作已经存在。优先修改现有测试，新增测试文件仅在职责明确时使用。

## 4. 最低验收用例

| ID | 用例 | 必须验证 |
|---|---|---|
| B01 | 正常任务终局及提现 | 初态/终态、每笔账本、实际支付、无重复支付 |
| B02 | 错链/错合约/错task nonce的签名 | 拒绝；无活跃任务和抵押污染 |
| B03 | 未授权respond/step | 拒绝且状态/账本不变 |
| B04 | 改写输出/轨迹/步数 | 独立计算反证导致确定裁决，或提交前拒绝 |
| B05 | 错误证据或自填赢家 | 不能改变客观裁决 |
| B06 | 挑战截止前、等于、后一单位 | 规则与实现一致；按代码时间单位测 |
| B07 | 重复提交/挑战/resolve/finalize/withdraw | 明确revert或幂等，不重复锁定/支付 |
| B08 | 已终局任务旧证据重放 | 不重开、不回滚、不再次罚没 |
| B09 | 恶意接收者回退/重入 | 其他任务可进行；可提现权不丢失；无重入收益 |
| B10 | 多任务并行与资金隔离 | 每任务及全局守恒 |
| B11 | 自挑战及串谋转移 | 结果正确、费用流向和净收益明确，不夸大处罚 |
| B12 | 输入上限、0/1/最大/超步数 | 边界正确，不截断或无界循环 |
| B13 | legacy反例重放到新入口 | 历史漏洞不复现；旧入口隔离 |
| B14 | Mock证明/DA与未实现接口 | 真实边界不被冒充，缺口交D/E |

有界模型没有Merkle区间时，不设置虚假“区间缩小pass”。参数上限从实现读取，不照抄历史常量覆盖当前版本。

## 5. 记录、负例和恢复运行

复用A样本三元身份、UTC、null原因和证据相对路径。将测试assertion的pass与预期场景rejected区分。自检用的fail样本与真实测试失败放不同experimentId，不从fail行总数直接得出协议测试失败。

若A尚不容纳状态/余额详情，用evidence JSON存储；正式增字段须versioned extension，不能关闭validateEveryRecord。

至少保存before/after报告、revert状态摘要、角色地址、任务参数、receipt、账本快照、负例最小复现、实际命令。不要仅输出“23/23”；case数量以本轮实际case清单为准。

## 6. 阶段B完成标准与最终答复

B-completed要求：所有本阶段适用的安全/资金断言通过；所有合约变更有回归；任何明确可归责违规都有资金分配及提现证据；无已知可盗取资金/重复结算缺陷；C需要的状态/权限/接口已公开。

未实现DA强绑定和真实TEE不会单独导致B失败，但必须明示不是B已验证能力。核心安全缺陷未修复则stage failed/partial，受影响C/F不得放行。

交付新run下handoff.json、case_matrix.json、raw/、validation/、summary.json、report_zh.md与实际复现入口。答复包括：修改文件、前后行为、B01–B14结果、资金守恒结论、当前实现的可信边界、新源码/配置hash、进入C条件。不要修改论文、不要commit/push，不要宣称生产审计完成。
