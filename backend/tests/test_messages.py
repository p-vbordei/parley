"""HTTP-level tests for /v1/rooms/{id}/messages."""

from datetime import UTC, datetime, timedelta

from agentrooms.crypto import canonical_json, generate_keypair, sign


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


def _sign_accept(sk, *, room_id, agent_pk):
    return sign(
        sk, canonical_json({"room_id": str(room_id), "agent_pubkey": agent_pk.hex()})
    ).hex()


async def _bootstrap_room(client, *, max_turns=40):
    """Create a room with Alice + Bob both accepted, return (sk_a, pk_a, sk_b, pk_b, room_id)."""
    sk_a, pk_a = generate_keypair()
    sk_b, pk_b = generate_keypair()

    create_body = {
        "topic": "t",
        "invite_pubkeys": [pk_b.hex()],
        "max_turns": max_turns,
        "ttl_hours": 24,
        "sig": _sign_create(sk_a, topic="t", invitees=[pk_b.hex()], max_turns=max_turns),
    }
    r = await client.post("/v1/rooms", json=create_body, headers=_hdr(pk_a))
    assert r.status_code == 200, r.text
    room_id = r.json()["room_id"]

    r = await client.post(
        f"/v1/rooms/{room_id}/accept",
        json={"sig": _sign_accept(sk_b, room_id=room_id, agent_pk=pk_b)},
        headers=_hdr(pk_b),
    )
    assert r.status_code == 200, r.text

    return sk_a, pk_a, sk_b, pk_b, room_id


async def _post(client, sk, pk, *, room_id, turn_n, body, created_at=None):
    created_at = created_at or datetime.now(UTC)
    sig = _sign_message(sk, room_id=room_id, turn_n=turn_n, author_pk=pk, body=body, created_at=created_at)
    return await client.post(
        f"/v1/rooms/{room_id}/messages",
        json={
            "turn_n": turn_n,
            "body": body,
            "created_at": created_at.isoformat(),
            "sig": sig,
        },
        headers=_hdr(pk),
    )


async def test_post_then_poll(client):
    sk_a, pk_a, sk_b, pk_b, room_id = await _bootstrap_room(client)

    r = await _post(client, sk_a, pk_a, room_id=room_id, turn_n=1, body="hi from alice")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["turn_n"] == 1
    assert body["next_turn_owner_pubkey"] == pk_b.hex()
    assert body["room_status"] == "open"

    r = await client.get(f"/v1/rooms/{room_id}/messages?since=0", headers=_hdr(pk_b))
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["messages"]) == 1
    assert data["messages"][0]["body"] == "hi from alice"
    assert data["turn_n"] == 1
    assert data["turn_owner_pubkey"] == pk_b.hex()


async def test_turn_alternates(client):
    sk_a, pk_a, sk_b, pk_b, room_id = await _bootstrap_room(client)

    for turn, (sk, pk) in enumerate(
        [(sk_a, pk_a), (sk_b, pk_b), (sk_a, pk_a), (sk_b, pk_b)], start=1
    ):
        r = await _post(client, sk, pk, room_id=room_id, turn_n=turn, body=f"t{turn}")
        assert r.status_code == 200, f"turn {turn}: {r.text}"

    r = await client.get(f"/v1/rooms/{room_id}/messages?since=-1", headers=_hdr(pk_a))
    msgs = r.json()["messages"]
    assert [m["turn_n"] for m in msgs] == [1, 2, 3, 4]
    assert [m["author_pubkey"] for m in msgs] == [pk_a.hex(), pk_b.hex(), pk_a.hex(), pk_b.hex()]


async def test_reject_out_of_turn_author(client):
    sk_a, pk_a, sk_b, pk_b, room_id = await _bootstrap_room(client)
    # Bob tries to post first; Alice owns turn 1.
    r = await _post(client, sk_b, pk_b, room_id=room_id, turn_n=1, body="x")
    assert r.status_code == 403


async def test_reject_wrong_turn_n(client):
    sk_a, pk_a, sk_b, pk_b, room_id = await _bootstrap_room(client)
    r = await _post(client, sk_a, pk_a, room_id=room_id, turn_n=2, body="x")
    assert r.status_code == 409


async def test_reject_bad_signature(client):
    sk_a, pk_a, _, _, room_id = await _bootstrap_room(client)
    sk_other, _ = generate_keypair()
    created_at = datetime.now(UTC)
    bad_sig = _sign_message(
        sk_other, room_id=room_id, turn_n=1, author_pk=pk_a, body="x", created_at=created_at
    )
    r = await client.post(
        f"/v1/rooms/{room_id}/messages",
        json={"turn_n": 1, "body": "x", "created_at": created_at.isoformat(), "sig": bad_sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 401


async def test_reject_stale_timestamp(client):
    sk_a, pk_a, _, _, room_id = await _bootstrap_room(client)
    stale = datetime.now(UTC) - timedelta(minutes=5)
    r = await _post(client, sk_a, pk_a, room_id=room_id, turn_n=1, body="x", created_at=stale)
    assert r.status_code == 400


async def test_reject_oversized_body(client):
    sk_a, pk_a, _, _, room_id = await _bootstrap_room(client)
    big = "x" * (16 * 1024 + 1)
    r = await _post(client, sk_a, pk_a, room_id=room_id, turn_n=1, body=big)
    # Pydantic max_length kicks first → 422; either 422 or 413 is acceptable rejection.
    assert r.status_code in (413, 422)


async def test_outsider_cannot_poll(client):
    sk_a, pk_a, _, _, room_id = await _bootstrap_room(client)
    _, pk_outsider = generate_keypair()
    r = await client.get(f"/v1/rooms/{room_id}/messages?since=-1", headers=_hdr(pk_outsider))
    assert r.status_code == 403


async def test_post_blocked_after_close(client):
    sk_a, pk_a, _, _, room_id = await _bootstrap_room(client)
    # Close as creator
    sig = sign(sk_a, canonical_json({"room_id": room_id, "summary": None})).hex()
    r = await client.post(
        f"/v1/rooms/{room_id}/close",
        json={"summary": None, "sig": sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 200
    # Try to post
    r = await _post(client, sk_a, pk_a, room_id=room_id, turn_n=1, body="x")
    assert r.status_code == 409


async def test_max_turns_force_close(client):
    sk_a, pk_a, sk_b, pk_b, room_id = await _bootstrap_room(client, max_turns=2)

    r = await _post(client, sk_a, pk_a, room_id=room_id, turn_n=1, body="t1")
    assert r.status_code == 200
    assert r.json()["room_status"] == "open"

    r = await _post(client, sk_b, pk_b, room_id=room_id, turn_n=2, body="t2")
    assert r.status_code == 200
    assert r.json()["room_status"] == "closed"
    assert r.json()["next_turn_owner_pubkey"] is None

    # No more posts accepted
    r = await _post(client, sk_a, pk_a, room_id=room_id, turn_n=3, body="t3")
    assert r.status_code == 409
