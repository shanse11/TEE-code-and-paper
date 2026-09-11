from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import secrets

from .attestation import create_attestation, verify_attestation
from .model import build_model
from .utils import canonical_json, sha256_hex


def utc_now():
    return datetime.now(timezone.utc)


def to_iso8601(value):
    return value.astimezone(timezone.utc).isoformat()


def from_iso8601(value):
    return datetime.fromisoformat(value)


def _merkle_parent(left, right):
    return sha256_hex(canonical_json({"left": left, "right": right}))


def _build_merkle_tree(leaf_hashes):
    levels = [list(leaf_hashes)]
    while len(levels[-1]) > 1:
        current = levels[-1]
        next_level = []
        for index in range(0, len(current), 2):
            left = current[index]
            right = current[index + 1] if index + 1 < len(current) else left
            next_level.append(_merkle_parent(left, right))
        levels.append(next_level)
    return levels


def _merkle_proof(levels, leaf_index):
    proof = []
    index = leaf_index
    for level in levels[:-1]:
        sibling_index = index + 1 if index % 2 == 0 else index - 1
        if sibling_index >= len(level):
            sibling_index = index
        proof.append(
            {
                "position": "right" if index % 2 == 0 else "left",
                "hash": level[sibling_index],
            }
        )
        index = index // 2
    return proof


def build_da_merkle_bundle(payload):
    fields = sorted(payload.keys())
    leaves = []
    leaf_hashes = {}
    for field in fields:
        leaf_hash = sha256_hex(canonical_json({"field": field, "value": payload[field]}))
        leaf_hashes[field] = leaf_hash
        leaves.append(leaf_hash)
    if not leaves:
        root = sha256_hex("")
        return {
            "payload_hash": sha256_hex(canonical_json(payload)),
            "leaf_hashes": {},
            "merkle_root": root,
            "merkle_proofs": {},
        }
    levels = _build_merkle_tree(leaves)
    proofs = {}
    for index, field in enumerate(fields):
        proofs[field] = _merkle_proof(levels, index)
    return {
        "payload_hash": sha256_hex(canonical_json(payload)),
        "leaf_hashes": leaf_hashes,
        "merkle_root": levels[-1][0],
        "merkle_proofs": proofs,
    }


def verify_merkle_proof(field, value, proof, root):
    current = sha256_hex(canonical_json({"field": field, "value": value}))
    for item in proof:
        if item["position"] == "left":
            current = _merkle_parent(item["hash"], current)
        elif item["position"] == "right":
            current = _merkle_parent(current, item["hash"])
        else:
            return False
    return current == root


