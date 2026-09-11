import json
from urllib import error, request

from .utils import canonical_json, sha256_hex


class ModelError(RuntimeError):
    """Raised when the selected inference backend fails."""


class DeterministicDemoModel:
    def __init__(self, model_name):
        self.model_name = model_name

    def infer(self, prompt):
        normalized = " ".join(prompt.strip().split())
        if not normalized:
            normalized = "(empty prompt)"
        digest = sha256_hex(normalized)
        focus_words = normalized.split()[:8]
        focus = ", ".join(focus_words) if focus_words else "(none)"
        confidence = int(digest[12:20], 16) % 1000
        return "\n".join(
            [
                "DEMO_INFERENCE",
                "answer_id={0}".format(digest[:12]),
                "focus={0}".format(focus),
                "confidence_seed={0}".format(confidence),
            ]
        )

    def fingerprint(self):
        payload = {
            "backend": "mock",
            "model_name": self.model_name,
            "version": "v1",
        }
        return sha256_hex(canonical_json(payload))


class OllamaDeterministicModel:
    def __init__(self, base_url, model_name):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def infer(self, prompt):
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "seed": 0,
                "temperature": 0,
                "top_p": 1,
            },
        }
        raw_body = canonical_json(payload).encode("utf-8")
        http_request = request.Request(
            url="{0}/api/generate".format(self.base_url),
            data=raw_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=30) as response:
                raw_response = response.read().decode("utf-8")
        except (error.HTTPError, error.URLError) as exc:
            raise ModelError("ollama request failed: {0}".format(exc)) from exc
        try:
            decoded = json.loads(raw_response)
            return decoded["response"].strip()
        except (KeyError, ValueError) as exc:
            raise ModelError("invalid ollama response: {0}".format(raw_response)) from exc

    def fingerprint(self):
        payload = {
            "backend": "ollama",
            "base_url": self.base_url,
            "model_name": self.model_name,
            "temperature": 0,
            "seed": 0,
            "top_p": 1,
        }
        return sha256_hex(canonical_json(payload))


def build_model(config):
    if config.model_backend == "mock":
        return DeterministicDemoModel(config.model_name)
    if config.model_backend == "ollama":
        return OllamaDeterministicModel(config.ollama_base_url, config.model_name)
    raise ModelError("unsupported model backend: {0}".format(config.model_backend))
