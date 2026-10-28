# 阶段 E 报告｜真实 Blob、独立取回、任务绑定与 DA 结算

> 阶段：E｜状态：**partial**
> - **E-local：completed**
> - **E-public-transport / E-binding / E-DA-settlement / E-integrated：blocked**
>
> 按提示词："仅 E-local 或 E-public-transport 完成写 partial 并列出差异。"

---

## 1. 改动与产出

| 文件 | 说明 |
|---|---|
| `evm/revision/stageE_binding.js` | E1：规范 manifest 版本、单向承诺构造（无循环）、容量/填充度量、M1 链下验证、真实 KZG 封装 |
| `evm/revision/stageE_local.test.js` | E-local 测试与 E01–E15 状态登记 |

**合约零变更。** 核心合约 `BoundedTaskRollup` **没有 DA 引用/指针字段**，这是 E-binding 与 E-DA-settlement 无法完成的根本原因（需显式协议变更并重跑 B/C）。

测试：**7 passing / 0 failing**，19 个 case（verified=5、blocked=14）。

---

## 2. 真实密码学证据（非模拟）

| 项 | 值 |
|---|---|
| 库 | **c-kzg 4.1.0**（真实绑定，非模拟） |
| trusted setup | `evm/revision/trusted_setup.txt`，sha256 `d39b9f2d047cc9dca2de58f264b6a094…`（完整值见 `stageE/trusted_setup.json`） |
| 验证 | 真实 `blobToKzgCommitment` / `computeBlobKzgProof` / `verifyBlobKzgProof` |
| versionedHash | `0x01 \|\| sha256(commitment)[1:]`（EIP-4844），已校验格式 |

---

## 3. 容量与填充（E01）

| 项 | 值 |
|---|---|
| Blob 字节数 | 131072（4096 域 × 32 字节） |
| 每域数据字节 | 31（顶字节恒 0，保证 FE < BLS_MODULUS） |
| **单 Blob 帧容量 MAX_FRAME_LEN** | **126976** |
| 帧开销（本轮 domain 26 字节实测） | 79 = MAGIC(4) + 1 + 26 + 8 + 8 + 32 |
| **最大内容长度** | **126897** |

| 场景 | frameBytes | 结果 |
|---|---|---|
| 容量下界（小 manifest） | ≪ 126976 | 通过，blobCount=1，真实 KZG 通过 |
| **刚好上界** | **126976** | 通过，blobCount=1，真实 KZG 通过 |
| **超一字节** | **126977** | **blocked**（`SINGLE_BLOB_CAPACITY_EXCEEDED`），不截断、不缩小载荷、不把失败样本从分母消失 |

阶段 A 口径（全部来自实际序列化，非估计）：
`encodedBytes = ceil(frameBytes/31)*32`、`blobCount = ceil(encodedBytes/131072)`、
`paddingBytes = blobCount*131072 - encodedBytes`、`fieldPaddingBytes = ceil(frameBytes/31)*31 - frameBytes`、
`fieldPrefixBytes = ceil(frameBytes/31)`。

**多 Blob 策略选择**：采用提示词策略 1——保留单 Blob 能力，只选可容纳矩阵，超容量样本 explicit blocked（E08 记为 blocked，不实现少片/重复/调序/跨批拼接的假通过）。

---

## 4. 编码规范与绑定（E1 / M1 / M2）

### manifest 版本
`hybrid-tee-rollup.batch-manifest.v1`，编码版本 `blobcodec-field31-v1`。
字段包含：域、chainId、contract、batchId、task 数量与顺序、每 task 原始长度、程序版本、input/output/trace 承诺、分片位置、Blob 顺序、编码版本。

### 单向构造（避免循环承诺）——已验证

```
原始任务数据（不含摘要/manifest） -> inputDataHash
  -> taskCoreDigest（域、task/nonce、程序、input/output/trace；不含 DA 引用）
  -> manifest（含各 task coreDigest）与帧
  -> KZG commitment / versionedHash
  -> envelope(coreDigests, manifestHash, daRef, epoch/expiry)
```

**无循环证据**：同一 task 放在不同 manifest（不同 batchId）时 `coreDigest` **保持不变**，证明它不依赖 `manifestHash`/`versionedHash`，不存在自引用倒灌。

### M1 / M2

| 义务 | 定义 | 状态 |
|---|---|---|
| **M1** | 核心 task 摘要确实出现在该 versionedHash 对应 Blob 的规范 manifest 中 | **verified（仅链下）**：篡改 blob 数据后 payloadHash 自洽检查失败，且真实 KZG 验证同时失败 |
| **M2** | manifest 承诺的 payload/input/trace 与 Blob 实际数据一致且足以裁决 | **blocked**：需 KZG point-evaluation 证明（roots-of-unity/求值索引、field packing、字节序、域分离）与合约可验证路径；核心合约无 DA 字段 |

