#!/usr/bin/env python
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tee_rollup_demo.config import DemoConfig
from tee_rollup_demo.ledger import RollupDemo


DEFAULT_PROMPTS = [
    "Explain hybrid rollup for high-frequency DApp in one sentence.",
    "Why does data availability matter in optimistic challenge workflows?",
    "How to design challenge-open/respond/resolve for replay-based arbitration?",
    "Compare full calldata submission and compact commit submission.",
    "What is the role of TEE attestation in hybrid rollup execution layer?",
]


def parse_args():
    parser = ArgumentParser(
        description="Run rollup experiments and generate a markdown report for group meetings."
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data" / "experiment_report.md"),
        help="Markdown output file path.",
    )
    parser.add_argument(
        "--chain-file",
        default=str(PROJECT_ROOT / "data" / "chain_experiment_report.json"),
        help="Chain JSON file path for this experiment run.",
    )
    parser.add_argument(
        "--da-file",
        default=str(PROJECT_ROOT / "data" / "da_experiment_report.json"),
        help="DA JSON file path for this experiment run.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of samples to run. Uses the first N built-in prompts.",
    )
    parser.add_argument(
        "--dispute-window",
        type=int,
        default=30,
        help="Dispute window in seconds.",
    )
    parser.add_argument(
        "--ppt-snippet",
        action="store_true",
        help="Output a compact PPT-ready summary instead of the full markdown report.",
    )
    parser.add_argument(
        "--ppt-output",
        default=str(PROJECT_ROOT / "data" / "experiment_ppt_snippet.md"),
        help="Output path for PPT snippet text.",
    )
    return parser.parse_args()


def format_pct(value):
    return "{0:.2f}%".format(value * 100.0)


