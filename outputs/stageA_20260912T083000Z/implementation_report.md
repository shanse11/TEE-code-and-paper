# 阶段 A 实施报告

## 1. 实际修改的文件

- `evm/revision/experiment_config.js`
- `evm/revision/freeze_experiment.js`
- `evm/revision/config/stageA.local.json`
- `evm/revision/schemas/run_manifest.schema.json`
- `evm/revision/stageA_config.test.js`

未修改 `experiment_record.js`、`metric_definitions.json`、既有 revision 脚本或合约。

## 2. 新增命令和用法

```sh
node evm/revision/freeze_experiment.js --help
node evm/revision/freeze_experiment.js --validate-only --config evm/revision/config/stageA.local.json
node evm/revision/freeze_experiment.js --config evm/revision/config/stageA.local.json --run-dir /absolute/new-run --run-id stageA-run
node evm/revision/freeze_experiment.js --config evm/revision/config/stageA.local.json --run-dir /absolute/new-run --self-test
```

入口支持 `--help`、`--config`、`--run-dir`、`--run-id`、`--validate-only`、`--self-test` 和 `--resume`。`--run-dir` 优先于 `REVISION_RUN`；两者均缺失时失败；非空目录默认拒绝覆盖。

## 3. Manifest、schema、JSONL

最终本地自检 run：

```text
outputs/stageA_20260912T083000Z/stageA_freeze_self_test_final/
```

包含 `manifest/run_manifest.json`、稳定排序的 `config.resolved.json`、`source_files.sha256`、公开环境/依赖/git 快照、`raw` JSONL、校验结果、日志和 `summary.json`。run manifest schema 位于 `evm/revision/schemas/run_manifest.schema.json`。

## 4. 验收命令及结果

```sh
node --check evm/revision/experiment_config.js
node --check evm/revision/freeze_experiment.js
node --test evm/revision/stageA_config.test.js
node --test evm/revision/stageA_record.test.js
node evm/revision/freeze_experiment.js --help
node evm/revision/freeze_experiment.js --validate-only --config evm/revision/config/stageA.local.json
node evm/revision/freeze_experiment.js --config evm/revision/config/stageA.local.json --run-dir /absolute/new-run --self-test
```

结果：语法检查通过；新增配置/冻结测试 5/5 通过；既有记录器回归测试 16/16 通过；self-test 写入并验证 pass、fail、blocked 各一条。最终 run 的 75 个纳入文件已逐个重算，`sourceTreeSha256` 复核一致。

## 5. Git 与源码快照

- HEAD：`615bb3e9f1ae3b88b87f488decc61854cd555e16`
- 分支：`main`
- gitDirty：`true`
- 最终 `sourceTreeSha256`：`e4ab06e383ded9357af0d1aac3d20e5f94e3625ef55c4a5f3aa3a4b30ec1d237`

冻结入口每次真实调用 git，记录 HEAD、分支、dirty、tracked diff SHA-256 与未跟踪文件。源哈希按配置 include/exclude 和相对路径排序；排除当前 run、`outputs`、`revision_runs`、`node_modules`、`artifacts`、`cache`、pyc。

## 6. 固定口径

- Hardhat 本地链：chainId 31337、Cancun、in-process、local automining，无共识最终性。
- Solidity：0.8.26，optimizer enabled、runs 200、viaIR true；Hardhat accounts count 40。入口静态解析 `hardhat.config.js`，不 require，避免读取 `REVISION_RUN` 或运行实验。
- workload：batchSize、payloadKiBPerTask、concurrency 均为 `[1,8,32]`、`[1,8,32]`、`[1,4,16]`；`taskCount`、`dispatchGroupSize` 为 null；并发单位固定 `inflight_batches`。
- `payloadBytesPerTask = payloadKiBPerTask * 1024`，`batchPayloadBytes = batchSize * payloadBytesPerTask`；旧 `payloadKiB` 必须明确 `payloadScope=per-task` 或 legacy 标记。
- Blob 计数按实际 encoded bytes 推导，容量 131072 bytes；单 Blob 编码器超容量时记录 blocked。
- 指标字典随 manifest 冻结，包括三类吞吐、恢复时间点与费用主/次分母。费用在本地阶段保持 `not_measured`/`local-gas-only`，不虚构真实费用。

## 7. 限制和 blocked 项

当前仅冻结定义与本地记录能力：TEE 为 simulated-only，DA 为 local-mock-or-offline-only，Blob 为 offline-only。未实现或证明真实远程证明、真实 DA、真实 Blob 取回/费用、恢复协议、罚没闭环或公网性能。公共 backend 未提供相应资源会得到明确 blocked 结果，不联网。

环境快照只包含公开 OS、Node、Python、npm、时区、locale、CPU、内存信息；六个敏感变量仅保存存在性布尔值；未读取 `.env`。

## 8. 未完成的阶段 B-G

阶段 B-G 的本地安全/恢复/资金闭环、真实 TEE、真实 DA/Blob、公网费用和完整罚没闭环均不属于本次阶段 A 范围，仍需后续独立实施与验证。

## 9. 提交

未创建 commit、未 push。后续如需提交，需要用户明确批准。
