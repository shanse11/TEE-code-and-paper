# project_code 说明

这个目录是项目的可运行代码区。你之后只要做下面几类事情，基本都会在这里完成：

- 改原型逻辑
- 跑单元测试
- 生成组会实验摘要
- 生成论文实验结果

## 目录

- [`tee_rollup_demo`](</E:/项目/project_code/tee_rollup_demo>)
  - 原型源码
- [`scripts`](</E:/项目/project_code/scripts>)
  - 实验、汇报和辅助脚本
- [`tests`](</E:/项目/project_code/tests>)
  - 单元测试
- [`data`](</E:/项目/project_code/data>)
  - 小规模实验输出
- [`paper_outputs`](</E:/项目/project_code/paper_outputs>)
  - 论文实验结果、图表和配套文档
- [`evm`](</E:/项目/project_code/evm>)
  - Solidity / Hardhat 子工程，用于本地部署与真实 `gasUsed` 实测

## 原型能力

当前原型支持：

1. 确定性 mock 推理，或可选 Ollama 后端。
2. simulated TEE attestation。
3. 轻量 commit：
   - `state_root`
   - `output_hash`
   - `proof_hash`
   - `da_pointer`
   - `da_merkle_root`
4. DA payload 存储与字段级 Merkle proof。
5. recoverable optimistic challenge：
   - `challenge-open`
   - `challenge-respond`
   - `challenge-step`
   - `challenge-recover`
   - `challenge-replay`
   - `challenge-resolve`
6. 失败场景注入：
   - response tampering
   - attestation invalid
   - trace length mismatch
   - DA unavailable
   - DA proof invalid
7. 提交字节与多种 DA profile 的成本估算。

## 快速开始

在这个目录下运行：

```powershell
Set-Location E:\项目\project_code
```

### 最小提交流程

```powershell
python -m tee_rollup_demo submit "Explain optimistic AI rollups in one line."
python -m tee_rollup_demo list
python -m tee_rollup_demo show <tx_id>
python -m tee_rollup_demo verify <tx_id>
```

### 挑战流程

```powershell
python -m tee_rollup_demo tamper <tx_id> "dishonest response"
python -m tee_rollup_demo challenge-open <tx_id>
python -m tee_rollup_demo challenge-respond <tx_id>
python -m tee_rollup_demo challenge-status <tx_id>
python -m tee_rollup_demo challenge-step <tx_id>
python -m tee_rollup_demo challenge-recover <tx_id>
python -m tee_rollup_demo challenge-replay <tx_id>
python -m tee_rollup_demo challenge-resolve <tx_id>
```

### 常用参数

```powershell
python -m tee_rollup_demo --challenge-timeout 10 --max-bisection-rounds 6 challenge-open <tx_id>
```

默认链和 DA 文件位于：

- [`data/chain.json`](</E:/项目/project_code/data/chain.json>)（运行后生成）
- [`data/da.json`](</E:/项目/project_code/data/da.json>)（运行后生成）

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖：

- attestation round-trip
- 提交与验证
- DA Merkle proof
- DA 缺失 / proof 损坏
- tampered response 的挑战与罚没
- timeout recovery
- trace length mismatch
- 提交开销与 DA 策略成本估算

## 脚本说明

### 1. 组会实验报告

```powershell
python scripts\generate_experiment_report.py
python scripts\generate_experiment_report.py --ppt-snippet
```

默认输出：

- [`data/experiment_report.md`](</E:/项目/project_code/data/experiment_report.md>)
- [`data/chain_experiment_report.json`](</E:/项目/project_code/data/chain_experiment_report.json>)
- [`data/da_experiment_report.json`](</E:/项目/project_code/data/da_experiment_report.json>)
- [`data/experiment_ppt_snippet.md`](</E:/项目/project_code/data/experiment_ppt_snippet.md>)

### 2. 论文实验

```powershell
python scripts\run_paper_experiments.py --clean --samples 100 --payload-sizes 128,512,2048,8192 --batch-sizes 1,10,100,1000 --trace-steps 4,8,16,32,64,128
```

