#!/usr/bin/env python3
"""Conformance vectors for Agent Rooms SPEC v0.1.0.

Two modes:

  python conformance/run.py              # validate reference impl against vectors
  python conformance/run.py --generate   # regenerate vectors/*.json from reference

Intentionally standalone: depends on pynacl + stdlib only. A non-Python
implementation should write its own runner against the same vector files.

Vectors exercise three byte-level invariants:
  - canonical_json : input → expected UTF-8 bytes
  - signatures     : fixed SK + canonical bytes → expected signature
  - mutation       : valid (pk, bytes, sig) + tampered variants that must fail
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

from nacl import exceptions, signing

VECTORS_DIR = Path(__file__).parent / "vectors"

# Fixed test keypairs. Ed25519 derivation is deterministic.
SK1_HEX = "01" * 32
SK2_HEX = "02" * 32


def canonical_json(obj: Any) -> bytes:
    """Reference canonical encoding — SPEC §4."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sign(sk_hex: str, msg: bytes) -> str:
    sk = signing.SigningKey(bytes.fromhex(sk_hex))
    return sk.sign(msg).signature.hex()


def pk_for(sk_hex: str) -> str:
    sk = signing.SigningKey(bytes.fromhex(sk_hex))
    return bytes(sk.verify_key).hex()


