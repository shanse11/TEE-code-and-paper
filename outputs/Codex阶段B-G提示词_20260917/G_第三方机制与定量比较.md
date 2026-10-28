# 阶段 G｜给 Codex：TeeRollup、Arbitrum、Optimism 的公平比较

请在`/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup`执行本阶段的来源核对、可复现基线与分析，不只列相关工作名称。先读同包总控及F comparability contract，按子组依赖放行：F-local及其comparability contract验收通过即可做G-mechanism，F整体partial不阻塞此层；G-source、G-feasibility和官方组件自身复现可独立开展，但与本文进行量化优势比较须等待对应F子组验收。只将缺少匹配前置的比较项标blocked，不阻塞整个G。

## 1. 前置、范围与完成层级

用户已完成A，起点：`outputs/stageA_20260916T162724Z/stageA_freeze/manifest/run_manifest.json`。复用当前配置/schema/证据约定，读取B–F实际handoff，不把旧run或论文引用中的数字当本轮实测。

阶段层级：G-source来源与机制核对；G-feasibility官方实现可复现性；G-mechanism同模型机制微基准；G-official实际官方实现/实验artifact；G-literature不可复现项的原文定量资料。各层分别标结果，不以文献表替代同环境复测。

必须覆盖TeeRollup（TEEROLLUP）、Arbitrum和Optimism三个目标，不能以自制简化OP合约冒充官方实现。争取至少一个官方可运行争议/提交路径，优先有可复现artifact的最近工作；若全部不可运行，诚实标G定量回应partial。

只允许合法访问公开来源、自有本地devnet。不得执行未经检查的远程安装脚本、请求新付费资源或公开网络压力/交易，除非单独取得授权。不改主协议来适配对方好看指标、不commit/push、不改论文正文。

## 2. G1：来源和版本锁定

已有入口仅供定位，不预断言最新或正确版本：

- TeeRollup: Efficient Rollup Design Using Heterogeneous TEE：`https://arxiv.org/abs/2409.14647`。
- BoLD: Fast and Cheap Dispute Resolution：`https://arxiv.org/abs/2404.10491`。
- Optimism Fault Dispute Game：`https://specs.optimism.io/fault-proof/stage-one/fault-dispute-game.html`。
- 既有项目材料：`revision_runs/20260911T095029Z/audit/citations_zh.md`、`external_research/comparison_report_zh.md`，均须回源核对。

检索官方论文、spec、官方仓库、实验artifact和部署配置。保存题名、作者/组织、URL、版本/commit、发布日期、访问时间、页码/章节/表号、原始单位和威胁模型。网络访问失败标blocked，不凭训练知识补数值。

区分历史论文原型、当下官方实现和某条生产链的部署参数；固定版本后比较，不能把不同版本优点拼成一个对手。fork/community实现必须标来源，不自动视为官方。

针对相关工作中的opML、Dynamic Fraud Proof、LazyLedger可补就近引用来源表，但它们不是此次必须完整复现的三个主目标，不扩大到无界文献综述。

## 3. G2：先做机制和可比性矩阵

每方案列：

- 计算/状态模型：有界hash任务、小型VM、通用EVM等；
- 执行信任：TEE类型/阈值、诚实观察者、验证服务、密钥/回滚处理；
- DA载体与可用性/持久性假设、谁承担披露义务；
- 正常提交内容与成本范围；
- 争议触发、参与/接管资格、已有争议如何继续、超时/计时规则；
- 证据形式、最坏计算/交互、链上最终裁决；
- 提交确认、应用可用、挑战关闭、最终结算、提款定义；
- 恢复状态、经济处罚和终止所需假设；
- 信息来源与证据级别。

字段使用supported / not_supported_with_source / not_verified / not_applicable等清晰标记。没有找到材料只能not_verified，不能填“不支持恢复”。必须认真核对对方已有动态争议图、第三方继续参与和超时接续机制，不能遗漏后宣称本方案首创。

将本文候选差异写成可检验问题，而非预设优越：固定争议事实的接续状态是什么、期限上界和攻击者成本是什么、恢复者需哪些数据/权限、增加多少提交/存储/证明开销、在哪种故障分布下受益。

## 4. G3：建立三个独立比较层

### L1 同计算模型机制微基准

输入、计算步数、字节、批大小、并发、编译器、硬件、链环境和故障位置一致，比较本方案恢复与无恢复/不同裁决路径。使用F实际测量记录和同口径runner，不能重用历史5样本结果充当新正式实验。

可实现小型基线，但必须命名为mechanism baseline而非Arbitrum/Optimism/TeeRollup原系统。不许只给本方案独立TEE/DA保障而去掉对照必要工作，仍宣称同等安全。

