import hashlib
import json


def sha256_hex(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
