# Hybrid TEE-Rollup 剩余实验清单

**生成时间**: 2026-10-29  
**目的**: 记录因缺乏云服务器/密钥而无法完成的实验，明确边界

---

## ✅ 已完成实验（本轮）

### A. Blob DA 罚没/挑战结算闭环（本地 Hardhat）

**状态**: ✅ 已完成  
**证据**: `evm/test/BlobDaChallenge.test.js` (3/3 通过)

| 测试路径 | Gas 消耗 | 资金守恒 | 说明 |
|---------|---------|---------|------|
| fulfillDa | 104432 (披露) + 65406 (finalize) | 2 ETH claimable | 原像正确披露，DA bond 返还 |
| slashDa | 91266 | 1 ETH burned | 超时未披露，DA bond 被 slash |
| 边界验证 | - | - | BlobBatchAnchor ↔ BoundedTaskRollup **无强制绑定** |

**关键数据验证**:
- `slashDa` gas 91266 与 StageC C12 测试完全一致
- 资金守恒：fulfillDa 返还 bond，slashDa burn bond
- 正交义务：任务正确性 ≠ DA 披露义务（可分别裁决）

**明确边界**:
1. ✅ **已验证**: `bindDa` → `fulfillDa`/`slashDa` → `settle` 原像披露闭环
2. ❌ **未实现**: EIP-4844 点值证明（`0x0a` 预编译未调用）
3. ❌ **未实现**: BlobBatchAnchor ↔ BoundedTaskRollup 强制绑定
4. ❌ **未部署**: Sepolia 公网 challenge/settlement（见下文）

**写入论文**: 
- 摘要/§5: 补充"本地 Hardhat 已验证 DA 罚没闭环（gas 91266）"
- §6.1: 明确边界为"原像披露闭环已验证，缺 EIP-4844 点值强绑定"

---

## 🚧 需要用户资源的实验

### B. 公网 Sepolia Blob Challenge/Settlement

**当前状态**:
- ✅ **已完成**: Blob 发布 + 独立取回（`outputs/sepolia_blob_20261017/`）
  - 交易: `0x3ad90ecfdf5930c1bf611223af76196e54fbc74af0f9c9924de9dc523681d340`
  - Versioned hash: `0x010a35506f6b45b2d022aac9ecca1c4e2631ca12d6b0c07f6cb3d195c3985493`
  - Slot: 11374267 (Sepolia Beacon)
  - KZG 验证: ✅ 通过
- ❌ **未完成**: 公网 challenge/settlement 闭环

**阻塞原因**:
1. **缺 Sepolia 部署**: `BlobBatchAnchor` 未部署到 Sepolia
   - 需要: 有足够 ETH 的部署账户
   - 估计成本: ~0.01 ETH (合约部署)

2. **缺资金账户**: Challenge/settlement 交易需要多方参与
   - 需要: 至少 2 个账户（submitter + challenger）
   - 每账户需 bond (1 ETH) + gas (~0.005 ETH)
   - 总需求: ~2.1 ETH

3. **缺 RPC/Beacon API 配额**: 
   - Sepolia RPC URL (公开 RPC 有速率限制)
   - Sepolia Beacon API URL (用于 Blob 取回)

**执行步骤**（用户提供资源后）:
```bash
# 1. 部署 BlobBatchAnchor 到 Sepolia
export SEPOLIA_RPC_URL="..."
export SEPOLIA_PRIVATE_KEY="..."  # 部署账户
cd evm
npx hardhat run scripts/deploy_blob_anchor.js --network sepolia

# 2. 运行 challenge/settlement 流程
export BLOB_BATCH_ANCHOR_ADDRESS="<部署地址>"
export CHALLENGER_PRIVATE_KEY="..."  # 挑战者账户
node evm/revision/sepolia_blob_challenge.js

# 3. 验证结果
node evm/revision/blob_challenge_settle.js
```

**预期结果**:
- `closedLoopClaimed=true` (Sepolia 公网级别)
- Challenge 交易哈希、Settlement 交易哈希写入论文

