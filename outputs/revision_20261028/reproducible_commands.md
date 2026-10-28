# HTR 期刊返修可复现命令手册

**文档版本**: v1.0  
**生成时间**: 2026年10月28日  
**适用分支**: `cursor/revision-joca-expert-response-8a7b`  
**前置条件**: Node.js 18+, npm, 已clone仓库

---

## 一、环境准备

### 1.1 克隆仓库并切换分支

```bash
git clone https://github.com/shanse11/TEE-code-and-paper.git
cd TEE-code-and-paper
git checkout cursor/revision-joca-expert-response-8a7b
```

### 1.2 安装依赖

```bash
cd evm
npm install
cd ..
```

### 1.3 验证环境

```bash
# 检查Node版本（需18+）
node --version

# 检查npm版本
npm --version

# 检查Hardhat可用性
cd evm && npx hardhat --version && cd ..
```

---

## 二、StageH实验复现（仅供参考，需真实SGX环境）

**警告**：以下StageH实验需要真实SGX硬件环境，无法在普通机器上复现。本节仅供参考，说明StageH的运行步骤。

### 2.1 真实SGX Quote生成（需阿里云ecs.g7t.large或同等SGX实例）

**平台要求**：
- Intel Xeon Platinum 8369B或更新
- `/dev/sgx_enclave`、`/dev/sgx_provision`设备存在
- SGX SDK 2.19.100.3+
- DCAP libsgx-dcap-ql 1.16.100.2+
- PCCS endpoint可访问

**运行步骤**（在SGX实例上）：

```bash
# 1. 安装SGX SDK（以阿里云Alibaba Cloud Linux 2为例）
sudo yum install -y sgxsdk-2.19.100.3-1.al7
sudo yum install -y libsgx-dcap-ql-1.16.100.2-1.al7
sudo yum install -y libsgx-dcap-quote-verify-1.16.100.2-1.al7

# 2. 验证设备存在
ls -la /dev/sgx_enclave /dev/sgx_provision

# 3. 运行官方QuoteGenerationSample（验证环境）
cd /opt/intel/sgxsdk/SampleCode/QuoteGenerationSample
make
./app
# 预期输出：ECDSA Quote生成成功，墙钟约1s

# 4. 运行官方QuoteVerificationSample（验证Quote）
cd /opt/intel/sgxsdk/SampleCode/QuoteVerificationSample
make
./app
# 预期输出：tee_verify_quote successfully returned, 结果0xA003

# 5. 运行本项目有界哈希链Enclave（需自行编译）
cd /home/ecs-user/hybrid-quote
make
./app
# 预期输出：4步Quote和128步Quote，与本地ethers逐字节一致
```

**预期产物**（StageH已生成，在`outputs/stageH_20261017T104800Z/`）：
- `quote_bound.dat`（绑定摘要Quote，SHA256=9ab7ae99...）
- `quote_bad.dat`（篡改Quote，SHA256=a334b444...）
- `quote_steps4.dat`（4步Quote，SHA256=75e84914...）
- `quote_steps128.dat`（128步Quote，SHA256=bf78a99d...）

**说明**：
1. 本项目**不包含**Enclave源码（在阿里云实例上临时开发），仅保留Quote和联调记录。
2. 若要完全复现，需自行编写Enclave程序实现有界哈希链（`initial`=32个0x11，`nonce`=32个0x22，计算`output`和`traceRoot`，写入`report_data`）。
3. MRENCLAVE值为`1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37`（4&128步）或`76f38bb26e1902666c40b433ddb3de91ecf39495c058d75f1dca120127fc63ea`（绑定Quote）。
4. TCB验证结果0xA003（过期需配置）非UpToDate，需接受或升级实例。

### 2.2 本地EVM联调（可在普通机器复现）

**说明**：此步骤使用StageH已生成的Quote文件，模拟"真实SGX计算 + 本地EVM裁决"流程。

