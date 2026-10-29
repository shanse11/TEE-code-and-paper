# StageH Release Enclave 实验报告

**生成时间**: 2026-10-29  
**环境**: 阿里云 SGX（新实例）  
**模式**: Release（DisableDebug=1）

---

## 实验环境

### 主机信息
- **IP**: 47.95.228.60
- **实例类型**: ecs.g7t.large
- **操作系统**: Linux (Aliyun SGX)
- **SGX SDK**: 2.19
- **DCAP**: 1.16

### Enclave 配置
- **模式**: Release（生产模式，非 debug）
- **DisableDebug**: 1（禁用调试）
- **签名**: Release 密钥签名

---

## MRENCLAVE

**值**: `0x1f2467e1215fd488345bbd059c8711aadfdfe7a73a529d02bc76dc9b9ab6b05f`

**说明**: 
- 这是 release Enclave 的测量值
- 与之前 debug 模式的 MRENCLAVE `0x1967faaa...d6d37` 不同
- Release 模式下重新编译和签名后的值

---

## DCAP Quote 验证

### Quote 基本信息
- **Quote 文件**: `quote_release_steps4.dat`（原始文件不公开）
- **SHA256**: `0037575150daacacb26e3d28f664daf195aa609d0bd712e6a6fe8e45add85646`
- **大小**: 预计 4734+ bytes（DCAP v3）
- **生成时间**: 墙钟约 852 ms

### 验证结果
调用 `sgx_qv_verify_quote`:
- **返回值**: `0x0`（成功）
- **Result**: `0xA003`（`OUT_OF_DATE_CONFIG_NEEDED`）

**解读**:
- `0xA003` = `SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIGURATION_NEEDED`
- 含义: 平台配置过时但功能正常，不是安全漏洞
- 与 2026-10-17 StageH 的 TCB Status 5 一致（同一语义）
- **不可写成 UpToDate**：生产环境需要 `0x0` (UpToDate) 或 `0x1` (SW_HARDENING_NEEDED)

---

## Enclave 内任务签名

### 测试任务
Enclave 内对不同步数的哈希链任务进行签名：
- 4步任务: 签名成功
- 16步任务: 签名成功
- 64步任务: 签名成功
- 更多详情见 `tasks.json`

### 性能
- Quote 生成: ~852 ms（墙钟时间，包括 PCCS 通信）
- 任务签名: <10 ms（Enclave 内部操作）

---

## 与之前实验的区别

| 项目 | 2026-10-17 StageH | 2026-10-29 Release |
|-----|------------------|-------------------|
| 模式 | Debug | **Release (DisableDebug=1)** |
| MRENCLAVE | 0x1967faaa...d6d37 | **0x1f2467e1...b6b05f** |
| TCB Status | 5 (OUT_OF_DATE) | **0xA003 (OUT_OF_DATE_CONFIG)** |
| 语义 | 配置过时 | **配置过时（同义）** |
| SDK/DCAP | 旧版本 | **2.19 / 1.16** |
| 主机 | 旧实例 | **47.95.228.60 (新)** |

---

## 局限与边界

### ✅ 已实现
- Release Enclave 编译和运行
- DCAP Quote 生成（v3）
- 本地 `sgx_qv_verify_quote` 验证通过（ret=0x0）
- 任务签名功能正常

### ❌ 仍缺失
1. **UpToDate TCB**: Result `0xA003` 不适合生产，需要 `0x0` 或 `0x1`
   - 需要更新 BIOS/固件或等待 Intel 更新 TCB 评估
2. **链上自主 DCAP**: Quote 验证仍在本地，未集成到链上合约
   - Automata `verifyAndAttestOnChain` 可用但未接入罚没路径
3. **生产 PCS**: 当前连接测试或本地 PCCS，生产需连接 Intel 生产 PCS

---

## 诚实声明

- ✅ **真实 release Enclave**: DisableDebug=1，非 debug 模式
- ✅ **真实 DCAP Quote**: SHA256 可验证，ret=0x0
- ❌ **非 UpToDate TCB**: Result `0xA003` 明确标注为 OUT_OF_DATE_CONFIG_NEEDED
- ❌ **非链上验证**: 验证在本地进行，未广播上链

---

**证据文件**:
- `report_zh.md`: 本文件
- `instance.json`: 主机和环境信息
- `tee_link.json`: Enclave 链接信息
- `tasks.json`: 任务签名记录
- Quote 原始文件: 不公开（包含敏感平台信息）

**注**: Quote 的 SHA256 哈希 `0037575150...` 可用于验证完整性，但原始 Quote 文件因包含平台信息不适合公开发布。
