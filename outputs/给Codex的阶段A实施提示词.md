# 给 Codex 的阶段 A 实施提示词

> 使用方式：将下方“提示词正文”完整复制给 Codex。该提示词要求 Codex **只实现阶段 A：冻结版本、环境和实验口径**，不提前改造恢复协议、真实 TEE、真实 DA 或罚没逻辑。

---

## 提示词正文

你是本项目的工程实现代理。请在以下工作区内完成 **Hybrid TEE-Rollup 返修实验阶段 A：冻结版本、环境和实验口径**：

```text
工作区：/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup
```

### 一、背景与当前工程事实

本项目正在根据两位评审专家的意见补充实验。阶段 A 的目标不是产生新的性能结论，而是先把后续实验所依赖的代码版本、配置、任务规模、并发含义、Blob 计数、吞吐量分母、恢复时间定义和费用分母固定下来，使后续结果可以复现并与论文第 5 章逐项对应。

请先确认以下现状，不要假设当前 git commit 已经包含所有实验代码：

1. 当前分支是 `main`，当前 HEAD 为：

   ```text
   615bb3e9f1ae3b88b87f488decc61854cd555e16
   ```

2. 工作区存在未跟踪或未提交的阶段性工程文件。不得使用 `git reset --hard`、`git clean -fd`、删除未跟踪文件或覆盖既有实验产物。
3. 既有基线目录为：

   ```text
   /Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/revision_runs/20260911T095029Z
   ```

   必须保留，不能覆盖、重命名或删除。
4. 需要重点检查的现有文件包括：

   ```text
   evm/revision/hardhat.config.js
   evm/revision/revision_env.js
   evm/revision/performance.js
   evm/revision/blobcodec.js
   evm/revision/blob_offline.js
   evm/revision/blob_publish.js
   evm/revision/blob_fetch.js
   evm/revision/blob_verify.js
   evm/revision/blob_receipt.js
   evm/revision/blob_challenge_settle.js
   evm/revision/security.test.js
   evm/revision/random_security.js
   evm/revision/legacy_counterexamples.js
   evm/revision/package.json
   evm/package.json
   evm/contracts/BoundedTaskRollup.sol
   evm/contracts/BlobBatchAnchor.sol
   revision_runs/20260911T095029Z/external_status.json
   ```

5. 已知口径问题：
   - `performance.js` 当前有 `concurrency=[1,4,16]`、`payloadKiB=[1,8,32]`、`batchSize=[1,8,32]`，且使用 `Math.min(batchSize, concurrency)`，导致 `batchSize=1` 时设置的并发 4/16 实际退化为 1；
   - `performance.js` 中的 `payloadKiB` 语义是“每任务”，而 `blobcodec.js` 当前的同名参数可能表示“整批”，不能直接混用；
   - `revision_env.js` 在加载 `.env` 前捕获 `REVISION_RUN`，所以 `REVISION_RUN` 必须在进程启动前设置，且必须是绝对路径；
   - 当前 revision Hardhat 配置使用 Solidity 0.8.26、`viaIR=true`、Cancun，具体 optimizer 设置和账户配置必须从实际配置读取并记录，不要凭记忆硬编码；
   - 当前本地链配置为 Hardhat、chainId 31337、hardfork Cancun；
   - 真实 Sepolia Blob 和真实 TEE 当前不是阶段 A 的实现范围，也不得在本任务中广播交易、调用云服务或伪造真实实验结果。

### 二、严格范围

#### 本次必须完成

1. 实现一个可追溯的实验运行清单 `run_manifest`；
2. 实现一个规范化实验配置文件及配置校验器；
3. 固定代码来源、工作区状态、编译配置、链配置、依赖版本和公开环境信息；
4. 固定任务规模、载荷大小、并发、Blob 数量、吞吐量、恢复时间和费用的定义；
5. 建立机器可读的 JSON/JSONL 原始记录格式；
6. 让现有 revision 实验脚本能够读取统一配置，或者至少提供不改变原有行为的适配层；
7. 用本地、离线、无网络的自检验证阶段 A 产物；
8. 输出清晰的实现报告，列出修改文件、执行命令、验收结果和剩余限制。