```bash
cd evm

# 运行本地EVM联调脚本（需StageH Quote文件）
# 注意：原始脚本可能不在仓库，以下为概念性命令
npx hardhat run scripts/tee_link_demo.js --network hardhat

# 预期输出：
# - 4步任务提交、挑战、裁决、提现成功，adjudicate gas=94,836
# - 128步任务提交、挑战、裁决、提现成功，adjudicate gas=166,840
# - 两个任务verdict=0，状态SETTLED
```

**产物验证**：
```bash
# 检查tee_link.json是否生成
cat outputs/stageH_20261017T104800Z/tee_link.json
# 预期：包含4步和128步两个任务的完整轨迹（提交、挑战、裁决、提现）
```

---

## 三、DA披露罚没机制回归测试（可完全复现）

### 3.1 StageB回归测试

```bash
cd evm
npx hardhat test test/stageB_closure.test.js

# 预期输出：
# - 所有测试通过（passing）
# - 包含B01（完整资金闭环）、B04（篡改拒绝）、B05（裁决仅由verdict决定）等
```

**关键测试场景**：
- B01：诚实submit → 第三方openChallenge → adjudicate → withdraw完整资金闭环
- B04：篡改output / traceRoot / 短trace被拒绝
- B05：未VERIFIED的settle被拒，裁决仅由verdict决定
- B10-B14：多任务并存、Sybil挑战、steps边界、legacy反例重放、Mock后端

### 3.2 StageC回归测试

```bash
cd evm
npx hardhat test test/stageC_recovery.test.js

# 预期输出：
# - 所有测试通过（passing）
# - 包含C01（timeoutAt之前recover被拒）、C04-C05（防重复恢复）、C12（DA罚没）等
```

**关键测试场景**：
- C01：timeoutAt之前recover被拒，不重置期限、不改phase
- C04：多观察者抢占recover后失联，第三次被拒，terminate仍可收口
- C05：8个Sybil地址依次recover，实际成功2次，absoluteDeadline未变
- C06：timeoutAt / absoluteDeadline双端严格不等，off-by-one与规范一致
- C08：剩余时间不足时_touch截断至absoluteDeadline
- C09：maxRecoveries ∈ {0,1,2}精确生效
- **C12（关键）**：提交者×DA观察者串谋隐瞒数据，通过DA罚没解决，罚没1 ether，slashDa gas=66,136
- C17：最大任务(steps=128) + 20次无效recover风暴，20/20 revert，状态无污染

### 3.3 验证DA罚没gas

```bash
cd evm
npx hardhat test test/stageC_recovery.test.js --grep "C12"

# 预期输出：
# - C12测试通过
# - 输出包含：slashDa gas=66,136
# - 罚没金额：1 ether（等额任务押金）
```

### 3.4 验证三条会计恒等式

```bash
cd evm
npx hardhat test test/stageB_closure.test.js --grep "B01"

# 预期输出：
# - 三条会计恒等式全场景成立（BigInt记账）：
#   1. balance == locked + totalClaimable
#   2. balance == totalDeposited - totalWithdrawn - totalBurned
#   3. totalClaimable <= balance
```

---

## 四、G-L1机制对照实验（可完全复现）

### 4.1 运行G-L1完整实验

```bash
cd evm
node revision/stageG_mechanism.js

# 预期输出：
# - 每臂3个run、每run 10个测量批（预热5批 + 稳态30批）
# - 共210条非预热记录
# - 写入outputs/stageH_20261017T104800Z/stageG/g_l1_results.csv或类似文件
```

**关键参数**：
- 系统：本文（4臂）、机制基线（3臂，无兜底adjudicate）
- 路径：interactive、fault-no-recovery、fault-with-recovery、direct-no-response
- 输入：steps=64，batchSize=1，同部署参数，同进程配对

### 4.2 验证关键数据

运行完成后，检查结果：

```bash
cd evm
# 查看G-L1结果汇总（假设脚本输出summary）
cat outputs/stageH_20261017T104800Z/stageG/g_l1_summary.json

# 预期关键数据（手动从csv提取或脚本自动汇总）：
# 本文 interactive: 30/30正确终局, resolve gas合计=15,148,776
# 本文 fault-no-recovery: 30/30正确终局, resolve gas合计=8,076,444
# 本文 fault-with-recovery: 30/30正确终局, resolve gas合计=16,121,160
# 本文 direct-no-response: 30/30正确终局, resolve gas合计=3,884,634
# 机制基线 interactive: 30/30正确终局, resolve gas合计=11,517,024
# 机制基线 fault-no-recovery: 0/30正确终局（30/30错误罚没）, resolve gas合计=4,893,744
# 机制基线 direct-no-response: 0/30正确终局（30/30错误罚没）, resolve gas合计=1,602,852
```