> 已如实记录：**M1 成立 ≠ M2 成立**。当前只完成"摘要存在于 manifest"的链下验证，没有客观链上裁决路径，因此不是强绑定。

### 畸形与篡改

- 篡改 blob 数据 → `payloadHash` 自洽检查失败 + 真实 KZG 验证失败。
- 坏 magic → 解码被拒。
- 如实记录：当前 codec 解码时**忽略每个域元素的顶字节**，因此把顶字节置非零不会改变解码结果——这是编码设计使然（顶字节恒 0），已如实说明而非声称"校验了非法域元素"。

---

## 5. E01–E15 状态

| ID | 等级 | 状态 | 说明 |
|---|---|---|---|
| E01 | E-local | **verified** | 容量下界/刚好上界/超一字节、可逆性、真实 KZG、单向承诺、篡改拒绝、trusted setup |
| E02 | E-public-transport | blocked | type-3 发布与链上确认（需授权） |
| E03 | E-public-transport | blocked | 独立取回（需不同 endpoint/进程） |
| E04 | E-binding | blocked | Blob A 配 manifest B（合约无 DA 字段） |
| E05 | E-binding | blocked | 错索引/旧 batch 复用（需合约约束） |
| E06 | E-binding | blocked | 内容改动重算 KZG |
| E07 | E-binding | blocked | M2（point-evaluation 与合约裁决） |
| E08 | E-local | blocked | 多 Blob 分片（`encoderMaxBlobs=1`） |
| E09–E12 | E-DA-settlement | blocked | 无 DA 披露义务与罚没闭环 |
| E13 | E-public-transport | blocked | 广播后崩溃/reorg/nonce |
| E14 | E-integrated | blocked | 与 B/C/D 联调（D 已 blocked） |
| E15 | E-DA-settlement | blocked | DA 待决时的 adjudicate/finalize/withdraw 互锁 |

---

## 6. 授权范围与所需资源（不含任何秘密值）

**本轮未广播任何交易，未使用任何私钥/助记词/RPC token。**

需要用户提供的资源与最小权限：

| 资源 | 最小权限 |
|---|---|
| Sepolia（或等价测试网）RPC endpoint | 可发 type-3 交易并查询 receipt；**不需私钥入库** |
| 持有测试币的钱包 | **仅需公开地址**；私钥由用户自管，不进实验包 |
| Beacon/Consensus 完整 Blob 取回端点 | 用于独立取回；需与发布者不同进程/存储 |
| 广播授权与预算 | 需明确：网络与 chainId、交易与 Blob 数量、费用上限、最大重试数、测试币余额 |

**明确不做**：不随机创建钱包、不绕过链身份检查、不在主网广播、不对公网实施 DoS/数据破坏/恶意审查。

**费用口径（待有真实 receipt 后）**：`totalExecutionFee = gasUsed × effectiveGasPrice`、`blobFee = blobGasUsed × blobGasPrice`，均以 BigInt 计算并序列化为十进制字符串；字段缺失记 `null`+原因，不用估算值冒充实付；交易 revert 若已打包仍计 gas；押金/退款/罚没赔付属价值转移，不计为燃烧费用。

---

## 7. 当前源码 / 配置哈希

| 项 | 值 |
|---|---|
| gitHead | `615bb3e9f1ae3b88b87f488decc61854cd555e16` |
| gitDirty | `true` |
| **E 阶段 sourceTreeSha256** | `9da9f3783cc46db763ce2d299acbad2cadfc2cb942c1befe2459b36d175253e4` |
| E 阶段 configSha256 | `9d1399132ddf880bb561dcf11a58fe1e3cd982ed84be3e8189b10396b6d6ec4b` |
| 父（D）sourceTreeSha256 | `e8467bd4c35cfec9491dc57460f869167c660e54d99d3de9a63d95d01b105cfe` |

---

## 8. 对 F / G 的可交付数据

- **可用**：E01 的容量/填充度量（供 F 的 Blob 填充阶梯）、真实 KZG 开销基线、manifest 规范版本、M1 链下验证结论。
- **不可用**：任何真实公网 receipt 费用、独立取回耗时、Blob 阶梯的真实跨 Blob 开销——这些需 E-public-transport，当前 blocked；**F 不得用本地离线数据冒充公网费用**。
- 因此 **F-Blob 同样 blocked**；F-local 不依赖 E 公网资源，可先行。
