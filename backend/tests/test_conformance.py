"""Runs conformance/vectors/*.json through the backend crypto module.

The conformance runner under conformance/ is intentionally standalone. This
test closes the loop — it proves the *backend* produces the same bytes and
signatures as the committed vectors, so the runner can't silently drift
from what the service actually signs.
"""

import json
from pathlib import Path

from agentrooms.crypto import canonical_json
from agentrooms.crypto.keys import sign, verify

VECTORS = Path(__file__).resolve().parents[2] / "conformance" / "vectors"


def test_canonical_json_matches_vectors() -> None:
    for v in json.loads((VECTORS / "canonical_json.json").read_text()):
        assert canonical_json(v["input"]).decode("utf-8") == v["expected_bytes_utf8"], v["name"]


def test_signatures_match_vectors() -> None:
    for v in json.loads((VECTORS / "signatures.json").read_text()):
        cbytes = canonical_json(v["payload"])
        assert cbytes.decode("utf-8") == v["canonical_bytes_utf8"], v["name"]
        sig = sign(bytes.fromhex(v["sk_hex"]), cbytes)
        assert sig.hex() == v["expected_sig_hex"], v["name"]
        assert verify(bytes.fromhex(v["pk_hex"]), cbytes, sig), v["name"]


def test_mutation_vectors_behave() -> None:
    for v in json.loads((VECTORS / "mutation.json").read_text()):
        cbytes = v["canonical_bytes_utf8"].encode("utf-8")
        got = verify(bytes.fromhex(v["pk_hex"]), cbytes, bytes.fromhex(v["sig_hex"]))
        assert got is v["must_verify"], v["name"]
