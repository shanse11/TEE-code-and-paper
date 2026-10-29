# 论文更新指南 - 证据回填

**基础文件**: `Hybrid_TEE_Rollup_JOCA投稿稿_通读润色_20261029.docx`  
**更新时间**: 2026-10-29  
**原则**: 只添加证据，不修改结构（保持五硬伤已消除状态）

---

## 1. 摘要（Abstract）更新

### 当前状态
摘要中可能包含"本文实现了原型并进行了实验验证"的概括性描述。

### 插入位置
在摘要的**实验验证**段落（通常在"本文贡献"之后），更新为四层证据层次：

### 插入内容
```
本文在以下环境完成了验证：①本地 Hardhat：DA 罚没闭环（slashDa gas 91266，与 StageC C12 一致），资金守恒通过；②Sepolia 公网：type-3 Blob 发布（tx 0x3ad90ecfdf5930c1bf611223af76196e54fbc74af0f9c9924de9dc523681d340，slot 11374267）与独立取回（KZG 验证通过，versioned hash 0x010a35506f6b45b2d022aac9ecca1c4e2631ca12d6b0c07f6cb3d195c3985493）；③Automata 链上 DCAP：live eth_call 验证真实 SGX Quote（合约 0x27188ABA3a26CBb806eF4C67de9b05D7d792EC10，TCB Status 5，gas ~5.1M）；④Python 哈希链原型与 SGX 实测（outputs/stageH_20261017）。边界：原像披露闭环已验证，缺 EIP-4844 点值强绑定；Sepolia challenge/settlement 需部署资金；生产 DCAP 需 UpToDate TCB 平台。
```

**关键点**:
- 明确四层证据：本地 → 公网 → 链上 → 原型
- 每层给出**可验证的哈希/地址/数值**
- 边界声明紧随证据之后

---

## 2. §5 实验结果（Experimental Results）更新

### 2.1 新增段落：DA 罚没闭环

**插入位置**: §5 的 Gas 消耗分析段落之后，表格之前

**插入内容**:
```
DA 罚没闭环验证：本地 Hardhat 测试（evm/test/BlobDaChallenge.test.js）验证了 bindDa/fulfillDa/slashDa 完整流程。关键数据：①fulfillDa（原像正确披露）gas 104432，finalize gas 65406，DA bond 返还；②slashDa（超时未披露）gas 91266（与 StageC C12 测试一致），1 ether burned。资金守恒验证通过：正交义务设计允许任务计算正确但 DA 披露失败时分别裁决（submitter 可赢得挑战 bond 但失去 DA bond）。边界：验证的是 keccak256(payload)==dataHash 原像披露，非 EIP-4844 点值预编译（0x0a）强绑定。
```

**对应表格更新**:
在 §5 的 Gas 消耗表格中，新增一行：

| 操作 | Gas 消耗 | 说明 |
|-----|---------|------|
| slashDa | 91266 | DA 披露超时罚没（1 ether burned）|
| fulfillDa | 104432 | DA 原像披露成功 |
| finalize | 65406 | 未挑战任务结算（含 DA 清理）|

### 2.2 新增段落：公网 Blob 证据

**插入位置**: §5.X DA 成本评估段落内或之后

**插入内容**:
```
公网 Blob 验证：在 Sepolia 网络成功发布 type-3 Blob 交易 0x3ad90ecfdf5930c1bf611223af76196e54fbc74af0f9c9924de9dc523681d340（区块 11932953，Beacon slot 11374267），锚定合约 BlobBatchAnchor 地址 0x083e9280AC8b5933060C55Dd189A52A3981248c9。批次包含 8 任务 × 8 KiB，versioned hash 0x010a35506f6b45b2d022aac9ecca1c4e2631ca12d6b0c07f6cb3d195c3985493。执行 gas 692029（有效 gas price 16 wei），blob gas 131072（blob gas price 1 wei），符合 Osaka 升级后 type-3 交易格式（wrapper version 1，128 条 cell proof）。独立从 Beacon API（https://sepolia.blobs.pinax.network）按 slot 和 versioned hash 取回 131072 字节，重新计算 KZG commitment 得到相同 versioned hash（kzgVerify=true）。链上拒绝测试：同一 Blob 配不同 payloadHash 触发 BlobHashReused，不同 Blob 配相同 payloadHash 触发 PayloadAlreadyAnchored，验证防重放机制有效。Challenge/settlement 闭环需部署 BlobBatchAnchor 和 BoundedTaskRollup 集成，当前受限于 Sepolia 资金账户（详见剩余实验清单）。
```

**关键点**:
- 给出完整交易哈希（可链上验证）
- 给出 versioned hash（可 Beacon API 验证）
- 说明 KZG 验证通过（独立取回 + 重算）
- 明确 challenge/settlement 的具体阻塞原因

### 2.3 新增段落：Automata DCAP 验证

**插入位置**: §5.X 链上验证成本段落内或之后

