"""Edge cases discovered in the v0.2 debugging round.

Each test pins a specific edge that produced the wrong status code or
(worse) a 500 in v0.2.0. After the fixes:
  - Naive datetimes are rejected at the schema layer (422), not blown up
    inside is_timestamp_fresh (500).
  - Duplicate pubkeys in invite_pubkeys are silently deduped (per SPEC §6.1).
  - close and accept on a TTL-expired or already-closed room return 409,
    in line with SPEC §8.1 ("any write after ttl_until returns room_closed").
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import update

from parley.crypto import canonical_json, generate_keypair, sign
from parley.models import Room


def _hdr(pk: bytes) -> dict[str, str]:
    return {"X-Agent-Pubkey": pk.hex()}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sign_create(sk, *, topic, invitees, max_turns=40, ttl_hours=24, created_at):
    return sign(
        sk,
        canonical_json(
            {
                "topic": topic,
                "invite_pubkeys": invitees,
                "max_turns": max_turns,
                "ttl_hours": ttl_hours,
                "created_at": created_at,
            }
        ),
    ).hex()


def _sign_accept(sk, *, room_id, agent_pk, created_at):
    return sign(
        sk,
        canonical_json(
            {"room_id": str(room_id), "agent_pubkey": agent_pk.hex(), "created_at": created_at}
        ),
    ).hex()


def _sign_close(sk, *, room_id, summary, created_at):
    return sign(
        sk,
        canonical_json(
            {"room_id": str(room_id), "summary": summary, "created_at": created_at}
        ),
    ).hex()


async def _create_room_simple(client, sk_a, pk_a, *, invitees=None, ttl_hours=24):
    invitees = invitees or []
    ts = _now_iso()
    body = {
        "topic": "t",
        "invite_pubkeys": invitees,
        "max_turns": 40,
        "ttl_hours": ttl_hours,
        "created_at": ts,
        "sig": _sign_create(sk_a, topic="t", invitees=invitees, ttl_hours=ttl_hours, created_at=ts),
    }
    r = await client.post("/v1/rooms", json=body, headers=_hdr(pk_a))
    assert r.status_code == 200, r.text
    return r.json()["room_id"]


async def _force_ttl_expired(engine, room_id: str) -> None:
    """Push ttl_until into the past via a direct DB update."""
    async with engine.begin() as conn:
        await conn.execute(
            update(Room)
            .where(Room.id == UUID(room_id))
            .values(ttl_until=datetime.now(UTC) - timedelta(hours=1))
        )


# ---------------------------------------------------------------------------
# Bug: naive datetime crashes the freshness check with TypeError → HTTP 500
# Fix: schemas reject naive datetimes at the request layer (422)
# ---------------------------------------------------------------------------


async def test_naive_created_at_in_post_message_is_rejected_4xx(client):
    """A client that sends a tz-naive ISO 8601 timestamp must get a clean 4xx,
    not a 500 from `(ts - now).total_seconds()` blowing up."""
    sk_a, pk_a = generate_keypair()
    room_id = await _create_room_simple(client, sk_a, pk_a)

    # naive ISO — no Z, no offset
    naive = "2026-04-25T12:00:00"
    sig = sign(
        sk_a,
        canonical_json(
            {
                "room_id": room_id,
                "turn_n": 1,
                "author_pubkey": pk_a.hex(),
                "body": "x",
                "created_at": naive,
            }
        ),
    ).hex()
    r = await client.post(
        f"/v1/rooms/{room_id}/messages",
        json={"turn_n": 1, "body": "x", "created_at": naive, "sig": sig},
        headers=_hdr(pk_a),
    )
    assert 400 <= r.status_code < 500, (
        f"naive datetime must produce a 4xx, got {r.status_code}: {r.text[:200]}"
    )


async def test_naive_created_at_in_create_room_is_rejected_4xx(client):
    sk_a, pk_a = generate_keypair()
    naive = "2026-04-25T12:00:00"
    sig = _sign_create(sk_a, topic="t", invitees=[], created_at=naive)
    r = await client.post(
        "/v1/rooms",
        json={
            "topic": "t",
            "invite_pubkeys": [],
            "max_turns": 40,
            "ttl_hours": 24,
            "created_at": naive,
            "sig": sig,
        },
        headers=_hdr(pk_a),
    )
    assert 400 <= r.status_code < 500, r.text[:200]


# ---------------------------------------------------------------------------
# Bug: duplicate invitees produced a DB IntegrityError → HTTP 500
# Fix: services/rooms.create_room silently dedupes
# ---------------------------------------------------------------------------


async def test_duplicate_invitee_pubkeys_silently_deduped(client):
    sk_a, pk_a = generate_keypair()
    _, pk_b = generate_keypair()

    ts = _now_iso()
    payload = {
        "topic": "t",
        "invite_pubkeys": [pk_b.hex(), pk_b.hex()],  # SAME pubkey twice
        "max_turns": 40,
        "ttl_hours": 24,
        "created_at": ts,
    }
    sig = sign(sk_a, canonical_json(payload)).hex()
    r = await client.post("/v1/rooms", json={**payload, "sig": sig}, headers=_hdr(pk_a))

    assert r.status_code == 200, f"duplicate invitee should not 500: {r.text[:200]}"
    parts = r.json()["participants"]
    bob_count = sum(1 for p in parts if p["agent_pubkey"] == pk_b.hex())
    assert bob_count == 1, f"expected one Bob, got {bob_count}"
    assert len(parts) == 2, f"creator + Bob = 2, got {len(parts)}"


# ---------------------------------------------------------------------------
# Bug: close on a TTL-expired room returned 200 (SPEC §8.1 says 409).
# Fix: close handler also checks is_expired().
# ---------------------------------------------------------------------------


async def test_close_on_ttl_expired_room_returns_409(client, engine):
    sk_a, pk_a = generate_keypair()
    room_id = await _create_room_simple(client, sk_a, pk_a, ttl_hours=1)
    await _force_ttl_expired(engine, room_id)

    ts = _now_iso()
    sig = _sign_close(sk_a, room_id=room_id, summary=None, created_at=ts)
    r = await client.post(
        f"/v1/rooms/{room_id}/close",
        json={"summary": None, "created_at": ts, "sig": sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 409, (
        f"close on TTL-expired room must be 409 per SPEC §8.1, got {r.status_code}"
    )


# ---------------------------------------------------------------------------
# Bug: accept on a closed/expired room is not blocked.
# Fix: accept handler checks status + is_expired() before mutating state.
# ---------------------------------------------------------------------------


async def test_accept_on_already_closed_room_returns_409(client):
    sk_a, pk_a = generate_keypair()
    sk_b, pk_b = generate_keypair()
    room_id = await _create_room_simple(client, sk_a, pk_a, invitees=[pk_b.hex()])

    # Alice closes the room before Bob accepts.
    ts = _now_iso()
    close_sig = _sign_close(sk_a, room_id=room_id, summary=None, created_at=ts)
    r = await client.post(
        f"/v1/rooms/{room_id}/close",
        json={"summary": None, "created_at": ts, "sig": close_sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 200

    # Bob now tries to accept.
    ts2 = _now_iso()
    accept_sig = _sign_accept(sk_b, room_id=room_id, agent_pk=pk_b, created_at=ts2)
    r = await client.post(
        f"/v1/rooms/{room_id}/accept",
        json={"created_at": ts2, "sig": accept_sig},
        headers=_hdr(pk_b),
    )
    assert r.status_code == 409, (
        f"accept on closed room must be 409 per SPEC §8.1, got {r.status_code}"
    )


async def test_accept_on_ttl_expired_room_returns_409(client, engine):
    sk_a, pk_a = generate_keypair()
    sk_b, pk_b = generate_keypair()
    room_id = await _create_room_simple(client, sk_a, pk_a, invitees=[pk_b.hex()], ttl_hours=1)
    await _force_ttl_expired(engine, room_id)

    ts = _now_iso()
    accept_sig = _sign_accept(sk_b, room_id=room_id, agent_pk=pk_b, created_at=ts)
    r = await client.post(
        f"/v1/rooms/{room_id}/accept",
        json={"created_at": ts, "sig": accept_sig},
        headers=_hdr(pk_b),
    )
    assert r.status_code == 409, (
        f"accept on TTL-expired room must be 409 per SPEC §8.1, got {r.status_code}"
    )
