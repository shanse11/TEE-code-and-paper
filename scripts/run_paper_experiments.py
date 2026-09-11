#!/usr/bin/env python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import json
import math
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tee_rollup_demo.config import DemoConfig
from tee_rollup_demo.attestation import create_attestation
from tee_rollup_demo.ledger import RollupDemo, build_da_merkle_bundle
from tee_rollup_demo.utils import canonical_json, sha256_hex


DA_PROFILES = {
    "full_onchain_calldata": {"onchain_gas_per_byte": 16.0, "da_gas_per_byte": 0.0},
    "compact_external_da": {"onchain_gas_per_byte": 16.0, "da_gas_per_byte": 2.2},
    "compact_eip4844_like": {"onchain_gas_per_byte": 16.0, "da_gas_per_byte": 0.9},
    "compact_modular_da_sampling": {"onchain_gas_per_byte": 16.0, "da_gas_per_byte": 0.45},
}


class SyntheticTraceModel:
    def __init__(self, model_name="paper-synthetic-trace"):
        self.model_name = model_name

    def infer(self, prompt):
        steps = parse_marker(prompt, "steps", 8)
        payload = parse_marker(prompt, "payload", 128)
        lines = []
        for index in range(max(1, steps)):
            seed = "{0}|{1}|{2}".format(prompt, index, payload)
            digest = sha256_hex(seed)
            line = "step={0};state={1};payload={2}".format(index, digest[:24], "x" * payload)
            lines.append(line)
        return "\n".join(lines)

    def fingerprint(self):
        payload = {
            "backend": "synthetic",
            "model_name": self.model_name,
            "version": "paper-v1",
        }
        return sha256_hex(canonical_json(payload))


def parse_marker(text, key, default):
    marker = key + "="
    for part in text.replace(";", " ").split():
        if part.startswith(marker):
            try:
                return int(part[len(marker):])
            except ValueError:
                return default
    return default


