# 阶段 D 报告｜真实 TEE 远程证明与应用执行

> 阶段：D｜状态：**partial**
> - **D-local：completed**
> - **D-quote / D-application / D-integrated：blocked**（本机无 SGX/TDX 硬件）
>
> 本阶段按提示词要求：**不伪造 Quote、不以普通签名或 HMAC 冒充 Quote、不用 fixture 延迟冒充硬件延迟、缺设备绝不静默 fallback 到模拟后记为 real。**

---

## 1. 实际平台（已实测）

| 项 | 实测结果 |
|---|---|
| CPU / 架构 | Apple M5 / **arm64** |
| 操作系统 | darwin |
| SGX 设备节点 | **无**（`/dev/sgx_enclave`、`/dev/sgx_provision`、`/dev/sgx/enclave`、`/dev/sgx/provision` 均不存在） |
| TDX 设备节点 | **无**（`/dev/tdx_guest`、`/dev/tdx-guest` 均不存在） |

结论：本机**无法生成真实 Quote**，D-quote 及以上等级 blocked。

---

## 2. 具体文件与命令

### 新增文件

| 文件 | 说明 |
|---|---|
| `evm/revision/tee_attestation.js` | D1/D2：统一后端契约、fail-closed、reportData 与任务绑定规范编码、DCAP 策略评估 |
| `evm/revision/stageD_attestation.test.js` | D-local 测试与 D01–D12 状态登记，产出 `case_matrix.json` |
| `outputs/stageD_20260916T180557Z/REMOTE_QUOTE_RUNBOOK.md` | 远端真实 Quote 采集运行手册（流程框架 + 官方核对清单，**未杜撰命令**） |

**合约零变更。** 实际命令见 `commands.txt`（均已执行验证）。

测试结果：**8 passing / 0 failing**；12 个 case 登记——`verified=5`、`partial=1`、`blocked=6`，其中 `fixture=4`。

---

## 3. 已实现能力（D-local，可真实执行）

1. **后端契约隔离**：`backendId` 区分 `simulated-hmac` / `sgx-dcap-real` / `tdx-dcap-real`；真实与模拟分开入口与证据类别。
2. **fail-closed**：real 后端无设备时抛 `DEVICE_UNAVAILABLE`；即便强制创建，`getQuote()` 也抛 `NOT_IMPLEMENTED_LOCAL`——**不回退模拟、不伪造 Quote**。
3. **规范编码（32 字节摘要，canonical JSON + sha256）**：
   - `buildReportDataDigest({ execPubkey, domain, nonce, epoch, appDigest })`
   - `buildTaskBindingDigest({ chainId, verifyingContract, taskId, nonce, input/output/trace 承诺, programVersion, daRef })`
   - 已验证对 **chainId / verifyingContract / taskId / nonce / epoch / appDigest / 各类承诺** 任一变化都敏感；缺字段 fail-closed。
4. **策略评估**：显式区分 `OK / invalid / revoked / out-of-date / configuration-needed / unknown / blocked`：
   - `realQuote !== true` 一律 `blocked`（HMAC/普通签名不得冒充 Quote）；
   - `measurement` 不匹配归为**策略拒绝**，不声称密码学签名损坏；
   - `OutOfDate`、`ConfigurationNeeded`、`collateral expired`、TCB 缺失分别归类，**不把非致命码一律当 pass**。

---

## 4. D01–D12 结果