### L2 官方实现或artifact复现

对每个目标制作feasibility清单：官方URL/commit、许可证、依赖、硬件、需要完整rollup node还是可运行孤立争议合约、VM/证明artifact、离线/本地可行性、资源成本及缺口。

优先选择可验证范围：

1. 官方仓库提供的单元/集成fixture、争议game或提交路径微基准；
2. 论文提供的artifact与原始配置；
3. 若完整节点可运行且经批准，再做本地devnet端到端。

必须使用官方代码和其合法生成的证明/输入，不把简化自写程序贴官方名称。仅跑单元fixture就标component benchmark，不代表整条Rollup TPS。需要修改官方代码时保留patch/hash与原因，标modified-official并分清是否改变安全语义。

执行前检查脚本、依赖和授权范围；在隔离目录固定依赖和镜像版本，不全局安装、不改项目已有锁文件、不盲目执行curl管道脚本。复制仓库或使用公开安装资源属于此阶段实施，不是本轮提示词已经做过。

记录实际命令、环境、退出码、成功/失败和原始样本，产物沿A身份和新profile关联。没有真实命令验证就不能给“已复现”的说明。

### L3 文献定量表

不可运行的指标从原文提取，保留原始环境、网络、任务模型、指标定义、样本量/未报告、数字、单位、页码/图表号。明确literature_reported，非本机实测。

来自图的估读值注明估读方法/误差；原文不报的字段null+not_reported，不从别处猜。不可比数值保留原始语境，不能拼成一张胜负排名表。

## 5. G4：统一四类主比较指标

### 提交成本

分开正常提交gas、DA gas/字节、验证gas、链下证明/TEE时间和实际网络货币费用。批/task/transaction三种分母不混用。共享固定成本分配规则一致。A/Hardhat只有gas不能与第三方生产美元账单直接算领先比例。

### 挑战轮数

先冻结定义：逻辑交互轮、单方move、L1交易数、DAG edge数是不同计数。实际测交互序列并输出字段映射；不能把二分理论log值和完整官方交易数直接相除。无挑战正常路径也单列。

### 恢复能力

复用C故障模型：谁失联、在哪一步、第三方能取得何种证据、能否接管、保留何种状态、最大恢复/延迟、最后责任方和资金结果。不能将本方案“超时终止”与对方“无需接管自动继续”用单一yes/no排名。

### 结算延迟

提交纳入、挑战窗口、证明生成、争议解决、协议终局、bridge提款可用分别报告。自定义较短测试窗口只证明流程，不能和对方生产挑战期比“快N倍”。短参数devnet与规范/部署参数上界分表。

其余吞吐/尾延迟作为补充：同工作负载和计时口径才计算差异，混合环境仅描述。安全假设不同要另栏，不以单一性能指标证明整体更优。

## 6. G5：统计、来源审计与结论

配对比较只在L1或真正对齐的L2配置上执行，复用F独立run、预设尝试/超时、失败与右删失、CI方法。记录原始指标和相对差异公式方向，分母0/样本不足则不计算。

给每个比较行一个comparability标签：comparable / partially_comparable / not_directly_comparable以及理由。固定价格参数重价属于modelled scenario，文献/观测/模拟/实测分层，禁止跨层生成统一百分比。

新增claim-evidence表：结论文本、方案/版本、指标、来源行、raw/文献页码、可比级别、限制。所有“优于、降低、首创、无需信任”等词必须有证据；数据不支持优势时写出负面或相当结果。

## 7. 必须交付与自动检查

建议在当前G run内交付（按已有项目规范调整）：

- sources.json：官方来源、版本、定位、抓取/访问状态；
- mechanism_matrix及feasibility：三目标均有条目和未知项；
- raw/official、raw/mechanism、literature分层数据；
- metric_mapping、comparability_contract、claim_evidence_matrix；
- 分开的机制微基准表、官方组件/devnet实测表、文献数字表与绘图脚本；
- handoff.json、实际重现命令、report_zh.md和供作者回填的引文定位建议，不直接改论文。

自动检查：每个数值有origin/单位/分母/版本/来源；literature没有冒充measured；未运行不填0；所有三目标都覆盖；缺失source或raw链接报错；不同finality/round单位的行不会被自动合并；F重复/失败/删失样本规则一致。

G-completed不能仅以文献检索完成定义。分层报告已完成程度：若无官方实现复测，G-official=blocked，专家定量对照诉求至少partial；仍交付机制对照和可靠文献表，不捏造结果。

最终回答：每目标版本与复现层级、实际运行命令及结果、四类指标差异、哪些能直接比较、哪些不能、本文候选贡献是否得到支持、证据路径和后续缺口。资源有限优先给最有证据的有限结论，不再无界拓展实验。