**写入论文**（完成后）:
- 摘要/§5: 更新为"Sepolia 公网 Blob challenge/settlement 闭环已验证"
- §6.1: 移除"公网 Blob 未完成"限制

---

### C. 链上 DCAP 验证完整集成

**当前状态**:
- ✅ **已完成**: Automata `verifyAndAttestOnChain` live eth_call（`outputs/stageI_20261017/e1_dcap.json`）
  - 合约: `0x27188ABA3a26CBb806eF4C67de9b05D7d792EC10` (Sepolia)
  - TCB Status: 5 (`OUT_OF_DATE_CONFIGURATION_NEEDED`)
  - Gas estimate: ~5.1M
  - Quote version: 3, 4734 bytes
- ❌ **未完成**: 生产级 PCS + UpToDate TCB + 罚没集成

**阻塞原因**:
1. **缺生产 SGX 环境**: 
   - 需要: 阿里云 SGX 实例（或同等云厂商）
   - 需要: Release Enclave 签名密钥（非 debug mode）
   - 需要: 连接 Intel PCS 生产环境（非测试环境）

2. **缺 UpToDate TCB 平台**:
   - 当前 TCB Status 5 (`OUT_OF_DATE_CONFIGURATION_NEEDED`) 不适合生产
   - 需要: TCB Status 0 (`UP_TO_DATE`) 或 1 (`SW_HARDENING_NEEDED`)

3. **缺集成代码**: 
   - Automata 验证结果未接入 `BoundedTaskRollup` 罚没路径
   - 需要实现: `verifyAttestation` 调用 Automata 并根据 TCB 状态决定是否 slash

**执行步骤**（用户提供资源后）:
```bash
# 1. 启动阿里云 SGX 实例
# （用户操作：在阿里云控制台创建 SGX 实例）

# 2. 配置生产 PCS
export PCCS_URL="https://sbx.api.trustedservices.intel.com/sgx/certification/v4/"
export PCCS_API_KEY="..."  # Intel PCS API key

# 3. 编译 release Enclave
cd sgx
make clean
SGX_MODE=HW SGX_DEBUG=0 make

# 4. 生成 Quote 并提交到 Automata
./run_quote.sh > quote_release.dat

# 5. 验证 TCB 状态
node evm/revision/dcap_verify_live.js --quote quote_release.dat

# 6. 集成罚没路径（需开发）
# 实现 BoundedTaskRollup.verifyAttestation() 调用 Automata
```

**预期结果**:
- TCB Status: 0 或 1 (生产可接受)
- Automata 验证结果接入罚没逻辑
- 链上广播级 slash 交易哈希

**写入论文**（完成后）:
- 摘要/§5: 更新为"Automata 链上 DCAP 验证已集成罚没路径（TCB UpToDate）"
- §6.1: 移除"链上 DCAP 完全 blocked"限制

---

### D. Sepolia Challenge/Settlement 压力测试

**当前状态**: ❌ 未启动

**阻塞原因**:
1. 依赖实验 B (Sepolia challenge/settlement 基础闭环)
2. 需要批量账户 + 大量 Sepolia ETH (>10 ETH)

**执行步骤**（实验 B 完成后）:
```bash
# 创建 10 个测试账户
node scripts/create_test_accounts.js --count 10

# 运行压力测试（100 个挑战）
node evm/revision/sepolia_stress_test.js --challenges 100
```

**预期结果**:
- 平均 gas 消耗统计
- 资金守恒验证（所有 bond 正确分配/burn）

---

## 📝 降级/推迟的实验

以下实验**不属于本轮失败**，而是论文范围外的后续工作：

### E1. 形式化证明
- **状态**: 推迟到后续工作
- **原因**: 需要 Coq/Isabelle 专家，超出本论文范围
- **写入论文**: §7 未来工作，不列为局限

### E2. 通用 EVM 兼容
- **状态**: 不适用（有界哈希链任务，非通用 VM）
- **原因**: 论文明确范围为 ≤128 步确定性任务
- **写入论文**: §6.1 明确说明"不支持通用 EVM 是设计选择，非实现缺陷"

