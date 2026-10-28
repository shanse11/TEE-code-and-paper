# 状态、权限与信任边界矩阵

| 组件/参与者 | 可执行权限 | 当前信任假设 | 可验证证据 | 当前状态 | 不应宣称 |
|---|---|---|---|---|---|
| `BoundedTaskRollup` 修订合约 | 接收 submit/challenge/respond/recover/adjudicate/settle/finalize/withdraw 等调用 | EVM 执行语义和部署字节码与本地测试一致 | 23 项回归、随机状态机、资金守恒 | 已完成本地验证 | 不应宣称已完成主网/测试网上链验证 |
| submitter | 提交任务和绑定 digest；不能代替 challenger 角色 | 签名/域绑定和 task 状态检查有效 | replay、非法 version/steps、重复提交测试 | 已验证 | 不应宣称外部 TEE 签名已真实接入 |
| challenger | 发起挑战并提交允许的证据路径 | 恶意挑战不应罚没诚实 submitter；超时可公开裁决 | challenge、adjudicate、timeout 矩阵 | 已验证 | 不应宣称对所有网络审查模型形式化成立 |
| responder | 仅授权 submitter 可对其 task 响应 | 非 submitter response 应失败 | 未授权 response 测试 | 已验证 | 不应宣称真实 sequencer 在线性已验证 |
| recover caller | 在有界次数和规则内推动恢复 | 恢复次数有限且不刷新 absolute deadline | recover 上限、回退和 deadline 测试 | 已验证 | 不应宣称真实跨地域故障恢复延迟 |
| withdraw recipient | 接收或拒收资金；可能尝试重入 | checks-effects-interactions / 状态锁正确 | 拒收和重入 recipient 测试 | 已验证 | 不应宣称已覆盖所有未知外部调用模式 |
| Mock/测试 oracle | 仅用于自检或测试部署 | 独立 JS 接受谓词不依赖合约自判 | security report note | 已区分 | 不应把 MockTEE/MockDA 结果写成真实 TEE/DA |
| `BlobBatchAnchor` | 记录当前 type-3 tx 的 blob versioned hash 和 payload metadata | EVM 不能读取 Blob 字节，业务语义必须链下独立验证 | 合约源码、离线 KZG；无公网 receipt | 仅本地编译/逻辑可用 | 不应宣称已锚定真实公共链 Blob |
| `blob_offline.js` | 本地生成、保存和复验 Blob/KZG 工件 | Ethereum EIP-4844 SRS 和本地 codec 正确 | 9 批次+负例全部通过 | 已完成离线验证 | 不应宣称 Blob 已发布或可由 Beacon 取回 |
| `blob_publish.js` | 在凭据、网络、合约和余额齐备时广播 | 用户明确提供凭据；脚本 fail-closed | 本次无发送 | 未执行公网分支 | 不应宣称有交易 hash 或费用数据 |
| `blob_fetch.js` | 向指定 Beacon API 读取完整 Blob | endpoint 提供完整 sidecar；不使用本地替代 | 本次无 `BEACON_API_URL` | 未执行 | 不应宣称已独立取回 |
| Sepolia Beacon 节点/PeerDAS | 提供其 custody 范围内的 Blob 数据 | 生产环境需 supernode/归档/按需下载能力 | 官方文档级资料 | 未做实时验证 | 不应宣称普通节点一定能回放历史 Blob |
| TDX 实例 | 生成 TD Report/Quote；PCCS/DCAP 提供 collateral | 实例硬件、镜像和测量值可信且可独立验证 | 官方文档流程；无真实 Quote | 未完成 | 不应宣称真实 TEE 已证明部署测量值 |
| 云控制台/供应商 | 提供实例、库存、计费和区域配额信息 | 价格/库存需实时账户级查询 | 无凭据，文档级存在性 | 未核实 | 不应作 500 元内确切采购承诺 |
| 论文/外部比较数字 | 仅作为引用和背景 | 分母、威胁模型、测试环境需保持原文语境 | `sources.json` 与比较报告 | 文档级完成 | 不应转换成跨协议统一领先百分比 |

## 信任转移规则

- 本地 EVM 证据只能支持合约行为和测试模型结论。
- 离线 KZG 证据只能支持真实编码/证明/篡改检测结论。
- 公网 Blob 结论必须同时有 type-3 receipt、链上 anchor 读取、Beacon 独立取回和字段一致性验证。
- 真实 TEE 结论必须同时有 Quote、PCK 证书链、collateral、DCAP 验证和部署测量值比对。
- 缺少任一关键证据时，状态应保持“未完成/不可证实”，不能使用本地工件补位。