#### 本次禁止完成

1. 不修改 `BoundedTaskRollup.sol`、`BlobBatchAnchor.sol` 或其他合约的状态转移、权限、挑战、恢复、结算语义；
2. 不实现真实 SGX/TDX Quote、PCCS/DCAP、云实例或远程证明；
3. 不广播 Sepolia 或其他公网交易；
4. 不调用真实 Blob endpoint，不把本地 Blob 文件伪装成公网取回结果；
5. 不实现 DA 罚没闭环；
6. 不把本地 Hardhat gas、离线 KZG 或 MockTEE/MockDA 结果写成真实网络实验；
7. 不覆盖 `revision_runs/20260911T095029Z`；
8. 不提交 git commit、不 push、不修改用户已有提交历史。可以记录当前 HEAD；如果实现后需要提交，先停止并报告，不要自行提交；
9. 不把私钥、助记词、RPC token、`.env` 值或其他密钥写入 manifest、日志、JSONL、错误堆栈或报告。

### 三、第一步：只读检查和工作区保护

在编写代码前，先执行并保存以下信息：

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git diff --stat
git ls-files --others --exclude-standard
```

同时检查以下目录是否存在以及是否已有内容：

```text
revision_runs/20260911T095029Z
revision_runs/
outputs/
ev​​m/revision/
```

注意：上面最后一项实际路径是 `evm/revision/`，不要创建名为 `ev​​m` 的错误目录。

如果工作区不是 clean，必须在 manifest 中明确记录 `dirty=true`，不能声称存在一个已经包含所有实现的干净冻结 commit。阶段 A 的“版本冻结”应表示为：

- `gitHead`：当前 HEAD；
- `gitDirty`：工作区是否有改动；
- `trackedDiffSha256`：已跟踪文件 diff 的哈希；
- `untrackedFiles`：未跟踪文件列表；
- `sourceTreeSha256`：纳入本次实验的源文件集合哈希；
- `sourceFileSha256`：逐文件哈希清单。

### 四、推荐实现文件

先检查仓库中是否已有等价模块。如果已有，应扩展已有模块，避免重复创建。若没有，建议新增以下文件：

```text
evm/revision/experiment_config.js
 evm/revision/freeze_experiment.js
 evm/revision/experiment_record.js
 evm/revision/config/stageA.local.json
 evm/revision/schemas/run_manifest.schema.json
 evm/revision/schemas/experiment_record.schema.json
