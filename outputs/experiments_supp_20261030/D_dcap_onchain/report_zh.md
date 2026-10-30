# D. 链上 DCAP 验证（Automata，Sepolia，2026-10-30）

- 合约：AutomataDcapAttestationFee `0x27188ABA3a26CBb806eF4C67de9b05D7d792EC10`（来源：https://docs.ata.network/tee-overview/tee-verifiers/intel-sgx-tdx-dcap/automata-dcap-attestation/contract-addresses/v1.1.0）
- 交易：[0xcdc1cdcc4886996583764ac43d744d9f419cfd9390c6e1a6ee0d829ab95b6fe0](https://sepolia.etherscan.io/tx/0xcdc1cdcc4886996583764ac43d744d9f419cfd9390c6e1a6ee0d829ab95b6fe0)，区块 12025195，status=1，gasUsed **5037977**
- Quote：`sgx_requote/instance_quote.dat`，4734 字节，SHA256 `5e6e179f4ec9281d7afb31ee5b314fc0a0c23c47694fbc8328c7744c1b3b3b90`（未入库）
- 结果：AttestationSubmitted success=**true**；输出 TCB 状态枚举 = **5 = TCB_OUT_OF_DATE_CONFIGURATION_NEEDED**（即 0xA003），FMSPC `0x00606a000000`，输出中含 MRENCLAVE `0x1f2467e1…9ab6b05f`

诚实边界：链上验证通过签名链与抵押物校验，但 TCB **不是 UpToDate**，与本地验证一致；需云厂商升级固件/微码才可能改善。手续费 bp=0。