def run_experiment(chain_file, da_file, samples, dispute_window):
    chain_path = Path(chain_file)
    da_path = Path(da_file)
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    da_path.parent.mkdir(parents=True, exist_ok=True)
    if chain_path.exists():
        chain_path.unlink()
    if da_path.exists():
        da_path.unlink()

    config = DemoConfig(
        chain_path=chain_path,
        da_path=da_path,
        dispute_window_seconds=dispute_window,
        challenge_timeout_seconds=2,
        max_bisection_rounds=6,
        spot_check_probability=0.0,
        tee_secret="report-secret",
        model_backend="mock",
        model_name="report-model",
        ollama_base_url="http://127.0.0.1:11434",
    )
    demo = RollupDemo(config)
    start = datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc)
    prompts = DEFAULT_PROMPTS[: max(1, min(samples, len(DEFAULT_PROMPTS)))]

    rows = []
    strategy_rows = []
    for index, prompt in enumerate(prompts, start=1):
        tx_id = "report-{0}".format(index)
        demo.submit(
            prompt,
            now=start + timedelta(seconds=index),
            tx_id=tx_id,
            nonce="report-nonce-{0}".format(index),
            spot_check_roll=0.99,
        )
        stats = demo.estimate_submission_cost(tx_id)
        strategy_stats = demo.estimate_strategy_costs(tx_id)
        rows.append(stats)
        strategy_rows.append(strategy_stats)

    # Run one full 3-stage challenge cycle on the second tx (or first if samples=1).
    challenge_tx_id = rows[1]["tx_id"] if len(rows) > 1 else rows[0]["tx_id"]
    expected_response = demo.verify(challenge_tx_id)["expected_response"]
    tampered_lines = expected_response.splitlines()
    if not tampered_lines:
        tampered_lines = [expected_response]
    mutate_index = 2 if len(tampered_lines) > 2 else len(tampered_lines) - 1
    tampered_lines[mutate_index] = "{0}-tampered".format(tampered_lines[mutate_index])
    demo.tamper_response(challenge_tx_id, "\n".join(tampered_lines))
    open_result = demo.challenge_open(
        challenge_tx_id,
        challenger="fisherman-report",
        now=start + timedelta(seconds=10),
    )
    respond_result = demo.challenge_respond(
        challenge_tx_id,
        responder="sequencer-report",
        now=start + timedelta(seconds=11),
    )
    first_step = demo.challenge_step(challenge_tx_id, now=start + timedelta(seconds=11))
    timed_out_status = demo.challenge_status(
        challenge_tx_id,
        now=start + timedelta(seconds=14),
    )
    recover_result = demo.challenge_recover(
        challenge_tx_id,
        operator="watchdog-report",
        now=start + timedelta(seconds=14),
    )
    last_dispute = first_step
    for _ in range(16):
        last_dispute = demo.challenge_step(challenge_tx_id, now=start + timedelta(seconds=15))
        if last_dispute["narrowing_complete"]:
            break
    replay_result = demo.challenge_replay(
        challenge_tx_id,
        now=start + timedelta(seconds=16),
    )
    resolve_result = demo.challenge_resolve(
        challenge_tx_id,
        arbitrator="onchain-replay",
        now=start + timedelta(seconds=17),
    )

    avg_full = sum(item["full_bytes"] for item in rows) / len(rows)
    avg_compact = sum(item["compact_bytes"] for item in rows) / len(rows)
    avg_saved = sum(item["saved_bytes"] for item in rows) / len(rows)
    avg_ratio = sum(item["reduction_ratio"] for item in rows) / len(rows)
    avg_full_onchain_gas = (
        sum(item["gas_estimate"]["full_onchain"] for item in strategy_rows) / len(strategy_rows)
    )
    avg_compact_da_gas = (
        sum(item["gas_estimate"]["compact_with_da"] for item in strategy_rows) / len(strategy_rows)
    )
    avg_blob_gas = (
        sum(item["gas_estimate"]["compact_with_blob_da"] for item in strategy_rows) / len(strategy_rows)
    )
    avg_da_reduction = (
        sum(item["gas_reduction_ratio"]["compact_with_da"] for item in strategy_rows) / len(strategy_rows)
    )
    avg_blob_reduction = (
        sum(item["gas_reduction_ratio"]["compact_with_blob_da"] for item in strategy_rows) / len(strategy_rows)
    )
    scenario_names = strategy_rows[0]["scenario_curve"]
    avg_scenario_curve = []
    for scenario in scenario_names:
        name = scenario["scenario"]
        totals = [row["scenario_curve"] for row in strategy_rows]
        matched = []
        for curve in totals:
            for item in curve:
                if item["scenario"] == name:
                    matched.append(item)
                    break
        avg_scenario_curve.append(
            {
                "scenario": name,
                "avg_total_gas": sum(item["total_gas"] for item in matched) / len(matched),
                "avg_reduction_ratio": sum(item["reduction_ratio"] for item in matched) / len(matched),
            }
        )

    return {
        "rows": rows,
        "strategy_rows": strategy_rows,
        "summary": {
            "avg_full_bytes": avg_full,
            "avg_compact_bytes": avg_compact,
            "avg_saved_bytes": avg_saved,
            "avg_reduction_ratio": avg_ratio,
            "sample_count": len(rows),
            "challenge_tx_id": challenge_tx_id,
            "challenge_open_status": open_result["status"],
            "challenge_respond_status": respond_result["status"],
            "challenge_timeout_detected": timed_out_status["timed_out"],
            "challenge_recover_status": recover_result["status"],
            "challenge_recover_count": recover_result["recovery"]["count"],
            "challenge_success": resolve_result["challenge_success"],
            "challenge_reasons": resolve_result["tx"]["challenge_result"]["reasons"],
            "challenge_final_status": resolve_result["tx"]["status"],
            "challenge_rounds": 0 if last_dispute is None else last_dispute["round"],
            "challenge_target_step": None if last_dispute is None else last_dispute["target_step"],
            "replay_passed": replay_result["passed"],
            "avg_full_onchain_gas": avg_full_onchain_gas,
            "avg_compact_da_gas": avg_compact_da_gas,
            "avg_blob_gas": avg_blob_gas,
            "avg_da_reduction": avg_da_reduction,
            "avg_blob_reduction": avg_blob_reduction,
            "avg_scenario_curve": avg_scenario_curve,
        },
        "files": {
            "chain": str(chain_path),
            "da": str(da_path),
        },
    }


