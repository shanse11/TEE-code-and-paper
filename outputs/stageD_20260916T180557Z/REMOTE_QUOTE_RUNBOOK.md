# 阶段 D：远端真实 Quote 采集运行手册

> 用途：在**具备 Intel SGX（DCAP）或 Intel TDX 的平台**上采集真实 Quote 并独立验证，产出可供
> `evm/revision/tee_attestation.js` 的 `evaluatePolicy()` 消费的 verification 结构，从而解锁 D-quote 及以上等级。
>
> **重要**：本手册只给出**流程框架与核对清单**。具体命令、设备路径、TCB 字段取值与返回码
> **必须按 Intel 官方文档与所用库版本核对**，本手册不凭记忆杜撰任何命令参数。
> 阶段 D 提示词明确要求："不要凭记忆杜撰命令、设备路径、TCB字段或返回码。"

---

## 0. 当前状态（为何需要本手册）

本机实测：`Apple M5 / arm64 / darwin`，`/dev/sgx_enclave`、`/dev/sgx_provision`、`/dev/sgx/enclave`、
`/dev/sgx/provision`、`/dev/tdx_guest`、`/dev/tdx-guest` **均不存在**。

因此 `createProvider(SGX_DCAP|TDX_DCAP)` 会抛 `DEVICE_UNAVAILABLE`（fail-closed），
`provider.getQuote()` 会抛 `NOT_IMPLEMENTED_LOCAL`——**不回退模拟、不伪造 Quote**。

---

## 1. 前置条件核对（逐项记录，不要跳过）

| 项 | 需核对内容 | 记录字段 |
|---|---|---|
| 平台类型 | SGX（DCAP）还是 TDX；具体 CPU 型号 | `platformType` |
| 设备节点 | 实际存在的设备路径（**以本机 `ls` 结果为准**） | `deviceNodes[]` |
| 官方 SDK / 工具链 | 名称、**版本**、官方下载/文档 URL、获取日期 | `sdkVersion`, `sourceUrl`, `retrievedAt` |
| 验证库 | QVL 或等价官方验证库的名称、**版本**、URL | `verifierLib`, `verifierVersion` |
| Collateral 来源 | PCCS 自建缓存 或 Intel PCS；版本/端点 | `collateralSource`, `collateralVersion` |
| 策略版本 | 允许的 measurement 清单、TCB 要求 | `policyVersion` |

> 以上每一项都要保存 URL、获取日期与版本，供后续独立复核。**版本不实则结论不可用。**

---

## 2. 流程（在具备硬件的平台上执行）

### 步骤 1：确认设备与工具链
- 列出实际设备节点（不要照抄文档路径）。
- 按官方文档安装/确认 SDK 与验证库版本。

### 步骤 2：在受保护环境内生成应用执行密钥
- 执行私钥**在受保护环境内生成并保持不可导出**；只有通过验证后才授权该公钥参与协议。
- 不应把私钥释放给宿主；配置适用的生命周期策略。
- 记录：公钥、`appDigest`（应用/镜像摘要）、构建输入与镜像标识。

### 步骤 3：构造 reportData
调用本仓库已实现的规范编码（**可直接复用，不需重写**）：

```js
const { buildReportDataDigest } = require("./evm/revision/tee_attestation");
const reportDataDigest = buildReportDataDigest({
  execPubkey, domain: "HYBRID_BOUNDED_TASK_V1",   // 协议域，需与链上 DOMAIN 一致
  nonce,        // 验证方提供的 fresh nonce
  epoch,        // session/epoch
  appDigest,    // 应用摘要
});
```

- `reportData` 长度有限（SGX/TDX 通常为 64 字节），**不能假定任意长字段可直接装入**；
  这里固定输出 32 字节摘要，放入 reportData 前 32 字节并按规定补齐。
- 记录：长度、hash 算法（sha256）、编码方式（canonical JSON）。

### 步骤 4：生成 Quote
- 用官方支持路径生成 Quote，把步骤 3 的摘要写入 reportData。
- **命令与参数以官方文档为准**，不要沿用任何未经核对的记忆命令。

### 步骤 5：取得 collateral 并**独立**验证
- 验证必须在**不依赖发布程序"自报成功"**的验证进程中进行。
- 至少检查：签名、证书链、collateral、TCB 状态、撤销状态、有效期、measurement 策略、
  nonce/reportData 一致性、执行公钥绑定。

### 步骤 6：映射为 verification 结构并调用策略
```js
const { evaluatePolicy } = require("./evm/revision/tee_attestation");
const verdict = evaluatePolicy({
  realQuote: true,              // 只有真实硬件 Quote 才能置 true
  signatureValid,               // 步骤 5 结论
  nonceMatches,                 // reportData/nonce 与验证方挑战一致
  measurement,                  // 实际 measurement
  tcbStatus,                    // 原样记录，如 OK / UpToDate / OutOfDate / Revoked / ConfigurationNeeded / SWHardeningNeeded
  collateralStatus,             // ok / expired / unavailable
  execPubkey,
  validUntil,
}, {
  allowedMeasurements: [...], revokedMeasurements: [...],
  requireUpToDate: true, allowConfigurationNeeded: false,
});
```
- `evaluatePolicy` 显式区分 `OK / invalid / revoked / out-of-date / configuration-needed / unknown / blocked`，
  **不会把非致命码一律当 pass**；`realQuote !== true` 一律 `blocked`。

### 步骤 7：留存证据
- 保存**原始签名 Quote 与 collateral 字节**以便独立重验；原始字节**不可"脱敏修改"后仍当有效证明**。
- 原始 Quote 可能含平台识别信息：默认按**受控私有证据**保存，对外只公开摘要/hash 与非敏感验证结果；
  是否公开需先审查批准。
- **私钥与 token 绝不进入实验包**。

---

## 3. 验证路线与信任桥（需用户确认后再实施）

默认优先路线：**独立验证者执行 DCAP/QVL 验证 → 由认证服务签发证书 → 合约只验证该证书**。

> 这是**显式信任桥**，不能称为"链上自主验 Quote"。若目标论文不接受新增服务信任，
> 需先取得用户确认，不得暗中更换威胁模型。

如采用该桥，证书必须绑定：执行公钥、程序、域、epoch、有效期、policy 摘要、验证结果；
并明确登记管理信任与更新/撤销权限。

---

## 4. 明令禁止

- ❌ 伪造 Quote。
- ❌ 以普通签名或 HMAC 冒充 Quote（`realQuote` 必须真实反映来源）。
- ❌ 用 fixture 测出的延迟冒充真实硬件延迟。
- ❌ 缺设备/缺 collateral 时静默 fallback 到模拟并把结果记为 real。
- ❌ 实施侧信道、硬件漏洞、实际窃钥或未授权快照攻击。

## 5. 需要用户提供的资源（最小授权）

- 具备 SGX/TDX 的 Linux 机器或已授权远端实例（**本阶段不新建计费云实例**；如确需，将先列出资源、预算与数据范围并取得批准）。
- 在该机器上执行官方 quote 生成工具与验证库的权限。
- 运行本地 PCCS 或访问 Intel PCS 的网络权限（仅取公开 collateral）。
- **不需要、也不接受**任何私钥、助记词或 RPC token 进入实验包。
