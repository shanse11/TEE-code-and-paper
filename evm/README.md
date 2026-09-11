# EVM 子工程说明

这个目录把当前 Python 原型中的关键链上部分映射成了一个可部署、可测试、可量 `gasUsed` 的 Solidity 原型。

## 合约组成

- [`contracts/MockTEEVerifier.sol`](</E:/项目/project_code/evm/contracts/MockTEEVerifier.sol>)
  - 对应 Python 中的 `attestation.py`
  - 使用 ECDSA 签名模拟链上可验证的 TEE attestation
- [`contracts/MockDARegistry.sol`](</E:/项目/project_code/evm/contracts/MockDARegistry.sol>)
  - 对应 Python 中的 DA 记录层
  - 存储 `daPointer / payloadHash / merkleRoot / availability`
- [`contracts/MerkleVerifier.sol`](</E:/项目/project_code/evm/contracts/MerkleVerifier.sol>)
  - 对应 Python 中的字段级 Merkle proof 验证逻辑
- [`contracts/HybridTEERollup.sol`](</E:/项目/project_code/evm/contracts/HybridTEERollup.sol>)
  - 对应 Python 中的 `ledger.py`
  - 负责 compact commit 提交、challenge open/respond/step/recover/replay/resolve、finalize

## 这套 Solidity 原型解决了什么

它的目标不是把 Python 原型一字不差搬到链上，而是把“适合链上的状态推进与最小验证逻辑”真正部署到本地 EVM 中，从而得到：

1. 本地合约层面的真实 `gasUsed`
2. 可运行的 challenge 状态机
3. 可验证的 DA Merkle root / proof
4. 可验证的 mock TEE attestation

## 快速使用

进入目录：

```powershell
Set-Location E:\项目\project_code\evm
```

### 编译

```powershell
npm.cmd run compile
```

### 测试

```powershell
npm.cmd run test
```

### 本地部署

```powershell
npm.cmd run deploy:local
```

### Sepolia 预检查

先复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

然后填写：

- `SEPOLIA_RPC_URL`
- `SEPOLIA_PRIVATE_KEY`
- `ETHERSCAN_API_KEY`
- 可选 `TEE_SIGNER_ADDRESS`

检查配置：

```powershell
npm.cmd run check:sepolia
```

### 部署到 Sepolia

```powershell
npm.cmd run deploy:sepolia
```

### Etherscan 验证

部署完成并生成 `deployments/sepolia.json` 后：

```powershell
npm.cmd run verify:sepolia
```

### 本地 Gas 实测

```powershell
npm.cmd run measure:gas
```

## Gas 实测输出

Gas 测量结果会写到：

- [`../paper_outputs/evm_gas/measured_gas.csv`](</E:/项目/project_code/paper_outputs/evm_gas/measured_gas.csv>)
- [`../paper_outputs/evm_gas/measured_gas_summary.json`](</E:/项目/project_code/paper_outputs/evm_gas/measured_gas_summary.json>)
- [`../paper_outputs/evm_gas/measured_gas_report.md`](</E:/项目/project_code/paper_outputs/evm_gas/measured_gas_report.md>)

部署记录会写到：

- [`deployments/hardhat.json`](</E:/项目/project_code/evm/deployments/hardhat.json>)
- [`deployments/sepolia.json`](</E:/项目/project_code/evm/deployments/sepolia.json>)（部署成功后生成）

ABI 与地址索引会写到：

- [`deployments/hardhat_abis/address_index.json`](</E:/项目/project_code/evm/deployments/hardhat_abis/address_index.json>)
- [`deployments/sepolia_abis/address_index.json`](</E:/项目/project_code/evm/deployments/sepolia_abis/address_index.json>)（部署成功后生成）
- `deployments/*_abis/*.abi.json`

## 和 Python 原型的对应关系

- `submit()` -> `submitRollup()`
- `verify_da_field()` -> `verifyDAField()`
- `challenge_open()` -> `openChallenge()`
- `challenge_respond()` -> `respondChallenge()`
- `challenge_step()` -> `stepChallenge()`
- `challenge_recover()` -> `recoverChallenge()`
- `challenge_replay()` -> `replayChallenge()`
- `challenge_resolve()` -> `resolveChallenge()`
- `finalize_expired()` -> `finalizeExpired()`

## 需要诚实说明的边界

这套 Solidity 工程已经是“本地测试链真实部署 + 真实 gasUsed 测量”，但它仍然不是完整主网部署，原因包括：

1. 当前仍是 mock TEE，不是真实 SGX/TDX attestation
2. challenge 中的 mismatch index 和 replay 哈希仍由链下提供
3. 当前 DA 是 mock registry，不是真实 DA 网络
4. 真实主网还会受 calldata、blob 价格和网络环境影响

因此，这套结果最适合论文中的定位是：

> 链上关键路径的本地 EVM 实测基线
