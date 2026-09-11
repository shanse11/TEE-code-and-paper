# 失败场景设计

| 场景 | 注入方式 | 预期检测方式 | 预期结果 |
| --- | --- | --- | --- |
| normal | 不篡改 | verify 通过 | 无 mismatch，不 slash |
| response_tampered | 修改 DA payload 中 response | response_mismatch / attestation_invalid / replay failure | challenge success，SLASHED |
| attestation_invalid | 修改 attestation signature | attestation_invalid | verify failure |
| trace_length_mismatch | 截断 claimed response trace | trace_length_mismatch | replay failure，challenge success |
| challenge_timeout_no_recover | challenge step 后等待超时，不恢复 | challenge session timed out | 流程停滞，不完成 resolve |
| challenge_timeout_recover | 超时后 watchdog recover | recovery history + replay | challenge success，SLASHED |
| da_unavailable | 删除 DA entry | da_unavailable | verify failure |
| da_proof_invalid | 篡改 Merkle proof | da_proof_invalid | verify failure |

实验输出文件：`failure_scenarios.csv`。该表用于论文 Evaluation 中说明原型覆盖了主要异常路径。