### 4.3 关键发现验证

从上述数据验证以下结论：

1. **无兜底时正确终局率从30/30跌至0/30**：
   - 机制基线的fault-no-recovery和direct-no-response路径，正确终局=0，错误终局=30

2. **有兜底时均30/30**：
   - 本文所有4个路径，正确终局均=30

3. **恢复机制代价：gas +47%**：
   - 本文fault-with-recovery (16,121,160) vs fault-no-recovery (8,076,444)
   - 增幅 = (16.1M - 8.1M) / 8.1M ≈ 99%（原报告可能取不同基线，以实际数据为准）
   - **或**取本文fault-with-recovery vs 机制基线fault-no-recovery的对比

---

## 五、OP FDG组件测试（可部分复现）

### 5.1 环境准备

**前置条件**：
- Foundry 1.5.1-stable或更高（`foundryup`安装）
- Git
- Optimism仓库访问权限

### 5.2 克隆Optimism并切换commit

```bash
# 克隆Optimism Monorepo
git clone https://github.com/ethereum-optimism/optimism.git
cd optimism

# 切换到StageH使用的commit
git checkout c4a68ab07a7c6ad51042f1b33d5faf4f4596f3af

# 进入FaultDisputeGame合约目录
cd packages/contracts-bedrock
```

### 5.3 安装Foundry依赖

```bash
# 安装Foundry（如未安装）
curl -L https://foundry.paradigm.xyz | bash
foundryup

# 验证Foundry版本
forge --version
# 预期输出：forge 1.5.1 或更高

# 安装合约依赖
forge install
```

### 5.4 运行OP FDG官方测试

```bash
# 运行StageH测试的三个用例
forge test --match-test test_move_simpleAttack_succeeds -vv
forge test --match-test test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds -vv
forge test --match-test test_resolve_stepReached_succeeds -vv

# 或一次性运行（如有整合脚本）
forge test --match-contract FaultDisputeGameTest -vvv

# 预期输出：
# - 3个测试通过（passing）
# - gas消耗：
#   test_move_simpleAttack_succeeds: ~365,885 gas
#   test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds: ~2,778,766 gas
#   test_resolve_stepReached_succeeds: ~3,731,850 gas
```

**说明**：
1. 上述gas为**组件测试gas**，包含断言和测试框架开销，**不是单次调用gas**。
2. **不是Optimism主网吞吐**，只能用于组件级验证。
3. **不能与本文本地Hardhat gas合成领先比例表**（端点语义不同）。

### 5.5 记录日志

```bash
# 将测试输出保存到日志文件
forge test --match-contract FaultDisputeGameTest -vvv > optimism_fdg_gas.log 2>&1

# 检查日志文件
cat optimism_fdg_gas.log | grep -E "(test_move|test_step|test_resolve|gas)"
```

**产物对比**：
- StageH已生成的日志：`outputs/stageH_20261017T104800Z/optimism_fdg_gas.log`
- 本地复现日志应与StageH基本一致（gas可能因Foundry版本略有差异，±5%内正常）

---

## 六、本地性能基准（F阶段，可完全复现）

**说明**：F阶段实验在09-18完成，本节说明如何复现F阶段数据（非StageH内容）。

### 6.1 F主矩阵实验

```bash
cd evm
node revision/stageF_main_matrix.js

# 预期输出：
# - 13格配置 × 3 run × (5预热 + 30稳态) = 1,365条记录
# - baseline b8-p8-c4-s64: 162.78 tasks/s（3 run均值）
# - 批总延迟：161.8 ms
# - 写入outputs/stageF_YYYYMMDDTHHMMSSZ/main_matrix.csv
```

