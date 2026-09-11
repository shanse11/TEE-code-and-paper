# final_refs_12_core 修改报告

## 1. 最终保留数量

最终保留 12 篇参考文献。

## 2. 保留文献清单

1. WEN X, FENG Q, LYU H, et al. TEEROLLUP: efficient Rollup design using heterogeneous TEE.
2. BUTERIN V. An incomplete guide to Rollups.
3. ETHEREUM FOUNDATION. Optimistic Rollups.
4. ARBITRUM FOUNDATION. Arbitrum Nitro technical documentation.
5. OP LABS. Optimism documentation: fault proofs and dispute games.
6. PICCO G, FORTUGNO A. Dynamic fraud proof.
7. AL-BASSAM M. LazyLedger: a distributed data availability ledger with client-side smart contracts.
8. TAS E N, TSE D, YANG L, et al. Light clients for lazy blockchains.
9. EIGENLABS. EigenDA documentation.
10. CELESTIA. Celestia: modular blockchain network.
11. INTEL CORPORATION. Intel Software Guard Extensions developer guide.
12. ETHEREUM FOUNDATION. EIP-4844: shard blob transactions.

## 3. 删除文献清单与理由

- 原 [3] RISC Zero zkVM documentation：正文仅泛泛提到 ZK-Rollup 成本，没有展开 zkVM 实现，删除。
- 原 [4] SP1 documentation：与原 [3] 同类，属于辅助性 zkVM 文档，删除。
- 原 [6] Offchain Labs Arbitrum overview：与 Arbitrum Nitro 文档重复，保留更直接的 Nitro 技术文档。
- 原 [9] Goldwasser, Micali, Rackoff interactive proofs：理论背景过宽，正文没有实质展开交互证明复杂性，删除。
- 原 [16] Intel TDX architecture specification：正文没有区分 SGX 与 TDX，保留 SGX 开发指南作为 TEE/远程证明背景。
- 原 [17] Cartesi Rollups documentation：验证/重放语义已由 Arbitrum Nitro 与 Optimism dispute game 文档支撑，删除。
- 原 [18] Canetti UC security：安全理论过宽，正文只是机制边界说明，删除引用并保留原句语义。

## 4. 旧编号到新编号映射

- 原 [1] -> 新 [1]
- 原 [2] -> 新 [2]
- 原 [3] -> 删除
- 原 [4] -> 删除
- 原 [5] -> 新 [3]
- 原 [6] -> 删除
- 原 [7] -> 新 [4]
- 原 [8] -> 新 [5]
- 原 [9] -> 删除
- 原 [10] -> 新 [6]
- 原 [11] -> 新 [7]
- 原 [12] -> 新 [8]
- 原 [13] -> 新 [9]
- 原 [14] -> 新 [10]
- 原 [15] -> 新 [11]
- 原 [16] -> 删除
- 原 [17] -> 删除
- 原 [18] -> 删除
- 原 [19] -> 新 [12]

## 5. 正文引用修改位置

- 引言：Hybrid TEE-Rollup 背景引用保留为新 [1]。
- 第 2.1 节 Rollup/ZK/Optimistic Rollup 段：删除 zkVM 文档引用，原 [5] 改为新 [3]。
- 第 2.1 节乐观挑战段：原 [6][7][8][9] 精简为新 [4][5]，原 [10] 改为新 [6]。
- 第 2.1 节数据可用性段：原 [11][12][13][14] 改为新 [7][8][9][10]。
- 第 3.1 节 TEE/远程证明段：原 [15][16] 精简为新 [11]。
- 第 3.3 节验证与恢复触发段：原 [17] 改为新 [4][5]。
- 第 4.1.4 节协议性质段：删除原 [18] 引用，保留原句机制语义。
- 第 4.3 节 DA 路径和成本模型段：原 [19] 改为新 [12]。

## 6. 自检结果

- 正文引用编号为 [1] 到 [12]，连续无跳号。
- 文末参考文献为 12 篇，与正文首次引用顺序一致。
- 未发现正文引用不存在文献的编号。
- 未发现文末参考文献未被正文引用。
- 摘要、关键词、图题、表题、章节标题中未新增引用。
- 已导出 `final_refs_12_core.pdf` 并检查参考文献页，双栏版式正常。

## 7. 需要人工复核的位置

- 第 4.1.4 节删除了原 UC security 引用，当前作为本文机制性质说明保留；如导师希望该段仍有理论安全引用，可人工决定是否恢复一篇安全理论文献。
