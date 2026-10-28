# 阶段 F｜给 Codex：性能、费用、统计与消融

请在`/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup`实施测量与分析，不只写实验设计。先读同包总控及A/B/C/D/E真实handoff。

## 1. 依赖、范围和数据真实性

A交接起点：`outputs/stageA_20260916T162724Z/stageA_freeze/manifest/run_manifest.json`。复用配置/记录器/schema及已有`performance.js`，不要重做A或覆盖旧run。A的并发矩阵为1/4/16，不从早先计划擅改1/4/8；需要其他点时另列新配置和原因。

B/C安全/资金缺陷未解决时，不测受影响路径的优势。F-local可在D/E真实资源缺失时运行，F-TEE须D真实应用验收，F-Blob须E相应层级验收，F-full须同一任务真实后端联调。不同组分别标completed/partial/blocked，不用Mock填空。

本阶段默认不改变协议机制，只修正仪器、调度器和统计错误；发现协议漏洞退回B/C/D/E并使受影响旧数据失效。任何代码或参数改变后先冻结新source/config哈希再测。

不部署主网、不自行付费/广播、不做公网压力攻击。公网采样需批准预算、尝试数和速率，使用用户授权网络资源。禁止自主commit/push、写秘密或修改论文结论。

## 2. 测量前必须冻结的设计

### F1：数据身份与记录扩展

读取A schema：每样本一逻辑批，taskCount=batchSize，吞吐numerator不超过该样本taskCount，事件须关联已有样本。不要把多个批次的任务总数塞入一条A样本。

实现versioned窗口聚合记录，引用所有sampleId及输入hash；窗口记录包含batchCount、distinctTaskCount、attemptCount、accepted/finalized/executed计数、失败/重试/删失、起止时钟与队列信息。保留旧schema验证，真实费用与backend仅在新profile可用。

耗时使用单机monotonicNs（字符串）计算；UTC用于跨进程关联并记录同步误差；区块timestamp是链时钟。evm_increaseTime/automining不能产生真实墙钟恢复或共识最终性结论。

### F2：计划与采样规则

先写实验设计配置，包括主要指标、矩阵、warmup、固定尝试数、独立run数、停止/超时/预算规则、失败处理和统计方法，再执行。不能观察初步结果后只留下效果好的格子。

推荐起点：3个独立run，每格每run先固定预热5批、再固定尝试30批，保留所有失败和重试。预热也记录但按预先规则不参与稳态统计；这是试验起点，不保证足以估计尾部/95%CI。根据先导方差预先追加样本并说明，禁止只收集到30个成功才停止。

公网以预算为上限，可较少且分时间块交错采样；样本不足则描述性报告，不凭少量样本给稳定p99或精确优势。

### F3：工作负载与实际批处理语义

默认矩阵：batchSize 1/8/32；payloadKiBPerTask 1/8/32；configuredConcurrency 1/4/16；执行步数在实际有界模型内选1/中间/最大，含超上限拒绝边界。先固定其他维度做单变量筛查，再对支撑主结论的组合预设交叉实验，不无限展开笛卡尔积。

每任务载荷和步数独立。若大payload只是DA传输填充而计算仅处理一个hash，明确标记，不把吞吐称高频DApp通用业务TPS。补一种落在实际模型内的可复现确定性应用样例；如果没有真实应用，只称合成微基准。

A定义frameBytes→31/32域编码→实际Blob数；新多Blob编码计每片头部。超容量单Blobcase为blocked，不缩小payload或截断。所有组使用相同逻辑内容与预期结果。

batch若仍client-dispatch-group，不称链上批量提交。记录logicalBatch、dispatchGroup、实际tx数和聚合类型，不能把任务数上升自动解释为合约摊销。

## 3. 独立并发与队列测量

并发单位继承inflight_batches；每批有batchSize任务，同时在途批次数不受batchSize限制。禁用min(batchSize,concurrency)静默折叠。

记录configuredConcurrency、inflight峰值/平均/时间序列、批内并发、queueDepth、到达速率/完成速率、总batch数。达到目标需要足够队列和真正重叠的批次生命周期，不以Promise数量代替在途观测。

至少验证batchSize=1、concurrency=1/4/16三个配置保留差异；实际低于目标因任务短暂结束、硬件限速或nonce序列化，要解释而不是改配置数字。nonce分配策略、signer数量、重试规则固定，使用多个EOA会改变系统条件，不能不报告。

Hardhat in-process自动挖矿适合gas/客户端开销，不能证明共识吞吐。若需要节点排队实验，另设interval mining模式且冻结参数，不能与automining数据混合。负载生成器用开放/封闭模型二选一并说明；闭环模型不能宣称无限到达压力下的容量，避免忽略排队等待。

## 4. 指标、费用与不确定性

### F4：延迟和吞吐

记录排队→编码→TEE执行/签名→证明验证→tx发送→纳入→按确认策略确认→独立DA获取→挑战→接管→首次有效推进→resolve→finalize→withdrawable→实际withdraw。