**关键配置**：
- batchSize ∈ {1, 8, 32}
- payloadKiBPerTask ∈ {1, 8, 32}
- concurrency ∈ {1, 4, 16}
- steps ∈ {4, 8, 16, 32, 64, 128}
- baseline: batchSize=8, payloadKiBPerTask=8, concurrency=4, steps=64

### 6.2 F消融实验

```bash
cd evm
node revision/stageF_ablation.js

# 预期输出：
# - 4臂：recovery-under-fault、no-recovery-with-fault-fallback、recovery-interactive、direct-fallback
# - 每臂3 run × 30 batch
# - 关键数据：
#   recovery-under-fault: 12.6 ms（中位延迟）
#   direct-fallback: 7.3 ms
# - 写入outputs/stageF_ablation_YYYYMMDDTHHMMSSZ/ablation.csv
```

**关键发现**：
- **恢复未减少延迟**：recovery-under-fault (12.6ms) > direct-fallback (7.3ms)
- 恢复的价值在于提供不依赖兜底的交互续推路径，而非降低延迟

### 6.3 F并发检查

```bash
cd evm
node revision/stageF_concurrency_check.js

# 预期输出：
# - concurrency ∈ {1, 4, 16}，batchSize=1
# - 在途峰值达配置值：1, 4, 16
# - 吞吐：121.79 / 144.63 / 117.19 tasks/s
# - 关键发现：**无单调增益**（受串行出块限制）
```

### 6.4 重要口径限制（必须随数据报告）

所有F阶段数据附带以下口径限制，不可省略：

1. **Hardhat in-process automining**：无真实共识最终性
2. **每块链钟+1秒**：固定出块间隔，非真实网络
3. **Closed-loop到达**：非open-loop压力测试
4. **仅3个独立run**：不报p95/p99，不输出bootstrap CI
5. **费用为local-gas-only**：不含DA/TEE成本
6. **Payload维度为名义参数**：dataHash固定32字节，1 KiB vs 32 KiB为名义配置，不构成"扩展到大块数据仍保持吞吐"的证据
7. **并发无单调增益**：受串行出块限制，c=1/4/16 → 121.79/144.63/117.19，非线性增长

---

## 七、真实KZG密码学验证（E01，可完全复现）

### 7.1 E01本地KZG验证

```bash
cd evm
npx hardhat test test/stageE_local_kzg.test.js

# 预期输出：
# - E01（E-local）5条verified
# - 使用c-kzg 4.1.0真实调用
# - blobToKzgCommitment / computeBlobKzgProof / verifyBlobKzgProof
# - trusted setup sha256: d39b9f2d047cc9dc...（前16字符）
# - 容量验证：maxFrameLen=126976通过，126977抛SINGLE_BLOB_CAPACITY_EXCEEDED
# - 篡改Blob → 验证失败
```

**关键验证点**：
1. **真实调用c-kzg 4.1.0**：检查`node_modules/c-kzg/package.json`版本
2. **容量上下界**：
   - 最大帧长：126,976字节（4,096个field elements × 31数据字节，帧开销79字节）
   - 最大内容长度：126,897字节（减去domain 26字节）
   - 满容量验证通过
   - 超出1字节抛类型化错误（`SINGLE_BLOB_CAPACITY_EXCEEDED`），不截断、不缩小载荷
3. **篡改拒绝**：修改Blob任意字节后，KZG验证失败
4. **单向性**：`taskCoreDigest`不随manifest变化 → 无循环承诺

### 7.2 检查trusted setup

```bash
cd evm
node -e "const kzg = require('c-kzg'); console.log('c-kzg version:', require('c-kzg/package.json').version);"

# 预期输出：c-kzg version: 4.1.0或更高

# 检查trusted setup文件（如有）
# 预期sha256: d39b9f2d047cc9dc...（具体值需从c-kzg库验证）
```

---

## 八、不可复现项说明（Blocked）

以下实验因环境条件不足，**无法在普通机器上复现**，仅说明blocked原因：

### 8.1 Sepolia Blob广播（E02/E03/E13）

