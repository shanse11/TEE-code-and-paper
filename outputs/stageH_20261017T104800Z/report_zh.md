# 2026-10-17 实验记录

论文未改。本轮只跑实验，并给权威合约加了可选的 DA 披露罚没。原始 Quote 含平台身份信息，默认不要公开 `quote_bound.dat` 和 `quote_bad.dat`。

## 平台

- 实例：`ecs.g7t.large`，华北 2（北京），公网 `101.200.228.143`
- CPU：Intel Xeon Platinum 8369B，`/proc/cpuinfo` 含 `sgx` 与 `sgx_lc`
- 设备：`/dev/sgx_enclave`、`/dev/sgx_provision` 存在；没有 TDX 设备
- 系统：Alibaba Cloud Linux 2.1903，内核 `4.19.91-28.5.al7.x86_64`
- SDK：`sgxsdk-2.19.100.3-1.al7`，DCAP `libsgx-dcap-ql-1.16.100.2-1.al7`，`libsgx-dcap-quote-verify-1.16.100.2-1.al7`
- PCCS：`https://sgx-dcap-server-vpc.cn-beijing.aliyuncs.com/sgx/certification/v4/`
- 安装步骤来自阿里云《构建 SGX 机密计算环境》，访问日期 2026-10-17

文档里提到的内核内存泄漏对应 `4.19.91-23`。当前内核是 `4.19.91-28.5`，没有安装那个旧补丁。

## 1. 真实 SGX Quote

官方 `SampleEnclave` 在硬件模式下返回 `SampleEnclave successfully returned`。

官方 `QuoteGenerationSample` 生成 ECDSA Quote（`cert_key_type = 0x5`，quote 版本 3，attestation key type 2）。三次生成墙钟约 1.25 s、1.06 s、1.03 s。空 `report_data` 的 Quote sha256 为 `b5fabef4ae11396f53099c9a40f8233253cc0c418696e047e834c87d3738a776`。

独立的 `QuoteVerificationSample`（可信 QvE 路径和非可信路径）都返回：

- `tee_verify_quote successfully returned`
- 非终态结果 `0xA003`
- SDK 头文件 `sgx_qve_header.h` 中该值是 `SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED`
- 附带的 advisory：`INTEL-SA-00657`、`INTEL-SA-00767`、`INTEL-SA-01079`、`INTEL-SA-01103`、`INTEL-SA-01153`、`INTEL-SA-00615`

签名和证书链被验证库接受。TCB 状态是过期且需要配置，不能记成 UpToDate 或策略通过。

随后在 `/home/ecs-user/hybrid-quote` 把 64 字节 `report_data` 写进 Quote。前 32 字节是本仓库 `buildReportDataDigest` 的结果 `2172d84a5845fd468dd5af008b7aa92ad2b3c4c6fcefe40298c45e555554bcd3`。输入为执行公钥 `02` 加 32 个 `11`、域 `HYBRID_BOUNDED_TASK_V1`、nonce 32 个 `aa`、epoch `1`、应用摘要 `aliyun-sgxsdk-quote-generation-sample-2.19.100.3`。

| Quote | sha256 | report_data 前 32 字节 | 验证结果 |
| --- | --- | --- | --- |
| `quote_bound.dat` | `9ab7ae99bf5353fde73aef2746bb8aad99f46562f2eab00333024795a2cfe2a2` | 与上面的摘要一致 | `0xA003` |
| `quote_bad.dat` | `a334b44436834b62547e641d39a06a10ff92b13ff4e6c208fb1f61dabd5f6650` | 首字节改为 `20` | `0xA003` |

绑定 Quote 的 `MRENCLAVE` 为 `76f38bb26e1902666c40b433ddb3de91ecf39495c058d75f1dca120127fc63ea`。生成墙钟：匹配摘要 0.99 s，改过的摘要 1.30 s。两条 Quote 的密码学验证结果相同；区分它们的是 `report_data` 是否等于事先约定的摘要。

随后把本文的有界哈希链放进同一个 Enclave。`initial` 为 32 个 `0x11`，nonce 为 32 个 `0x22`。Enclave 内部计算 `output`、`traceRoot`，并把 `keccak256(output ‖ root ‖ nonce)` 写入 Quote 的 `report_data`。4 步和 128 步的结果都与本机 ethers 逐字节一致。

