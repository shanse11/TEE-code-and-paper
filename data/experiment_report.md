# 第八周代码实现实验报告（自动生成）

生成时间：`2026-05-09 08:20:41 UTC`

## 1. 轻量化提交开销对比

| 样本ID | 全量提交字节 | 轻量提交字节 | 节省字节 | 降幅 |
| --- | ---: | ---: | ---: | ---: |
| report-1 | 687 | 406 | 281 | 40.90% |
| report-2 | 698 | 406 | 292 | 41.83% |

平均全量提交：`692.50 bytes`
平均轻量提交：`406.00 bytes`
平均节省字节：`286.50 bytes`
平均降幅：`41.37%`

## 2. 策略成本估算（Gas）

| 样本ID | 全量上链Gas | 轻量提交+DA Gas | 轻量提交+BlobDA Gas |
| --- | ---: | ---: | ---: |
| report-1 | 10992 | 6496 | 4872 |
| report-2 | 11168 | 6496 | 4872 |

平均全量上链Gas：`11080.00`
平均轻量提交+DA Gas：`6496.00`
平均轻量提交+BlobDA Gas：`4872.00`
平均Gas降幅（轻量+DA）：`41.37%`
平均Gas降幅（轻量+BlobDA）：`56.03%`

## 3. 多场景数据层成本曲线

| 场景 | 平均总Gas | 平均降幅 |
| --- | ---: | ---: |
| full_onchain_calldata | 11080.00 | 0.00% |
| compact_commit_external_da | 8019.00 | 27.62% |
| compact_commit_eip4844_like | 7119.00 | 35.75% |
| compact_commit_modular_da_sampling | 6807.50 | 38.56% |

## 4. 三阶段挑战流程实验

- 挑战交易ID：`report-2`
- 挑战开启状态：`OPEN`
- 挑战应答状态：`RESPONDED`
- 会话超时检测：`True`
- 恢复后状态：`RECOVERED`（恢复次数 `1`）
- 二分定位轮次：`2`
- 单步重放目标步：`2`
- 单步重放结果：`passed=False`
- 仲裁结果：`challenge_success=True`
- 判定原因：`da_payload_hash_mismatch, da_proof_invalid, attestation_invalid, state_root_mismatch`
- 最终交易状态：`SLASHED`

## 5. 可贴组会结论

在本次 `2` 组样本实验中，轻量化提交（`state_root + output_hash + proof_hash + da_pointer`）相较全量提交平均节省 `286.50` 字节，平均降幅 `41.37%`。
在Gas估算中，轻量提交+DA 和 轻量提交+BlobDA 相较全量上链分别实现 `41.37%` 和 `56.03%` 的平均降幅。
对篡改样本执行 `challenge-open -> challenge-respond -> challenge-step -> challenge-recover -> challenge-replay -> challenge-resolve` 后，系统在会话超时场景下完成失败恢复，并通过二分定位与单步重放识别异常，最终将交易状态置为 `SLASHED`。

## 6. 结果文件

- 链上轻量提交文件：`E:\项目\project_code\data\chain_experiment_report.json`
- DA 完整数据文件：`E:\项目\project_code\data\da_experiment_report.json`
