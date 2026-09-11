# Sepolia 部署记录模板

## 部署环境

- Network: `Sepolia`
- Chain ID: `11155111`
- Deployment Date: `2026-05-10`
- Deployer Address: `0x517652941fd04dAA9A9D4dC52f38B7d23CDE1307`
- Mock TEE Signer Address: `0x517652941fd04dAA9A9D4dC52f38B7d23CDE1307`
- RPC Provider: `Infura Sepolia`
- Etherscan API Key: 已配置

## 合约参数

- disputeWindowSeconds: `60`
- challengeTimeoutSeconds: `2`
- maxBisectionRounds: `16`

## 合约地址

| Contract | Address | Role | Verified |
| --- | --- | --- | --- |
| MockTEEVerifier | `0xC42CB0Cf0D112Bd59E0f212F2DB2002ca50a8b6A` | 模拟 TEE attestation 链上验证 | Etherscan 请求超时，需重试 |
| MockDARegistry | `0xc42C64a7De05bf3ad4f1c75CbD8E0506F7De99Ff` | DA 根与可用性记录 | Etherscan 请求超时，需重试 |
| HybridTEERollup | `0xB9B72f10bB8aBC1ed090f1B0443Fe57189c497Fd` | compact commit、challenge、recover、replay、resolve | Etherscan 请求超时，需重试 |

## 部署产物

- `evm/deployments/sepolia.json`
- `evm/deployments/sepolia_abis/address_index.json`
- `evm/deployments/sepolia_abis/*.abi.json`

## 备注

- 当前为 mock TEE + mock DA registry 的 Sepolia 原型部署。
- Gas 与状态行为可作为论文中的链上实测补充材料。
- 本次部署已成功上链并生成地址记录；`verify:sepolia` 因 block explorer `Connect Timeout Error` 暂未完成源码验证，不影响部署地址和构造参数的有效性。