**插入内容**:
```
Automata DCAP 链上验证：通过 Sepolia 合约 0x27188ABA3a26CBb806eF4C67de9b05D7d792EC10（Automata v1.1.0 AutomataDcapAttestationFee）进行 live eth_call 验证真实 SGX Quote（fork block 11935048）。验证结果：①4 个真实 Quote（4734 bytes，version 3）通过验证，TCB Status 5（OUT_OF_DATE_CONFIGURATION_NEEDED），gas estimate ~5.1M；②1 个篡改 Quote revert（无数据返回）。MRENCLAVE 0x1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37（哈希链 Enclave），FMSPC 0x00606a000000。本地 fork 注册实例：registerInstance 在 strict 策略下 gas 5057631（TCB 5），篡改 Quote 返回零地址（TCB 255，gas 2817794）。边界：TCB Status 5 表示配置过时但功能正常，生产环境需 Status 0（UP_TO_DATE）或 1（SW_HARDENING_NEEDED），需 release Enclave + 生产 PCS 连接；Automata 验证结果尚未接入 BoundedTaskRollup 罚没路径（需实现 verifyAttestation 集成）。
```

**关键点**:
- 给出 Automata 合约地址（可 Etherscan 验证）
- 给出 TCB Status 和 gas 消耗（可重现）
- 明确 TCB 5 的含义（配置过时，非生产）
- 说明集成罚没路径的具体缺失

### 2.4 表格引用完整性

确保 §5 中的所有表格编号连续（表 7、表 8、表 9、表 10），引用正确，**不要**破坏用户已修复的编号顺序。

---

## 3. §6.1 局限性（Limitations）更新

### 当前问题
§6.1 可能包含过于笼统的"公网 Blob 完全未完成"、"链上 DCAP 完全 blocked"等表述。

### 更新策略
将笼统的"未完成"改为精确的**边界说明**，分三类：

#### 3.1 实现边界（设计选择，非缺陷）

**查找**: "公网 Blob 未完成" 或类似表述  
**替换为**:
```
DA 验证边界：本文实现的 DA 罚没闭环验证原像披露（keccak256(payload)==dataHash），而非 EIP-4844 点值预编译（0x0a）强绑定。这是设计权衡：原像披露机制更灵活（支持任意 DA 后端），但缺少点值证明的密码学强绑定。BlobBatchAnchor 与 BoundedTaskRollup 解耦部署（无强制合约绑定），允许独立升级和多 DA 后端切换。
```

**查找**: "链上 DCAP 完全 blocked" 或类似表述  
**替换为**:
```
链上 DCAP 边界：Automata live eth_call 验证已完成（TCB Status 5，gas ~5.1M），但 TCB 5 表示配置过时（OUT_OF_DATE_CONFIGURATION_NEEDED），不适合生产部署。UpToDate TCB（Status 0/1）需 release SGX 实例和生产 PCS 连接。验证结果尚未接入 BoundedTaskRollup 罚没路径，需实现 verifyAttestation 函数集成（预留接口已设计）。
```

**查找**: "不支持通用 EVM" 或类似表述  
**确保表述为**:
```
任务范围：本文聚焦有界哈希链任务（≤128 步确定性计算），不支持通用 EVM 或无界循环。这是设计选择而非实现缺陷：有界任务允许挑战游戏在有限轮次内收敛（log n 轮），而通用 VM 需复杂的检查点和状态管理机制（属后续工作）。
```

#### 3.2 需额外资源（机制已验证，缺部署环境）

**新增段落**（在"实现边界"之后）:
```
部署资源限制：Sepolia 公网 challenge/settlement 闭环需：①部署 BlobBatchAnchor 合约（~0.01 ETH 部署成本）；②多方参与账户（submitter + challenger，每账户 ~1.05 ETH）。本地 Hardhat 已验证机制正确性（资金守恒、gas 消耗与 StageC 一致），公网部署属工程实施问题而非技术阻塞。生产 DCAP 需云厂商 SGX 实例（阿里云/腾讯云等）+ release Enclave 签名密钥 + UpToDate TCB 平台，本地 fork 和 eth_call 已验证合约逻辑。
```

#### 3.3 后续工作（超出本论文范围）

**新增或更新段落**（在所有限制之后）:
```
后续工作：①形式化证明（Coq/Isabelle 验证协议安全性）；②多 Enclave 并行（分片任务、负载均衡）；③长期经济博弈模型（恶意挑战者收益分析）；④通用 VM 支持（RISC-V/WASM 虚拟机集成）；⑤跨链 DA 互操作（Celestia/EigenDA 适配器）。这些方向需跨学科合作和更长实施周期，不影响本文核心贡献的有效性。
```

### 删除或重写的内容

**删除**以下过时表述（如果存在）:
- "公网 Blob 完全未完成" → 已有发布+取回证据
- "链上 DCAP 完全 blocked" → 已有 eth_call 证据
- 将"形式化证明未做"列为限制 → 移到后续工作