默认输出到 [`paper_outputs`](</E:/项目/project_code/paper_outputs>)，包括：

- `cost_grid.csv`
- `challenge_grid.csv`
- `failure_scenarios.csv`
- `summary.json`
- `experiment_report.md`
- `figures/*.png`
- `paper_outline.md`
- `related_work_table.md`
- `system_design.md`
- `failure_scenarios.md`

### 3. 本地 EVM 合约与 Gas 实测

```powershell
Set-Location E:\项目\project_code\evm
npm.cmd run compile
npm.cmd run test
npm.cmd run deploy:local
npm.cmd run measure:gas
```

实测输出写到：

- [`paper_outputs/evm_gas/measured_gas.csv`](</E:/项目/project_code/paper_outputs/evm_gas/measured_gas.csv>)
- [`paper_outputs/evm_gas/measured_gas_summary.json`](</E:/项目/project_code/paper_outputs/evm_gas/measured_gas_summary.json>)
- [`paper_outputs/evm_gas/measured_gas_report.md`](</E:/项目/project_code/paper_outputs/evm_gas/measured_gas_report.md>)

Sepolia 部署支持也已经补好，准备步骤是：

```powershell
Set-Location E:\项目\project_code\evm
Copy-Item .env.example .env
npm.cmd run check:sepolia
npm.cmd run deploy:sepolia
npm.cmd run verify:sepolia
```

部署地址会自动记录到：

- [`evm/deployments/hardhat.json`](</E:/项目/project_code/evm/deployments/hardhat.json>)
- [`evm/deployments/sepolia.json`](</E:/项目/project_code/evm/deployments/sepolia.json>)
- [`evm/deployments/hardhat_abis/address_index.json`](</E:/项目/project_code/evm/deployments/hardhat_abis/address_index.json>)
- [`evm/deployments/sepolia_abis/address_index.json`](</E:/项目/project_code/evm/deployments/sepolia_abis/address_index.json>)

Sepolia 汇报模板也已经准备好：

- [`paper_outputs/sepolia_deployment_record_template.md`](</E:/项目/project_code/paper_outputs/sepolia_deployment_record_template.md>)
- [`paper_outputs/sepolia_paper_table_template.md`](</E:/项目/project_code/paper_outputs/sepolia_paper_table_template.md>)
- [`paper_outputs/sepolia_group_meeting_talking_points.md`](</E:/项目/project_code/paper_outputs/sepolia_group_meeting_talking_points.md>)

### 4. 周报 PPT 生成

当前保留并可直接配合现有周报文件使用的脚本：

- `build_week8_ppt.py`
- `build_week9_ppt.py`

它们依赖 [`E:\项目\meetings\weekly_reports\ppt`](</E:/项目/meetings/weekly_reports/ppt>) 里已有的周报 PPT 作为模板来源。

### 5. 保留但非主流程脚本

- `generate_monthly_allowance_sheet.py`
  - 行政用途脚本。
- `make_teerollup_ppt.py`
  - 旧的 PPT 生成脚本；当前工作区未保留它依赖的模板目录，默认不建议直接使用。

## 论文主线

当前代码和实验围绕这条主线组织：

> 在已有 Hybrid TEE-Rollup 思路下，研究交互式挑战在异常场景中的可恢复性，并量化轻量 DA 提交对高频 DApp 的成本收益。

如果你后面继续推进论文，最值得优先看的文件是：

- [`tee_rollup_demo/ledger.py`](</E:/项目/project_code/tee_rollup_demo/ledger.py>)
- [`scripts/run_paper_experiments.py`](</E:/项目/project_code/scripts/run_paper_experiments.py>)
- [`paper_outputs/system_design.md`](</E:/项目/project_code/paper_outputs/system_design.md>)
- [`paper_outputs/paper_outline.md`](</E:/项目/project_code/paper_outputs/paper_outline.md>)