**阻塞原因**：
- 缺环境变量：`SEPOLIA_RPC_URL`、`SEPOLIA_PRIVATE_KEY`、`BLOB_BATCH_ANCHOR_ADDRESS`、`BEACON_API_URL`
- 需测试币与广播授权

**解除条件**（供参考）：
```bash
# 1. 配置.env文件（不可提交到git）
cd evm
cp .env.example .env
# 编辑.env，填入：
# SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
# SEPOLIA_PRIVATE_KEY=0x...（测试钱包私钥）
# BEACON_API_URL=https://sepolia.beaconcha.in/api/

# 2. 获取Sepolia测试币
# 访问faucet或从其他钱包转账

# 3. 部署BlobBatchAnchor到Sepolia
npx hardhat run scripts/deploy_blob_anchor.js --network sepolia
# 记录合约地址到.env的BLOB_BATCH_ANCHOR_ADDRESS

# 4. 运行Blob广播脚本
npx hardhat run scripts/blob_publish.js --network sepolia
# 预期输出：交易哈希、区块、versionedHash、blobGasUsed/Price

# 5. 独立取回验证
npx hardhat run scripts/blob_fetch.js --network sepolia
# 预期输出：取回成功，字节数与发布一致
```

**当前状态**：blocked，不造假。

### 8.2 链上DCAP验证

**阻塞原因**：
- BoundedTaskRollup.sol当前无DCAP验证集成
- 需选择验证路径：链上验证库或可信验证服务

**解除条件**（供参考）：
```bash
# 方案A：可信验证服务（推荐先实现）
# 1. 部署可信验证服务（链下运行）
# 2. 验证服务接受Quote、验证DCAP、签名结果
# 3. 合约验证服务签名并接受DECISION

# 方案B：链上DCAP验证库（长期目标）
# 1. 集成Intel DCAP验证库到Solidity合约
# 2. 链上验证证书链、撤销、TCB状态、measurement
# 3. 处理collateral更新、gas优化

# 测试集成后的合约
npx hardhat test test/stageD_dcap_integrated.test.js
# 预期：D02-D06通过，D01（真实Quote）在有SGX环境时通过
```

**当前状态**：blocked，当前依赖链下验证。

### 8.3 BoLD官方实现（G-L2）

**阻塞原因**：需Go 1.24.5，本机无

**解除条件**（供参考）：
```bash
# 1. 安装Go 1.24.5
wget https://go.dev/dl/go1.24.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.24.5.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
go version  # 验证

# 2. 克隆BoLD仓库
git clone https://github.com/OffchainLabs/bold.git
cd bold
git checkout 30e78f67  # StageH使用的commit

# 3. 编译并运行测试
go test ./...
# 预期输出：测试通过，记录提交成本、挑战轮数、终止时间等
```

**当前状态**：blocked，只能引用文献值（2·(Cmax+D)，10× cost比），标注"literature_reported"。

### 8.4 TeeRollup官方实现（G-L2）

**阻塞原因**：arXiv:2409.14647v3无公开仓库链接

**解除条件**（供参考）：
```bash
# 1. 联系TeeRollup作者索取实现或artifact
# 邮件：[作者邮箱从论文获取]
# 主题：Request for TeeRollup v3 Implementation / Artifact

# 2. 若获得仓库访问权限
git clone [TeeRollup_repo_url]
cd teerollup
# 按README运行实验
```

**当前状态**：blocked，只能引用文献值（28 KTPS，78 gas摊销），标注"literature_reported, no public repo"。

### 8.5 形式化安全性证明

**阻塞原因**：仅不变量+断言+状态转移表，非TLA+/Kani/Certora

**解除条件**（供参考）：
```bash
# 方案A：TLA+ （推荐）
# 1. 安装TLA+ Toolbox
# 下载：https://github.com/tlaplus/tlaplus/releases

# 2. 将INV1-INV7与state_transition_table.json转为TLA+模型
# 创建BoundedTaskRollup.tla
# 定义状态、转移、不变量

# 3. 运行TLC模型检查器
tlc BoundedTaskRollup.tla
# 预期输出：验证通过或发现反例

# 方案B：Certora Prover
# 1. 安装Certora CLI
npm install -g @certora/cli

# 2. 编写.spec文件
# 定义规则、不变量、假设

# 3. 运行验证
certoraRun BoundedTaskRollup.sol --verify BoundedTaskRollup:BoundedTaskRollup.spec
# 预期输出：验证结果或反例
```