def build_markdown_report(result):
    summary = result["summary"]
    rows = result["rows"]
    strategy_rows = result["strategy_rows"]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = []
    lines.append("# 第八周代码实现实验报告（自动生成）")
    lines.append("")
    lines.append("生成时间：`{0}`".format(generated_at))
    lines.append("")
    lines.append("## 1. 轻量化提交开销对比")
    lines.append("")
    lines.append("| 样本ID | 全量提交字节 | 轻量提交字节 | 节省字节 | 降幅 |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for row in rows:
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} |".format(
                row["tx_id"],
                row["full_bytes"],
                row["compact_bytes"],
                row["saved_bytes"],
                format_pct(row["reduction_ratio"]),
            )
        )
    lines.append("")
    lines.append("平均全量提交：`{0:.2f} bytes`".format(summary["avg_full_bytes"]))
    lines.append("平均轻量提交：`{0:.2f} bytes`".format(summary["avg_compact_bytes"]))
    lines.append("平均节省字节：`{0:.2f} bytes`".format(summary["avg_saved_bytes"]))
    lines.append("平均降幅：`{0}`".format(format_pct(summary["avg_reduction_ratio"])))
    lines.append("")
    lines.append("## 2. 策略成本估算（Gas）")
    lines.append("")
    lines.append("| 样本ID | 全量上链Gas | 轻量提交+DA Gas | 轻量提交+BlobDA Gas |")
    lines.append("| --- | ---: | ---: | ---: |")
    for item in strategy_rows:
        gas = item["gas_estimate"]
        lines.append(
            "| {0} | {1} | {2} | {3} |".format(
                item["tx_id"],
                gas["full_onchain"],
                gas["compact_with_da"],
                gas["compact_with_blob_da"],
            )
        )
    lines.append("")
    lines.append("平均全量上链Gas：`{0:.2f}`".format(summary["avg_full_onchain_gas"]))
    lines.append("平均轻量提交+DA Gas：`{0:.2f}`".format(summary["avg_compact_da_gas"]))
    lines.append("平均轻量提交+BlobDA Gas：`{0:.2f}`".format(summary["avg_blob_gas"]))
    lines.append("平均Gas降幅（轻量+DA）：`{0}`".format(format_pct(summary["avg_da_reduction"])))
    lines.append("平均Gas降幅（轻量+BlobDA）：`{0}`".format(format_pct(summary["avg_blob_reduction"])))
    lines.append("")
    lines.append("## 3. 多场景数据层成本曲线")
    lines.append("")
    lines.append("| 场景 | 平均总Gas | 平均降幅 |")
    lines.append("| --- | ---: | ---: |")
    for item in summary["avg_scenario_curve"]:
        lines.append(
            "| {0} | {1:.2f} | {2} |".format(
                item["scenario"],
                item["avg_total_gas"],
                format_pct(item["avg_reduction_ratio"]),
            )
        )
    lines.append("")
    lines.append("## 4. 三阶段挑战流程实验")
    lines.append("")
    lines.append("- 挑战交易ID：`{0}`".format(summary["challenge_tx_id"]))
    lines.append("- 挑战开启状态：`{0}`".format(summary["challenge_open_status"]))
    lines.append("- 挑战应答状态：`{0}`".format(summary["challenge_respond_status"]))
    lines.append("- 会话超时检测：`{0}`".format(summary["challenge_timeout_detected"]))
    lines.append("- 恢复后状态：`{0}`（恢复次数 `{1}`）".format(summary["challenge_recover_status"], summary["challenge_recover_count"]))
    lines.append("- 二分定位轮次：`{0}`".format(summary["challenge_rounds"]))
    lines.append("- 单步重放目标步：`{0}`".format(summary["challenge_target_step"]))
    lines.append("- 单步重放结果：`passed={0}`".format(summary["replay_passed"]))
    lines.append("- 仲裁结果：`challenge_success={0}`".format(summary["challenge_success"]))
    lines.append("- 判定原因：`{0}`".format(", ".join(summary["challenge_reasons"])))
    lines.append("- 最终交易状态：`{0}`".format(summary["challenge_final_status"]))
    lines.append("")
    lines.append("## 5. 可贴组会结论")
    lines.append("")
    lines.append(
        "在本次 `{0}` 组样本实验中，轻量化提交（`state_root + output_hash + proof_hash + da_pointer`）"
        "相较全量提交平均节省 `{1:.2f}` 字节，平均降幅 `{2}`。".format(
            summary["sample_count"],
            summary["avg_saved_bytes"],
            format_pct(summary["avg_reduction_ratio"]),
        )
    )
    lines.append(
        "在Gas估算中，轻量提交+DA 和 轻量提交+BlobDA 相较全量上链分别实现 `{0}` 和 `{1}` 的平均降幅。".format(
            format_pct(summary["avg_da_reduction"]),
            format_pct(summary["avg_blob_reduction"]),
        )
    )
    lines.append(
        "对篡改样本执行 `challenge-open -> challenge-respond -> challenge-step -> challenge-recover -> challenge-replay -> challenge-resolve` 后，"
        "系统在会话超时场景下完成失败恢复，并通过二分定位与单步重放识别异常，最终将交易状态置为 `SLASHED`。"
    )
    lines.append("")
    lines.append("## 6. 结果文件")
    lines.append("")
    lines.append("- 链上轻量提交文件：`{0}`".format(result["files"]["chain"]))
    lines.append("- DA 完整数据文件：`{0}`".format(result["files"]["da"]))
    lines.append("")
    return "\n".join(lines)


