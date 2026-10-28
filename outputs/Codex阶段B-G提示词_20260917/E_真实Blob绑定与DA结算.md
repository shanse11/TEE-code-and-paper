# 阶段 E｜给 Codex：真实 Blob、独立取回、任务绑定与 DA 结算

请在`/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup`实现并验证本阶段，不只写计划。先读同包总控与B/C实际handoff。A起点为`outputs/stageA_20260916T162724Z/stageA_freeze/manifest/run_manifest.json`，复用配置/记录机制，不覆盖A。

## 1. 完成层级与安全边界

E分层交付：

- E-local：真实密码学离线编码/KZG及本地绑定、披露与资金测试。
- E-public-transport：实际type-3发布、链上确认、独立取回、真实receipt费用。
- E-binding：合约对被承诺任务、输入、程序和DA载荷有可裁决关联，不只是事件并列。
- E-DA-settlement：预先抵押的责任方在窗口内披露或客观超时被结算，并实际提现。
- E-integrated：取回同一真实批次的数据用于同一任务挑战/恢复/结算，串起B/C及可用的D后端。

E-public-transport通过不代表其余层级通过。D未就绪可用明确标注simulated TEE+real Blob测试E，不能称全真实TEE/DA端到端。

不对公网实施DoS、真实数据破坏或恶意审查。主网默认禁用。任何部署/交易广播前列出目标网络/chainId、钱包公开地址、合约版本、交易和Blob数量、费用上限、测试币余额及最大重试数并取得批准。缺RPC、测试币、端点或批准时只做E-local和dry-run，不随机创建钱包、不绕过链身份检查。

## 2. 必读代码与A继承

核对`BlobBatchAnchor.sol`、`BoundedTaskRollup.sol`、`blobcodec.js`、`kzg.js`、`blob_offline.js`、`blob_publish.js`、`blob_fetch.js`、`blob_verify.js`、`blob_receipt.js`和`blob_challenge_settle.js`的当前实现。

旧challenge/settle脚本标NOT_IMPLEMENTED不能直接改status通过；需真正实现方法、状态和经济闭环。链下重算并列hash不是强绑定。禁止臆造现成ABI，生成和部署均来自真实源码。

A中encodedBytes已是域编码字节：`ceil(frameBytes/31)*32`；单Blob可容4096×31=126976帧字节，实际物理长度131072字节，业务容量还要减frame/task头。A当前只支持单Blob，超容量标blocked。真实模式需新增profile/schema承载chainId、部署、费用字符串与网络证据，不能关闭A校验或伪装31337。

## 3. E1：可逆编码、容量与内容承诺

先固定manifest版本：域、chain/contract或协议身份、batchId、task数量与顺序、每task原始长度、程序版本、input/output/trace承诺、分片位置、Blob顺序、编码版本。明确哪些字段属于有界任务计算输入，哪些只是压力载荷；输入只有hash时不能假称VM实际执行了全部大载荷。

避免循环承诺，先定义单向构造顺序：原始任务数据（不含任务摘要/manifest）→inputDataHash→不含DA引用的taskCoreDigest（域、task/nonce、程序、input/output/trace）→含coreDigest的manifest及帧→KZG commitment/versionedHash→最终签名envelope(coreDigest,DAref,manifestHash,epoch/expiry)。coreDigest不可包含本帧manifestHash或自身Blob的versionedHash；输入数据hash不能对包含coreDigest的整帧再次取hash并倒灌。versionedHash在编码后、广播前可离线计算，不必等receipt。若anchorId只能链上产生，采用预先确定的batch标识同交易原子关联，或明确两步precommit/finalize-binding；未完成绑定的任务不得进入依赖DA的确认/结算。证明任务摘要包含在Blob与最终签名绑定DA两项各自验证，防循环、自引用和替换。

每批保存payloadBytes、frameBytes、fieldEncodedBytes、填充分类、blobCount和manifest哈希，全部来自实际序列化而非估计。

多Blob策略二选一并记录：

