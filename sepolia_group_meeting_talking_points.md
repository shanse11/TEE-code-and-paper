# Sepolia 部署后的组会口径

## 1 分钟版本

本周我把原来的 Python 原型进一步映射成了一套可部署的 Solidity 合约，并补齐了 Sepolia 部署配置、地址记录和 ABI 导出。当前已经完成本地 Hardhat 测试链的真实部署与 `gasUsed` 实测，并且已经把同一套合约成功部署到 Sepolia，生成了真实测试网地址记录。这样论文中的 gas 分析就可以从“参数估算”进一步升级为“本地 EVM 实测 + Sepolia 公开测试网部署”。

## 3 分钟版本

在链上化这一部分，我当前做了三层推进。第一层是把 Python 原型中适合链上的部分映射成 Solidity 合约，包括 mock TEE attestation verifier、DA registry、Merkle proof verifier，以及负责 submit、challenge、recover、replay、resolve 的 HybridTEERollup 主合约。第二层是在 Hardhat 本地测试链上完成真实部署和关键路径 `gasUsed` 实测，已经得到了 submit、challenge open、recover、replay、resolve 等操作的链上 gas 基线。第三层是补齐了 Sepolia 部署工程，并已成功部署到 Sepolia，自动生成了 `sepolia.json` 地址记录和 ABI 索引。当前 Etherscan 验证请求因为 block explorer 连接超时暂未完成，但不影响部署结果本身的有效性。

## 建议强调的价值

1. 这说明当前工作已经不只是 Python 层面的机制原型，而是具备链上可部署对应物。
2. Gas 分析的口径已经从“理论估算”升级为“本地 EVM 实测 + Sepolia 公开测试网部署”。
3. 这为论文里回答“系统是否能真正落到链上”提供了直接证据。
