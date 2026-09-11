# 论文表格模板：Sepolia 部署与链上实测

## 表 1：Sepolia 合约部署信息

| 合约 | 功能 | Sepolia 地址 | 是否 Etherscan 验证 |
| --- | --- | --- | --- |
| MockTEEVerifier | 模拟 TEE attestation 验证 | `0xC42CB0Cf0D112Bd59E0f212F2DB2002ca50a8b6A` | 请求超时，待重试 |
| MockDARegistry | DA 根与可用性记录 | `0xc42C64a7De05bf3ad4f1c75CbD8E0506F7De99Ff` | 请求超时，待重试 |
| HybridTEERollup | 提交、挑战、恢复、重放与结算 | `0xB9B72f10bB8aBC1ed090f1B0443Fe57189c497Fd` | 请求超时，待重试 |

## 表 2：链上关键操作的本地 EVM / Sepolia 实测对照

| 操作 | Local Hardhat `gasUsed` | Sepolia `gasUsed` | 说明 |
| --- | ---: | ---: | --- |
| register DA | 113526.00 | 待补充 | DA 记录写入 |
| submit rollup | 299033.67 | 待补充 | compact commit 上链 |
| challenge open | 283769.00 | 待补充 | 开启争议并写入初始证据 |
| challenge respond | 65886.00 | 待补充 | 响应挑战 |
| challenge step | 93807.00 | 待补充 | 二分定位一次 |
| challenge recover | 156891.00 | 待补充 | 超时恢复 |
| challenge replay | 135632.00 | 待补充 | 单步重放 |
| challenge resolve | 113402.00 | 待补充 | 仲裁与罚没 |
| finalize | 33477.00 | 待补充 | 争议窗口结束后最终确认 |

## 表 3：从估算到实测的口径升级

| 阶段 | 数据来源 | 结论边界 |
| --- | --- | --- |
| 成本估算阶段 | Python 原型中的字节和参数估算 | 说明趋势，不代表真实链上费用 |
| 本地 EVM 实测阶段 | Hardhat 本地链 `gasUsed` | 说明合约关键路径的真实执行成本 |
| Sepolia 部署阶段 | Sepolia 部署地址、构造参数与交易回执 | 说明公开测试网环境下的可部署性；后续可继续补全逐操作 `gasUsed` |