提交确认、应用可用、协议终局、可提现和实际提现分开；并行阶段不能直接相加，使用关键路径或真实端点差值。

吞吐按同一测量窗口内去重逻辑任务：executed、accepted、finalized分别计算。记录分子、秒数、窗口起止、attempt/failure/retry/censored，批内样本不是完全独立样本。边界任务跨出窗口要规定归属和drain期，不只统计完成最快的一部分。

恢复指标沿C定义，分别给可接续比例、超时结算比例和未终止比例；recover交易成功不是恢复完成。超时未完成属于右删失/失败，不能删除后仅对成功计算“总平均恢复时间”。条件于成功的延迟可以报告但必须同时报告成功率、分母和删失。

### F5：整数gas、货币与分母

链上计量使用原始整数，gas保安全整数或十进制字符串，wei价格/费用必须BigInt运算和十进制字符串序列化；不先转换JS Number再保存，不用字符串比较大小。

本地gas与实际货币费用分开。实际receipt费用：执行gas×实际价格+blobGasUsed×blobGasPrice；未取得真实字段不填0不填估算。发送前失败、链上revert、替换交易、未确认交易分别记录费用来源。Blob字节数不等于Blob gas。

总成本以不重叠primitive费用项计，再按submit/challenge/recover/settle标签归因，不能把阶段归因重复加到总额。押金、退款、罚没赔付作为价值转移单列；TEE/DA/云¥费用和链上wei分账，除非提供时间一致的外部价格与假设，不直接相加。

同一任务群、同一窗口的totalMeasuredCost分别除以finalizedTasks、acceptedTasks、submittedBatches；失败重试成本是总额子集不再加一次。分母0或未测为null+reason。共享批次费用分配规则固定，保留未分配失败批次成本。

calldata和Blob比较保持相同原始任务、同确认条件和费用统计边界；实际公开网络价格变动用相近时间块/配对方式呈现，同时另给固定价格的情景重价表，后者明确modelled，不称实付。

### F6：统计

保存raw后单独聚合，统计脚本从raw重建。不按均值先筛异常；预设系统故障排除策略，任何排除有标志且原数据保留。

每格报告尝试/成功/失败/重试/删失、独立run数、均值、中位数、p50/p95、分位算法和样本量。以独立run/批为cluster做配对差异或合适bootstrap，固定统计seed；仅3个独立run时承认CI不稳，不凭大量批内任务伪造大样本。

少样本不报p99，不输出无法计算的置信区间；没有可比数据不填提升百分比。顺序随机化或配对交错，记录CPU/内存/实例、缓存、网络/限速、时段、其他负载及预热。

## 5. 消融与对照设计

分别设置且不要混表：

- 恢复开/关：保持同一计算/资金政策、窗口、故障位置；对照可能无法继续，报告失败率而不是只比成功延迟。当前有界合约若保留不依赖恢复的adjudicate直接重算兜底，必须另列恢复交互、无恢复但有兜底、直接兜底三种策略，不关闭兜底伪造“无恢复必失败”；若恢复没有改善正确终局时间，照实报告其仅对交互路径的作用。
- TEE：模拟后端功能控制、真实受保护执行、同硬件同程序原生对照；模拟HMAC不是TEE性能基线。无法同硬件则列混杂因素。
- 提交形态：全量与紧凑提交比较包括证据、元数据、DA字节和验证gas。
- DA：calldata与真实Blob，计实际填充和跨Blob阶梯、取回及兜底披露。
- 裁决：有界重算与Merkle单步仅在两者确实实现且语义可比时对照，未实现为not_applicable。
- 去掉签名/DA强绑定等安全机制：只能隔离本地负控制，标security-weakened，不列为同等安全的性能改进，不带到公网。

## 6. 验收、输出与下游交接

至少输出：

1. config/matrix/采样计划、source/config/依赖hash和实际runner；
2. raw sample/events/window records、数据字典、完整失败/右删失记录；
3. 汇总JSON/CSV（无公式注入内容）、单位清楚的SVG/PNG和生成脚本；
4. 参数扩展图、分阶段延迟图、故障恢复时间与成功率、gas/真实费用分表、Blob填充阶梯、消融表；
5. `comparability_contract`：指标端点、模型、环境、数据规模、信任、计费范围，供G引用；
6. handoff.json、report_zh.md、可从raw重建汇总图表的实际命令。

对统计代码加fixture测试：已知分位数、分母0、全失败、右删失、重复task/tx、超大wei、缺费用字段、跨窗口任务、批内相关、nonce重试；小规模实际并发冒烟与足量测量分开。

复核源数据聚合总数与sample身份、费用总和、图表与表格数值一致，保留校验结果。旧A schema回归不能因扩展失效。

阶段完成按F-local/F-TEE/F-Blob/F-full列。因缺D/E真实资源时本地组完成仍可交G机制对照，但整体F报告partial。最终答复给实际矩阵规模、样本分母、测得指标、CI限制、没有测到的项和下一步；不要给虚构提升值，不修改论文，不commit/push。