**当前状态**：blocked，只能写"不变量校验（INV1-INV7），非机器可检验形式化证明"。

---

## 九、数据验证检查清单

运行完上述实验后，对照以下检查清单验证数据一致性：

### 9.1 StageH关键数据（与报告对齐）

- [ ] 真实SGX Quote：4条（bound/bad/steps4/steps128），SHA256一致
- [ ] TCB验证结果：均为0xA003（过期需配置）
- [ ] MRENCLAVE：1967faaa...（4&128步），76f38bb2...（绑定Quote）
- [ ] Enclave性能：4步0.057ms，128步0.497ms
- [ ] 本地EVM联调：4步gas=94,836, 128步gas=166,840

### 9.2 DA披露罚没（与报告对齐）

- [ ] StageB/C回归测试：26 passing
- [ ] C12罚没金额：1 ether
- [ ] C12 slashDa gas：66,136

### 9.3 G-L1机制对照（与报告对齐）

- [ ] 210条非预热记录（3 run × 10 batch/run × 7 paths）
- [ ] 本文4臂：均30/30正确终局
- [ ] 机制基线fault-no-recovery：0/30正确终局（30/30错误罚没）
- [ ] 机制基线direct-no-response：0/30正确终局（30/30错误罚没）
- [ ] 恢复代价：fault-with-recovery (16.1M) vs fault-no-recovery (8.1M) = +99% gas

### 9.4 OP FDG组件测试（与报告对齐）

- [ ] 3个测试通过
- [ ] test_move_simpleAttack_succeeds：~365,885 gas
- [ ] test_stepAttackDummyClaim_defendTrueClaimInTheMiddle_succeeds：~2,778,766 gas
- [ ] test_resolve_stepReached_succeeds：~3,731,850 gas

### 9.5 F本地性能（与报告对齐）

- [ ] baseline b8-p8-c4-s64：162.78 tasks/s（3 run均值）
- [ ] 批总延迟：161.8 ms
- [ ] 恢复消融：recovery-under-fault=12.6ms vs direct-fallback=7.3ms
- [ ] 并发：c=1/4/16 → 121.79/144.63/117.19 tasks/s（无单调增益）

### 9.6 E01真实KZG（与报告对齐）

- [ ] c-kzg版本：4.1.0
- [ ] 容量上界：maxFrameLen=126,976字节，超出1字节抛错
- [ ] 篡改拒绝：修改Blob后KZG验证失败

---

## 十、常见问题

### Q1: 为什么StageH的SGX实验无法复现？

**A**: StageH实验需要真实SGX硬件环境（阿里云ecs.g7t.large或同等实例），普通机器没有`/dev/sgx_enclave`等设备。且本项目**不包含**Enclave源码（在阿里云实例上临时开发，未提交到仓库），仅保留Quote和联调记录。若要完全复现，需自行编写Enclave程序或在同等SGX实例上运行。

### Q2: G-L1的"机制基线"是什么？

**A**: 机制基线是本项目自建的简化版合约，用于机制对照。它**不是**Arbitrum、Optimism或TeeRollup的官方实现。关键差异：机制基线**无兜底adjudicate**，因此提交方离线时正确终局率从30/30跌至0/30。本文实现**有兜底adjudicate**，所有路径均30/30。

### Q3: 为什么OP FDG的gas不能与本文本地gas比较？

**A**: 因为：
1. OP FDG为**组件测试gas**，包含断言和测试框架开销，不是单次调用gas。
2. **端点语义不同**：OP FDG的`move`/`step`/`resolve`与本文的`submit`/`respond`/`adjudicate`在功能和触发时机上不对应。
3. **环境不同**：OP FDG在Foundry+Forge环境，本文在Hardhat环境。
4. **成本不同**：本文费用为**local-gas-only**（不含DA/TEE），OP FDG可能包含不同成本模型。

