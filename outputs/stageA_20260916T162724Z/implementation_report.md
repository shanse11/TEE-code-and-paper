# 阶段 A 实施报告（再次确认 / 复核）

> 本报告对应本次会话的复核与执行结果。在 2026-09-12 完成阶段 A 主实现（见 `outputs/stageA_20260912T083000Z/implementation_report.md`）后，本次重新跑通了所有验收项，并新增了 2026-09-16 的本地 self-test run，作为当前状态的可复现证据。
>
> 未对已实现文件做任何修改；本次仅为复核与新 run。

## 1. 实际修改的文件

阶段 A 主实现（2026-09-12）已完成的文件清单：

- `evm/revision/experiment_config.js`
- `evm/revision/freeze_experiment.js`
- `evm/revision/config/stageA.local.json`
- `evm/revision/schemas/run_manifest.schema.json`
- `evm/revision/stageA_config.test.js`

既有文件被复用、未修改：

- `evm/revision/experiment_record.js`
- `evm/revision/metric_definitions.json`
- `evm/revision/schemas/experiment_record.schema.json`
- `evm/revision/schemas/experiment_event.schema.json`
- `evm/revision/stageA_record.test.js`

本次会话未对上述任何文件做修改。`git diff --stat` 输出为空，HEAD 与 `evm/revision/` 下源代码内容未改变，仅生成了新的 run 输出。

## 2. 新增的命令和用法

```sh
# 语法检查
node --check evm/revision/experiment_config.js
node --check evm/revision/freeze_experiment.js
node --check evm/revision/experiment_record.js

# 帮助
node evm/revision/freeze_experiment.js --help

# 仅校验配置，不创建 run 目录
node evm/revision/freeze_experiment.js --validate-only --config evm/revision/config/stageA.local.json

# 完整 freeze + self-test
node evm/revision/freeze_experiment.js \
  --config evm/revision/config/stageA.local.json \
  --run-dir /absolute/new-run \
  --run-id stageA-freeze-run \
  --self-test

# 单测
cd evm/revision && NODE_PATH=../../evm/node_modules node --test stageA_config.test.js
cd evm/revision && NODE_PATH=../../evm/node_modules node --test stageA_record.test.js
```

入口支持 `--help`、`--config`、`--run-dir`、`--run-id`、`--resume`、`--validate-only`、`--self-test`。`--run-dir` 优先于 `REVISION_RUN`；两者均缺失时失败；非空目录默认拒绝覆盖，仅 `--resume` 可显式允许。

## 3. Manifest、schema、JSONL 位置

本次会话新增的 run：

