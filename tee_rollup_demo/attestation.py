import hmac
import secrets

from .utils import canonical_json, sha256_hex


def build_attestation_message(prompt, response, nonce, mrenclave):
    return {
        "input_hash": sha256_hex(prompt),
        "output_hash": sha256_hex(response),
        "nonce": nonce,
        "mrenclave": mrenclave,
    }


def create_attestation(prompt, response, mrenclave, secret, nonce=None):
    final_nonce = nonce or secrets.token_hex(16)
    message = build_attestation_message(prompt, response, final_nonce, mrenclave)
    signature = hmac.new(
        secret.encode("utf-8"),
        canonical_json(message).encode("utf-8"),
        "sha256",
    ).hexdigest()
    message["signature"] = signature
    message["scheme"] = "simulated-hmac-sha256"
    return message


def verify_attestation(attestation, prompt, response, secret):
    expected_message = build_attestation_message(
        prompt,
        response,
        attestation["nonce"],
        attestation["mrenclave"],
    )
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        canonical_json(expected_message).encode("utf-8"),
        "sha256",
    ).hexdigest()
    return hmac.compare_digest(attestation["signature"], expected_signature)
