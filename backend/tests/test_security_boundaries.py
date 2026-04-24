"""Security-boundary tests mapped 1:1 to SPEC §10.

Self-contained on purpose. A reviewer can open this file, read SPEC.md
§10 next to it, and see one test per bullet — both for *defended*
threats (§10.1) and *documented limits* (§10.2, §10.3). If a test here
changes behavior, the SPEC boundary moved and SPEC.md needs an update
first.
"""

from datetime import UTC, datetime

from agentrooms.crypto import canonical_json, generate_keypair, sign, verify


def _hdr(pk: bytes) -> dict[str, str]:
    return {"X-Agent-Pubkey": pk.hex()}


def _sign_create(sk, *, topic, invitees, max_turns=40, ttl_hours=24):
    return sign(
        sk,
        canonical_json(
            {
                "topic": topic,
                "invite_pubkeys": invitees,
                "max_turns": max_turns,
                "ttl_hours": ttl_hours,
            }
        ),
    ).hex()


def _sign_accept(sk, *, room_id, agent_pk):
    return sign(
        sk, canonical_json({"room_id": str(room_id), "agent_pubkey": agent_pk.hex()})
    ).hex()


def _sign_close(sk, *, room_id, summary):
    return sign(
        sk, canonical_json({"room_id": str(room_id), "summary": summary})
    ).hex()


def _sign_message(sk, *, room_id, turn_n, author_pk, body, created_at):
    return sign(
        sk,
        canonical_json(
            {
                "room_id": str(room_id),
                "turn_n": turn_n,
                "author_pubkey": author_pk.hex(),
                "body": body,
                "created_at": created_at.isoformat(),
            }
        ),
    ).hex()


async def _two_agent_room(client):
    sk_a, pk_a = generate_keypair()
    sk_b, pk_b = generate_keypair()
    body = {
        "topic": "t",
        "invite_pubkeys": [pk_b.hex()],
        "max_turns": 40,
        "ttl_hours": 24,
        "sig": _sign_create(sk_a, topic="t", invitees=[pk_b.hex()]),
    }
    r = await client.post("/v1/rooms", json=body, headers=_hdr(pk_a))
    assert r.status_code == 200
    return sk_a, pk_a, sk_b, pk_b, r.json()["room_id"]


# ---------------------------------------------------------------------------
# §10.1 — what v0.1 defends
# ---------------------------------------------------------------------------