def verify(pk_hex: str, msg: bytes, sig_hex: str) -> bool:
    try:
        signing.VerifyKey(bytes.fromhex(pk_hex)).verify(msg, bytes.fromhex(sig_hex))
        return True
    except (exceptions.BadSignatureError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Canonical JSON vectors
# ---------------------------------------------------------------------------

FIXED_TS = "2026-04-24T12:00:00+00:00"

CANONICAL_INPUTS: list[tuple[str, Any]] = [
    ("empty_object", {}),
    ("empty_array", []),
    ("sorts_keys", {"b": 2, "a": 1}),
    ("sorts_keys_nested", {"z": {"b": 2, "a": 1}, "y": 0}),
    ("no_whitespace", {"key": "value", "n": 1}),
    ("null_value", {"summary": None, "room_id": "r1"}),
    ("booleans", {"ok": True, "done": False}),
    ("array_order_preserved", {"xs": [3, 1, 2]}),
    ("utf8_literal_not_escaped", {"topic": "café — 日本語"}),
    ("string_escapes_standard", {"s": 'line1\nline2\t"quoted"'}),
    (
        "create_room_payload",
        {
            "topic": "auth-ui integration",
            "invite_pubkeys": [pk_for(SK2_HEX)],
            "max_turns": 40,
            "ttl_hours": 24,
            "created_at": FIXED_TS,
        },
    ),
    (
        "accept_payload",
        {
            "room_id": "00000000-0000-0000-0000-000000000001",
            "agent_pubkey": pk_for(SK2_HEX),
            "created_at": FIXED_TS,
        },
    ),
    (
        "close_payload_with_summary",
        {
            "room_id": "00000000-0000-0000-0000-000000000001",
            "summary": "shipped.",
            "created_at": FIXED_TS,
        },
    ),
    (
        "close_payload_null_summary",
        {
            "room_id": "00000000-0000-0000-0000-000000000001",
            "summary": None,
            "created_at": FIXED_TS,
        },
    ),
    (
        "post_message_payload",
        {
            "room_id": "00000000-0000-0000-0000-000000000001",
            "turn_n": 1,
            "author_pubkey": pk_for(SK1_HEX),
            "body": "what's the timeline?",
            "created_at": FIXED_TS,
        },
    ),
]


def build_canonical_vectors() -> list[dict[str, Any]]:
    vectors = []
    for name, obj in CANONICAL_INPUTS:
        out = canonical_json(obj)
        vectors.append(
            {
                "name": name,
                "input": obj,
                "expected_bytes_utf8": out.decode("utf-8"),
                "expected_bytes_b64": base64.b64encode(out).decode("ascii"),
            }
        )
    return vectors


# ---------------------------------------------------------------------------
# Signature vectors
# ---------------------------------------------------------------------------

SIGNATURE_INPUTS: list[tuple[str, str, Any]] = [
    (
        "create_room_sig_sk1",
        SK1_HEX,
        {
            "topic": "auth-ui integration",
            "invite_pubkeys": [pk_for(SK2_HEX)],
            "max_turns": 40,
            "ttl_hours": 24,
            "created_at": FIXED_TS,
        },
    ),
    (
        "accept_sig_sk2",
        SK2_HEX,
        {
            "room_id": "00000000-0000-0000-0000-000000000001",
            "agent_pubkey": pk_for(SK2_HEX),
            "created_at": FIXED_TS,
        },
    ),
    (
        "close_sig_sk1",
        SK1_HEX,
        {
            "room_id": "00000000-0000-0000-0000-000000000001",
            "summary": "shipped.",
            "created_at": FIXED_TS,
        },
    ),
    (
        "post_message_sig_sk1",
        SK1_HEX,
        {
            "room_id": "00000000-0000-0000-0000-000000000001",
            "turn_n": 1,
            "author_pubkey": pk_for(SK1_HEX),
            "body": "what's the timeline?",
            "created_at": FIXED_TS,
        },
    ),
]


def build_signature_vectors() -> list[dict[str, Any]]:
    vectors = []
    for name, sk_hex, payload in SIGNATURE_INPUTS:
        cbytes = canonical_json(payload)
        vectors.append(
            {
                "name": name,
                "sk_hex": sk_hex,
                "pk_hex": pk_for(sk_hex),
                "payload": payload,
                "canonical_bytes_utf8": cbytes.decode("utf-8"),
                "expected_sig_hex": sign(sk_hex, cbytes),
            }
        )
    return vectors


# ---------------------------------------------------------------------------
# Mutation vectors
# ---------------------------------------------------------------------------


def build_mutation_vectors() -> list[dict[str, Any]]:
    """Each vector is a valid signature paired with a must-fail tamper."""
    base_payload = {
        "room_id": "00000000-0000-0000-0000-000000000001",
        "turn_n": 1,
        "author_pubkey": pk_for(SK1_HEX),
        "body": "what's the timeline?",
        "created_at": "2026-04-24T12:00:00+00:00",
    }
    cbytes = canonical_json(base_payload)
    pk_hex = pk_for(SK1_HEX)
    good_sig = sign(SK1_HEX, cbytes)

    tampered_body_payload = {**base_payload, "body": "what's the timeline!"}  # '?' -> '!'
    tampered_body_bytes = canonical_json(tampered_body_payload)

    tampered_turn_payload = {**base_payload, "turn_n": 2}
    tampered_turn_bytes = canonical_json(tampered_turn_payload)

    flipped_sig_hex = ("01" if good_sig[:2] != "01" else "02") + good_sig[2:]
    truncated_sig_hex = good_sig[: len(good_sig) - 2]

    # Non-canonical wire bytes (reordered keys) produce the same canonical form
    # when re-canonicalized — so the signature still verifies against the
    # CANONICAL bytes. This is a feature, not a bug. Vector documents it.
    noncanonical_wire = json.dumps(
        base_payload, sort_keys=False, separators=(", ", ": ")
    ).encode("utf-8")

    return [
        {
            "name": "valid_baseline",
            "pk_hex": pk_hex,
            "canonical_bytes_utf8": cbytes.decode("utf-8"),
            "sig_hex": good_sig,
            "must_verify": True,
            "note": "the known-good signature must verify",
        },
        {
            "name": "flipped_first_byte_of_sig",
            "pk_hex": pk_hex,
            "canonical_bytes_utf8": cbytes.decode("utf-8"),
            "sig_hex": flipped_sig_hex,
            "must_verify": False,
            "note": "any bit-flip in the 64-byte signature must fail",
        },
        {
            "name": "truncated_sig",
            "pk_hex": pk_hex,
            "canonical_bytes_utf8": cbytes.decode("utf-8"),
            "sig_hex": truncated_sig_hex,
            "must_verify": False,
            "note": "sig shorter than 64 bytes must fail",
        },
        {
            "name": "body_mutated_one_char",
            "pk_hex": pk_hex,
            "canonical_bytes_utf8": tampered_body_bytes.decode("utf-8"),
            "sig_hex": good_sig,
            "must_verify": False,
            "note": "any change to the canonical body invalidates the signature",
        },
        {
            "name": "turn_n_bumped",
            "pk_hex": pk_hex,
            "canonical_bytes_utf8": tampered_turn_bytes.decode("utf-8"),
            "sig_hex": good_sig,
            "must_verify": False,
            "note": "turn_n is inside the signed payload; bumping it invalidates the sig",
        },
        {
            "name": "wire_reordered_keys_but_canonical_identical",
            "pk_hex": pk_hex,
            "non_canonical_wire_utf8": noncanonical_wire.decode("utf-8"),
            "canonical_bytes_utf8": cbytes.decode("utf-8"),
            "sig_hex": good_sig,
            "must_verify": True,
            "note": (
                "wire bytes may arrive in any key order / whitespace; signature "
                "verifies against the CANONICAL bytes, which are identical."
            ),
        },
    ]


# ---------------------------------------------------------------------------
# Validate / generate
# ---------------------------------------------------------------------------


def validate() -> int:
    failures: list[str] = []

    cv = json.loads((VECTORS_DIR / "canonical_json.json").read_text())
    for v in cv:
        actual = canonical_json(v["input"]).decode("utf-8")
        if actual != v["expected_bytes_utf8"]:
            failures.append(
                f"canonical_json[{v['name']}] mismatch: "
                f"expected {v['expected_bytes_utf8']!r}, got {actual!r}"
            )

    sv = json.loads((VECTORS_DIR / "signatures.json").read_text())
    for v in sv:
        cbytes = canonical_json(v["payload"])
        if cbytes.decode("utf-8") != v["canonical_bytes_utf8"]:
            failures.append(f"signatures[{v['name']}] canonical bytes drifted")
            continue
        actual_sig = sign(v["sk_hex"], cbytes)
        if actual_sig != v["expected_sig_hex"]:
            failures.append(
                f"signatures[{v['name']}] sig mismatch: "
                f"expected {v['expected_sig_hex']}, got {actual_sig}"
            )
        if pk_for(v["sk_hex"]) != v["pk_hex"]:
            failures.append(f"signatures[{v['name']}] pk derivation drifted")
        if not verify(v["pk_hex"], cbytes, actual_sig):
            failures.append(f"signatures[{v['name']}] self-verify failed")

    mv = json.loads((VECTORS_DIR / "mutation.json").read_text())
    for v in mv:
        cbytes = v["canonical_bytes_utf8"].encode("utf-8")
        got = verify(v["pk_hex"], cbytes, v["sig_hex"])
        if got != v["must_verify"]:
            failures.append(
                f"mutation[{v['name']}] expected verify={v['must_verify']}, got {got}"
            )

    if failures:
        print("FAIL:", len(failures), "failures", file=sys.stderr)
        for f in failures:
            print("  -", f, file=sys.stderr)
        return 1

    total = len(cv) + len(sv) + len(mv)
    print(f"OK: {total} vectors passed "
          f"(canonical_json={len(cv)}, signatures={len(sv)}, mutation={len(mv)})")
    return 0


def generate() -> int:
    VECTORS_DIR.mkdir(exist_ok=True)
    for name, builder in [
        ("canonical_json", build_canonical_vectors),
        ("signatures", build_signature_vectors),
        ("mutation", build_mutation_vectors),
    ]:
        out = VECTORS_DIR / f"{name}.json"
        out.write_text(json.dumps(builder(), indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    args = ap.parse_args()
    sys.exit(generate() if args.generate else validate())