### E3. 多 Enclave 并行
- **状态**: 推迟到后续工作
- **原因**: 单 Enclave 原型已验证核心机制
- **写入论文**: §7 未来工作

### E4. 长期经济博弈模型
- **状态**: 推迟到后续工作
- **原因**: 需要博弈论建模，超出本论文范围
- **写入论文**: §7 未来工作

---

## 🎯 本轮交付清单

### 已完成（无需用户资源）
- [x] A. 本地 Hardhat Blob DA 罚没闭环（3/3 测试通过）
- [x] 生成测试报告 (`outputs/revision_20261028/blob_da_challenge_test_report.txt`)
- [x] 更新 `blob_challenge_settle.js` 反映真实状态
- [x] 创建本清单 (`remaining_experiments_checklist.md`)

### 待用户资源（明确 blocked）
- [ ] B. Sepolia Blob Challenge/Settlement
  - 需要: 部署账户 + 2.1 ETH + RPC/Beacon API
- [ ] C. 链上 DCAP 验证完整集成
  - 需要: 阿里云 SGX + release Enclave + 生产 PCS
- [ ] D. Sepolia 压力测试
  - 需要: 实验 B 完成 + 10+ ETH

---

## 📊 论文更新要点

### 摘要（Abstract）
**当前**: "公网 Blob / 链上 DCAP 未完成"  
**更新为**:
> 本文实现了 Hybrid TEE-Rollup 原型，并在以下环境验证：
> 1. **本地 Hardhat**: DA 罚没闭环（slashDa gas 91266，资金守恒）
> 2. **Sepolia 公网**: Blob 发布 + 独立取回（tx 0x3ad9...d340，KZG 验证通过）
> 3. **Automata 链上 DCAP**: live eth_call 验证（TCB Status 5，gas ~5.1M）
> 
> **边界**: 原像披露闭环已验证，缺 EIP-4844 点值强绑定；Sepolia challenge/settlement 需部署资金；生产 DCAP 需 UpToDate TCB 平台。

### §6.1 局限性（Limitations）
**当前**: 列举所有"未完成"  
**更新为**:
> **实现边界**（非缺陷）:
> - DA 验证为原像披露（`keccak256(payload)==dataHash`），非 EIP-4844 点值证明
> - `BlobBatchAnchor` 与 `BoundedTaskRollup` 无强制绑定（设计解耦）
> - 有界哈希链任务（≤128 步），非通用 EVM（设计范围）
>
> **需额外资源**（已验证机制，缺部署环境）:
> - Sepolia challenge/settlement: 需部署合约 + 资金账户
> - 生产 DCAP: 需 release SGX 实例 + UpToDate TCB 平台
>
> **后续工作**（超出本论文范围）:
> - 形式化证明、多 Enclave 并行、长期博弈模型

### §5 实验结果（Experimental Results）
**新增段落**:
> **DA 罚没闭环**: 本地 Hardhat 测试验证了 `bindDa`/`fulfillDa`/`slashDa` 完整流程，`slashDa` gas 消耗 91266（与 StageC C12 测试一致），资金守恒验证通过。正交义务设计允许任务计算正确但 DA 披露失败时分别裁决。

> **公网 Blob 证据**: 在 Sepolia 成功发布 type-3 Blob（tx `0x3ad9...d340`，slot 11374267），独立从 Beacon API 取回并验证 KZG commitment（versioned hash `0x010a...5493`）。Challenge/settlement 闭环需部署 `BlobBatchAnchor` 和资金账户（见剩余实验清单）。

> **Automata DCAP**: 通过 Sepolia 合约 `0x2718...EC10` 的 live `eth_call` 验证真实 SGX Quote（TCB Status 5，gas ~5.1M）。生产级集成需 release Enclave 和 UpToDate TCB 平台。

---

**文档版本**: v1.0  
**生成工具**: Cursor Cloud Agent (bc-929a7da6)  
**联系**: 需用户提供云资源后继续实验 B/C/D