```text
/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/stageA_20260916T162724Z/stageA_freeze/
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

schema 位于 `evm/revision/schemas/{run_manifest,experiment_record,experiment_event}.schema.json`。

`summary.json` 内容（要点）：

```json
{"records":{"blocked":1,"fail":1,"pass":1,"skipped":0,"total":3},"runId":"stageA-freeze-20260916T162724Z","status":"ready"}
```

`validation/record_validation.json` 内容（要点）：

```json
{"counts":{"blocked":1,"fail":1,"pass":1,"skipped":0},"errors":[],"pass":true,"total":3}
```

## 4. 运行的验收命令及结果

| # | 命令 | 结果 |
| - | --- | --- |
| 1 | `node --check evm/revision/experiment_config.js` | OK |
| 2 | `node --check evm/revision/freeze_experiment.js` | OK |
| 3 | `node --check evm/revision/experiment_record.js` | OK |
| 4 | `cd evm/revision && NODE_PATH=../../evm/node_modules node --test stageA_config.test.js` | 5/5 pass |
| 5 | `cd evm/revision && NODE_PATH=../../evm/node_modules node --test stageA_record.test.js` | 16/16 pass |
| 6 | `node evm/revision/freeze_experiment.js --help` | 退出码 0，输出含 `--validate-only` |
| 7 | `node evm/revision/freeze_experiment.js --validate-only --config evm/revision/config/stageA.local.json` | `ready` |
| 8 | `node evm/revision/freeze_experiment.js --run-dir relative` | 拒绝：run 目录必须是绝对路径，退出码 1 |
| 9 | `node evm/revision/freeze_experiment.js --run-dir <existing-non-empty>` | 拒绝：非空目录需 `--resume`，退出码 1 |
| 10 | `node evm/revision/freeze_experiment.js --config evm/revision/config/stageA.local.json --run-dir /Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/stageA_20260916T162724Z/stageA_freeze --run-id stageA-freeze-20260916T162724Z --self-test` | `ready …`，生成完整 run |
| 11 | `python3 -c '…'` 复核 `sourceTreeSha256` | 与 manifest 一致（77 行，SHA-256 复算一致） |
| 12 | `grep` 输出目录中 `stageA_freeze\|stageA_20260916T162724Z` | 不在自身 `source_files.sha256` 中 |
| 13 | `grep -r 'SEPOLIA_PRIVATE_KEY\|SEPOLIA_RPC_URL\|BEACON_API_URL\|BLOB_BATCH_ANCHOR_ADDRESS\|ETHERSCAN_API_KEY' outputs/stageA_20260916T162724Z` | 无任何匹配 |
| 14 | 内联配置校验 9 例（合法、缺 schemaVersion、错误 chainId 类型、payloadKiBPerTask<=0、concurrency<=0、legacy payloadKiB 无 scope、相对 run 目录、非空 run 目录、公共 backend 无资源） | 全部按预期 pass / fail / fail / fail / fail / fail / fail / fail / blocked |
| 15 | 内联口径回归 `(batchSize, payloadKiBPerTask, concurrency)` 五组 | `configuredConcurrency` 严格保持 1/4/16/4/16，`batchPayloadBytes` 与公式一致 |
| 16 | 内联 Blob 超容量：`batchPayloadBytes=262144`（>131072） | 状态=`blocked`，`failure.code=SINGLE_BLOB_CAPACITY_EXCEEDED`，`blobCount=3`，校验通过 |

## 5. 当前 HEAD、gitDirty、sourceTreeSha256

- HEAD：`615bb3e9f1ae3b88b87f488decc61854cd555e16`
- 分支：`main`
- gitDirty：`true`（`git status --short` 输出非空，工作区含有未跟踪的阶段 A 与既有 revision 文件）
- `sourceTreeSha256`（新 run）：`7998677f3f19f1433d3f3a92c8698ef8b27a10ab924f8d6561786e982089f126`（77 文件）

`trackedDiffSha256` 与既有 `revision_runs/20260911T095029Z` 未被本次会话读取或覆盖；`manifest.untrackedFiles` 由 `git ls-files --others --exclude-standard` 给出，按相对路径排序。

## 6. batchSize / payload / concurrency / blobCount / throughput / recovery / cost 最终口径

- 链：Hardhat 本地、chainId 31337、Cancun、in-process、`local-automining-no-consensus-finality`。
- 编译：Solidity 0.8.26、optimizer enabled、runs 200、viaIR=true、evmVersion=cancun、Hardhat accounts.count=40。`hardhat.config.js` 静态解析，不 require，避免触发链或 `REVISION_RUN`。
- workload：batchSize=`[1,8,32]`、payloadKiBPerTask=`[1,8,32]`、concurrency=`[1,4,16]`；`taskCount`、`dispatchGroupSize=null`；并发单位固定 `inflight_batches`；编码版本 `blobcodec-field31-v1`。
- payload：`payloadBytesPerTask = payloadKiBPerTask * 1024`，`batchPayloadBytes = batchSize * payloadBytesPerTask`。旧 `payloadKiB` 必须显式 `payloadScope=per-task` 或 `legacyPayloadSemantics=per-task`，否则失败。
- 并发：禁止 `Math.min(batchSize, concurrency)` 替代配置值；样本中同时保留 `configuredConcurrency`、`actualInFlight`、`concurrencyUnit`。当底层无法满足目标并发时，样本需在 `statusReason` / `failure` 中说明，并记录 `actualInFlight`。
- Blob：`blobBytes=131072`、`blobCount=ceil(encodedBytes/131072)`、`encodedBytes=ceil(frameBytes/31)*32`。当前实际编码器仅单 Blob；`blobCount>1` 时样本必须 `blocked`，不截断、不缩小、不伪装。
- 吞吐：三类（execution / accepted / finalized），每个含 `value / numerator / denominator / start / end / failure / retry`；`throughputEnvironment=local-hardhat-automining`。
- 恢复：`faultInjectedAt → failureDetectedAt → recoveryTriggeredAt → firstValidProgressAt → resolvedAt → finalizedAt → withdrawableAt`；阶段 A 只冻结定义，未测量值用 `null + notApplicableReason`。
- 费用：主分母 `finalizedTask`，次分母 `acceptedTask`/`submittedBatch`；`l1ExecutionFee=gasUsed*effectiveGasPrice`，`blobFee=blobGasUsed*blobGasPrice`；本地阶段统一 `feeStatus=not_measured`，`feeSource=local-gas-only`，不构造真实公网费用。

## 7. 已知限制和 blocked 项

- 不实现真实 SGX/TDX、PCCS/DCAP、云实例或远程证明；TEE 后端固定 `simulated-only`。
- 不实现真实 DA 与真实 Blob 取回；DA/Blob 固定 `local-mock-or-offline-only` / `offline-only`。
- 不广播 Sepolia 或其他公网交易；不调用真实 Blob endpoint、不伪造结果。
- 不实现 DA 罚没闭环、`BoundedTaskRollup.sol` 与 `BlobBatchAnchor.sol` 的状态机改动；`blob_challenge_settle.js` 当前的 `NOT_IMPLEMENTED` 未被改写。
- 当前 `blobcodec.js` 仅单 Blob；超容量样本标记 `blocked`，`encoderMaxBlobs=1`。
- 环境快照仅含公开信息（OS、Node、Python、npm、时区、locale、CPU、内存），六个敏感环境变量仅记录 exists 布尔值；不读取 `.env`、不写入私钥、token 或助记词。
- gitDirty=true：当前结果依赖工作区快照，不等同于仅由 HEAD commit 表示。

## 8. 未完成的阶段 B–G

按提示词范围，本次只冻结定义与本地记录能力；以下工作不属于阶段 A：

- 阶段 B：本地安全/恢复/资金闭环的真实实现（恢复协议、罚没、对抗性随机种子、撤回资金回收）。
- 阶段 C：真实 TEE 集成（SGX/TDX、PCCS/DCAP、远程证明、attestation 验证回路）。
- 阶段 D：真实 DA（替代 MockDA、链上证明、抽样可用性）。
- 阶段 E：真实 Sepolia Blob 发布/取回与多 Blob 编码器。
- 阶段 F：公网费用、gas/Blob 真实定价与吞吐报告。
- 阶段 G：端到端罚没闭环结算与挑战结算实现（`blob_challenge_settle.js` 当前 `NOT_IMPLEMENTED`）。

## 9. 是否需要用户批准后续 commit

未创建 git commit、未 push。需要由用户明确批准后才能把阶段 A 主实现文件加入下一次提交。本次会话仅新增 run 输出目录 `outputs/stageA_20260916T162724Z/`，对应新 run 目录下的所有文件均位于工作区未跟踪范围内；如用户希望将这些 run 一起提交，请一并批准。