# B. Sepolia 真实 Blob + point-eval（2026-10-30）

- Blob 交易（type-3）：[0x450ac7fd5ed7a135318bf6ee22e90741fd2ba6561e0b6b7198338a4deda6a51d](https://sepolia.etherscan.io/tx/0x450ac7fd5ed7a135318bf6ee22e90741fd2ba6561e0b6b7198338a4deda6a51d)，区块 12025170，status=1
  - versioned hash `0x01eb19ae77f06c15a3fd9227fe83a27f9af234bcf99843dd493c4e3e760592f2`（与 `B_point_eval/kzg_fixture.json` 一致）
  - blobGasUsed 131072，blobGasPrice 2 wei，执行 gas 12000
  - Sepolia 已过 Osaka：旧版 4844 sidecar 被节点拒绝，改用 EIP-7594 wrapper v1（128 个 cell proof）
- point-eval（0x0a 预编译）交易：[0x4f98c197af818c434b6685ff0634562c38e7a23d05fb1f9ecc97dd7a270967d0](https://sepolia.etherscan.io/tx/0x4f98c197af818c434b6685ff0634562c38e7a23d05fb1f9ecc97dd7a270967d0)，gasUsed 67700（含 21000 基础 + calldata + 50000 预编译）
  - eth_call 返回 FIELD_ELEMENTS_PER_BLOB=4096 与 BLS_MODULUS，验证通过；篡改 y 后 eth_call 回退
- 余额：0.019164986999569856 → 0.019164986667700851 ETH

诚实边界：point-eval 是直接调用预编译，未在 Sepolia 部署 PointEvalDaDuty 做 bind/fulfill（该合约路径仅在本地 Hardhat 测过）；预编译只校验 KZG 开点与 versioned hash，不读取 blob 本体。
