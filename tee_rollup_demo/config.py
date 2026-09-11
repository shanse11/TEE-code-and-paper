from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class DemoConfig:
    chain_path: Path
    da_path: Path
    dispute_window_seconds: int = 60
    challenge_timeout_seconds: int = 30
    max_bisection_rounds: int = 8
    spot_check_probability: float = 0.01
    tee_secret: str = "demo-tee-secret"
    model_backend: str = "mock"
    model_name: str = "demo-deterministic-v1"
    ollama_base_url: str = "http://127.0.0.1:11434"


def load_config(
    chain_path=None,
    model_backend=None,
    model_name=None,
    dispute_window_seconds=None,
    challenge_timeout_seconds=None,
    max_bisection_rounds=None,
    spot_check_probability=None,
):
    default_chain = Path.cwd() / "data" / "chain.json"
    default_da = Path.cwd() / "data" / "da.json"
    return DemoConfig(
        chain_path=Path(chain_path or os.getenv("CHAIN_FILE", default_chain)),
        da_path=Path(os.getenv("DA_FILE", default_da)),
        dispute_window_seconds=int(
            dispute_window_seconds
            if dispute_window_seconds is not None
            else os.getenv("DISPUTE_WINDOW_SECONDS", 60)
        ),
        challenge_timeout_seconds=int(
            challenge_timeout_seconds
            if challenge_timeout_seconds is not None
            else os.getenv("CHALLENGE_TIMEOUT_SECONDS", 30)
        ),
        max_bisection_rounds=int(
            max_bisection_rounds
            if max_bisection_rounds is not None
            else os.getenv("MAX_BISECTION_ROUNDS", 8)
        ),
        spot_check_probability=float(
            spot_check_probability
            if spot_check_probability is not None
            else os.getenv("SPOT_CHECK_PROBABILITY", 0.01)
        ),
        tee_secret=os.getenv("TEE_SECRET", "demo-tee-secret"),
        model_backend=(model_backend or os.getenv("MODEL_BACKEND", "mock")).lower(),
        model_name=model_name or os.getenv("MODEL_NAME", "demo-deterministic-v1"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    )