```

文件名可以根据现有项目风格调整，但最终必须提供一个明确的主入口，建议为：

```text
evm/revision/freeze_experiment.js
```

主入口应支持：

```text
--help
--config <absolute-or-repository-relative-json>
--run-dir <absolute-path>
--run-id <id>
--validate-only
--self-test
```

要求：

1. `--run-dir` 和 `REVISION_RUN` 二选一；如果二者都存在，命令行参数优先；
2. 最终 run 目录必须是绝对路径；
3. 不传 run 目录时必须失败，不能默默写入临时目录；
4. 不同运行不能复用已有 run 目录，除非显式传入 `--resume`；阶段 A 默认不允许覆盖已有文件；
5. 配置、manifest 和记录写入前先创建目标目录，并使用 UTF-8；
6. JSON 使用稳定键排序或等价的规范化序列化，以便生成可复核哈希；
7. JSONL 每行必须是一个完整 JSON 对象，禁止把多行 JSON 写成一条记录；
8. 所有时间统一用 UTC ISO 8601，例如 `2026-09-12T08:00:00.000Z`；
9. 所有相对证据路径相对于本次 run 根目录，不能写入机器特有的临时绝对路径作为唯一定位；
10. 失败必须显式返回非零退出码，并写入 `status=fail` 或 `status=blocked` 的记录，不能只打印错误后退出。

### 五、统一配置格式

请实现配置读取、默认值、字段校验和规范化输出。推荐配置结构如下；字段名称可以微调，但语义不得改变：

```json
{
  "schemaVersion": "hybrid-tee-rollup.stageA.v1",
  "runId": "20260912T000000Z-stageA-local",
  "protocolVersion": "hybrid-tee-rollup-revision-1",
  "source": {
    "include": [
      "evm/contracts/**/*.sol",
      "evm/revision/**/*.js",
      "evm/revision/**/*.json",
      "evm/revision/**/*.txt",
      "tee_rollup_demo/**/*.py",
      "scripts/**/*.py",
      "tests/**/*.py"
    ],
    "exclude": [
      ".git/**",
      "node_modules/**",
      "artifacts/**",
      "cache/**",
      "revision_runs/**",
      "outputs/**",
      "__pycache__/**",
      "*.pyc"
    ]
  },
  "chain": {
    "backend": "hardhat",
    "network": "hardhat-local",
    "chainId": 31337,
    "hardfork": "cancun",
    "rpcMode": "in-process",
    "finalityDefinition": "local-automining-no-consensus-finality"
  },
  "build": {
    "configPath": "evm/revision/hardhat.config.js",
    "artifactRoot": "<resolved-by-runtime>",
    "cacheRoot": "<resolved-by-runtime>",
    "solidity": "<read-from-config>",
    "viaIR": "<read-from-config>",
    "optimizer": "<read-from-config>",
    "nodeVersion": "<runtime>",
    "pythonVersion": "<runtime-if-used>"
  },
  "workload": {
    "batchSize": [1, 8, 32],
    "payloadKiBPerTask": [1, 8, 32],
    "concurrency": [1, 4, 16],
    "stepCount": "<read-from-script-or-null>",
    "encodingVersion": "<explicit-version>"
  },
  "backends": {
    "tee": "simulated-only",
    "da": "local-mock-or-offline-only",
    "blobMode": "offline-only"
  },
  "metrics": {
    "throughputUnit": "finalized_tasks_per_second",
    "throughputNumerator": "finalizedTasks",
    "throughputDenominator": "measurementWindowSeconds",
    "recoveryStart": "faultInjectedAt",
    "recoveryEndpoints": [
      "firstValidProgressAt",
      "resolvedAt",
      "withdrawableAt"
    ],
    "costPrimaryDenominator": "finalizedTask",
    "costSecondaryDenominators": [
      "acceptedTask",
      "submittedBatch"
    ],
    "includeFailedAttempts": true,
    "l1FeeDefinition": "gasUsed_times_effectiveGasPrice",
    "blobFeeDefinition": "blobGasUsed_times_blobGasPrice"
  },
  "output": {
    "writeManifest": true,
    "writeSourceHashes": true,
    "writeEnvironmentSnapshot": true,
    "writeConfigResolved": true,
    "writeJsonl": true,
    "validateEveryRecord": true
  }
}
```

注意：配置示例中的 `<read-from-config>` 等只是说明，最终生成的实际配置不能保留尖括号占位符。所有字段要么填入实际值，要么明确使用 `null` 并记录 `not_applicable` 原因。

### 六、必须固定的口径

#### 1. batchSize

将 `batchSize` 定义为一个逻辑实验批次中的任务数，而不是客户端内部的调度组大小。

如果现有 `performance.js` 中的 `batchSize` 实际只是客户端调度组大小，必须：

- 将内部变量重命名为 `dispatchGroupSize`，或增加明确的语义字段；
- 在记录中同时保存 `batchSize`、`dispatchGroupSize` 和 `taskCount`；
- 不得继续用同一个字段表示两个不同概念；
- 如果现有脚本无法真正形成链上聚合批次，必须在 manifest 中写明 `batchSemantics="client-dispatch-group"`，不能假装已经实现链上批处理。

#### 2. payloadBytes

统一使用：

```text
payloadBytesPerTask = payloadKiBPerTask * 1024
batchPayloadBytes = batchSize * payloadBytesPerTask
```

必须在每条实验记录中同时记录：

```text
payloadKiBPerTask
payloadBytesPerTask
batchPayloadBytes
encodedBytes
```

禁止让 `blobcodec.js` 和 `performance.js` 对同一个 `payloadKiB` 使用不同含义。旧参数如果必须兼容，改名为 `legacyPayloadKiB` 或提供显式 `payloadScope`，不能静默解释。

#### 3. concurrency

将 `concurrency` 定义为同时在途的逻辑任务或批次数量，并在配置中明确是：

```text
concurrencyUnit = "inflight_batches"
```

禁止使用：

```js
Math.min(batchSize, concurrency)
```

来替代用户配置的并发值。可以记录实际调度值 `actualInFlight`，但必须同时保留：

```text
configuredConcurrency
actualInFlight
concurrencyUnit
```

当 `batchSize=1`、`concurrency=4` 或 `16` 时，必须能够区分这三组实验；如果底层实现受限而无法达到目标并发，应记录 `status="blocked"` 或 `actualInFlight`，并说明原因，不能把实际值静默改成 1。

#### 4. Blob 数量

`blobCount` 必须由编码后的真实字节数和Blob容量推导，不能由任务数直接假定。对 EIP-4844 离线模式，记录：

```text
blobBytes = 131072
encodedBytes
paddingBytes
blobCount = ceil(encodedBytes / blobBytes)
```

如果现有编码器暂时只支持单Blob，遇到超容量输入时必须明确失败或阻塞，并写出原因；不能截断、静默缩小载荷或把多Blob数据伪装成一个Blob。

#### 5. 吞吐量

吞吐量不是配置输入，而是根据记录计算的派生指标。至少区分：

```text
executionThroughput = executedTasks / executionWindowSeconds
acceptedThroughput = acceptedTasks / l1AcceptanceWindowSeconds
finalizedThroughput = finalizedTasks / finalizationWindowSeconds
```

每个吞吐值必须同时记录 numerator、denominator、时间窗口起止时间和失败/重试数量。Hardhat 自动出块速度不得写成公网 TPS，manifest 中要有：

```text
throughputEnvironment = "local-hardhat-automining"
```

#### 6. 恢复时间

阶段 A 只冻结定义，不要求本次实现恢复协议。统一记录以下时间字段，暂时没有值时使用 `null`，并在 `notApplicableReason` 中说明：

```text
faultInjectedAt
failureDetectedAt
recoveryTriggeredAt
firstValidProgressAt
resolvedAt
finalizedAt
withdrawableAt
```

推荐派生定义：

```text
failureDetectionTime = failureDetectedAt - faultInjectedAt
recoveryTakeoverTime = recoveryTriggeredAt - failureDetectedAt
firstProgressRecoveryTime = firstValidProgressAt - faultInjectedAt
settlementRecoveryTime = finalizedAt - faultInjectedAt
withdrawalRecoveryTime = withdrawableAt - faultInjectedAt
```

禁止只写一个没有起止点的 `recoveryTime`，也不能把“调用 recover 函数成功”直接等同于“恢复完成”。

#### 7. 费用分母

统一主指标为：

```text
costPerFinalizedTask = totalMeasuredCost / finalizedTasks
```

并同时保留：

```text
costPerAcceptedTask
costPerSubmittedBatch
failedAttemptCost
```

所有费用记录必须区分：

```text
l1ExecutionGas
l1ExecutionFee
blobGasUsed
blobGasPrice
blobFee
teeExecutionCost
teeVerificationCost
daServiceCost
challengeCost
recoveryCost
settlementCost
```

本地 Hardhat 只有 gas 计量时，字段应标注 `feeStatus="not_measured"` 或 `feeSource="local-gas-only"`，不得填入虚构的 Blob fee。

### 七、run_manifest 的最低字段

生成的 `manifest/run_manifest.json` 至少包含以下字段：

```json
{
  "schemaVersion": "hybrid-tee-rollup.stageA.v1",
  "runId": "...",
  "createdAtUtc": "...",
  "status": "planned|ready|closed|fail|blocked",
  "gitHead": "...",
  "gitBranch": "...",
  "gitDirty": true,
  "trackedDiffSha256": "...",
  "untrackedFiles": [],
  "sourceTreeSha256": "...",
  "sourceFileSha256Path": "manifest/source_files.sha256",
  "configPath": "manifest/config.resolved.json",
  "configSha256": "...",
  "environmentSnapshotPath": "manifest/environment_public.json",
  "dependencySnapshotPath": "manifest/dependencies.json",
  "chain": {},
  "build": {},
  "workload": {},
  "backends": {},
  "metricDefinitions": {},
  "evidenceRoot": ".",
  "limitations": []
}
```

补充要求：

1. `untrackedFiles` 必须包括现有 revision 工程文件，但不能把本次新生成的 run 输出再次纳入自己的 source hash；
2. `source_files.sha256` 必须按规范化相对路径排序；
3. `gitDirty=true` 时，`limitations` 中必须自动写入“当前结果依赖工作区快照，不等同于仅由 HEAD commit 表示”；
4. 环境清单只能记录公开信息：OS、Node/Python版本、npm包版本、编译器配置、时区、locale、CPU/内存摘要；
5. 对以下环境变量只能记录是否存在，不得记录值：

   ```text
   SEPOLIA_RPC_URL
   SEPOLIA_PRIVATE_KEY
   BLOB_BATCH_ANCHOR_ADDRESS
   BEACON_API_URL
   ETHERSCAN_API_KEY
   ```

### 八、机器可读 JSONL 记录格式

实现一个统一记录函数，例如：

```js
recordExperimentSample(record)
recordExperimentEvent(event)
recordFailure(failure)
```

每条样本记录至少包含：

```json
{
  "schemaVersion": "hybrid-tee-rollup.sample.v1",
  "runId": "...",
  "experimentId": "stageA-self-test",
  "caseId": "local-config-validation",
  "sampleId": "000001",
  "status": "pass|fail|blocked|skipped",
  "startedAtUtc": "...",
  "endedAtUtc": "...",
  "durationMs": 0,
  "gitHead": "...",
  "configSha256": "...",
  "chain": {
    "backend": "hardhat",
    "chainId": 31337,
    "hardfork": "cancun"
  },
  "workload": {
    "batchSize": 1,
    "taskCount": 1,
    "payloadKiBPerTask": 1,
    "payloadBytesPerTask": 1024,
    "batchPayloadBytes": 1024,
    "encodedBytes": null,
    "blobCount": null,
    "stepCount": null,
    "configuredConcurrency": 1,
    "actualInFlight": null,
    "concurrencyUnit": "inflight_batches"
  },
  "backend": {
    "tee": "simulated-only",
    "da": "local-mock-or-offline-only"
  },
  "timeline": {
    "faultInjectedAt": null,
    "failureDetectedAt": null,
    "recoveryTriggeredAt": null,
    "firstValidProgressAt": null,
    "resolvedAt": null,
    "finalizedAt": null,
    "withdrawableAt": null
  },
  "cost": {
    "gasUsed": null,
    "l1ExecutionFee": null,
    "blobGasUsed": null,
    "blobGasPrice": null,
    "blobFee": null,
    "feeStatus": "not_measured"
  },
  "failure": null,
  "evidence": []
}
```

请将样本记录写入：

```text
<run-dir>/raw/experiment_records.jsonl
```

将状态变化或端到端时间线事件写入：

```text
<run-dir>/raw/experiment_events.jsonl
```

验证器必须检查：

- 必填字段存在；
- 枚举值合法；
- 字节数、KiB、batchSize 和 taskCount 的派生关系一致；
- `configuredConcurrency` 和 `actualInFlight` 不为负数；
- `actualInFlight > configuredConcurrency` 时必须失败；
- `status=fail/blocked` 时必须有 failure 对象；
- `status=pass` 时不得带未解释的关键字段缺失；
- 时间字段满足 UTC 格式；
- 同一 `runId + experimentId + sampleId` 不重复；
- 不允许记录私钥、助记词、Authorization header 或完整 `.env` 内容。

### 九、现有脚本的适配要求

请根据检查结果，对现有 revision 脚本做最小、可审计的适配：

1. 增加统一配置入口，例如 `--config`；如果暂时不能改全部脚本，至少提供 `experiment_config.js` 作为单一解析入口，并由主实验入口生成 resolved config；
2. 保留旧环境变量和旧命令的兼容性，但在记录中标注 `configSource="legacy-env"`；
3. `REVISION_RUN` 必须在脚本启动阶段校验绝对路径；
4. 性能脚本不得继续通过 `Math.min(batchSize, concurrency)` 静默降低并发；
5. Blob 编解码脚本必须明确参数是每任务还是整批；推荐统一使用 `payloadKiBPerTask`，并计算 `batchPayloadBytes`；
6. Blob 超容量时必须输出 `blocked` 或 `fail`，不能自动缩小输入；
7. 所有脚本的输出必须至少能关联到 `runId`、`configSha256` 和 `sampleId`；
8. 不得改动合约行为或把当前独立 `BlobBatchAnchor` 写成已经与核心任务强绑定；
9. 不得把 `blob_challenge_settle.js` 当前的 `NOT_IMPLEMENTED` 改写为已完成，只能如实记录为未实现/阻塞。

### 十、输出目录结构

新 run 建议采用以下结构：

```text
<run-dir>/
  manifest/
    run_manifest.json
    config.resolved.json
    source_files.sha256
    environment_public.json
    dependencies.json
    git_status.txt
    git_diff_stat.txt
  raw/
    experiment_records.jsonl
    experiment_events.jsonl
    failures.jsonl
  validation/
    config_validation.json
    record_validation.json
    secret_scan.json
  logs/
    freeze_experiment.log
  summary.json
