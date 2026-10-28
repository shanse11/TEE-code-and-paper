# 阶段 D｜给 Codex：真实 TEE 远程证明与应用执行

请在`/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup`实施本阶段，不只输出方案。先读同包总控和实际B/C handoff；独立执行时遵守下文完整边界。

## 1. 目标、前置和可分开交付的成果

阶段A交接：`outputs/stageA_20260916T162724Z/stageA_freeze/manifest/run_manifest.json`，复用现有配置/记录器。A仅local/offline，新增真实TEE profile必须versioned，不能把真实Quote混入simulated-only记录。

D分四个验收等级：D-local适配器/负例；D-quote真实硬件Quote且独立验证；D-application已证明应用内实际执行与密钥绑定；D-integrated与B/C协议联调。仅有D-quote不算端到端真实TEE实验完成。

选择一种可实际获得的SGX或TDX，不要求双平台，不买云实例。先核对用户提供环境、官方工具版本及访问权限；本机无硬件不能生成真实Quote。可在用户已有授权远端运行；新建计费资源、注册付费接口需先给出资源、预算和数据范围并取得批准。缺硬件时完成D-local和远端可运行脚本/说明，记录blocked并让不依赖真实硬件的工作继续。

不实施侧信道、硬件漏洞、实际窃钥或未授权快照攻击；只在自有测试密钥/测试镜像上做协议层负例。禁止伪造Quote、以普通签名或HMAC冒充Quote、使用fixture测出的延迟冒充真实硬件延迟。

## 2. 读取现状并确定验证路线

读取`tee_rollup_demo/attestation.py`、主执行程序、`MockTEEVerifier.sol`、B/C任务摘要/nonce/epoch/权限接口，以及已有`external_research/tee_precheck_quote.md`。先判断已有模块可复用多少，不创建同名影子实现。

从提供商和Intel等官方来源确认所选平台真实接口、验证库、Quote类型、collateral和版本；检索只用于确认流程，保存URL、获取日期和依赖版本。不要凭记忆杜撰命令、设备路径、TCB字段或返回码。

给出唯一实际路线：

- 独立验证者执行DCAP/QVL等适用验证，再发认证服务签名证书，合约只验该证书：这是显式信任桥，不能称链上自主验Quote。
- 如果仓库已有可靠链上证明桥，可复用并单独验证其证明/验证成本与假设；不为本阶段临时发明通用ZK证明系统。

默认优先完成真实Quote+独立验证+明确可信注册服务的可执行路线；如目标论文不接受新增服务信任，先让用户确认，不暗中换威胁模型。

## 3. 实现任务

### D1：统一后端接口但隔离真实与模拟

定义与现有程序兼容的AttestationProvider/Verifier契约：生成challenge/nonce、获取Quote、验证、返回结构化decision/measurement/reportDataDigest/TCB状态/collateral有效期/应用密钥/失败原因。

真实与模拟分开entrypoint、backendId和证据类别；real模式缺设备、验证失败或无法拿collateral时fail-closed。仅显式fixture模式允许Mock，记录realQuote=false。单元测试不得依赖联网。

### D2：应用、执行公钥与任务绑定

固定源码commit、构建输入、镜像/启动链、运行配置、程序摘要和允许measurement。解释被度量的是平台/TD/启动镜像还是应用本身；TDX平台度量不能自动证明可变客户机里任意程序身份。要有不可变镜像、可核验启动/运行测量或可信加载策略，能追溯真正执行程序。

在受保护环境内生成执行私钥并保持不可导出；只有通过验证后才授权该公钥参与协议，不应把私钥释放给宿主。配置适用的生命周期策略。

将执行公钥、协议域、验证方fresh nonce、session/epoch和应用摘要规范编码后作摘要写入平台允许的reportData；记录长度、hash算法和编码，不假定所有长字段能直接装入。任务签名另绑定chainId、verifyingContract、taskId、nonce、input/output/trace承诺、程序版本、DA引用，防跨链跨任务重放。

SGX enclave、TDX guest管理员、宿主各自权限写清；guest root能访问的密钥不能无条件宣称对所有guest软件保密。应用身份未补齐，D-application不能通过。

### D3：真实Quote与独立验证

使用真实平台官方支持路径获取Quote，在不依赖发布程序“自报成功”的验证进程检查签名、证书链、适用collateral、TCB、撤销、有效期、measurement策略、nonce/reportData和公钥绑定。

策略显式区分OK、invalid/revoked、out-of-date、configuration-needed及unknown，不将所有非致命码当pass；允许某状态需明确政策与限制。验证返回值、工具版本、policy版本及collateral版本可追溯。Quote本身并不自动带应用要求的新鲜性，要验证challenge上下文。