async def test_10_1_tampering_at_rest_is_detectable(client):
    """Stored messages carry the author's signature. A reader can re-compute
    canonical bytes and re-verify — hub compromise cannot silently rewrite
    history without invalidating stored sigs."""
    sk_a, pk_a, sk_b, pk_b, room_id = await _two_agent_room(client)

    r = await client.post(
        f"/v1/rooms/{room_id}/accept",
        json={"sig": _sign_accept(sk_b, room_id=room_id, agent_pk=pk_b)},
        headers=_hdr(pk_b),
    )
    assert r.status_code == 200

    created_at = datetime.now(UTC)
    msg_sig = _sign_message(
        sk_a, room_id=room_id, turn_n=1, author_pk=pk_a, body="hi", created_at=created_at
    )
    r = await client.post(
        f"/v1/rooms/{room_id}/messages",
        json={"turn_n": 1, "body": "hi", "created_at": created_at.isoformat(), "sig": msg_sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 200

    poll = (await client.get(f"/v1/rooms/{room_id}/messages", headers=_hdr(pk_a))).json()
    m = poll["messages"][0]
    reconstructed = canonical_json(
        {
            "room_id": m["room_id"],
            "turn_n": m["turn_n"],
            "author_pubkey": m["author_pubkey"],
            "body": m["body"],
            "created_at": m["created_at"],
        }
    )
    assert verify(bytes.fromhex(m["author_pubkey"]), reconstructed, bytes.fromhex(m["sig"])), (
        "stored message signature must re-verify against canonically-reconstructed bytes"
    )


# ---------------------------------------------------------------------------
# §10.2 — documented v0.1 limits (these are not bugs; they are boundaries)
# ---------------------------------------------------------------------------


async def test_10_2_read_authn_by_claim_only(client):
    """GET endpoints accept any caller whose pubkey is in the participants list.
    There is no signature on reads, so knowing a participant pubkey + room_id
    is sufficient to read. v0.1 treats room_id as a capability token."""
    _, pk_a, _, pk_b, room_id = await _two_agent_room(client)

    # A reader holding neither SK can read the room just by presenting Bob's
    # pubkey in the header. This is the documented limit.
    r = await client.get(f"/v1/rooms/{room_id}", headers=_hdr(pk_b))
    assert r.status_code == 200, r.text
    assert r.json()["room_id"] == room_id

    # An unrelated pubkey is still rejected — membership is checked.
    _, pk_outsider = generate_keypair()
    r = await client.get(f"/v1/rooms/{room_id}", headers=_hdr(pk_outsider))
    assert r.status_code == 403


async def test_10_2_create_room_replay_creates_duplicate(client):
    """POST /v1/rooms has no nonce or timestamp in its signed payload.
    Re-submitting the identical signed body creates a second room.
    Mitigation today: TLS. Phase-2: add freshness / dedup."""
    sk_a, pk_a = generate_keypair()
    body = {
        "topic": "t",
        "invite_pubkeys": [],
        "max_turns": 40,
        "ttl_hours": 24,
        "sig": _sign_create(sk_a, topic="t", invitees=[]),
    }
    r1 = await client.post("/v1/rooms", json=body, headers=_hdr(pk_a))
    r2 = await client.post("/v1/rooms", json=body, headers=_hdr(pk_a))
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["room_id"] != r2.json()["room_id"], (
        "v0.1 limit: identical signed create_room payloads produce two distinct rooms"
    )


async def test_10_2_accept_replay_is_idempotent(client):
    """Accept has no nonce either, but replaying it is a no-op: the first
    accept sets accepted_at; subsequent identical POSTs return the same
    accepted_at without rotating the stored signature."""
    _, _, sk_b, pk_b, room_id = await _two_agent_room(client)
    accept_sig = _sign_accept(sk_b, room_id=room_id, agent_pk=pk_b)

    r1 = await client.post(
        f"/v1/rooms/{room_id}/accept", json={"sig": accept_sig}, headers=_hdr(pk_b)
    )
    r2 = await client.post(
        f"/v1/rooms/{room_id}/accept", json={"sig": accept_sig}, headers=_hdr(pk_b)
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["accepted_at"] == r2.json()["accepted_at"], (
        "replayed accept must be a no-op and must not rotate accepted_at"
    )


async def test_10_2_double_close_is_rejected(client):
    """Close has no nonce, but replaying it hits the already-closed guard
    (HTTP 409). So close-replay is functionally harmless even without
    cryptographic replay protection."""
    sk_a, pk_a, _, _, room_id = await _two_agent_room(client)
    close_body = {"summary": None, "sig": _sign_close(sk_a, room_id=room_id, summary=None)}

    r1 = await client.post(f"/v1/rooms/{room_id}/close", json=close_body, headers=_hdr(pk_a))
    r2 = await client.post(f"/v1/rooms/{room_id}/close", json=close_body, headers=_hdr(pk_a))
    assert r1.status_code == 200
    assert r2.status_code == 409, "second close must be rejected with room_closed"


# ---------------------------------------------------------------------------
# §10.3 — signature domain separation
# ---------------------------------------------------------------------------


async def test_10_3_accept_sig_does_not_verify_as_close(client):
    """Every signed payload has a unique key set (§10.3 + Appendix A), so a
    signature produced for one operation cannot be replayed as another. The
    close-sig verify uses canonical({'room_id', 'summary': null}); an
    accept-sig produced over canonical({'room_id', 'agent_pubkey'}) has
    different bytes and therefore fails verify."""
    sk_a, pk_a, _, _, room_id = await _two_agent_room(client)
    accept_sig = _sign_accept(sk_a, room_id=room_id, agent_pk=pk_a)

    r = await client.post(
        f"/v1/rooms/{room_id}/close",
        json={"summary": None, "sig": accept_sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 401, "close must not accept a signature produced for accept"
