from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tee_rollup_demo.attestation import create_attestation, verify_attestation
from tee_rollup_demo.config import DemoConfig
from tee_rollup_demo.ledger import RollupDemo, build_da_merkle_bundle, verify_merkle_proof


class RollupDemoTests(unittest.TestCase):
    def make_demo(self, tmpdir, **overrides):
        config = DemoConfig(
            chain_path=Path(tmpdir) / "chain.json",
            da_path=Path(tmpdir) / "da.json",
            dispute_window_seconds=5,
            challenge_timeout_seconds=2,
            max_bisection_rounds=4,
            spot_check_probability=0.25,
            tee_secret="test-secret",
            model_backend="mock",
            model_name="test-model",
            ollama_base_url="http://127.0.0.1:11434",
        )
        if overrides:
            config = DemoConfig(**{**config.__dict__, **overrides})
        return RollupDemo(config)

    def test_attestation_round_trip(self):
        attestation = create_attestation(
            prompt="hello",
            response="world",
            mrenclave="mrenclave-1",
            secret="shared-secret",
            nonce="fixed-nonce",
        )
        self.assertTrue(verify_attestation(attestation, "hello", "world", "shared-secret"))
        self.assertFalse(verify_attestation(attestation, "hello", "changed", "shared-secret"))

    def test_submit_and_verify_valid_transaction(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            tx = demo.submit(
                "describe the rollup",
                now=created_at,
                nonce="nonce-1",
                tx_id="tx-1",
                spot_check_roll=0.99,
            )
            report = demo.verify("tx-1")

            self.assertEqual(tx["status"], "PENDING")
            self.assertTrue(report["valid"])
            self.assertEqual(report["mismatches"], [])
            self.assertIn("commit", tx)
            self.assertIn("da_pointer", tx["commit"])
            self.assertIn("da_merkle_root", tx["commit"])
            da_entry = demo.get_da_entry("tx-1")
            self.assertEqual(da_entry["prompt"], "describe the rollup")

    def test_da_merkle_proof_round_trip(self):
        payload = {"prompt": "hello", "response": "world", "tx_id": "tx-merkle"}
        bundle = build_da_merkle_bundle(payload)
        proof = bundle["merkle_proofs"]["response"]

        self.assertTrue(verify_merkle_proof("response", "world", proof, bundle["merkle_root"]))
        self.assertFalse(verify_merkle_proof("response", "tampered", proof, bundle["merkle_root"]))

    def test_da_field_proof_is_available_for_submitted_payload(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("proof me", now=created_at, tx_id="tx-proof", spot_check_roll=0.99)

            proof_status = demo.verify_da_field("tx-proof", "response")

            self.assertTrue(proof_status["available"])
            self.assertTrue(proof_status["valid"])
            self.assertEqual(proof_status["reason"], "da_proof_valid")

    def test_missing_da_entry_is_reported_as_unavailable(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("missing da", now=created_at, tx_id="tx-missing-da", spot_check_roll=0.99)
            demo.remove_da_entry("tx-missing-da")

            report = demo.verify("tx-missing-da")

            self.assertFalse(report["valid"])
            self.assertIn("da_unavailable", report["mismatches"])

    def test_corrupt_da_proof_is_reported_invalid(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("bad proof", now=created_at, tx_id="tx-bad-proof", spot_check_roll=0.99)
            demo.corrupt_da_proof("tx-bad-proof", "response")

            report = demo.verify("tx-bad-proof")

            self.assertFalse(report["valid"])
            self.assertIn("da_proof_invalid", report["mismatches"])

    def test_challenge_slashes_tampered_transaction(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("secure inference", now=created_at, tx_id="tx-2", spot_check_roll=0.99)
            demo.tamper_response("tx-2", "dishonest output")
            demo.challenge_open("tx-2", now=created_at + timedelta(seconds=1))
            demo.challenge_respond("tx-2", now=created_at + timedelta(seconds=1))
            result = demo.challenge_resolve("tx-2", now=created_at + timedelta(seconds=1))
            tx = demo.get_transaction("tx-2")

            self.assertTrue(result["challenge_success"])
            self.assertEqual(tx["status"], "SLASHED")
            self.assertTrue(
                any(
                    reason in tx["challenge_result"]["reasons"]
                    for reason in ["response_mismatch", "attestation_invalid", "state_root_mismatch"]
                )
            )
            self.assertEqual(tx["challenge_session"]["status"], "RESOLVED")

    def test_finalize_marks_expired_transaction(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("finalize me", now=created_at, tx_id="tx-3", spot_check_roll=0.99)

            finalized = demo.finalize_expired(now=created_at + timedelta(seconds=6))
            tx = demo.get_transaction("tx-3")

            self.assertEqual(finalized, ["tx-3"])
            self.assertEqual(tx["status"], "FINALIZED")

    def test_forced_spot_check_detects_tampering(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("spot check me", now=created_at, tx_id="tx-4", spot_check_roll=0.99)
            demo.tamper_response("tx-4", "bad output")

            result = demo.run_spot_check("tx-4", now=created_at + timedelta(seconds=1), force=True)
            tx = demo.get_transaction("tx-4")

            self.assertTrue(result["triggered"])
            self.assertFalse(result["passed"])
            self.assertEqual(tx["status"], "SLASHED")

    def test_estimate_cost_reports_reduction(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("cost estimation", now=created_at, tx_id="tx-5", spot_check_roll=0.99)
            stats = demo.estimate_submission_cost("tx-5")

            self.assertGreater(stats["full_bytes"], stats["compact_bytes"])
            self.assertGreater(stats["saved_bytes"], 0)
            self.assertGreater(stats["reduction_ratio"], 0.0)

    def test_bisection_replay_flow_marks_tampered_step(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("bisection flow", now=created_at, tx_id="tx-6", spot_check_roll=0.99)
            demo.tamper_response("tx-6", "line1\nline2\nline3\nline4")

            session = demo.challenge_open("tx-6", now=created_at + timedelta(seconds=1))
            self.assertEqual(session["status"], "OPEN")

            # Continue narrowing until a single dispute step is located.
            for _ in range(6):
                dispute = demo.challenge_step("tx-6", now=created_at + timedelta(seconds=2))
                if dispute["narrowing_complete"]:
                    break

            self.assertTrue(dispute["narrowing_complete"])
            replay = demo.challenge_replay("tx-6", now=created_at + timedelta(seconds=3))
            self.assertFalse(replay["passed"])

            result = demo.challenge_resolve("tx-6", now=created_at + timedelta(seconds=4))
            self.assertTrue(result["challenge_success"])
            self.assertEqual(result["tx"]["status"], "SLASHED")

    def test_estimate_strategy_costs_reports_gas_drop(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("strategy estimate", now=created_at, tx_id="tx-7", spot_check_roll=0.99)
            metrics = demo.estimate_strategy_costs("tx-7")

            full_onchain = metrics["gas_estimate"]["full_onchain"]
            compact_with_da = metrics["gas_estimate"]["compact_with_da"]
            compact_with_blob = metrics["gas_estimate"]["compact_with_blob_da"]
            self.assertGreater(full_onchain, compact_with_da)
            self.assertGreater(full_onchain, compact_with_blob)
            self.assertGreater(metrics["gas_reduction_ratio"]["compact_with_da"], 0.0)
            self.assertGreater(metrics["gas_reduction_ratio"]["compact_with_blob_da"], 0.0)
            self.assertEqual(metrics["scenario_curve"][0]["scenario"], "full_onchain_calldata")
            self.assertEqual(metrics["scenario_curve"][0]["total_gas"], full_onchain)
            self.assertTrue(
                any(item["reduction_ratio"] > 0.0 for item in metrics["scenario_curve"][1:])
            )

    def test_challenge_recover_restores_timed_out_session(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("recover flow", now=created_at, tx_id="tx-8", spot_check_roll=0.99)
            demo.tamper_response("tx-8", "line1\nline2\nline3\nline4")
            demo.challenge_open("tx-8", now=created_at + timedelta(seconds=1))
            demo.challenge_respond("tx-8", now=created_at + timedelta(seconds=1))
            demo.challenge_step("tx-8", now=created_at + timedelta(seconds=2))

            status = demo.challenge_status("tx-8", now=created_at + timedelta(seconds=5))
            self.assertTrue(status["timed_out"])

            recovered = demo.challenge_recover("tx-8", operator="watchdog", now=created_at + timedelta(seconds=5))
            self.assertIn(recovered["status"], ["RECOVERED", "RESPONDED", "READY_FOR_REPLAY"])
            self.assertEqual(recovered["recovery"]["count"], 1)
            self.assertEqual(recovered["recovery"]["history"][0]["operator"], "watchdog")

            dispute = demo.challenge_step("tx-8", now=created_at + timedelta(seconds=6))
            while not dispute["narrowing_complete"]:
                dispute = demo.challenge_step("tx-8", now=created_at + timedelta(seconds=6))
            replay = demo.challenge_replay("tx-8", now=created_at + timedelta(seconds=7))
            result = demo.challenge_resolve("tx-8", now=created_at + timedelta(seconds=8))

            self.assertFalse(replay["passed"])
            self.assertTrue(result["challenge_success"])

    def test_plain_challenge_without_recover_fails_after_timeout(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("timeout flow", now=created_at, tx_id="tx-timeout", spot_check_roll=0.99)
            demo.tamper_response("tx-timeout", "line1\nline2\nline3\nline4")
            demo.challenge_open("tx-timeout", now=created_at + timedelta(seconds=1))
            demo.challenge_respond("tx-timeout", now=created_at + timedelta(seconds=1))
            demo.challenge_step("tx-timeout", now=created_at + timedelta(seconds=2))

            with self.assertRaises(ValueError):
                demo.challenge_step("tx-timeout", now=created_at + timedelta(seconds=5))

    def test_trace_length_mismatch_is_detected_by_replay(self):
        with TemporaryDirectory() as tmpdir:
            demo = self.make_demo(tmpdir)
            created_at = datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc)
            demo.submit("trace length", now=created_at, tx_id="tx-trace-length", spot_check_roll=0.99)
            demo.truncate_response_trace("tx-trace-length", keep_lines=1)
            demo.challenge_open("tx-trace-length", now=created_at + timedelta(seconds=1))
            demo.challenge_respond("tx-trace-length", now=created_at + timedelta(seconds=1))
            dispute = demo.challenge_step("tx-trace-length", now=created_at + timedelta(seconds=2))
            while not dispute["narrowing_complete"]:
                dispute = demo.challenge_step("tx-trace-length", now=created_at + timedelta(seconds=2))

            replay = demo.challenge_replay("tx-trace-length", now=created_at + timedelta(seconds=3))

            self.assertFalse(replay["passed"])
            self.assertEqual(replay["reason"], "trace_length_mismatch")


if __name__ == "__main__":
    unittest.main()
