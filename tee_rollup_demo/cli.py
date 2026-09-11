import argparse
import json
import sys

from .config import load_config
from .ledger import RollupDemo


def build_parser():
    parser = argparse.ArgumentParser(
        description="Simulated TEE + optimistic rollup demo for AI inference."
    )
    parser.add_argument("--chain-file", default=None, help="Path to the JSON DA / chain file.")
    parser.add_argument(
        "--backend",
        choices=["mock", "ollama"],
        default=None,
        help="Inference backend. Defaults to deterministic mock model.",
    )
    parser.add_argument("--model-name", default=None, help="Model name or demo model label.")
    parser.add_argument(
        "--dispute-window",
        type=int,
        default=None,
        help="Challenge window in seconds.",
    )
    parser.add_argument(
        "--spot-check-probability",
        type=float,
        default=None,
        help="Probability that a pseudo-ZK spot check is triggered.",
    )
    parser.add_argument(
        "--challenge-timeout",
        type=int,
        default=None,
        help="Per-session timeout in seconds for challenge recovery.",
    )
    parser.add_argument(
        "--max-bisection-rounds",
        type=int,
        default=None,
        help="Maximum bisection rounds before forcing replay or recovery.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit = subparsers.add_parser("submit", help="Run inference in the simulated TEE and append it to the chain.")
    submit.add_argument("prompt", help="User prompt to infer on.")
    submit.add_argument(
        "--force-response",
        default=None,
        help="Override the model output to simulate a dishonest sequencer.",
    )

    subparsers.add_parser("list", help="List all submitted rollup transactions.")

    show = subparsers.add_parser("show", help="Show a single transaction.")
    show.add_argument("tx_id", help="Transaction id.")

    verify = subparsers.add_parser("verify", help="Validate response, attestation, and MRENCLAVE.")
    verify.add_argument("tx_id", help="Transaction id.")

    challenge = subparsers.add_parser("challenge", help="Run the fisherman challenge path.")
    challenge.add_argument("tx_id", help="Transaction id.")
    challenge.add_argument("--challenger", default="fisherman", help="Human-readable challenger id.")

    challenge_open = subparsers.add_parser("challenge-open", help="Open a challenge session.")
    challenge_open.add_argument("tx_id", help="Transaction id.")
    challenge_open.add_argument("--challenger", default="fisherman", help="Human-readable challenger id.")
    challenge_open.add_argument("--reason", default="state_transition_dispute", help="Challenge reason.")

    challenge_respond = subparsers.add_parser("challenge-respond", help="Respond to an open challenge.")
    challenge_respond.add_argument("tx_id", help="Transaction id.")
    challenge_respond.add_argument("--responder", default="sequencer", help="Human-readable responder id.")

    challenge_status = subparsers.add_parser("challenge-status", help="Inspect the current challenge session.")
    challenge_status.add_argument("tx_id", help="Transaction id.")

    challenge_recover = subparsers.add_parser("challenge-recover", help="Recover a timed-out challenge session.")
    challenge_recover.add_argument("tx_id", help="Transaction id.")
    challenge_recover.add_argument("--operator", default="watchdog", help="Human-readable recovery operator id.")

    challenge_resolve = subparsers.add_parser("challenge-resolve", help="Resolve an open/responded challenge.")
    challenge_resolve.add_argument("tx_id", help="Transaction id.")
    challenge_resolve.add_argument("--arbitrator", default="onchain-replay", help="Human-readable arbitrator id.")

    challenge_step = subparsers.add_parser("challenge-step", help="Run one bisection round on dispute range.")
    challenge_step.add_argument("tx_id", help="Transaction id.")

    challenge_replay = subparsers.add_parser("challenge-replay", help="Run single-step replay after narrowing.")
    challenge_replay.add_argument("tx_id", help="Transaction id.")

    subparsers.add_parser("finalize", help="Finalize pending transactions whose dispute window expired.")

    spot_check = subparsers.add_parser("spot-check", help="Trigger a pseudo-ZK spot check.")
    spot_check.add_argument("tx_id", help="Transaction id.")
    spot_check.add_argument(
        "--force",
        action="store_true",
        help="Force the check even if the random trigger would skip it.",
    )

    tamper = subparsers.add_parser("tamper", help="Demo-only helper to mutate a stored response.")
    tamper.add_argument("tx_id", help="Transaction id.")
    tamper.add_argument("response", help="Replacement response to store on chain.")

    da_show = subparsers.add_parser("da-show", help="Show full payload from DA by tx id.")
    da_show.add_argument("tx_id", help="Transaction id.")

    estimate = subparsers.add_parser("estimate-cost", help="Estimate full vs compact submission size.")
    estimate.add_argument("tx_id", help="Transaction id.")

    estimate_strategies = subparsers.add_parser(
        "estimate-strategies",
        help="Estimate byte and gas costs for full onchain vs DA strategies.",
    )
    estimate_strategies.add_argument("tx_id", help="Transaction id.")

    return parser


def dump_json(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(
        chain_path=args.chain_file,
        model_backend=args.backend,
        model_name=args.model_name,
        dispute_window_seconds=args.dispute_window,
        challenge_timeout_seconds=args.challenge_timeout,
        max_bisection_rounds=args.max_bisection_rounds,
        spot_check_probability=args.spot_check_probability,
    )
    demo = RollupDemo(config)

    try:
        if args.command == "submit":
            dump_json(
                demo.submit(
                    args.prompt,
                    forced_response=args.force_response,
                )
            )
            return 0
        if args.command == "list":
            dump_json(demo.list_transactions())
            return 0
        if args.command == "show":
            dump_json(demo.get_transaction(args.tx_id))
            return 0
        if args.command == "verify":
            dump_json(demo.verify(args.tx_id))
            return 0
        if args.command == "challenge":
            dump_json(demo.challenge(args.tx_id, challenger=args.challenger))
            return 0
        if args.command == "challenge-open":
            dump_json(
                demo.challenge_open(
                    args.tx_id,
                    challenger=args.challenger,
                    reason=args.reason,
                )
            )
            return 0
        if args.command == "challenge-respond":
            dump_json(demo.challenge_respond(args.tx_id, responder=args.responder))
            return 0
        if args.command == "challenge-status":
            dump_json(demo.challenge_status(args.tx_id))
            return 0
        if args.command == "challenge-recover":
            dump_json(demo.challenge_recover(args.tx_id, operator=args.operator))
            return 0
        if args.command == "challenge-resolve":
            dump_json(demo.challenge_resolve(args.tx_id, arbitrator=args.arbitrator))
            return 0
        if args.command == "challenge-step":
            dump_json(demo.challenge_step(args.tx_id))
            return 0
        if args.command == "challenge-replay":
            dump_json(demo.challenge_replay(args.tx_id))
            return 0
        if args.command == "finalize":
            dump_json({"finalized": demo.finalize_expired()})
            return 0
        if args.command == "spot-check":
            dump_json(demo.run_spot_check(args.tx_id, force=args.force))
            return 0
        if args.command == "tamper":
            dump_json(demo.tamper_response(args.tx_id, args.response))
            return 0
        if args.command == "da-show":
            dump_json(demo.get_da_entry(args.tx_id))
            return 0
        if args.command == "estimate-cost":
            dump_json(demo.estimate_submission_cost(args.tx_id))
            return 0
        if args.command == "estimate-strategies":
            dump_json(demo.estimate_strategy_costs(args.tx_id))
            return 0
    except Exception as exc:  # pragma: no cover - exercised by CLI usage
        print("error: {0}".format(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 1