| 步数 | Enclave 计算加报告 | 宿主同代码 128 步 | Quote sha256 | report_data 前 32 字节 |
| --- | --- | --- | --- | --- |
| 4 | 0.057 ms |  | `75e84914d0946cf95a73afff44bbaf66761011a821525c486c792ab13b190752` | `d7ddfc6038ebeb13597cc2700d8d22e166e39ee40f1cb8f2fb4def600bb74eea` |
| 128 | 0.497 ms | 100 次合计 30.495 ms，单次 0.305 ms | `bf78a99d5e227b5fe5941698172492c989829b39893d96257ca0528aeb849fa3` | `dd38eea6ecebcbf06e52a265792e3567acadbf98d5f9d00025d5740f64e796e5` |

`MRENCLAVE` 为 `1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37`。4 步 Quote 的独立验证仍是 `0xA003`。宿主时间只含哈希链，不含进出 Enclave 和生成 Quote。

本地 Hardhat 用这两份轨迹完成了提交、挑战、裁决和提现，裁决都是 0，任务进入 SETTLED。4 步的 `adjudicate` gas 是 94836，128 步是 166840。详见 `tee_link.json`。合约没有链上验证 Quote，这次联调是「真实 SGX 计算 + 本地 EVM」。

## 2. DA 披露罚没

`evm/contracts/BoundedTaskRollup.sol` 增加了可选的 `bindDa`、`fulfillDa`、`slashDa`。提交者在挑战窗口内另交一份与任务押金相同的 DA 押金，并登记 `daRef`。窗口内交出 `dataHash` 的原像则押金变为可提取；超时后任何人可以 `slashDa`，押金销毁到 `address(0)`。绑定之后，`adjudicate`、`settle`、`terminate`、`finalize` 在披露或罚没完成前会回退 `da pending`。未调用 `bindDa` 的任务行为与原来相同。

这里检查的是原像披露，不是 EIP-4844 的点值证明。

重跑 `stageB_closure.test.js` 与 `stageC_recovery.test.js`：26 passing。C12 记录罚没 1 ether，`slashDa` gas 66136。产物在本目录的 `stageB/` 和 `stageC/`。

## 3. 同模型对照

重跑 `evm/revision/stageG_mechanism.js`。每臂 3 个 run、每 run 10 个测量批，共 210 条非预热记录。本地 Hardhat，费用只计 gas。

| 系统 | 路径 | 正确终局 | 错误终局 | resolve gas 合计 |
| --- | --- | --- | --- | --- |
| 本文 | interactive | 30/30 | 0 | 15148776 |
| 本文 | fault-no-recovery | 30/30 | 0 | 8076444 |
| 本文 | fault-with-recovery | 30/30 | 0 | 16121160 |
| 本文 | direct-no-response | 30/30 | 0 | 3884634 |
| 机制基线 | interactive | 30/30 | 0 | 11517024 |
| 机制基线 | fault-no-recovery | 0/30 | 30 | 4893744 |
| 机制基线 | direct-no-response | 0/30 | 30 | 1602852 |

机制基线不是 Arbitrum、Optimism 或 TeeRollup 的官方实现。

## 4. Optimism Fault Dispute Game

在 commit `c4a68ab07a7c6ad51042f1b33d5faf4f4596f3af` 上，用 Foundry 1.5.1-stable 跑了官方测试里的三个用例。三个都通过。日志是 `optimism_fdg_gas.log`。下面的 gas 是整个测试函数的消耗，包含断言，不只是单次 `move`、`step` 或 `resolve`。

| 测试 | gas |
| --- | --- |
| `test_move_simpleAttack_succeeds` | 365885 |
| `test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds` | 2778766 |
| `test_resolve_stepReached_succeeds` | 3731850 |

这是组件测试，不是 Optimism 主网吞吐，也不能和本文的本地 gas 合成一张领先比例表。

## 5. 仍然没有跑成的部分

Sepolia type-3 Blob 没有广播。环境里仍然没有 `SEPOLIA_RPC_URL`、`SEPOLIA_PRIVATE_KEY`、`BLOB_BATCH_ANCHOR_ADDRESS` 和 `BEACON_API_URL`。合约也没有在链上验证 DCAP Quote。