保存原始签名Quote/collateral以便独立重验，原始字节不可“脱敏修改”后当有效证明。原始Quote可能含平台识别信息，公开与否先审查/批准；默认受控私有证据、公开摘要和hash、非敏感验证结果。私钥和token绝不入实验包。

### D4：登记、撤销与B/C联调

如果链上只接受验证服务认证，证书必须绑定执行公钥、程序、域、epoch、有效期、policy摘要及验证结果；防未经认证密钥直接注册。登记的管理信任、更新/撤销权限明确。

撤销分别作用于新任务、在途任务、已终局任务。撤销不能自行证明旧结果错误，也不能无规则无限阻塞终局；在途任务按预定义独立计算/超时机制收口。若B/C不支持所需状态，做最小接口改动并重跑其安全/资金回归。

联调至少走真实受保护执行→应用结果签名→独立验证注册→本地B/C接受任务→观察者挑战/终局。若L1仍本地，正确标注“real TEE + local EVM”，不是公网端到端。

## 4. 验收用例与分类

| ID | 场景 | 期望证据 |
|---|---|---|
| D01 | 真实硬件、正确measurement与新nonce | 原始Quote摘要、独立verify输出、应用/镜像映射 |
| D02 | 公钥或reportData替换 | Quote签名/上下文验证拒绝 |
| D03 | 合法Quote但不在measurement策略 | policy拒绝；不是声称密码签名损坏 |
| D04 | collateral失效、不可接受TCB或撤销 | 对应policy拒绝/blocked，记录真实状态或明确fixture |
| D05 | 旧nonce/epoch、跨chain/contract/task | 不登记错误密钥、不接受重放结果 |
| D06 | 非TEE进程伪装real/缺设备fallback | 明确失败，backend不偷换 |
| D07 | 重启后旧任务重复执行/提交 | 链上nonce/epoch防重放，正确恢复状态 |
| D08 | 自有测试快照回滚或等价旧状态重放 | 区分真实快照与仿真，只证明协议抗重放 |
| D09 | 同key同task互斥双签/测试泄钥 | 可验证双签或计算反证、撤销与在途处理；不宣称硬件阻止已泄露密钥签名 |
| D10 | 真实执行与原生参考程序同输入 | 输出一致、任务/程序/DA绑定一致 |
| D11 | 应用镜像变化但平台身份相近 | 应用绑定应拒绝或明确信任漏洞 |
| D12 | 真实任务接入B/C并完成裁决提现 | 与同task的真实Quote/密钥/签名关联，不是独立展示两组无关实验 |

难以真实制造的TCB撤销等case可用fixture测policy分支，但必须标记fixture，不计入真实平台成功样本。若缺独立反证，泄钥期正确性依赖密钥未泄露假设，要写进限制。

## 5. 指标与对照

分别测真实Quote生成、collateral首次取得、缓存验证、冷/热验证、公钥登记、应用执行、任务签名、重启接续。一次性证明开销与每会话/每任务摊销分开；缓存策略、有效期和是否含网络耗时写清。

优先使用同硬件同输入同程序的非TEE原生执行对照；平台无法同硬件对照则记录不同CPU/实例干扰，不将模拟HMAC时间作为硬件隔离开销。模拟后端可另列功能控制组。

此阶段采集基础真实样本，F负责正式重复设计；预先固定尝试数与超时，保存失败重试，不只收集成功样本。monotonic计本机耗时，跨机UTC要有时钟误差，不能直接相减伪造精度。

## 6. 交付、闸门与最终回复

提供实际可执行本地测试和远端采集/验证入口、依赖版本、必要环境变量名称（无值）、policy、编码测试向量、真实/fixture分离报告、B/C回归、D1–D12结果、每等级completed/blocked状态、handoff.json及report_zh.md。

新增schema须保持A本地样本兼容，并允许真实TEE证据标识；不在A旧manifest上把simulated改real。freeze新run、source/config/policy/measurement摘要。

D-completed要求D-application与D-integrated证据齐全，不能仅以接收到一个Quote文件结束。公网L1未开展并不妨碍明确标注的real TEE+local EVM实验；但F不能将其称公网性能。

没有实例或授权时给D-local成果+blocked清单、用户需要提供的环境和最少授权；禁止假数据，继续可独立阶段。最终回复具体文件、命令、实际平台、验证服务信任、Quote公开范围、未验证攻击和后续F可用数据。不改论文、不commit/push。