1. 保留单Blob能力，只选可容纳矩阵；超容量样本explicit blocked，不把失败样本从分母消失。
2. 实现多Blob分片与重组，绑定片序号/总片数/批次，按每片头部计算真实容量；逐BlobKZG验证，禁止少片、重复片、调序和跨批拼接。

不为了凑齐1/8/32矩阵自动缩小每任务载荷。至少覆盖容量下界、刚好上界和超一字节，编码解码hash一致及畸形长度/域元素/任务头拒绝。trusted setup记录来源和hash，库版本可复核。

## 4. E2：合约任务绑定——先本地再公网

制定并实现显式绑定协议，推荐同一个type-3调用中锚定并注册受其约束的任务，或由核心验证并消费规范锚点；锚点所有者、用途、批次、索引、可复用/不可复用规则均可校验。

必须分别解决两个证明义务：

- M1：核心task摘要确实出现在该versionedHash对应Blob的规范manifest中。
- M2：manifest承诺的payload/input/trace与Blob中实际数据一致，且足以裁决计算。

可选的有界实现路线：规范manifest字段编码为明确的field elements，用KZG求值证明将字段连接到Blob；再在有界数据挑战中披露指定任务的数据与其位置/一致性见证，重算任务承诺，并交B/C确定性验证器裁决。包含证明、数据披露和计算裁决不可混为一个证明。

KZG point-evaluation证明的是指定域点的多项式值，不是任意byte offset包含证明。必须明确roots-of-unity/evaluation索引、field packing、跨field字段、字节序和域分离，使用已验证库/参考向量。不要假定现有通用frame布局能用少量点证明验证任意任务；先用最小有界任务实现pack→真实Blob→证明生成→本地合约验证的往返测试，核对domain/tag、偏移、字段大小端和边界。未通过这一测试禁止广播依赖该绑定的任务，先报告E-binding=partial。每一个在裁决中有意义的payload字段都需被承诺约束；仅证明manifest摘要存在不能证明所有载荷都匹配。

如果完整一致性依赖诚实观察者发起反证，说明它如何取得足够数据、提交何种合约可验证的证据、窗口和最大gas，属于optimistic binding而非提交时全量验证。若只能链下比较、无客观裁决路径，则E-binding=partial，不称强绑定。

不把全通用ZK/新VM当默认方案。不足以给出有界可执行M2时，应先实现和报告E-public-transport及本地绑定原型，明确阻塞，而不是删掉M2验收。

## 5. E3：DA披露义务与可归责罚没

默认选择“提交者作为最后披露责任方”，除非已有用户确认的抵押DA服务。不要无授权引入外部服务商责任。

任务接受时写明披露数据范围、截止、保证金、最大挑战数、补偿/退款/罚没分配和最终保障窗口。保障应覆盖挑战及有限恢复；历史Blob不保证永久取回，归档策略另计成本与信任。

挑战者指定任务/范围并付约定保证金；责任方在固定时限内公开足以继续验证的数据及与承诺一致的证明，或进入确定性timeout结算。只交KZG proof/摘要/“我持有”声明不能替代数据可获得性。

有界任务可以calldata作为兜底，但需证明披露的数据受原承诺约束，限制总字节/证明数，测最坏gas；大任务分块须有总体上限、覆盖/重构条件和最终出口。随机抽样不等于完整可用性证明，若用抽样必须量化假设与错误概率。

某RPC下载失败不能直接作为罚没证明；可客观处罚的是已抵押方未履行协议披露义务。Blob过期、公共endpoint故障、责任方拒绝分别记。

将DA状态与计算裁决/终局资金互锁：DA披露义务尚未终结时，不得从原adjudicate/finalize/withdraw路径先退清承担该义务的抵押；DA结果与计算结果的合成及优先次序必须确定。同一task只有一次总账收口，双争议不能重复罚没同一份抵押。新增披露窗口必须可装入固定总预算，不能无限续期。资金遵循B会计模型，提现前后链上证据齐全；合约变更后重跑B/C。

## 6. E4：真实发布、独立取回和续跑