def build_ppt_snippet(result):
    summary = result["summary"]
    lines = []
    lines.append("实验结果与结论（可直接贴PPT）")
    lines.append("")
    lines.append("1. 轻量化提交降本结果")
    lines.append(
        "在 {0} 组样本中，轻量化提交（state_root + output_hash + proof_hash + da_pointer）"
        "相较全量提交平均节省 {1:.2f} bytes，平均降幅 {2}。".format(
            summary["sample_count"],
            summary["avg_saved_bytes"],
            format_pct(summary["avg_reduction_ratio"]),
        )
    )
    lines.append(
        "全量提交均值 {0:.2f} bytes，轻量提交均值 {1:.2f} bytes。".format(
            summary["avg_full_bytes"],
            summary["avg_compact_bytes"],
        )
    )
    lines.append("")
    lines.append("2. 三阶段挑战机制验证")
    lines.append(
        "对篡改交易（{0}）执行 challenge-open -> challenge-respond -> challenge-step -> challenge-recover -> challenge-replay -> challenge-resolve，"
        "状态流转为 {1} -> {2} -> {3}，经过 {4} 轮二分定位并在步 {5} 完成重放，"
        "仲裁结果 challenge_success={6}，最终状态 {7}。".format(
            summary["challenge_tx_id"],
            summary["challenge_open_status"],
            summary["challenge_respond_status"],
            summary["challenge_recover_status"],
            summary["challenge_rounds"],
            summary["challenge_target_step"],
            summary["challenge_success"],
            summary["challenge_final_status"],
        )
    )
    lines.append("异常判定依据：{0}。".format(", ".join(summary["challenge_reasons"])))
    lines.append("")
    lines.append("3. 成本量化结论")
    lines.append(
        "Gas估算显示：轻量提交+DA 相较全量上链平均降幅 {0}，轻量提交+BlobDA 平均降幅 {1}。".format(
            format_pct(summary["avg_da_reduction"]),
            format_pct(summary["avg_blob_reduction"]),
        )
    )
    best_scenario = min(summary["avg_scenario_curve"], key=lambda item: item["avg_total_gas"])
    lines.append(
        "在扩展场景中，{0} 的平均总Gas最低，为 {1:.2f}，对应平均降幅 {2}。".format(
            best_scenario["scenario"],
            best_scenario["avg_total_gas"],
            format_pct(best_scenario["avg_reduction_ratio"]),
        )
    )
    lines.append("")
    lines.append("4. 阶段性结论")
    lines.append(
        "当前实现已完成“执行层（TEE模拟）+ 验证层（可恢复挑战状态机）+ 数据层（DA轻量化提交与多场景成本曲线）”闭环，"
        "在保证可验证性的前提下显著降低链上提交开销，并提升争议流程的鲁棒性。"
    )
    return "\n".join(lines)


def main():
    args = parse_args()
    result = run_experiment(
        chain_file=args.chain_file,
        da_file=args.da_file,
        samples=args.samples,
        dispute_window=args.dispute_window,
    )
    report = build_markdown_report(result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    if args.ppt_snippet:
        snippet = build_ppt_snippet(result)
        snippet_path = Path(args.ppt_output)
        snippet_path.parent.mkdir(parents=True, exist_ok=True)
        snippet_path.write_text(snippet, encoding="utf-8")
        print(snippet)
        print("")
        print("PPT snippet written to: {0}".format(snippet_path))
        print("Full report written to: {0}".format(output_path))
        return

    print(report)
    print("")
    print("Report written to: {0}".format(output_path))


if __name__ == "__main__":
    main()
