# 面向评审的证据回应与限制说明

## 评审意见 1：安全结论是否只来自合约自测？

不是。修订分支使用独立 JS 接受谓词、状态迁移和资金守恒检查，合约 `compute` 仅用于一致性自检，不作为唯一判定 oracle。定向回归共 23 项，全部通过；固定种子随机序列共 1000 条，执行 27401 次操作，22686 次 revert 均进行了协议状态和资金账目不变性检查。证据见 `security/security_report.json` 和 `security/random_report.json`。

## 评审意见 2：随机测试是否覆盖了恢复和超时边界？

已覆盖 `maxRecoveries={0,1,2}`、`steps={4,16,64,128}`，并在定向测试中检查提前恢复、重复恢复、超限恢复、固定 absolute deadline、超时后的第三方裁决和重复结算。随机测试不是形式化证明，仍不能替代更大规模随机测试、符号执行或形式化验证。

## 评审意见 3：Blob/KZG 实验是否使用了 Mock？

离线 Blob/KZG 实验没有使用 Mock 密码学。它加载真实 Ethereum 主网 EIP-4844 KZG trusted setup，生成 9 个任务数×payload 大小组合，并对每个组合检查正向证明、内容篡改、Blob 字节篡改、payload hash 变化和帧解码。该结果证明本地编码和验证链路成立，但不证明 Blob 已进入任何公共链。

## 评审意见 4：为何没有报告 Sepolia 链上结果？

当前环境没有 Sepolia RPC、签名私钥、已部署的 `BlobBatchAnchor` 地址、Beacon API 或可证明的发布状态。发布脚本设计为 fail-closed，在缺少任一必要输入时不广播交易；取回脚本也不会用本地 Blob 替代 Beacon 实时结果。因此本次不能诚实地给出交易哈希、区块号、锚定事件或独立取回结论。

续跑路径已经实现：`blob_publish.js` -> `blob_fetch.js` -> `blob_verify.js`。完整条件见 `external_status.json`。

## 评审意见 5：性能结果能否与公网 Rollup 或 EIP-4844 费用比较？

不能直接比较。性能实验运行于本地 Hardhat Cancun、chainId 31337、自动挖矿环境；主要矩阵是合约交互测量，另有 calldata 对照和 EVM 时间跳跃下的恢复测量。结果可作为回归基线，不能解释为公网 TPS、共识最终性、真实 Blob gas 价格或 L1 成本节省。真实 Blob 费用必须使用确认的 type-3 receipt 和 Blob gas 字段重新测量。

## 评审意见 6：真实 TEE 证据为何缺失？

外部研究已核实 TDX 提供商、支持规格、特定 AZ、Quote 生成接口和 DCAP/PCCS 流程，但环境没有云凭据或运行中的 TDX 实例。没有伪造 Quote，也没有代用户购买或登录云服务。真实证据需要实例产生的 Quote、PCK 证书链、TCB Info、QE Identity、PCK CRL 和独立验证结果，并进一步比对部署 sequencer 的测量值。

## 评审意见 7：旧实现问题是否只是静态审查？

不是。旧实现 10 类反例均由 `legacy_counterexamples.js` 执行并写入独立 JSON 工件，`report.json` 记录 10/10 复现，包括任意 responder、第三方证据误罚、调用者自填 hash、无限恢复/延期、无资金罚没和无访问控制 DA 修改等问题。

## 保留意见

1. 本地测试覆盖的是当前模型和参数矩阵，不是形式化安全证明。
2. 离线 KZG 证明的是密码学工件链路，不是数据可用性服务长期保留能力。
3. PeerDAS/Fusaka 后，普通 Beacon 节点可能只 custody 部分列；生产部署需要完整 Blob 取回策略。
4. TDX 文档级可用性不等价于实时库存、配额或计费可用性。
5. 跨协议比较中的时延、成本和威胁模型不同，不能合并为单一领先百分比。