执行前从官方网络/客户端/RPC资料确认当前type-3与完整Blob取回接口、链身份、费用字段、保留策略、单交易/区块约束；保存来源与版本，不硬编码过时协议上限，不假设普通Beacon节点能返回所有完整Blob。

开发dry-run：真实序列化、KZG、ABI、chainId校验、预计调用、费用预算；不签发可泄露的raw交易到公开报告。确认批准后部署、广播有限交易并持久化已发送txHash/nonce。

状态机至少区分prepared/broadcast/mined/confirmed/fetched/verified/challenged/settled/withdrawn/failed，进程重启先查已发送交易状态；不重复广播导致双扣费。RPC错误重试有总次数/费用上限，费用超预算停止。

独立观察者只接收公共定位信息，不挂载发布者原始Blob目录；用不同进程/存储和可说明独立性的endpoint获取。验证区块/tx/Blob索引/versionedHash/KZG及规范解码，重算manifest和task对应关系。保留节点来源、响应摘要/原始数据受控副本、字节数、时间和请求失败。

收到reorg/过期/数据缺失时按确认政策标记，不凭孤块receipt宣称最终。跨端点取回失败说明观测范围，不外推整个DA网络失效。

用实际取回的同一任务数据构造挑战，执行C恢复/超时、B经济结算和真实提现；若只有本地链完成罚没，public-settlement单独标not_run。

## 7. 最低case清单

| ID | 场景 | 验收 |
|---|---|---|
| E01 | 离线正例和容量边界 | 可逆、KZG正确、长度和填充正确 |
| E02 | 公网type-3且正确引用blobIndex=0 | receipt、event与实际versionedHash对应 |
| E03 | 独立获取正确批次 | 不读本地发布文件，内容全链验证 |
| E04 | Blob A配task/manifest B | 核心拒绝或有效反证裁决，不只是脚本告警 |
| E05 | 错索引、无关anchor、旧batch复用 | 合约约束用途和上下文 |
| E06 | 内容改动、重算KZG但原task未改 | 能区分新Blob合法与原任务不一致 |
| E07 | 只改payload保持manifest | M2路径可裁决，不仅M1通过 |
| E08 | 多Blob少片/重复/调序/跨批拼接 | 若支持则拒绝；不支持标blocked |
| E09 | 责任方按时补发 | 接管者可继续验证且责任账本正确 |
| E10 | 责任方超时、重复DA挑战/恢复 | 固定期限、有界义务、实际扣罚/退款/提现 |
| E11 | RPC失败/保留期过期 | 不自动罚没无责任外部方，原因准确 |
| E12 | 观察者崩溃和恢复 | 从公共信息/持久记录继续同一任务 |
| E13 | 广播后崩溃/reorg/nonce冲突 | 续跑不重复支付，重组状态准确 |
| E14 | E与B/C/D联调 | 同task链条、真实和模拟部分明确 |
| E15 | DA待决时直接adjudicate/finalize/withdraw；DA与计算争议交错 | 不提前释放责任抵押、不双罚/双付，有固定终局出口 |

## 8. 费用与交付

receipt逐交易保存gasUsed、effectiveGasPrice、blobGasUsed、blobGasPrice，BigInt整数计算并序列化十进制字符串。totalExecutionFee=gasUsed×effectiveGasPrice，blobFee=blobGasUsed×blobGasPrice；字段缺失标null及原因，不用估算值冒充实付。

交易revert若已打包仍有gas费用；发送前拒绝无上链gas但可有链下开销。总成本不要重复加阶段归因成本，不把抵押转移计作燃烧。Sepolia币值不作为主网经济结论。

交付编码规范/向量、合约ABI与实际部署、绑定证明说明、本地B/C回归、每等级gate、授权范围、真实receipt和独立取回、资金事件、实际runner/重现命令、handoff.json、report_zh.md。公网receipt与Quote等受控证据公开范围明确。

本阶段只有各层完成才写E-completed；仅E-local或E-public-transport完成写partial并列出差异。提示用户需要提供的资源名称和最小权限，无秘密值。不改论文、不commit/push。
