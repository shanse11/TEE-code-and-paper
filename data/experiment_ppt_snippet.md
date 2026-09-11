实验结果与结论（可直接贴PPT）

1. 轻量化提交降本结果
在 2 组样本中，轻量化提交（state_root + output_hash + proof_hash + da_pointer）相较全量提交平均节省 286.50 bytes，平均降幅 41.37%。
全量提交均值 692.50 bytes，轻量提交均值 406.00 bytes。

2. 三阶段挑战机制验证
对篡改交易（report-2）执行 challenge-open -> challenge-respond -> challenge-step -> challenge-recover -> challenge-replay -> challenge-resolve，状态流转为 OPEN -> RESPONDED -> RECOVERED，经过 2 轮二分定位并在步 2 完成重放，仲裁结果 challenge_success=True，最终状态 SLASHED。
异常判定依据：da_payload_hash_mismatch, da_proof_invalid, attestation_invalid, state_root_mismatch。

3. 成本量化结论
Gas估算显示：轻量提交+DA 相较全量上链平均降幅 41.37%，轻量提交+BlobDA 平均降幅 56.03%。
在扩展场景中，compact_commit_modular_da_sampling 的平均总Gas最低，为 6807.50，对应平均降幅 38.56%。

4. 阶段性结论
当前实现已完成“执行层（TEE模拟）+ 验证层（可恢复挑战状态机）+ 数据层（DA轻量化提交与多场景成本曲线）”闭环，在保证可验证性的前提下显著降低链上提交开销，并提升争议流程的鲁棒性。