```

不要把 `node_modules/`、Hardhat `artifacts/`、`cache/` 或完整工作区复制进 run；只保留路径、版本和哈希清单。

### 十一、必须执行的本地验收

实现后，在不访问公网、不需要云凭据、不使用私钥的条件下完成以下验收：

#### A. 语法和帮助信息

```bash
node --check evm/revision/experiment_config.js
node --check evm/revision/freeze_experiment.js
node --check evm/revision/experiment_record.js
node evm/revision/freeze_experiment.js --help
```

如果实际文件名不同，使用对应文件执行同等检查。

#### B. 配置校验

至少测试：

1. 合法配置通过；
2. 缺少 `schemaVersion` 失败；
3. `chainId` 类型错误失败；
4. `payloadKiBPerTask <= 0` 失败；
5. `concurrency <= 0` 失败；
6. 旧的模糊 `payloadKiB` 没有 `payloadScope` 时失败或被明确标记 legacy；
7. 运行目录不是绝对路径时失败；
8. 已存在且非空的 run 目录默认拒绝覆盖；
9. 配置引用公网 backend 但没有相应资源时得到 `blocked`，不得广播或继续伪造。

#### C. 版本和环境冻结

运行一次全新的本地 self-test，确认生成：

```text
run_manifest.json
config.resolved.json
source_files.sha256
environment_public.json
dependencies.json
git_status.txt
git_diff_stat.txt
```

检查：

- `gitHead` 正确；
- `gitDirty` 与 `git status` 一致；
- 未跟踪 revision 文件被列出；
- `sourceTreeSha256` 可重复计算；
- `.env` 中的秘密值没有出现在任何输出中；
- run 输出没有反向进入自身 source hash。

#### D. JSON/JSONL 校验

至少写入一条 pass、一条 fail、一条 blocked 记录，然后执行验证器。要求：

- 每行都可以独立解析；
- 非法记录被指出具体行号和字段；
- 重复 sampleId 被拒绝；
- 失败记录含原因；
- 记录中不存在秘密值；
- 聚合 summary 能给出通过数、失败数、阻塞数和总数。

#### E. 口径回归

至少验证以下配置不会被静默改写：

```text
batchSize=1, concurrency=1
batchSize=1, concurrency=4
batchSize=1, concurrency=16
batchSize=8, concurrency=4
batchSize=32, concurrency=16
```

输出中必须能看出 `configuredConcurrency` 和 `actualInFlight` 的差异。若当前调度实现无法满足某个目标并发，必须显式标记原因，而不是将配置值改成实际值后继续报告通过。

同时验证：

```text
payloadKiBPerTask=8, batchSize=1  -> batchPayloadBytes=8192
payloadKiBPerTask=8, batchSize=8  -> batchPayloadBytes=65536
payloadKiBPerTask=8, batchSize=32 -> batchPayloadBytes=262144
```

当 `batchPayloadBytes` 超过单Blob容量时，必须根据实际编码策略计算 `blobCount`，或者显式标记当前编码器不支持多Blob；不得截断载荷。

#### F. 既有安全回归的边界

阶段 A 完成后可以运行现有本地语法、配置和离线检查；可以运行已有单元测试作为回归确认，但不要将此次阶段 A 的通过写成恢复、TEE、DA 或罚没闭环已经完成。

### 十二、完成标准

只有同时满足以下条件，阶段 A 才能报告为完成：

1. 有一个明确的冻结入口和配置入口；
2. 每次运行都有唯一 `runId` 和独立 run 目录；
3. manifest 同时记录 HEAD、dirty 状态、diff 哈希、未跟踪文件和源文件哈希；
4. Hardhat chainId、hardfork、编译器、optimizer、viaIR、账户和依赖版本均来自实际运行环境；
5. `batchSize`、`payloadBytesPerTask`、`batchPayloadBytes`、`concurrency`、`actualInFlight`、`blobCount` 的语义无歧义；
6. 吞吐量、恢复时间和费用分母已经写入数据字典，并能在样本中回溯；
7. 现有性能脚本不再静默使用 `Math.min(batchSize, concurrency)` 代替并发配置，或明确记录该限制并使对应样本为 blocked；
8. `blobcodec.js` 与性能脚本不再对相同参数使用相反的批次/任务语义；
9. JSON/JSONL 记录可以逐行解析并通过 schema/字段验证；
10. 失败、阻塞、跳过和通过状态可区分；
11. 输出中没有私钥、助记词、token 或完整环境变量；
12. 不修改合约语义、不广播公网交易、不伪造真实 TEE/DA 结果；
13. 生成实现报告，列出尚未完成的阶段 B-G 工作。

### 十三、最终报告格式

完成后请不要只回复“已完成”。请按以下结构报告：

```text
1. 实际修改的文件
2. 新增的命令和用法
3. manifest、schema、JSONL 的位置
4. 运行的验收命令及结果
5. 当前 HEAD、gitDirty、sourceTreeSha256
6. batchSize/payload/concurrency/blobCount/throughput/recovery/cost 的最终口径
7. 已知限制和 blocked 项
8. 未完成的阶段 B-G 项目
9. 是否需要用户批准后续 commit（不要自行 commit）
```

再次强调：本任务只负责把实验“固定、可追溯、可复现”，不负责证明真实 TEE、真实 DA、真实 Blob fee、生产网络性能或完整罚没闭环。任何尚未完成的部分必须在 manifest 和最终报告中如实标记为 `blocked`、`not_measured` 或 `not_implemented`。

---

## 给用户的补充说明

将提示词交给 Codex 后，建议要求它先完成“只读检查和实现计划”，再开始写代码。重点关注以下四个输出是否正确：

1. `gitDirty` 是否如实反映当前工作区，而不是把 HEAD 假装成完整冻结版本；
2. `batchSize` 是否与 `dispatchGroupSize` 区分；
3. `payloadKiB` 是否统一为“每任务”并计算整批字节数；
4. 并发 4/16 是否不再在 `batchSize=1` 时被静默压成 1。

阶段 A 完成后，才能进入阶段 B 的本地安全、恢复和资金闭环实验。真实 TEE、真实 Blob 和公网费用不属于本提示词的执行范围。