| ID | 等级 | 状态 | fixture | 说明 |
|---|---|---|---|---|
| D01 | D-quote | **blocked** | 否 | 无设备；real 后端 fail-closed，不伪造 |
| D02 | D-local | verified | **是** | nonce/reportData 不一致 → INVALID（缺少新鲜性） |
| D03 | D-local | verified | **是** | 签名有效但 measurement 不在策略 → INVALID（策略拒绝，非密码学损坏） |
| D04 | D-local | verified | **是** | Revoked / OutOfDate（严格与宽松）/ ConfigurationNeeded / collateral expired / TCB 缺失 分别归类 |
| D05 | D-local | verified | 否 | 绑定编码对跨域/跨任务/旧 nonce 敏感；缺字段 fail-closed（纯逻辑，真实可执行） |
| D06 | D-local | verified | 否 | 模拟后端 `realQuote=false`；backendId 不被偷换 |
| D07 | D-integrated | **blocked** | 否 | 需真实受保护执行环境；链上 taskId 唯一性已由阶段 C 的 C10 覆盖 |
| D08 | D-integrated | **blocked** | 否 | 本机无 SGX/TDX 快照能力；仅能证明协议层抗重放（同 C15） |
| D09 | D-application | **blocked** | 否 | 需真实撤销与在途处理；泄钥期正确性依赖密钥未泄露假设 |
| D10 | D-application | **blocked** | 否 | 需真实受保护执行与原生对照 |
| D11 | D-application | **partial** | **是** | 编码层已能区分 appDigest 变化；但 `evaluatePolicy` 未实现 `allowedAppDigests` 强制——**已知缺口，如实记为 partial** |
| D12 | D-integrated | **blocked** | 否 | 需真实 Quote+密钥+签名与 B/C 同一 task 关联 |

> `fixture=true` 的 case 使用构造输入测试策略分支，**不含真实 Quote，不计入真实平台成功样本**。

---

## 5. 验证服务信任与 Quote 公开范围

- **验证路线**：默认采用 *独立验证者执行 DCAP/QVL 验证 → 由认证服务签发证书 → 合约只验证该证书*。
  这是**显式信任桥**，**不能称为"链上自主验 Quote"**。若目标论文不接受新增服务信任，需先取得用户确认——**不暗中更换威胁模型**。
- **撤销语义**（规划，未实现）：需分别作用于新任务、在途任务、已终局任务；撤销不能自行证明旧结果错误，也不能无规则无限阻塞终局；在途任务按预定义独立计算/超时机制收口。
- **Quote 公开范围**：原始 Quote 可能含平台识别信息。默认按**受控私有证据**保存，对外只公开摘要/hash 与非敏感验证结果；是否公开原始字节需先审查批准。原始签名 Quote 与 collateral 字节需完整留存以便**独立重验**，且**不可"脱敏修改"后仍当有效证明**。
- **私钥与 token 绝不进入实验包**。

---

## 6. 未验证的攻击与残余假设

- 未验证（且本阶段不实施）：侧信道、硬件漏洞、实际窃钥、未授权快照攻击。
- 仅在自有测试密钥/测试镜像上做协议层负例。
- 残余假设：泄钥期的正确性依赖"密钥未泄露"；D09 无法在缺少独立反证时给出更强结论。

---

## 7. 当前源码 / 配置哈希

| 项 | 值 |
|---|---|
| gitHead | `615bb3e9f1ae3b88b87f488decc61854cd555e16` |
| gitDirty | `true` |
| **D 阶段 sourceTreeSha256** | `e8467bd4c35cfec9491dc57460f869167c660e54d99d3de9a63d95d01b105cfe` |
| D 阶段 configSha256 | `1eb42cf0a8d4bf640398559186da56a2a6be1d3274f4dbe228db473f6e1b0616` |
| 父（C）sourceTreeSha256 | `ead8b96a915afa53ca94e3bb99208d6621b970be8d261033540c3ad6b227a298` |

---

## 8. 后续 F 可用的数据（当前边界）

- **可用**：D05/D06 的绑定编码与 fail-closed 结论；策略评估的判定分类（供 F 标记 TEE 证据类别）。
- **不可用（不得用于 F）**：任何真实 Quote 生成/验证耗时、collateral 首次取得与缓存验证耗时、公钥登记耗时、应用执行与任务签名耗时——**这些必须来自真实硬件**，当前 `blocked`，F 不得用模拟 HMAC 时间作为 TEE 性能基线。
- 因此 **F-TEE 同样 blocked**；F-local 不依赖 D 真实资源，可先行。

---

## 9. 需要用户提供的资源（最小授权）

- 具备 Intel SGX（DCAP）或 TDX 的 **Linux** 机器，或已授权远端实例（**本阶段不新建计费云实例**；如确需，将先列出资源、预算与数据范围并取得批准）。
- 在该机器上执行官方 quote 生成工具与验证库的权限。
- 运行本地 PCCS 或访问 Intel PCS 的网络权限（仅取公开 collateral）。
- **不需要、也不接受**任何私钥、助记词或 RPC token 进入实验包。
