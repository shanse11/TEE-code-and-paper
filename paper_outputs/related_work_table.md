# Related Work 对比表

| 工作 | 核心问题 | 主要机制 | 与本文关系 | 本文差异点 |
| --- | --- | --- | --- | --- |
| TEEROLLUP | 如何用异构 TEE 降低 Rollup 验证成本并缩短提现延迟 | 异构 TEE 委员会、QC、多签、Challenge、DAP 惩罚 | 提供 Hybrid TEE-Rollup 的总体系统参考 | 本文不重做完整 TEEROLLUP，而聚焦异常 challenge 恢复和 DA 成本原型评估 |
| OTR / Optimistic TEE-Rollups | 如何验证链上生成式 AI 推理 | TEE 快速证明、Optimistic challenge、随机 ZK 抽查 | 提供 TEE + Optimistic + 抽查的 AI 推理验证参考 | 本文不实现 ZK 抽查，重点评估 recoverable challenge 和 DA 成本 |
| opML | 如何用 optimistic fraud proof 支持大模型或 ML 计算 | 交互式争议、二分定位、单步仲裁、FPVM | 提供 ML 执行争议和 bisection proof 参考 | 本文面向 Hybrid TEE-Rollup 原型，加入 DA payload 和 timeout recovery |
| Dynamic Fraud Proof | 如何缩短无争议场景的最终性并动态处理争议 | 动态挑战窗口、随机验证者集合、延迟结算 | 提供 challenge timeout 和快速最终性思路 | 本文当前只做可恢复状态机原型，不声称完整动态最终性协议 |
| LazyLedger | 如何将 DA 从执行中解耦并降低扩容瓶颈 | 数据可用性层、抽样、模块化区块链 | 提供 DA 层和数据可用性抽样理论基础 | 本文使用模拟 DA profile 和 Merkle proof，不实现真实 DAS 网络 |