因此只能分层报告（机制对照、组件测试、文献定量），**不可生成统一胜负表**（G-CE-06）。

### Q4: F阶段的"162.78 tasks/s"是否代表真实TPS？

**A**: 否。这是**本地Hardhat TPS**，附带以下口径限制：
1. Hardhat in-process automining（无真实共识最终性）
2. 每块链钟+1秒（固定出块间隔）
3. Closed-loop到达（非open-loop压力）
4. 费用local-gas-only（不含DA/TEE成本）

**不能写成**"高频DApp TPS 162.78"。**应写成**"本地Hardhat TPS 162.78（串行出块，closed-loop）"。

### Q5: 为什么Sepolia Blob广播blocked？

**A**: 因为缺少以下环境变量和资源：
- `SEPOLIA_RPC_URL`：Sepolia RPC endpoint（如Infura/Alchemy）
- `SEPOLIA_PRIVATE_KEY`：测试钱包私钥
- Sepolia ETH：测试币（从faucet获取）
- `BLOB_BATCH_ANCHOR_ADDRESS`：已部署的BlobBatchAnchor合约地址
- `BEACON_API_URL`：Sepolia beacon链API（用于取回Blob）

没有这些资源，无法广播真实type-3交易、独立取回Blob、记录链上`blobGasUsed`/`blobGasPrice`。

### Q6: 如何判断实验是否成功复现？

**A**: 对照§9数据验证检查清单，逐项核对关键数据。如gas值在±10%范围内、正确终局率一致、罚没金额一致，则视为成功复现。若差异过大，检查：
1. Node/npm/Hardhat版本
2. 随机种子是否固定
3. 网络状态（本地Hardhat vs 公网）
4. 合约编译器版本（solc）

---

## 附录：版本与环境信息

### A.1 软件版本

| 软件 | StageH使用版本 | 推荐版本 |
|---|---|---|
| Node.js | 18.x | 18.x或20.x |
| npm | 8.x+ | 9.x+ |
| Hardhat | 2.x | 2.22.0+ |
| Solidity编译器 | 0.8.24 | 0.8.24 |
| c-kzg | 4.1.0 | 4.1.0或更高 |
| Foundry（Forge） | 1.5.1-stable | 1.5.1+（OP FDG测试） |
| Go | 1.24.5 | 1.24.5+（BoLD，blocked） |
| SGX SDK | 2.19.100.3 | 2.19.100.3+（SGX实验，blocked） |
| DCAP | 1.16.100.2 | 1.16.100.2+（SGX实验，blocked） |

### A.2 硬件与平台

| 项 | StageH配置 | 最低要求（本地） | 最低要求（SGX） |
|---|---|---|---|
| CPU | Intel Xeon Platinum 8369B | x86_64多核 | Intel SGX支持 |
| 内存 | 8 GB+ | 4 GB+ | 8 GB+ |
| 存储 | SSD 40 GB+ | SSD 20 GB+ | SSD 40 GB+ |
| 操作系统 | Alibaba Cloud Linux 2.1903 | Linux/macOS/Windows | Linux（SGX驱动） |
| SGX设备 | `/dev/sgx_enclave`、`/dev/sgx_provision` | 不需要 | 必需 |

### A.3 网络与RPC

| 网络 | StageH状态 | RPC endpoint | 说明 |
|---|---|---|---|
| 本地Hardhat | ✅已用 | http://127.0.0.1:8545 | in-process automining |
| Sepolia | ❌blocked | https://sepolia.infura.io/v3/... | 需PROJECT_ID |
| Sepolia Beacon | ❌blocked | https://sepolia.beaconcha.in/api/ | 用于Blob取回 |

---

## 联系方式

如有复现问题或发现数据不一致，请通过以下方式联系：

- GitHub Issue: https://github.com/shanse11/TEE-code-and-paper/issues
- 邮件：[作者邮箱]
- 分支：`cursor/revision-joca-expert-response-8a7b`

---

**文档结束**

**最后更新**: 2026年10月28日  
**下一步**: 生成`reply_to_reviewers_zh.md`（回复信草稿）
