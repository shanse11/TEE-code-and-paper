# 论文大纲

## 题目

面向高频 DApp 的 Hybrid TEE-Rollup 可恢复挑战协议与轻量 DA 成本评估

## 摘要草稿

高频 DApp（如元宇宙资产交互、去中心化社交状态更新和 AI 推理服务）需要低延迟、低成本且可验证的执行环境。现有 Rollup 路线中，ZK-Rollup 验证强但证明成本高，Optimistic Rollup 成本较低但挑战窗口较长，单纯 TEE 方案又存在硬件信任和可用性风险。本文不提出全新的 TEEROLLUP 系统，而是在已有 Hybrid TEE-Rollup 思路下，聚焦两个更具体的问题：交互式挑战在异常场景下能否恢复推进，以及 compact commit + DA 是否能降低高频交互的提交成本。本文实现一个模拟 TEE、JSON ledger 和 DA payload 的原型，扩展可恢复 challenge 状态机，引入模拟 Merkle root / proof，并对 full-onchain、compact external DA、EIP-4844-like 和 modular DA profile 进行成本评估。实验结果用于说明原型趋势，而不声称真实链上 gas 或真实 TEE 安全。

## 贡献点

1. 设计并实现面向 Hybrid TEE-Rollup 的 recoverable interactive challenge 原型，支持 timeout recovery、bisection 和 single-step replay。
2. 为 DA payload 增加模拟 Merkle root / proof，使 compact commit 不只依赖 JSON pointer。
3. 建立多变量实验框架，覆盖 payload size、prompt length、batch size、trace steps、challenge timeout、bisection rounds 和 DA profile。
4. 构造 response tampering、attestation invalid、trace length mismatch、DA unavailable、DA proof invalid 等失败场景实验表。

## 章节结构

1. Introduction：高频 DApp / AI 推理上链的性能与可信问题。
2. Background：Rollup、TEE attestation、Optimistic Challenge、Data Availability。
3. Motivation：单纯 TEE、单纯 OP、全量上链的不足。
4. System Design：执行层、验证层、数据层三层架构。
5. Recoverable Challenge Protocol：状态机、恢复机制、单步重放、证据字段。
6. DA Cost Model：full-onchain、compact commit、DA profile 和 batch amortization。
7. Evaluation：实验设置、指标、结果和失败场景。
8. Discussion：simulated TEE、gas 估算、JSON ledger、真实部署不足。
9. Related Work：TEEROLLUP、OTR、opML、Dynamic Fraud Proof、LazyLedger。
10. Conclusion。