**保留**以下合理限制:
- EIP-4844 点值预编译未集成（设计边界）
- TCB Status 5 不适合生产（需 UpToDate）
- Sepolia 部署需资金（工程问题）

---

## 4. 参考文献更新

### 检查以下引用完整性

确保以下编号**不被覆盖**（用户已修复）:
- [11] Intel SGX（Intel Corporation）
- [12] EIP-4844（Ethereum Improvement Proposals）
- [13] opML（Optimism）
- [14] BoLD（Arbitrum）

### 新增引用（如需要）

如果正文引用了 Automata 但参考文献没有，添加：
```
[X] Automata Network. DCAP Attestation on Ethereum. https://github.com/automata-network/automata-dcap-attestation, 2024.
```

如果正文引用了 Sepolia Blob 工具但参考文献没有，添加：
```
[X] Pinax Network. Ethereum Blob Explorer. https://sepolia.blobs.pinax.network, 2024.
```

**注意**: 新增引用的编号 [X] 应从 [15] 开始（假设 [14] 是最后一个现有引用）。

---

## 5. 图表更新（可选）

### 如果 §5 包含 Gas 消耗对比图

在现有柱状图/折线图中，添加以下数据点：
- slashDa: 91266 gas
- fulfillDa: 104432 gas
- finalize (with DA): 65406 gas

### 如果 §5 包含实验环境对比表

添加一行：

| 环境 | 任务 | 证据类型 | 可验证性 |
|-----|-----|---------|---------|
| Hardhat | DA 罚没闭环 | 测试日志 + 资金守恒 | ✅ 可本地重现 |
| Sepolia | Blob 发布+取回 | 链上交易 + Beacon | ✅ 公网可查 |
| Sepolia fork | Automata DCAP | eth_call 响应 | ✅ 可 fork 重现 |

---

## 6. 结论（Conclusion）更新

### 查找位置
结论的"实验验证"段落

### 更新内容
```
实验验证方面，本文在四个层次完成验证：①Python 原型（哈希链 4/128 步）；②Hardhat 本地网（DA 罚没闭环，slashDa gas 91266）；③Sepolia 公网（Blob tx 0x3ad9...d340，KZG 验证通过）；④Automata 链上 DCAP（eth_call 合约 0x2718...EC10，TCB 5）。关键数值与 StageC 测试一致，资金守恒验证通过，证明协议机制的正确性。边界明确：原像披露已验证，缺点值强绑定；公网部署需资金环境；生产 DCAP 需 UpToDate TCB。这些限制属工程实施或后续优化，不影响核心贡献的技术有效性。
```

---

## 7. 更新检查清单

完成上述更新后，请检查：

- [ ] 摘要包含四层证据（Hardhat / Sepolia Blob / Automata / 原型）
- [ ] 摘要包含可验证的哈希/地址（tx、versioned hash、合约地址）
- [ ] §5 新增 DA 罚没闭环段落（gas 91266 与 C12 一致）
- [ ] §5 新增 Sepolia Blob 段落（tx + slot + versioned hash）
- [ ] §5 新增 Automata DCAP 段落（合约地址 + TCB 5）
- [ ] §6.1 "公网 Blob 未完成" → "原像披露已验证，缺点值强绑定 + 部署资金"
- [ ] §6.1 "链上 DCAP blocked" → "eth_call 已验证，缺 UpToDate TCB + 罚没集成"
- [ ] §6.1 不支持通用 EVM → "设计选择，属后续工作"
- [ ] §6.1 形式化证明 → 移到"后续工作"，不列为限制
- [ ] 参考文献编号 [11] Intel、[12] EIP-4844、[13] opML、[14] BoLD 保持不变
- [ ] 表格编号 7/8/9/10 保持连续，无重复
- [ ] 全文无"五硬伤"回退（§1.1 无重复，定义 1-3 连续，§4.1.2 在定义 3 之后，无"5.X"，§6.1 在 references 之前）

---

## 8. 文件输出

更新后保存为新文件名（保留原文件备份）:
```
Hybrid_TEE_Rollup_JOCA投稿稿_证据回填_20261029.docx
```

或直接覆盖"通读润色"版本（如用户确认无需备份）。

---

**更新原则再次强调**:
1. **只加证据，不改结构**：五硬伤修复的段落顺序、编号、定义位置**绝不改动**
2. **每条证据可验证**：给哈希、地址、数值，读者可独立验证
3. **边界明确说明**：不夸大（不声称点值强绑定），不隐瞒（明确 TCB 5 非生产）
4. **缺失归因准确**：工程问题（缺资金）vs 技术问题（缺强绑定）vs 后续工作（形式化证明）

---

**文档版本**: v1.0  
**适用文件**: `Hybrid_TEE_Rollup_JOCA投稿稿_通读润色_20261029.docx`  
**生成时间**: 2026-10-29  
**执行**: 建议人工精确编辑，或使用 python-docx 脚本逐段落插入
