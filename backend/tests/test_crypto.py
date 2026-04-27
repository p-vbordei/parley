import pytest

from parley.crypto import (
    canonical_json,
    generate_keypair,
    pubkey_to_str,
    sign,
    str_to_pubkey,
    verify,
)


def test_canonical_sorts_keys():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_canonical_no_whitespace():
    assert b" " not in canonical_json({"x": 1, "y": [1, 2, 3]})


def test_canonical_utf8_no_ascii_escape():
    assert "ă".encode() in canonical_json({"name": "ănă"})


def test_canonical_nested_deterministic():
    assert canonical_json({"x": [3, 1, 2]}) == b'{"x":[3,1,2]}'


def test_canonical_is_idempotent():
    """Identical input always yields identical canonical bytes (Task 2 acceptance)."""
    obj = {"room_id": "abc", "turn_n": 3, "body": "hello ănă", "nested": {"z": 1, "a": [2, 1]}}
    assert canonical_json(obj) == canonical_json(obj)
    assert canonical_json(dict(reversed(list(obj.items())))) == canonical_json(obj)


def test_generate_keypair_lengths():
    sk, pk = generate_keypair()
    assert len(sk) == 32
    assert len(pk) == 32


def test_sign_verify_roundtrip():
    sk, pk = generate_keypair()
    msg = b"hello parley"
    sig = sign(sk, msg)
    assert len(sig) == 64
    assert verify(pk, msg, sig) is True


def test_verify_rejects_tampered_message():
    sk, pk = generate_keypair()
    sig = sign(sk, b"original")
    assert verify(pk, b"tampered", sig) is False


def test_verify_rejects_bad_signature():
    _, pk = generate_keypair()
    assert verify(pk, b"msg", b"\x00" * 64) is False


def test_verify_rejects_wrong_pubkey():
    sk, _ = generate_keypair()
    _, other_pk = generate_keypair()
    sig = sign(sk, b"msg")
    assert verify(other_pk, b"msg", sig) is False


def test_pubkey_string_roundtrip():
    _, pk = generate_keypair()
    s = pubkey_to_str(pk)
    assert s.startswith("ed25519:")
    assert str_to_pubkey(s) == pk


def test_str_to_pubkey_rejects_bad_prefix():
    with pytest.raises(ValueError):
        str_to_pubkey("rsa:abcd")


def test_sign_canonical_payload():
    """End-to-end: canonicalize a structured payload, sign, verify — the actual usage pattern."""
    sk, pk = generate_keypair()
    payload = {"room_id": "r1", "turn_n": 5, "body": "ce zici?", "author": pubkey_to_str(pk)}
    msg = canonical_json(payload)
    sig = sign(sk, msg)
    # Re-canonicalize from a re-ordered dict — must produce same bytes, sig still valid.
    payload_reordered = {k: payload[k] for k in reversed(list(payload))}
    assert verify(pk, canonical_json(payload_reordered), sig) is True
