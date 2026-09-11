# 本地 EVM 实测 Gas 报告

说明：本报告基于 Hardhat 本地测试链，对当前 Solidity 原型的关键操作进行 `gasUsed` 实测。

## 样本结果

| Payload | register DA | submit | open | respond | step1 | recover | replay | resolve | finalize |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 113530 | 299051 | 283769 | 65886 | 93807 | 156891 | 135632 | 113402 | 33477 |
| 512 | 113530 | 299019 | 283769 | 65886 | 93807 | 156891 | 135632 | 113402 | 33477 |
| 2048 | 113518 | 299031 | 283769 | 65886 | 93807 | 156891 | 135632 | 113402 | 33477 |

## 平均结果

- register DA: 113526.00
- submit rollup: 299033.67
- challenge open: 283769.00
- challenge respond: 65886.00
- challenge step (round1): 93807.00
- challenge recover: 156891.00
- challenge replay: 135632.00
- challenge resolve: 113402.00
- finalize: 33477.00

## 解释

- 这些结果是本地 EVM 实测，不再只是纯字节估算。
- 当前合约主要测量链上提交、挑战、恢复、重放和结算的状态推进成本。
- 真实主网部署成本仍会受 calldata 定价、blob 价格和网络环境影响，因此这组数据更适合作为“本地合约实测基线”。