class RollupDemo:
    def __init__(self, config, model=None):
        self.config = config
        self.model = model or build_model(config)
        self.mrenclave = sha256_hex(self.model.fingerprint())

    def _load_state(self):
        chain_path = Path(self.config.chain_path)
        if not chain_path.exists():
            return {"transactions": []}
        with chain_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_state(self, state):
        chain_path = Path(self.config.chain_path)
        chain_path.parent.mkdir(parents=True, exist_ok=True)
        with chain_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=True)

    def _load_da_state(self):
        da_path = Path(self.config.da_path)
        if not da_path.exists():
            return {"entries": []}
        with da_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_da_state(self, state):
        da_path = Path(self.config.da_path)
        da_path.parent.mkdir(parents=True, exist_ok=True)
        with da_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=True)

    def _locate_transaction(self, state, tx_id):
        for transaction in state["transactions"]:
            if transaction["id"] == tx_id:
                return transaction
        raise ValueError("transaction not found: {0}".format(tx_id))

    def _locate_da_entry(self, da_state, da_pointer):
        for entry in da_state["entries"]:
            if entry["da_pointer"] == da_pointer:
                return entry
        raise ValueError("da entry not found: {0}".format(da_pointer))

    def _build_commit(self, prompt, response, attestation, da_merkle_root=None):
        state_root = sha256_hex(
            canonical_json(
                {
                    "prompt_hash": sha256_hex(prompt),
                    "response_hash": sha256_hex(response),
                    "mrenclave": self.mrenclave,
                }
            )
        )
        proof_hash = sha256_hex(
            canonical_json(
                {
                    "nonce": attestation["nonce"],
                    "signature": attestation["signature"],
                    "scheme": attestation["scheme"],
                }
            )
        )
        return {
            "state_root": state_root,
            "output_hash": sha256_hex(response),
            "proof_hash": proof_hash,
            "da_merkle_root": da_merkle_root,
        }

    def _store_da_entry(self, tx_id, prompt, response, attestation, created_at):
        payload = {
            "tx_id": tx_id,
            "prompt": prompt,
            "response": response,
            "attestation": attestation,
            "mrenclave": self.mrenclave,
            "created_at": to_iso8601(created_at),
        }
        merkle_bundle = build_da_merkle_bundle(payload)
        pointer = sha256_hex(canonical_json(payload))
        da_state = self._load_da_state()
        da_state["entries"].append(
            {
                "da_pointer": pointer,
                "payload": payload,
                "payload_hash": merkle_bundle["payload_hash"],
                "leaf_hashes": merkle_bundle["leaf_hashes"],
                "merkle_root": merkle_bundle["merkle_root"],
                "merkle_proofs": merkle_bundle["merkle_proofs"],
            }
        )
        self._save_da_state(da_state)
        return {
            "da_pointer": pointer,
            "merkle_root": merkle_bundle["merkle_root"],
        }

    def _validation_report(self, transaction):
        try:
            da_record = self.get_da_record(transaction["id"])
        except ValueError:
            return {
                "valid": False,
                "mismatches": ["da_unavailable"],
                "expected_response": None,
            }
        da_entry = da_record["payload"]
        expected_response = self.model.infer(da_entry["prompt"])
        mismatches = []
        if da_record.get("payload_hash") != sha256_hex(canonical_json(da_entry)):
            mismatches.append("da_payload_hash_mismatch")
        if transaction["commit"].get("da_merkle_root") != da_record.get("merkle_root"):
            mismatches.append("da_merkle_root_mismatch")
        da_response_proof = self.verify_da_field(transaction["id"], "response")
        if not da_response_proof["valid"]:
            mismatches.append(da_response_proof["reason"])
        if transaction["mrenclave"] != self.mrenclave:
            mismatches.append("mrenclave_mismatch")
        if transaction["commit"]["output_hash"] != sha256_hex(expected_response):
            mismatches.append("response_mismatch")
        if not verify_attestation(da_entry["attestation"], da_entry["prompt"], da_entry["response"], self.config.tee_secret):
            mismatches.append("attestation_invalid")
        expected_commit = self._build_commit(
            da_entry["prompt"],
            da_entry["response"],
            da_entry["attestation"],
            da_merkle_root=da_record.get("merkle_root"),
        )
        if transaction["commit"]["state_root"] != expected_commit["state_root"]:
            mismatches.append("state_root_mismatch")
        if transaction["commit"]["proof_hash"] != expected_commit["proof_hash"]:
            mismatches.append("proof_hash_mismatch")
        return {
            "valid": not mismatches,
            "mismatches": mismatches,
            "expected_response": expected_response,
        }

    def _execution_trace(self, prompt, response):
        lines = response.splitlines()
        if not lines:
            lines = [response]
        steps = []
        rolling_state = "prompt:{0}".format(prompt)
        for index, line in enumerate(lines):
            rolling_state = "{0}|step:{1}|{2}".format(rolling_state, index, line)
            steps.append(
                {
                    "index": index,
                    "line": line,
                    "state_hash": sha256_hex(rolling_state),
                }
            )
        return steps

    def _trace_bundle(self, tx_id):
        da_entry = self.get_da_entry(tx_id)
        expected_response = self.model.infer(da_entry["prompt"])
        expected_trace = self._execution_trace(da_entry["prompt"], expected_response)
        claimed_trace = self._execution_trace(da_entry["prompt"], da_entry["response"])
        comparable_length = min(len(expected_trace), len(claimed_trace))
        return {
            "expected_trace": expected_trace,
            "claimed_trace": claimed_trace,
            "comparable_length": comparable_length,
            "length_mismatch": len(expected_trace) != len(claimed_trace),
        }

    def _challenge_timeout_at(self, current_time):
        return current_time + timedelta(seconds=self.config.challenge_timeout_seconds)

    def _active_challenge_statuses(self):
        return ["OPEN", "RESPONDED", "NARROWING", "READY_FOR_REPLAY", "REPLAYED", "RECOVERED"]

    def _challenge_timed_out(self, session, current_time):
        timeout_at = session.get("timeout_at")
        if not timeout_at:
            return False
        return current_time > from_iso8601(timeout_at)

    def _touch_session(self, session, current_time):
        session["last_updated_at"] = to_iso8601(current_time)
        session["timeout_at"] = to_iso8601(self._challenge_timeout_at(current_time))

    def _find_first_mismatch(self, expected_trace, claimed_trace):
        comparable = min(len(expected_trace), len(claimed_trace))
        for index in range(comparable):
            if expected_trace[index]["state_hash"] != claimed_trace[index]["state_hash"]:
                return index
        if len(expected_trace) != len(claimed_trace):
            return comparable
        return None

    def _should_trigger_spot_check(self, roll=None, force=False):
        if force:
            return True, 0.0 if roll is None else float(roll)
        actual_roll = random.random() if roll is None else float(roll)
        return actual_roll < self.config.spot_check_probability, actual_roll

    def _build_spot_check_result(self, transaction, now=None, force=False, roll=None):
        triggered, actual_roll = self._should_trigger_spot_check(roll=roll, force=force)
        if not triggered:
            return {
                "triggered": False,
                "roll": actual_roll,
            }
        validation = self._validation_report(transaction)
        result = {
            "triggered": True,
            "roll": actual_roll,
            "checked_at": to_iso8601(now or utc_now()),
            "passed": validation["valid"],
            "reasons": validation["mismatches"],
        }
        if validation["valid"]:
            da_entry = self.get_da_entry(transaction["id"])
            result["proof"] = sha256_hex(
                canonical_json(
                    {
                        "tx_id": transaction["id"],
                        "prompt": da_entry["prompt"],
                        "response": da_entry["response"],
                        "mrenclave": transaction["mrenclave"],
                    }
                )
            )
        return result

    def submit(self, prompt, now=None, nonce=None, tx_id=None, forced_response=None, spot_check_roll=None):
        created_at = now or utc_now()
        response = forced_response if forced_response is not None else self.model.infer(prompt)
        final_tx_id = tx_id or secrets.token_hex(6)
        attestation = create_attestation(
            prompt=prompt,
            response=response,
            mrenclave=self.mrenclave,
            secret=self.config.tee_secret,
            nonce=nonce,
        )
        da_record = self._store_da_entry(final_tx_id, prompt, response, attestation, created_at)
        commit = self._build_commit(
            prompt,
            response,
            attestation,
            da_merkle_root=da_record["merkle_root"],
        )
        transaction = {
            "id": final_tx_id,
            "mrenclave": self.mrenclave,
            "model_backend": self.config.model_backend,
            "model_name": self.config.model_name,
            "created_at": to_iso8601(created_at),
            "challenge_deadline": to_iso8601(
                created_at + timedelta(seconds=self.config.dispute_window_seconds)
            ),
            "commit": {
                "state_root": commit["state_root"],
                "output_hash": commit["output_hash"],
                "proof_hash": commit["proof_hash"],
                "da_pointer": da_record["da_pointer"],
                "da_merkle_root": commit["da_merkle_root"],
            },
            "status": "PENDING",
            "challenge_result": None,
            "challenge_session": None,
            "spot_check": None,
        }
        transaction["spot_check"] = self._build_spot_check_result(
            transaction,
            now=created_at,
            roll=spot_check_roll,
        )
        state = self._load_state()
        state["transactions"].append(transaction)
        self._save_state(state)
        return deepcopy(transaction)

    def list_transactions(self):
        state = self._load_state()
        return deepcopy(state["transactions"])

    def get_transaction(self, tx_id):
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        return deepcopy(transaction)

    def get_da_entry(self, tx_id):
        return deepcopy(self.get_da_record(tx_id)["payload"])

    def get_da_record(self, tx_id):
        transaction = self.get_transaction(tx_id)
        da_pointer = transaction["commit"]["da_pointer"]
        da_state = self._load_da_state()
        da_entry = self._locate_da_entry(da_state, da_pointer)
        return deepcopy(da_entry)

    def get_da_proof(self, tx_id, field):
        da_record = self.get_da_record(tx_id)
        if field not in da_record["payload"]:
            raise ValueError("da field not found: {0}".format(field))
        return {
            "field": field,
            "value": deepcopy(da_record["payload"][field]),
            "leaf_hash": da_record.get("leaf_hashes", {}).get(field),
            "proof": deepcopy(da_record.get("merkle_proofs", {}).get(field, [])),
            "root": da_record.get("merkle_root"),
        }

    def verify_da_field(self, tx_id, field):
        try:
            proof = self.get_da_proof(tx_id, field)
        except ValueError:
            return {
                "available": False,
                "valid": False,
                "reason": "da_unavailable",
            }
        valid = verify_merkle_proof(proof["field"], proof["value"], proof["proof"], proof["root"])
        return {
            "available": True,
            "valid": valid,
            "reason": "da_proof_valid" if valid else "da_proof_invalid",
            "field": field,
            "root": proof["root"],
        }

    def verify(self, tx_id):
        transaction = self.get_transaction(tx_id)
        report = self._validation_report(transaction)
        report["tx_id"] = tx_id
        return report

    def challenge_open(self, tx_id, challenger="fisherman", now=None, reason="state_transition_dispute"):
        current_time = now or utc_now()
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        if transaction["status"] == "FINALIZED":
            raise ValueError("transaction already finalized")
        if current_time > from_iso8601(transaction["challenge_deadline"]):
            raise ValueError("dispute window already closed")
        if transaction.get("challenge_session") and transaction["challenge_session"]["status"] != "RESOLVED":
            raise ValueError("challenge already open")
        transaction["challenge_session"] = {
            "challenger": challenger,
            "opened_at": to_iso8601(current_time),
            "last_updated_at": to_iso8601(current_time),
            "timeout_at": to_iso8601(self._challenge_timeout_at(current_time)),
            "reason": reason,
            "status": "OPEN",
            "response": None,
            "dispute": None,
            "resolution": None,
            "evidence": {
                "da_status": None,
                "mismatch_types": [],
                "target_step": None,
                "expected_hash": None,
                "claimed_hash": None,
            },
            "recovery": {
                "count": 0,
                "history": [],
            },
        }
        trace_bundle = self._trace_bundle(tx_id)
        if trace_bundle["length_mismatch"]:
            right_bound = max(0, trace_bundle["comparable_length"])
            trace_length = right_bound + 1
        else:
            right_bound = max(0, trace_bundle["comparable_length"] - 1)
            trace_length = trace_bundle["comparable_length"]
        transaction["challenge_session"]["dispute"] = {
            "left": 0,
            "right": right_bound,
            "round": 0,
            "trace_length": trace_length,
            "length_mismatch": trace_bundle["length_mismatch"],
            "narrowing_complete": trace_length <= 1,
            "target_step": 0 if trace_length <= 1 and trace_bundle["length_mismatch"] else None,
            "history": [],
        }
        self._save_state(state)
        return deepcopy(transaction["challenge_session"])

    def challenge_respond(self, tx_id, responder="sequencer", now=None):
        current_time = now or utc_now()
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        session = transaction.get("challenge_session")
        if not session or session["status"] != "OPEN":
            raise ValueError("no open challenge")
        if self._challenge_timed_out(session, current_time):
            raise ValueError("challenge session timed out")
        validation = self._validation_report(transaction)
        session["evidence"]["mismatch_types"] = validation["mismatches"]
        session["evidence"]["da_status"] = self.verify_da_field(tx_id, "response")
        session["response"] = {
            "responder": responder,
            "responded_at": to_iso8601(current_time),
            "validation_preview": {
                "valid": validation["valid"],
                "mismatches": validation["mismatches"],
            },
        }
        session["status"] = "RESPONDED"
        self._touch_session(session, current_time)
        self._save_state(state)
        return deepcopy(session)

    def challenge_step(self, tx_id, now=None):
        current_time = now or utc_now()
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        session = transaction.get("challenge_session")
        if not session or session["status"] not in self._active_challenge_statuses():
            raise ValueError("no active challenge")
        if self._challenge_timed_out(session, current_time):
            raise ValueError("challenge session timed out")
        dispute = session.get("dispute")
        if not dispute:
            raise ValueError("no dispute context")
        if dispute["trace_length"] == 0:
            dispute["narrowing_complete"] = True
            dispute["target_step"] = 0
            session["status"] = "READY_FOR_REPLAY"
            self._touch_session(session, current_time)
            self._save_state(state)
            return deepcopy(dispute)
        if dispute["narrowing_complete"]:
            session["status"] = "READY_FOR_REPLAY"
            self._touch_session(session, current_time)
            self._save_state(state)
            return deepcopy(dispute)
        if dispute["round"] >= self.config.max_bisection_rounds:
            raise ValueError("max bisection rounds reached")
        trace_bundle = self._trace_bundle(tx_id)
        expected_trace = trace_bundle["expected_trace"]
        claimed_trace = trace_bundle["claimed_trace"]
        mismatch_index = self._find_first_mismatch(expected_trace, claimed_trace)
        if mismatch_index is None:
            dispute["narrowing_complete"] = True
            dispute["target_step"] = dispute["left"]
            dispute["history"].append(
                {
                    "round": dispute["round"] + 1,
                    "checked_at": to_iso8601(current_time),
                    "decision": "no_mismatch_in_trace",
                    "left": dispute["left"],
                    "right": dispute["right"],
                }
            )
            dispute["round"] += 1
            session["status"] = "READY_FOR_REPLAY"
            self._touch_session(session, current_time)
            self._save_state(state)
            return deepcopy(dispute)
        mid = (dispute["left"] + dispute["right"]) // 2
        if mismatch_index <= mid:
            new_left = dispute["left"]
            new_right = mid
            decision = "left_half"
        else:
            new_left = mid + 1
            new_right = dispute["right"]
            decision = "right_half"
        dispute["history"].append(
            {
                "round": dispute["round"] + 1,
                "checked_at": to_iso8601(current_time),
                "decision": decision,
                "mismatch_index": mismatch_index,
                "left": dispute["left"],
                "right": dispute["right"],
            }
        )
        dispute["left"] = new_left
        dispute["right"] = new_right
        dispute["round"] += 1
        session["status"] = "NARROWING"
        if new_left >= new_right:
            dispute["narrowing_complete"] = True
            dispute["target_step"] = new_left
            session["status"] = "READY_FOR_REPLAY"
        self._touch_session(session, current_time)
        self._save_state(state)
        return deepcopy(dispute)

    def challenge_replay(self, tx_id, now=None):
        current_time = now or utc_now()
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        session = transaction.get("challenge_session")
        if not session or session["status"] not in self._active_challenge_statuses():
            raise ValueError("no active challenge")
        if self._challenge_timed_out(session, current_time):
            raise ValueError("challenge session timed out")
        dispute = session.get("dispute")
        if not dispute:
            raise ValueError("no dispute context")
        if not dispute["narrowing_complete"]:
            raise ValueError("dispute narrowing not complete")
        target_step = dispute["target_step"] if dispute["target_step"] is not None else dispute["left"]
        trace_bundle = self._trace_bundle(tx_id)
        expected_trace = trace_bundle["expected_trace"]
        claimed_trace = trace_bundle["claimed_trace"]
        if target_step >= len(expected_trace) or target_step >= len(claimed_trace):
            replay_result = {
                "checked_at": to_iso8601(current_time),
                "step_index": target_step,
                "passed": False,
                "reason": "trace_length_mismatch",
            }
        else:
            passed = expected_trace[target_step]["state_hash"] == claimed_trace[target_step]["state_hash"]
            replay_result = {
                "checked_at": to_iso8601(current_time),
                "step_index": target_step,
                "passed": passed,
                "reason": "step_match" if passed else "step_state_mismatch",
                "expected_hash": expected_trace[target_step]["state_hash"],
                "claimed_hash": claimed_trace[target_step]["state_hash"],
            }
        session["dispute"]["replay_result"] = replay_result
        session["evidence"]["target_step"] = replay_result["step_index"]
        session["evidence"]["expected_hash"] = replay_result.get("expected_hash")
        session["evidence"]["claimed_hash"] = replay_result.get("claimed_hash")
        session["status"] = "REPLAYED"
        self._touch_session(session, current_time)
        self._save_state(state)
        return deepcopy(replay_result)

    def challenge_resolve(self, tx_id, arbitrator="onchain-replay", now=None):
        current_time = now or utc_now()
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        session = transaction.get("challenge_session")
        if not session or session["status"] not in self._active_challenge_statuses():
            raise ValueError("no resolvable challenge")
        report = self._validation_report(transaction)
        replay = None
        if session.get("dispute"):
            replay = session["dispute"].get("replay_result")
            if replay is None:
                try:
                    replay = self.challenge_replay(tx_id, now=current_time)
                except ValueError:
                    replay = None
        success = not report["valid"]
        if replay and not replay.get("passed", True):
            success = True
        resolution = {
            "arbitrator": arbitrator,
            "resolved_at": to_iso8601(current_time),
            "challenge_success": success,
            "reasons": report["mismatches"],
            "expected_response": report["expected_response"],
            "replay_result": replay,
            "evidence": deepcopy(session.get("evidence")),
        }
        session["status"] = "RESOLVED"
        self._touch_session(session, current_time)
        session["resolution"] = resolution
        transaction["challenge_result"] = resolution
        if success:
            transaction["status"] = "SLASHED"
        self._save_state(state)
        return {
            "tx": deepcopy(transaction),
            "challenge_success": success,
        }

    def challenge(self, tx_id, challenger="fisherman", now=None):
        current_time = now or utc_now()
        self.challenge_open(tx_id, challenger=challenger, now=current_time)
        self.challenge_respond(tx_id, now=current_time)
        return self.challenge_resolve(tx_id, now=current_time)

    def challenge_status(self, tx_id, now=None):
        current_time = now or utc_now()
        transaction = self.get_transaction(tx_id)
        session = transaction.get("challenge_session")
        if not session:
            raise ValueError("no challenge session")
        snapshot = deepcopy(session)
        snapshot["timed_out"] = self._challenge_timed_out(session, current_time)
        snapshot["max_bisection_rounds"] = self.config.max_bisection_rounds
        return snapshot

    def challenge_recover(self, tx_id, operator="watchdog", now=None):
        current_time = now or utc_now()
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        session = transaction.get("challenge_session")
        if not session or session["status"] == "RESOLVED":
            raise ValueError("no recoverable challenge")
        if not self._challenge_timed_out(session, current_time):
            raise ValueError("challenge session still active")
        prior_status = session["status"]
        recovery_history = session.setdefault("recovery", {"count": 0, "history": []})
        recovery_history["count"] += 1
        recovery_history["history"].append(
            {
                "operator": operator,
                "recovered_at": to_iso8601(current_time),
                "prior_status": prior_status,
                "prior_round": None if not session.get("dispute") else session["dispute"]["round"],
            }
        )
        dispute = session.get("dispute")
        if dispute and dispute.get("narrowing_complete"):
            session["status"] = "READY_FOR_REPLAY"
        elif dispute and dispute.get("round", 0) > 0:
            session["status"] = "RECOVERED"
        elif session.get("response"):
            session["status"] = "RESPONDED"
        else:
            session["status"] = "OPEN"
        self._touch_session(session, current_time)
        self._save_state(state)
        return deepcopy(session)

    def finalize_expired(self, now=None):
        current_time = now or utc_now()
        state = self._load_state()
        finalized_ids = []
        for transaction in state["transactions"]:
            if transaction["status"] != "PENDING":
                continue
            if current_time >= from_iso8601(transaction["challenge_deadline"]):
                transaction["status"] = "FINALIZED"
                finalized_ids.append(transaction["id"])
        self._save_state(state)
        return finalized_ids

    def run_spot_check(self, tx_id, now=None, force=False, roll=None):
        current_time = now or utc_now()
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        result = self._build_spot_check_result(
            transaction,
            now=current_time,
            force=force,
            roll=roll,
        )
        transaction["spot_check"] = result
        if result["triggered"] and not result.get("passed", False):
            transaction["status"] = "SLASHED"
        self._save_state(state)
        return deepcopy(result)

    def tamper_response(self, tx_id, new_response):
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        da_state = self._load_da_state()
        da_entry = self._locate_da_entry(da_state, transaction["commit"]["da_pointer"])
        da_entry["payload"]["response"] = new_response
        self._save_da_state(da_state)
        return deepcopy(transaction)

    def tamper_attestation(self, tx_id):
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        da_state = self._load_da_state()
        da_entry = self._locate_da_entry(da_state, transaction["commit"]["da_pointer"])
        da_entry["payload"]["attestation"]["signature"] = "tampered-" + da_entry["payload"]["attestation"]["signature"]
        self._save_da_state(da_state)
        return deepcopy(transaction)

    def truncate_response_trace(self, tx_id, keep_lines=1):
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        da_state = self._load_da_state()
        da_entry = self._locate_da_entry(da_state, transaction["commit"]["da_pointer"])
        lines = da_entry["payload"]["response"].splitlines()
        da_entry["payload"]["response"] = "\n".join(lines[: max(0, keep_lines)])
        self._save_da_state(da_state)
        return deepcopy(transaction)

    def remove_da_entry(self, tx_id):
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        da_state = self._load_da_state()
        da_state["entries"] = [
            entry
            for entry in da_state["entries"]
            if entry["da_pointer"] != transaction["commit"]["da_pointer"]
        ]
        self._save_da_state(da_state)
        return deepcopy(transaction)

    def corrupt_da_proof(self, tx_id, field="response"):
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        da_state = self._load_da_state()
        da_entry = self._locate_da_entry(da_state, transaction["commit"]["da_pointer"])
        proofs = da_entry.get("merkle_proofs", {})
        if field in proofs and proofs[field]:
            proofs[field][0]["hash"] = sha256_hex("corrupted-proof")
        else:
            proofs[field] = [{"position": "right", "hash": sha256_hex("corrupted-proof")}]
        self._save_da_state(da_state)
        return deepcopy(transaction)

    def estimate_submission_cost(self, tx_id):
        state = self._load_state()
        transaction = self._locate_transaction(state, tx_id)
        da_payload = self.get_da_entry(tx_id)
        full_payload = {
            "prompt": da_payload["prompt"],
            "response": da_payload["response"],
            "attestation": da_payload["attestation"],
            "mrenclave": da_payload["mrenclave"],
        }
        compact_payload = transaction["commit"]
        full_bytes = len(canonical_json(full_payload).encode("utf-8"))
        compact_bytes = len(canonical_json(compact_payload).encode("utf-8"))
        saved_bytes = full_bytes - compact_bytes
        reduction_ratio = 0.0 if full_bytes == 0 else float(saved_bytes) / float(full_bytes)
        return {
            "tx_id": tx_id,
            "full_bytes": full_bytes,
            "compact_bytes": compact_bytes,
            "saved_bytes": saved_bytes,
            "reduction_ratio": reduction_ratio,
        }

    def estimate_strategy_costs(self, tx_id):
        base = self.estimate_submission_cost(tx_id)
        full_onchain = base["full_bytes"] * 16
        compact_with_da = base["compact_bytes"] * 16
        compact_with_blob_da = int(base["compact_bytes"] * 12)
        scenario_curve = []
        scenario_params = [
            {
                "name": "full_onchain_calldata",
                "onchain_gas_per_byte": 16.0,
                "da_gas_per_byte": 0.0,
            },
            {
                "name": "compact_commit_external_da",
                "onchain_gas_per_byte": 16.0,
                "da_gas_per_byte": 2.2,
            },
            {
                "name": "compact_commit_eip4844_like",
                "onchain_gas_per_byte": 16.0,
                "da_gas_per_byte": 0.9,
            },
            {
                "name": "compact_commit_modular_da_sampling",
                "onchain_gas_per_byte": 16.0,
                "da_gas_per_byte": 0.45,
            },
        ]
        for params in scenario_params:
            if params["name"] == "full_onchain_calldata":
                onchain_commit_gas = int(base["full_bytes"] * params["onchain_gas_per_byte"])
                da_data_gas = 0
            else:
                onchain_commit_gas = int(base["compact_bytes"] * params["onchain_gas_per_byte"])
                da_data_gas = int(base["full_bytes"] * params["da_gas_per_byte"])
            total_gas = onchain_commit_gas + da_data_gas
            scenario_curve.append(
                {
                    "scenario": params["name"],
                    "onchain_commit_gas": onchain_commit_gas,
                    "da_data_gas": da_data_gas,
                    "total_gas": total_gas,
                    "reduction_ratio": 0.0
                    if full_onchain == 0
                    else float(full_onchain - total_gas) / float(full_onchain),
                }
            )
        return {
            "tx_id": tx_id,
            "byte_metrics": base,
            "gas_estimate": {
                "full_onchain": full_onchain,
                "compact_with_da": compact_with_da,
                "compact_with_blob_da": compact_with_blob_da,
            },
            "gas_reduction_ratio": {
                "compact_with_da": 0.0 if full_onchain == 0 else float(full_onchain - compact_with_da) / float(full_onchain),
                "compact_with_blob_da": 0.0
                if full_onchain == 0
                else float(full_onchain - compact_with_blob_da) / float(full_onchain),
            },
            "scenario_curve": scenario_curve,
        }
