# HTR 补充实验汇总（2026-10-30 包，汇总补写 2026-11-01）

仓库分支：`supp-experiments-20261030`。证据根目录：`outputs/experiments_supp_20261030/`。本文件只汇总已有 `result.json` / `report_zh.md` / `raw_results.json`，不新增实验数字。

## 总览

| 项 | 状态 | 关键结论 | 证据路径 |
|---|---|---|---|
| SGX 重取 Quote | 完成 | 新 Quote SHA256 `5e6e179f…3b90`；MRENCLAVE 不变 `0x1f2467e1…b6b05f`；本地校验仍 **0xA003**（OUT_OF_DATE_CONFIGURATION_NEEDED）；Intel PCS 不可达；租户无法单方修 TCB | `sgx_requote/result.json` |
| A 安全实验 S1–S5 | 完成 | BoundedTaskRollup 多数场景可防；HybridTEERollup / MockTEEVerifier 暴露 FINDING-H1…H7（见下） | `A_security/raw_results.json`，`evm/test/supp/Security.supp.test.js` |
| B 本地 point-eval | 完成（Hardhat，非 Sepolia） | 0x0a 预估 gas 73700；bind 158340 / fulfill(point-eval) 115710 / slash 89638；篡改 y 被拒 | `B_point_eval/raw_results.json` |
| B Sepolia Blob + point-eval | 完成 | type-3 Blob tx `0x450ac7fd…a51d`；point-eval tx `0x4f98c197…67d0`，gasUsed 67700；需 EIP-7594 cell proof sidecar | `B_sepolia/result.json`，`B_sepolia/report_zh.md` |
| D 链上 Automata DCAP | 完成 | tx `0xcdc1cdcc…6fe0`，gasUsed **5037977**；success=true，TCB 枚举 **5**（等同 0xA003），非 UpToDate | `D_dcap_onchain/result.json`，`D_dcap_onchain/report_zh.md` |
| C 同负载定量对比 | **未做** | 本方案本地实测表、Arb/OP 实测或引用、TEEROLLUP 引用均未交付 | （缺目录） |

## FINDING 清单（HybridTEERollup / Mock 路径）

| ID | 场景 | 要点 |
|---|---|---|
| H1 | S1/S3 | 任意地址可 `resolveChallenge` 任意 bits，可罚没诚实交易或清除挑战 |
| H2 | S1 | 陌生人 `recoverChallenge` 可改写 `session.operator` |
| H3 | S1 | `MockDARegistry.setAvailability` 无权限限制 |
| H4 | S2 | TEE attestation 可在新 txId / 另一合约实例重放（digest 缺 chainid/address/txId，nonce 未消费） |
| H5 | S2 | MockTEEVerifier 接受 ECDSA malleated 签名 |
| H6 | S4 | 旧 nonce、旧/debug MRENCLAVE 仍可被接受（无 nonce 登记、无 allowlist） |
| H7 | S5 | 泄露 TEE 签名密钥可伪造任意输出；无吊销 API、无 bond 罚没上界 |

BoundedTaskRollup：正确性侧多数 DEFENDED；S3 女巫挑战存在「正确性守住、经济净损可为 0」；S5 泄露提交者 EOA 可取走 claimable，但错误输出仍会被 finalize 烧毁。

## 诚实边界（写论文须保留）

1. TCB 仍为 0xA003 / 枚举 5，不得写成 UpToDate。
2. Sepolia point-eval 是直接调 0x0a，未在公网部署 PointEvalDaDuty 的 bind/fulfill 全路径。
3. 本地 Hardhat gas 与 Sepolia gas 分列，不得混称生产网验证。
4. FINDING 针对当前 HybridTEERollup/Mock 实现与测试配置；BoundedTaskRollup 为对照，不等于已修复 Hybrid 路径。
5. C 项缺失：在补齐前，论文「与 Arb/OP/TEEROLLUP 同负载定量对比」只能标未完成或改用既有 StageH/文献分层表述，并标明非本包新测。

## 复现入口

- 安全：`cd evm && npx hardhat test test/supp/*.js`
- Sepolia 脚本（需本人提供 `SEPOLIA_PK`，勿入库）：`evm/scripts/supp/sepolia_blob_osaka.mjs`、`evm/scripts/supp/sepolia_send.js`
- Quote 原文件未入库；本机曾落在 `~/supp_requote_20261030/`（见 `sgx_requote/result.json`）

## 建议下一步（仅记录，本汇总未执行）

1. 补 C：本方案本地实测表 + Arb/OP 能起 devnet 则测，否则公开数据「引用非实测」+ URL；TEEROLLUP 引用或标不可得。
2. 将 FINDING-H1…H7 写入答复信 / 正文威胁模型与局限，区分「Bounded 路径已测」与「Hybrid 旧路径缺口」。
3. 若投稿依赖 UpToDate TCB，需云厂商微码/BIOS，租户侧无法关闭 0xA003。
