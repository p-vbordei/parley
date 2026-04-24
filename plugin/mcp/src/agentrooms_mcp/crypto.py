"""Inlined to keep the plugin standalone — no shared lib with the backend.

Mirrors backend/src/agentrooms/crypto/{canonical,keys}.py byte-for-byte.
If a third client appears, extract `agentrooms-crypto` as its own package."""

import json
from typing import Any

from nacl import exceptions, signing


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sign(sk_bytes: bytes, message: bytes) -> bytes:
    sk = signing.SigningKey(sk_bytes)
    return sk.sign(message).signature


def verify(pk_bytes: bytes, message: bytes, signature: bytes) -> bool:
    try:
        signing.VerifyKey(pk_bytes).verify(message, signature)
        return True
    except (exceptions.BadSignatureError, ValueError):
        return False