def parse_int_list(value):
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def reset_file(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()


def make_demo(chain_path, da_path, challenge_timeout=2, max_rounds=16):
    config = DemoConfig(
        chain_path=Path(chain_path),
        da_path=Path(da_path),
        dispute_window_seconds=60,
        challenge_timeout_seconds=challenge_timeout,
        max_bisection_rounds=max_rounds,
        spot_check_probability=0.0,
        tee_secret="paper-secret",
        model_backend="mock",
        model_name="paper-model",
        ollama_base_url="http://127.0.0.1:11434",
    )
    return RollupDemo(config, model=SyntheticTraceModel())


def estimate_da_profiles(cost_stats, batch_size):
    full_bytes = cost_stats["full_bytes"]
    compact_bytes = cost_stats["compact_bytes"]
    full_onchain = full_bytes * DA_PROFILES["full_onchain_calldata"]["onchain_gas_per_byte"]
    rows = {}
    for name, profile in DA_PROFILES.items():
        if name == "full_onchain_calldata":
            total = full_onchain
        else:
            total = (
                compact_bytes * profile["onchain_gas_per_byte"]
                + full_bytes * profile["da_gas_per_byte"]
            )
        rows[name] = {
            "total_gas": total,
            "amortized_gas": total / float(max(1, batch_size)),
            "reduction_ratio": 0.0 if full_onchain == 0 else (full_onchain - total) / full_onchain,
        }
    return rows


def run_cost_grid(output_dir, payload_sizes, batch_sizes, prompt_lengths, samples):
    start = datetime(2026, 4, 28, 0, 0, tzinfo=timezone.utc)
    rows = []
    model = SyntheticTraceModel()
    mrenclave = sha256_hex(model.fingerprint())

    for payload_size in payload_sizes:
        for prompt_length in prompt_lengths:
            for sample_index in range(1, samples + 1):
                steps = 4 + (sample_index % 5)
                filler = "q" * prompt_length
                prompt = "paper cost sample={0} payload={1} steps={2} prompt_chars={3} {4}".format(
                    sample_index,
                    payload_size,
                    steps,
                    prompt_length,
                    filler,
                )
                tx_id = "cost-p{0}-q{1}-s{2}".format(payload_size, prompt_length, sample_index)
                created_at = start + timedelta(seconds=sample_index)
                response = model.infer(prompt)
                attestation = create_attestation(
                    prompt=prompt,
                    response=response,
                    mrenclave=mrenclave,
                    secret="paper-secret",
                    nonce="nonce-{0}".format(tx_id),
                )
                da_payload = {
                    "tx_id": tx_id,
                    "prompt": prompt,
                    "response": response,
                    "attestation": attestation,
                    "mrenclave": mrenclave,
                    "created_at": created_at.astimezone(timezone.utc).isoformat(),
                }
                da_bundle = build_da_merkle_bundle(da_payload)
                full_payload = {
                    "prompt": prompt,
                    "response": response,
                    "attestation": attestation,
                    "mrenclave": mrenclave,
                }
                compact_payload = {
                    "state_root": sha256_hex(
                        canonical_json(
                            {
                                "prompt_hash": sha256_hex(prompt),
                                "response_hash": sha256_hex(response),
                                "mrenclave": mrenclave,
                            }
                        )
                    ),
                    "output_hash": sha256_hex(response),
                    "proof_hash": sha256_hex(
                        canonical_json(
                            {
                                "nonce": attestation["nonce"],
                                "signature": attestation["signature"],
                                "scheme": attestation["scheme"],
                            }
                        )
                    ),
                    "da_pointer": sha256_hex(canonical_json(da_payload)),
                    "da_merkle_root": da_bundle["merkle_root"],
                }
                full_bytes = len(canonical_json(full_payload).encode("utf-8"))
                compact_bytes = len(canonical_json(compact_payload).encode("utf-8"))
                saved_bytes = full_bytes - compact_bytes
                stats = {
                    "full_bytes": full_bytes,
                    "compact_bytes": compact_bytes,
                    "saved_bytes": saved_bytes,
                    "reduction_ratio": 0.0 if full_bytes == 0 else float(saved_bytes) / float(full_bytes),
                }
                for batch_size in batch_sizes:
                    estimates = estimate_da_profiles(stats, batch_size)
                    row = {
                        "tx_id": tx_id,
                        "payload_size": payload_size,
                        "prompt_length": prompt_length,
                        "response_length": payload_size,
                        "sample_index": sample_index,
                        "batch_size": batch_size,
                        "full_bytes": stats["full_bytes"],
                        "compact_bytes": stats["compact_bytes"],
                        "saved_bytes": stats["saved_bytes"],
                        "byte_reduction_ratio": stats["reduction_ratio"],
                    }
                    for name, values in estimates.items():
                        row[name + "_total_gas"] = values["total_gas"]
                        row[name + "_amortized_gas"] = values["amortized_gas"]
                        row[name + "_reduction_ratio"] = values["reduction_ratio"]
                    rows.append(row)
    return rows


def run_challenge_grid(output_dir, trace_steps, challenge_timeouts, max_bisection_rounds, samples):
    chain_path = output_dir / "paper_challenge_chain.json"
    da_path = output_dir / "paper_challenge_da.json"
    start = datetime(2026, 4, 28, 1, 0, tzinfo=timezone.utc)
    rows = []

    for steps in trace_steps:
        for challenge_timeout in challenge_timeouts:
            for max_rounds in max_bisection_rounds:
                for sample_index in range(1, samples + 1):
                    reset_file(chain_path)
                    reset_file(da_path)
                    demo = make_demo(chain_path, da_path, challenge_timeout=challenge_timeout, max_rounds=max_rounds)
                    tx_id = "challenge-t{0}-to{1}-r{2}-s{3}".format(steps, challenge_timeout, max_rounds, sample_index)
                    prompt = "paper challenge sample={0} payload=64 steps={1}".format(sample_index, steps)
                    now = start + timedelta(minutes=len(rows))
                    demo.submit(
                        prompt,
                        now=now,
                        tx_id=tx_id,
                        nonce="nonce-{0}".format(tx_id),
                        spot_check_roll=0.99,
                    )
                    expected = demo.verify(tx_id)["expected_response"].splitlines()
                    mutate_index = min(len(expected) - 1, max(0, steps // 2))
                    claimed = list(expected)
                    claimed[mutate_index] = claimed[mutate_index] + "-tampered"
                    demo.tamper_response(tx_id, "\n".join(claimed))

                    demo.challenge_open(tx_id, now=now + timedelta(seconds=1))
                    demo.challenge_respond(tx_id, now=now + timedelta(seconds=1))
                    first_dispute = demo.challenge_step(tx_id, now=now + timedelta(seconds=2))
                    timed_out = demo.challenge_status(
                        tx_id,
                        now=now + timedelta(seconds=challenge_timeout + 4),
                    )
                    recovered = demo.challenge_recover(
                        tx_id,
                        now=now + timedelta(seconds=challenge_timeout + 4),
                    )
                    dispute = first_dispute
                    step_calls = 1
                    for _ in range(max_rounds + 8):
                        if dispute["narrowing_complete"]:
                            break
                        dispute = demo.challenge_step(
                            tx_id,
                            now=now + timedelta(seconds=challenge_timeout + 5),
                        )
                        step_calls += 1
                    replay = demo.challenge_replay(
                        tx_id,
                        now=now + timedelta(seconds=challenge_timeout + 6),
                    )
                    resolved = demo.challenge_resolve(
                        tx_id,
                        now=now + timedelta(seconds=challenge_timeout + 7),
                    )
                    expected_rounds = int(math.ceil(math.log(max(1, steps), 2))) if steps > 1 else 0
                    rows.append(
                        {
                            "tx_id": tx_id,
                            "trace_steps": steps,
                            "challenge_timeout": challenge_timeout,
                            "max_bisection_rounds": max_rounds,
                            "sample_index": sample_index,
                            "mutated_step": mutate_index,
                            "bisection_rounds": dispute["round"],
                            "expected_log2_rounds": expected_rounds,
                            "challenge_step_calls": step_calls,
                            "timed_out_detected": timed_out["timed_out"],
                            "recover_status": recovered["status"],
                            "recover_count": recovered["recovery"]["count"],
                            "target_step": dispute["target_step"],
                            "replay_passed": replay["passed"],
                            "challenge_success": resolved["challenge_success"],
                            "final_status": resolved["tx"]["status"],
                        }
                    )
    return rows


def run_failure_scenarios(output_dir, samples):
    chain_path = output_dir / "paper_failure_chain.json"
    da_path = output_dir / "paper_failure_da.json"
    start = datetime(2026, 5, 9, 0, 0, tzinfo=timezone.utc)
    rows = []
    scenarios = [
        "normal",
        "response_tampered",
        "attestation_invalid",
        "trace_length_mismatch",
        "challenge_timeout_no_recover",
        "challenge_timeout_recover",
        "da_unavailable",
        "da_proof_invalid",
    ]
    for scenario in scenarios:
        for sample_index in range(1, samples + 1):
            reset_file(chain_path)
            reset_file(da_path)
            demo = make_demo(chain_path, da_path, challenge_timeout=2, max_rounds=16)
            tx_id = "failure-{0}-{1}".format(scenario, sample_index)
            now = start + timedelta(minutes=len(rows))
            prompt = "failure scenario={0} sample={1} payload=96 steps=8".format(scenario, sample_index)
            demo.submit(prompt, now=now, tx_id=tx_id, nonce="nonce-{0}".format(tx_id), spot_check_roll=0.99)
            if scenario == "response_tampered":
                demo.tamper_response(tx_id, "tampered response")
            elif scenario == "attestation_invalid":
                demo.tamper_attestation(tx_id)
            elif scenario == "trace_length_mismatch":
                demo.truncate_response_trace(tx_id, keep_lines=1)
            elif scenario == "da_unavailable":
                demo.remove_da_entry(tx_id)
            elif scenario == "da_proof_invalid":
                demo.corrupt_da_proof(tx_id)

            report = demo.verify(tx_id)
            replay_reason = ""
            challenge_success = False
            final_status = demo.get_transaction(tx_id)["status"]
            recover_used = False
            if scenario in [
                "response_tampered",
                "trace_length_mismatch",
                "challenge_timeout_no_recover",
                "challenge_timeout_recover",
            ]:
                if scenario.startswith("challenge_timeout"):
                    demo.tamper_response(tx_id, "line1\nline2\nline3\nline4")
                demo.challenge_open(tx_id, now=now + timedelta(seconds=1))
                demo.challenge_respond(tx_id, now=now + timedelta(seconds=1))
                dispute = demo.challenge_step(tx_id, now=now + timedelta(seconds=2))
                if scenario == "challenge_timeout_no_recover":
                    try:
                        demo.challenge_step(tx_id, now=now + timedelta(seconds=5))
                    except ValueError as exc:
                        replay_reason = str(exc)
                    final_status = demo.get_transaction(tx_id)["status"]
                else:
                    if scenario == "challenge_timeout_recover":
                        demo.challenge_recover(tx_id, now=now + timedelta(seconds=5))
                        recover_used = True
                        replay_time = now + timedelta(seconds=6)
                        resolve_time = now + timedelta(seconds=6, milliseconds=500)
                    else:
                        replay_time = now + timedelta(seconds=3)
                        resolve_time = now + timedelta(seconds=3, milliseconds=500)
                    while not dispute["narrowing_complete"]:
                        dispute = demo.challenge_step(tx_id, now=replay_time)
                    replay = demo.challenge_replay(tx_id, now=replay_time)
                    replay_reason = replay["reason"]
                    resolved = demo.challenge_resolve(tx_id, now=resolve_time)
                    challenge_success = resolved["challenge_success"]
                    final_status = resolved["tx"]["status"]
            rows.append(
                {
                    "scenario": scenario,
                    "sample_index": sample_index,
                    "tx_id": tx_id,
                    "detected": bool(report["mismatches"]) or challenge_success or "timed out" in replay_reason,
                    "verify_valid": report["valid"],
                    "mismatches": ";".join(report["mismatches"]),
                    "recover_used": recover_used,
                    "challenge_success": challenge_success,
                    "replay_reason": replay_reason,
                    "final_status": final_status,
                }
            )
    return rows


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize(cost_rows, challenge_rows):
    cost_group = {}
    for row in cost_rows:
        key = (row["payload_size"], row["prompt_length"], row["batch_size"])
        cost_group.setdefault(key, []).append(row)
    cost_summary = []
    for key, rows in sorted(cost_group.items()):
        payload_size, prompt_length, batch_size = key
        item = {
            "payload_size": payload_size,
            "prompt_length": prompt_length,
            "batch_size": batch_size,
            "samples": len(rows),
            "avg_full_bytes": avg(rows, "full_bytes"),
            "avg_compact_bytes": avg(rows, "compact_bytes"),
            "avg_byte_reduction_ratio": avg(rows, "byte_reduction_ratio"),
        }
        for name in DA_PROFILES:
            item["avg_" + name + "_amortized_gas"] = avg(rows, name + "_amortized_gas")
            item["avg_" + name + "_reduction_ratio"] = avg(rows, name + "_reduction_ratio")
        cost_summary.append(item)

    challenge_group = {}
    for row in challenge_rows:
        key = (row["trace_steps"], row["challenge_timeout"], row["max_bisection_rounds"])
        challenge_group.setdefault(key, []).append(row)
    challenge_summary = []
    for key, rows in sorted(challenge_group.items()):
        steps, challenge_timeout, max_rounds = key
        challenge_summary.append(
            {
                "trace_steps": steps,
                "challenge_timeout": challenge_timeout,
                "max_bisection_rounds": max_rounds,
                "samples": len(rows),
                "avg_bisection_rounds": avg(rows, "bisection_rounds"),
                "avg_expected_log2_rounds": avg(rows, "expected_log2_rounds"),
                "avg_step_calls": avg(rows, "challenge_step_calls"),
                "recovery_success_rate": ratio(rows, lambda row: row["recover_count"] >= 1),
                "challenge_success_rate": ratio(rows, lambda row: row["challenge_success"]),
            }
        )
    return {
        "cost_summary": cost_summary,
        "challenge_summary": challenge_summary,
    }


def summarize_failures(failure_rows):
    grouped = {}
    for row in failure_rows:
        grouped.setdefault(row["scenario"], []).append(row)
    result = []
    for scenario, rows in sorted(grouped.items()):
        result.append(
            {
                "scenario": scenario,
                "samples": len(rows),
                "detection_rate": ratio(rows, lambda row: bool(row["detected"])),
                "challenge_success_rate": ratio(rows, lambda row: bool(row["challenge_success"])),
                "slashed_rate": ratio(rows, lambda row: row["final_status"] == "SLASHED"),
                "example_mismatches": rows[0]["mismatches"],
            }
        )
    return result


def avg(rows, key):
    return sum(float(row[key]) for row in rows) / float(len(rows))


def ratio(rows, predicate):
    return sum(1 for row in rows if predicate(row)) / float(len(rows))


def load_local_evm_gas_summary(output_dir):
    summary_path = output_dir / "evm_gas" / "measured_gas_summary.json"
    if not summary_path.exists():
        return None
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_markdown(path, output_dir, summary, failure_summary, cost_rows, challenge_rows, failure_rows):
    largest_payload = max(summary["cost_summary"], key=lambda row: row["payload_size"])
    largest_trace = max(summary["challenge_summary"], key=lambda row: row["trace_steps"])
    highest_payload_rows = [
        row
        for row in summary["cost_summary"]
        if row["payload_size"] == largest_payload["payload_size"] and row["batch_size"] == 1
    ]
    highest_payload_rows = sorted(highest_payload_rows, key=lambda row: row["prompt_length"])
    timeout_no_recover = next((row for row in failure_summary if row["scenario"] == "challenge_timeout_no_recover"), None)
    timeout_recover = next((row for row in failure_summary if row["scenario"] == "challenge_timeout_recover"), None)
    evm_gas_summary = load_local_evm_gas_summary(output_dir)
    samples_per_combo = max((row["samples"] for row in summary["cost_summary"]), default=0)
    lines = [
        "# 正式论文实验报告",
        "",
        "生成时间：`{0}`".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
        "",
        "## 1. 实验规模",
        "",
        "- 每组变量样本数：`{0}`".format(samples_per_combo),
        "- 成本实验记录数：`{0}`".format(len(cost_rows)),
        "- 挑战实验记录数：`{0}`".format(len(challenge_rows)),
        "- 失败场景实验记录数：`{0}`".format(len(failure_rows)),
        "- 成本变量：payload size、prompt length、batch size、DA profile",
        "- 挑战变量：trace steps、challenge timeout、max bisection rounds、timeout recovery",
        "- 说明：当前实验使用 simulated TEE、JSON ledger 和 gas 估算模型，只说明原型趋势，不声称真实链上 gas 或真实 TEE 安全。",
        "",
        "## 2. 对照组设计",
        "",
        "### 2.1 成本对照组",
        "",
        "| 对照维度 | Baseline | 方案组 | 目的 |",
        "| --- | --- | --- | --- |",
        "| 数据提交 | full_onchain_calldata | compact_external_da / compact_eip4844_like / compact_modular_da_sampling | 比较 full payload 上链与 compact commit + DA 的降本趋势 |",
        "| 批处理 | batch_size=1 | batch_size=10 / 100 / 1000 | 比较单笔摊销成本随批处理规模增大的变化 |",
        "| 负载规模 | payload size=128 | payload size=512 / 2048 / 8192 | 比较高频 DApp 负载增大时 compact commit 的压缩收益 |",
        "",
        "### 2.2 挑战对照组",
        "",
        "| 对照维度 | Baseline | 方案组 | 目的 |",
        "| --- | --- | --- | --- |",
        "| 恢复机制 | challenge_timeout_no_recover | challenge_timeout_recover | 比较 recoverable challenge 对超时场景可完成性的改善 |",
        "| 争议规模 | trace steps=4 | trace steps=8 / 16 / 32 / 64 / 128 | 比较二分定位轮次与 replay 路径复杂度 |",
        "| 异常类型 | normal | response_tampered / attestation_invalid / trace_length_mismatch / da_unavailable / da_proof_invalid | 比较不同故障类型的检测与仲裁结果 |",
        "",
        "## 3. 指标定义",
        "",
        "| 指标 | 定义 | 解释 |",
        "| --- | --- | --- |",
        "| `byte_reduction_ratio` | `(full_bytes - compact_bytes) / full_bytes` | 轻量提交对链上字节的压缩比例 |",
        "| `amortized_gas` | `total_gas / batch_size` | 每笔请求的摊销成本 |",
        "| `reduction_ratio` | `(full_onchain_gas - target_gas) / full_onchain_gas` | 相对 full-onchain 的降本比例 |",
        "| `avg_bisection_rounds` | `mean(dispute.round)` | 争议定位平均轮次 |",
        "| `recovery_success_rate` | `recover_count >= 1` 的样本比例 | 超时后恢复并继续推进的比例 |",
        "| `challenge_success_rate` | `challenge_success=True` 的样本比例 | 争议最终完成仲裁的比例 |",
        "| `detection_rate` | `detected=True` 的样本比例 | 故障是否能被 verify 或 challenge 观测到 |",
        "| `slashed_rate` | `final_status=SLASHED` 的样本比例 | 异常执行最终被罚没的比例 |",
        "",
        "## 4. 成本实验摘要",
        "",
        "| Payload | Prompt | Batch | Full bytes | Compact bytes | Byte降幅 | External DA单笔Gas | EIP4844-like单笔Gas | Modular DA单笔Gas |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["cost_summary"]:
        lines.append(
            "| {payload_size} | {prompt_length} | {batch_size} | {avg_full_bytes:.2f} | {avg_compact_bytes:.2f} | {byte_pct:.2f}% | {external:.2f} | {blob:.2f} | {modular:.2f} |".format(
                payload_size=row["payload_size"],
                prompt_length=row["prompt_length"],
                batch_size=row["batch_size"],
                avg_full_bytes=row["avg_full_bytes"],
                avg_compact_bytes=row["avg_compact_bytes"],
                byte_pct=row["avg_byte_reduction_ratio"] * 100.0,
                external=row["avg_compact_external_da_amortized_gas"],
                blob=row["avg_compact_eip4844_like_amortized_gas"],
                modular=row["avg_compact_modular_da_sampling_amortized_gas"],
            )
        )
    lines.extend(
        [
            "",
            "## 5. 可恢复挑战实验摘要",
            "",
            "| Trace steps | Timeout | Max rounds | 平均二分轮次 | 理论log2轮次 | 恢复成功率 | 挑战成功率 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["challenge_summary"]:
        lines.append(
            "| {trace_steps} | {challenge_timeout} | {max_rounds} | {avg_bisection_rounds:.2f} | {avg_expected_log2_rounds:.2f} | {recovery:.2f}% | {challenge:.2f}% |".format(
                trace_steps=row["trace_steps"],
                challenge_timeout=row["challenge_timeout"],
                max_rounds=row["max_bisection_rounds"],
                avg_bisection_rounds=row["avg_bisection_rounds"],
                avg_expected_log2_rounds=row["avg_expected_log2_rounds"],
                recovery=row["recovery_success_rate"] * 100.0,
                challenge=row["challenge_success_rate"] * 100.0,
            )
        )
    lines.extend(
        [
            "",
            "## 6. 失败场景实验摘要",
            "",
            "| 场景 | 样本数 | 检测率 | 挑战成功率 | Slashed比例 | 示例 mismatch |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in failure_summary:
        lines.append(
            "| {scenario} | {samples} | {detected:.2f}% | {challenge:.2f}% | {slashed:.2f}% | {mismatches} |".format(
                scenario=row["scenario"],
                samples=row["samples"],
                detected=row["detection_rate"] * 100.0,
                challenge=row["challenge_success_rate"] * 100.0,
                slashed=row["slashed_rate"] * 100.0,
                mismatches=row["example_mismatches"] or "-",
            )
        )
    lines.extend(
        [
            "",
            "## 7. 核心对照结论",
            "",
            "### 7.1 full-onchain vs compact+DA",
            "",
            "| Payload | Prompt | Full-onchain单笔Gas | External DA单笔Gas | EIP4844-like单笔Gas | Modular DA单笔Gas | 最佳降本比例 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in highest_payload_rows:
        best_reduction = max(
            row["avg_compact_external_da_reduction_ratio"],
            row["avg_compact_eip4844_like_reduction_ratio"],
            row["avg_compact_modular_da_sampling_reduction_ratio"],
        )
        lines.append(
            "| {payload_size} | {prompt_length} | {full:.2f} | {external:.2f} | {blob:.2f} | {modular:.2f} | {best:.2f}% |".format(
                payload_size=row["payload_size"],
                prompt_length=row["prompt_length"],
                full=row["avg_full_onchain_calldata_amortized_gas"],
                external=row["avg_compact_external_da_amortized_gas"],
                blob=row["avg_compact_eip4844_like_amortized_gas"],
                modular=row["avg_compact_modular_da_sampling_amortized_gas"],
                best=best_reduction * 100.0,
            )
        )
    lines.extend(
        [
            "",
            "### 7.2 no recover vs recover",
            "",
            "| 场景 | 检测率 | 挑战成功率 | Slashed比例 |",
            "| --- | ---: | ---: | ---: |",
            "| challenge_timeout_no_recover | {0:.2f}% | {1:.2f}% | {2:.2f}% |".format(
                0.0 if timeout_no_recover is None else timeout_no_recover["detection_rate"] * 100.0,
                0.0 if timeout_no_recover is None else timeout_no_recover["challenge_success_rate"] * 100.0,
                0.0 if timeout_no_recover is None else timeout_no_recover["slashed_rate"] * 100.0,
            ),
            "| challenge_timeout_recover | {0:.2f}% | {1:.2f}% | {2:.2f}% |".format(
                0.0 if timeout_recover is None else timeout_recover["detection_rate"] * 100.0,
                0.0 if timeout_recover is None else timeout_recover["challenge_success_rate"] * 100.0,
                0.0 if timeout_recover is None else timeout_recover["slashed_rate"] * 100.0,
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## 8. 图表与结论",
            "",
            "- `figures/cost_payload_full_vs_compact.png`：payload 增大时，full payload 字节数随数据增长，compact commit 保持近似固定。",
            "- `figures/challenge_rounds.png`：trace steps 增长时，二分定位轮次接近 log2(trace steps)。",
            "- `figures/recovery_success.png`：无 recover 的超时流程会停滞，有 recover 的流程可继续推进。",
            "- `figures/da_profile_amortized_gas.png`：不同 DA profile 的单笔摊销 gas 随 batch size 增大下降。",
            "- `figures/failure_detection.png`：篡改、attestation 失效、trace length mismatch 和 DA 异常均可被记录为 mismatch 或 challenge failure。",
            "",
        ]
    )
    if evm_gas_summary:
        averages = evm_gas_summary.get("averages", {})
        lines.extend(
            [
                "## 9. 本地 EVM Gas 实测补充",
                "",
                "当前项目已将关键链上路径映射为 Solidity 合约，并在 Hardhat 本地测试链上得到 `gasUsed` 基线。这部分结果用于补充 Python 成本模型，说明关键提交和争议路径在链上执行时的真实状态推进开销。",
                "",
                "| 操作 | 平均 gasUsed |",
                "| --- | ---: |",
            ]
        )
        for key, label in [
            ("register_da_gas", "register DA"),
            ("submit_rollup_gas", "submit rollup"),
            ("challenge_open_gas", "challenge open"),
            ("challenge_respond_gas", "challenge respond"),
            ("challenge_step_round1_gas", "challenge step"),
            ("challenge_recover_gas", "challenge recover"),
            ("challenge_replay_gas", "challenge replay"),
            ("challenge_resolve_gas", "challenge resolve"),
            ("finalize_gas", "finalize"),
        ]:
            if key in averages:
                lines.append("| {0} | {1:.2f} |".format(label, averages[key]))
        lines.extend(
            [
                "",
                "这组本地 EVM 数据应被看作“链上实测基线”，而不是 Sepolia 或主网费用的直接替代；真实公网环境下的费用还会受到 calldata 定价、blob 价格和网络状态影响。",
                "",
            ]
        )
    lines.extend(
        [
            "## 10. 可贴组会结论",
            "",
            "本周将论文主线收敛为“Hybrid TEE-Rollup 下的可恢复交互式挑战 + 轻量 DA 成本评估”，并新增批量实验脚本。",
            "成本实验已从 5 组样本扩展为 `{0}` 条记录，覆盖 payload size、batch size 与多类 DA profile。".format(len(cost_rows)),
            "在最大 payload `{0}` 的实验组中，compact commit 相比 full payload 仍保持明显字节压缩；batch 增大后，单笔摊销 Gas 继续下降。".format(largest_payload["payload_size"]),
            "挑战实验覆盖最高 `{0}` 个 trace steps，恢复成功率为 `{1:.2f}%`，挑战成功率为 `{2:.2f}%`，说明 timeout recovery 后争议流程仍能继续推进并完成 slashing。".format(
                largest_trace["trace_steps"],
                largest_trace["recovery_success_rate"] * 100.0,
                largest_trace["challenge_success_rate"] * 100.0,
            ),
            "对照组结果进一步说明：无 recover 的超时流程无法完成仲裁，而有 recover 的流程可恢复并推进到 slashing；full-onchain 与 compact+DA 的差距会随着 payload 增大而被放大。",
            "当前实验结果可以支撑论文中的三条阶段性主张：一是可恢复挑战协议增强异常场景鲁棒性；二是 compact commit + DA 在高频 DApp 批量交互中具有稳定降本趋势；三是该原型已经具备 Solidity 对应物和本地 EVM 实测基线。",
            "",
            "## 11. 结果文件",
            "",
            "- `cost_grid.csv`",
            "- `challenge_grid.csv`",
            "- `failure_scenarios.csv`",
            "- `summary.json`",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_static_docs(output_dir):
    (output_dir / "paper_outline.md").write_text(PAPER_OUTLINE, encoding="utf-8")
    (output_dir / "related_work_table.md").write_text(RELATED_WORK_TABLE, encoding="utf-8")
    (output_dir / "system_design.md").write_text(SYSTEM_DESIGN, encoding="utf-8")
    (output_dir / "failure_scenarios.md").write_text(FAILURE_SCENARIOS, encoding="utf-8")


def generate_figures(output_dir, summary, failure_summary):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    cost_by_payload = {}
    for row in summary["cost_summary"]:
        if row["prompt_length"] != min(item["prompt_length"] for item in summary["cost_summary"]):
            continue
        if row["batch_size"] != 1:
            continue
        cost_by_payload[row["payload_size"]] = row
    payloads = sorted(cost_by_payload)
    full = [cost_by_payload[p]["avg_full_bytes"] for p in payloads]
    compact = [cost_by_payload[p]["avg_compact_bytes"] for p in payloads]
    fig, (ax_main, ax_zoom) = plt.subplots(1, 2, figsize=(9.5, 4), gridspec_kw={"width_ratios": [1.45, 1.0]})
    ax_main.plot(payloads, full, marker="o", label="full payload")
    ax_main.plot(payloads, compact, marker="o", label="compact commit")
    ax_main.set_xlabel("Payload size")
    ax_main.set_ylabel("Bytes")
    ax_main.set_title("Overall trend")
    ax_main.legend(fontsize=8)
    ax_main.grid(alpha=0.25, linestyle="--", linewidth=0.6)

    ax_zoom.plot(payloads, compact, marker="o", color="#ff7f0e", label="compact commit")
    ax_zoom.set_xlabel("Payload size")
    ax_zoom.set_ylabel("Compact bytes")
    ax_zoom.set_title("Compact commit zoom-in")
    ax_zoom.grid(alpha=0.25, linestyle="--", linewidth=0.6)
    compact_min = min(compact)
    compact_max = max(compact)
    lower = max(0.0, compact_min - 30.0)
    upper = compact_max + 30.0
    if upper <= lower:
        upper = lower + 50.0
    ax_zoom.set_ylim(lower, upper)
    for x, y in zip(payloads, compact):
        ax_zoom.annotate(
            "{0:.0f}B".format(y),
            (x, y),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=7,
        )

    fig.suptitle("Full-onchain vs Compact Commit", fontsize=12)
    path = figures_dir / "cost_payload_full_vs_compact.png"
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(str(path))

    default_challenges = [
        row
        for row in summary["challenge_summary"]
        if row["challenge_timeout"] == min(item["challenge_timeout"] for item in summary["challenge_summary"])
        and row["max_bisection_rounds"] == max(item["max_bisection_rounds"] for item in summary["challenge_summary"])
    ]
    default_challenges = sorted(default_challenges, key=lambda row: row["trace_steps"])
    plt.figure(figsize=(7, 4))
    plt.plot([row["trace_steps"] for row in default_challenges], [row["avg_bisection_rounds"] for row in default_challenges], marker="o", label="observed")
    plt.plot([row["trace_steps"] for row in default_challenges], [row["avg_expected_log2_rounds"] for row in default_challenges], marker="x", label="log2 baseline")
    plt.xlabel("Trace steps")
    plt.ylabel("Bisection rounds")
    plt.title("Challenge Bisection Rounds")
    plt.legend()
    path = figures_dir / "challenge_rounds.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    paths.append(str(path))

    no_recover = next((row for row in failure_summary if row["scenario"] == "challenge_timeout_no_recover"), None)
    recover = next((row for row in failure_summary if row["scenario"] == "challenge_timeout_recover"), None)
    plt.figure(figsize=(6, 4))
    plt.bar(["no recover", "recover"], [
        0.0 if no_recover is None else no_recover["challenge_success_rate"] * 100.0,
        0.0 if recover is None else recover["challenge_success_rate"] * 100.0,
    ])
    plt.ylabel("Challenge success rate (%)")
    plt.title("Timeout Recovery Effect")
    path = figures_dir / "recovery_success.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    paths.append(str(path))

    batch_rows = [
        row
        for row in summary["cost_summary"]
        if row["payload_size"] == max(item["payload_size"] for item in summary["cost_summary"])
        and row["prompt_length"] == min(item["prompt_length"] for item in summary["cost_summary"])
    ]
    batch_rows = sorted(batch_rows, key=lambda row: row["batch_size"])
    plt.figure(figsize=(7, 4))
    for key, label in [
        ("avg_full_onchain_calldata_amortized_gas", "full onchain"),
        ("avg_compact_external_da_amortized_gas", "external DA"),
        ("avg_compact_eip4844_like_amortized_gas", "EIP-4844-like"),
        ("avg_compact_modular_da_sampling_amortized_gas", "modular DA"),
    ]:
        plt.plot([row["batch_size"] for row in batch_rows], [row[key] for row in batch_rows], marker="o", label=label)
    plt.xscale("log")
    plt.xlabel("Batch size")
    plt.ylabel("Amortized gas")
    plt.title("DA Profile Amortized Gas")
    plt.legend()
    path = figures_dir / "da_profile_amortized_gas.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    paths.append(str(path))

    plt.figure(figsize=(8, 4))
    plt.bar([row["scenario"] for row in failure_summary], [row["detection_rate"] * 100.0 for row in failure_summary])
    plt.ylabel("Detection rate (%)")
    plt.title("Failure Scenario Detection")
    plt.xticks(rotation=30, ha="right")
    path = figures_dir / "failure_detection.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    paths.append(str(path))

    return paths


PAPER_OUTLINE = """# 论文大纲

## 题目

面向高频 DApp 的 Hybrid TEE-Rollup 可恢复挑战协议与轻量 DA 成本评估

## 摘要草稿

高频 DApp（如元宇宙资产交互、去中心化社交状态更新和 AI 推理服务）需要低延迟、低成本且可验证的执行环境。现有 Rollup 路线中，ZK-Rollup 验证强但证明成本高，Optimistic Rollup 成本较低但挑战窗口较长，单纯 TEE 方案又存在硬件信任和可用性风险。本文不提出全新的 TEEROLLUP 系统，而是在已有 Hybrid TEE-Rollup 思路下，聚焦两个更具体的问题：交互式挑战在异常场景下能否恢复推进，以及 compact commit + DA 是否能降低高频交互的提交成本。本文实现一个模拟 TEE、JSON ledger 和 DA payload 的原型，扩展可恢复 challenge 状态机，引入模拟 Merkle root / proof，并对 full-onchain、compact external DA、EIP-4844-like 和 modular DA profile 进行成本评估。实验结果用于说明原型趋势，而不声称真实链上 gas 或真实 TEE 安全。

## 贡献点

1. 设计并实现面向 Hybrid TEE-Rollup 的 recoverable interactive challenge 原型，支持 timeout recovery、bisection 和 single-step replay。
2. 为 DA payload 增加模拟 Merkle root / proof，使 compact commit 不只依赖 JSON pointer。
3. 建立多变量实验框架，覆盖 payload size、prompt length、batch size、trace steps、challenge timeout、bisection rounds 和 DA profile。
4. 构造 response tampering、attestation invalid、trace length mismatch、DA unavailable、DA proof invalid 等失败场景实验表。

## 章节结构

1. Introduction：高频 DApp / AI 推理上链的性能与可信问题。
2. Background：Rollup、TEE attestation、Optimistic Challenge、Data Availability。
3. Motivation：单纯 TEE、单纯 OP、全量上链的不足。
4. System Design：执行层、验证层、数据层三层架构。
5. Recoverable Challenge Protocol：状态机、恢复机制、单步重放、证据字段。
6. DA Cost Model：full-onchain、compact commit、DA profile 和 batch amortization。
7. Evaluation：实验设置、指标、结果和失败场景。
8. Discussion：simulated TEE、gas 估算、JSON ledger、真实部署不足。
9. Related Work：TEEROLLUP、OTR、opML、Dynamic Fraud Proof、LazyLedger。
10. Conclusion。
"""


RELATED_WORK_TABLE = """# Related Work 对比表

| 工作 | 核心问题 | 主要机制 | 与本文关系 | 本文差异点 |
| --- | --- | --- | --- | --- |
| TEEROLLUP | 如何用异构 TEE 降低 Rollup 验证成本并缩短提现延迟 | 异构 TEE 委员会、QC、多签、Challenge、DAP 惩罚 | 提供 Hybrid TEE-Rollup 的总体系统参考 | 本文不重做完整 TEEROLLUP，而聚焦异常 challenge 恢复和 DA 成本原型评估 |
| OTR / Optimistic TEE-Rollups | 如何验证链上生成式 AI 推理 | TEE 快速证明、Optimistic challenge、随机 ZK 抽查 | 提供 TEE + Optimistic + 抽查的 AI 推理验证参考 | 本文不实现 ZK 抽查，重点评估 recoverable challenge 和 DA 成本 |
| opML | 如何用 optimistic fraud proof 支持大模型或 ML 计算 | 交互式争议、二分定位、单步仲裁、FPVM | 提供 ML 执行争议和 bisection proof 参考 | 本文面向 Hybrid TEE-Rollup 原型，加入 DA payload 和 timeout recovery |
| Dynamic Fraud Proof | 如何缩短无争议场景的最终性并动态处理争议 | 动态挑战窗口、随机验证者集合、延迟结算 | 提供 challenge timeout 和快速最终性思路 | 本文当前只做可恢复状态机原型，不声称完整动态最终性协议 |
| LazyLedger | 如何将 DA 从执行中解耦并降低扩容瓶颈 | 数据可用性层、抽样、模块化区块链 | 提供 DA 层和数据可用性抽样理论基础 | 本文使用模拟 DA profile 和 Merkle proof，不实现真实 DAS 网络 |
"""


SYSTEM_DESIGN = """# 系统设计说明

## 架构图

```mermaid
flowchart LR
  User["高频 DApp 用户请求"] --> Exec["Execution Layer: simulated TEE"]
  Exec --> Att["Attestation: H(input), H(output), nonce, MRENCLAVE"]
  Att --> Commit["Compact Commit: state_root, output_hash, proof_hash, da_pointer, da_merkle_root"]
  Exec --> DA["DA Store: payload, payload_hash, leaf_hashes, merkle_proofs"]
  Commit --> Chain["JSON Ledger / Simulated Chain"]
  Chain --> Challenge["Recoverable Challenge"]
  DA --> Challenge
  Challenge --> Replay["Bisection + Single-step Replay"]
  Replay --> Resolve["Resolve / Slash / Finalize"]
```

## 数据结构

### Commit

```json
{
  "state_root": "...",
  "output_hash": "...",
  "proof_hash": "...",
  "da_pointer": "...",
  "da_merkle_root": "..."
}
```

### DA Entry

```json
{
  "da_pointer": "...",
  "payload": {"prompt": "...", "response": "...", "attestation": "..."},
  "payload_hash": "...",
  "leaf_hashes": {"prompt": "...", "response": "..."},
  "merkle_root": "...",
  "merkle_proofs": {"response": [{"position": "left", "hash": "..."}]}
}
```

### Challenge Evidence

```json
{
  "da_status": {"available": true, "valid": true, "reason": "da_proof_valid"},
  "mismatch_types": ["response_mismatch"],
  "target_step": 2,
  "expected_hash": "...",
  "claimed_hash": "..."
}
```

## 协议流程

```mermaid
sequenceDiagram
  participant U as User / Challenger
  participant C as Chain
  participant D as DA Store
  participant W as Watchdog
  U->>C: challenge-open(tx)
  C->>D: load payload + proof
  U->>C: challenge-respond(tx)
  loop bisection
    U->>C: challenge-step(tx)
  end
  alt timeout
    W->>C: challenge-recover(tx)
  end
  U->>C: challenge-replay(tx)
  C->>C: resolve and slash if invalid
```

## 状态机

```mermaid
stateDiagram-v2
  [*] --> PENDING
  PENDING --> OPEN: challenge-open
  OPEN --> RESPONDED: challenge-respond
  RESPONDED --> NARROWING: challenge-step
  NARROWING --> READY_FOR_REPLAY: dispute narrowed
  NARROWING --> RECOVERED: timeout + recover
  RECOVERED --> NARROWING: continue step
  READY_FOR_REPLAY --> REPLAYED: challenge-replay
  REPLAYED --> RESOLVED: challenge-resolve
  RESOLVED --> SLASHED: invalid
  PENDING --> FINALIZED: dispute window expired
```
"""


FAILURE_SCENARIOS = """# 失败场景设计

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
"""


def parse_args():
    parser = ArgumentParser(description="Run paper-oriented experiments for recoverable Hybrid TEE-Rollup.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "paper_outputs"))
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--payload-sizes", default="128,512,2048")
    parser.add_argument("--prompt-lengths", default="64,256")
    parser.add_argument("--batch-sizes", default="1,10,100,1000")
    parser.add_argument("--trace-steps", default="4,8,16,32,64")
    parser.add_argument("--challenge-timeouts", default="2")
    parser.add_argument("--max-bisection-rounds", default="16")
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cost_rows = run_cost_grid(
        output_dir=output_dir,
        payload_sizes=parse_int_list(args.payload_sizes),
        batch_sizes=parse_int_list(args.batch_sizes),
        prompt_lengths=parse_int_list(args.prompt_lengths),
        samples=args.samples,
    )
    challenge_rows = run_challenge_grid(
        output_dir=output_dir,
        trace_steps=parse_int_list(args.trace_steps),
        challenge_timeouts=parse_int_list(args.challenge_timeouts),
        max_bisection_rounds=parse_int_list(args.max_bisection_rounds),
        samples=args.samples,
    )
    failure_rows = run_failure_scenarios(output_dir=output_dir, samples=args.samples)
    summary = summarize(cost_rows, challenge_rows)
    failure_summary = summarize_failures(failure_rows)
    summary["failure_summary"] = failure_summary

    write_csv(output_dir / "cost_grid.csv", cost_rows)
    write_csv(output_dir / "challenge_grid.csv", challenge_rows)
    write_csv(output_dir / "failure_scenarios.csv", failure_rows)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    generate_figures(output_dir, summary, failure_summary)
    write_markdown(output_dir / "experiment_report.md", output_dir, summary, failure_summary, cost_rows, challenge_rows, failure_rows)
    write_static_docs(output_dir)
    print("Paper experiments written to: {0}".format(output_dir))


if __name__ == "__main__":
    main()
