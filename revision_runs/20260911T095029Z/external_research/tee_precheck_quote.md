# TEE 预检 / 阻塞 + 官方 Quote 验证续跑建议

- **run_id**: 20260911T095029Z ｜ **日期**: 2026-09-11
- **研究者角色**: 仅独立研究与证据写入，未修改合约/测试；**未购买/登录/开通任何云服务**
- **配套**: `sources.json`、`comparison_report_zh.md`

---

## 1. 环境云凭据预检（布尔存在性，不读值、不查个人文件）

| 检查项 | 结果 |
|---|---|
| AWS / GCP / Azure / Aliyun / Tencent / DO / Linode / Akamai / Hetzner / Scaleway 等凭据名 | **全部 unset（布尔 = false）** |

**含义**：本环境无法以编程方式向任何云商查询 TDX 实例的**实时价格、库存（现货）、最低计费增量、区域配额**。因此所有账户相关事实在本文中一律标记为「未核实」，且**不因无凭据而替用户下单/登录/开通**。

---

## 2. TEE 预检结论（基于官方公开文档，已核实部分）

- ✅ **提供方存在性（已核实）**：Intel 官方产品页列出 TDX 云商 = 阿里巴巴、Google Cloud、Microsoft Azure（另列蚂蚁、Thales）。阿里云官方文档确认 ECS TDX 实例（`ecs.g8i.xlarge` 及以上）真实存在。
- ✅ **区域可用性（已核实，但仅文档层面）**：TDX 在阿里云**特定 AZ** 开放——北京 I/L、杭州 J、中国香港 B/C/D、新加坡 B。注意：TDX **非全地域全 AZ**，选 region 前须锁定支持 AZ。
- ✅ **Quote / DCAP 支持（已核实）**：
  - Quote 生成：用户态 `/dev/tdx_guest`（ACL3 内核 ≥5.10.134-16.al8）或 ConfigFS TSM `/sys/kernel/config/tsm/report`（上游 ≥6.7 镜像）。
  - DCAP：实例内 PCCS 地址 `sgx-dcap-server-vpc.<region_id>.aliyuncs.com`；验证需拉 collateral（TCB Info / QE Identity / PCK CRL）。DCAP 链路完整。
- ⚠️ **实时价格 / 库存 / 最低计费（未核实）**：无云凭据，无法确认。第三方快照 `ecs.g8i.xlarge ≈ ¥1.0885/h` 仅作量级参考。

---

## 3. 阻塞项（BLOCKING）

| 阻塞项 | 原因 | 是否可本环境解除 |
|---|---|---|
| 实时 TDX 单价、最低计费增量、现货库存 | 需云凭据/控制台 | ❌ 不可（须用户提供凭据或自行登录） |
| 500 元内确切可行性承诺 | 依赖上项 | ❌ 不可；仅能给「量级可行」（≤~19 天 @ ¥1.0885/h 第三方价） |
| 真实 Quote 采集 | 需先有运行中 TDX 实例 | ❌ 不可（须先开通实例，属用户动作） |
| 区域配额（如北京 I 是否当前有 g8i 现货） | 需控制台/RunInstances | ❌ 不可 |

> 所有阻塞项均**不通过替用户购买/登录解除**；仅给出可续跑的验证流程。

---

## 4. 官方 Quote 验证续跑建议（Run-continuation，避免样例 Quote）

> 原则：**不生成/不伪造样例 Quote**。以下为「获取并验证真实 Quote」的操作序列，执行主体在获得云凭据且用户开通实例后进行。

### 步骤 A — 开通 TDX 实例（用户动作，agent 不代做）
1. 选定支持 AZ（如 `cn-beijing-i`），`RunInstances` 参数：`SecurityOptions.ConfidentialComputingMode=TDX`、`InstanceType=ecs.g8i.xlarge`、UEFI 镜像（Alibaba Cloud Linux 3/4 或 Ubuntu 24.04 / Debian 13.1+）。
2. 开通后**不要**在实例内执行 `reboot`（TDX 实例不支持内部重启）。

### 步骤 B — 采集真实 TD Report / Quote（实例内执行，命令来自阿里云官方文档）
```bash
# 1) 确认 TDX 已启用
lscpu | grep -i tdx_guest

# 2) 确认证明接口存在（二选一）
ls -l /dev/tdx_guest                 # ACL3 内核
# 或
ls -d /sys/kernel/config/tsm/report  # 上游 6.7+ 镜像

# 3) 获取本实例地域 PCCS 地址（DCAP 缓存服务）
token=$(curl -s -X PUT -H "X-aliyun-ecs-metadata-token-ttl-seconds: 5" "http://100.100.100.200/latest/api/token")
region_id=$(curl -s -H "X-aliyun-ecs-metadata-token: $token" http://100.100.100.200/latest/meta-data/region-id)
PCCS_HOST=sgx-dcap-server-vpc.${region_id}.aliyuncs.com

# 4) 用官方 tdx-lab 工具生成并验证 Quote
git clone https://gitee.com/anolis/go-tdx-guest.git
cd go-tdx-guest/tools/tdx-lab
GOPROXY='https://goproxy.cn,direct' go build -o tdx-lab .
./tdx-lab --skip-early --pccs-url ${PCCS_HOST}
```
- 官方提示：「当前不承诺 tcb 状态为 UpToDate，部分场景下 Strict Tcb Check 失败符合预期」——属已知现象，非失败。

### 步骤 C — 独立验证 Quote（落地到项目证据）
1. 取步骤 B 产出的**真实** Quote（含 PCK 证书链），调用 DCAP 验证：校验 ECDSA 签名 + 证书链至 Intel Root of Trust；拉取 collateral（TCB Info / QE Identity / PCK CRL）核对平台 TCB 与吊销状态。
2. 将**真实 Quote 字节 + collateral + 验证结果**写入本项目证据文件（例如 `revision_runs/20260911T095029Z/external_research/tdx_quote_evidence.json`），**不要**用占位/样例 Quote 填充。
3. 与 TEEROLLUP 论文要求对齐：论文要求 sequencer 用 TEE 机密密钥对执行结果签名并上链；验证侧应确认 Quote 中的测量值（MRTD / RTMR[0~3]）与部署的 sequencer 软件度量一致。

### 步骤 D — 续跑触发条件
- 当用户提供云凭据 / 确认已开通 TDX 实例后，可继续执行 B→C，并将真实证据回填。
- 若仅做**文档级**核实（无需真实实例），本报告与 `sources.json` 已满足；真实 Quote 验证为**可选续跑项**，且必须由真实实例产出。

---

## 5. 一句话结论
- TDX 提供方/区域/Quote/DCAP 在**官方文档层面已核实可用**；**价格、库存、最低计费、真实 Quote** 因无云凭据而**未核实、不可承诺**；500 元内短租在第三方快照价下为「量级可行」。所有阻塞项通过「用户提供凭据 + 开通实例 + 跑官方 tdx-lab」续跑，agent 不代购/不伪造 Quote。
