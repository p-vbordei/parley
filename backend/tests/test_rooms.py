"""HTTP-level tests for /v1/rooms endpoints."""

from datetime import UTC, datetime

from agentrooms.crypto import canonical_json, generate_keypair, sign


def _hdr(pk: bytes) -> dict[str, str]:
    return {"X-Agent-Pubkey": pk.hex()}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sign_create(
    sk: bytes,
    *,
    topic: str,
    invitees: list[str],
    max_turns: int,
    ttl_hours: int,
    created_at: str,
) -> str:
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


def _sign_accept(sk: bytes, *, room_id: str, agent_pk: bytes, created_at: str) -> str:
    return sign(
        sk,
        canonical_json(
            {"room_id": room_id, "agent_pubkey": agent_pk.hex(), "created_at": created_at}
        ),
    ).hex()


def _sign_close(sk: bytes, *, room_id: str, summary: str | None, created_at: str) -> str:
    return sign(
        sk,
        canonical_json({"room_id": room_id, "summary": summary, "created_at": created_at}),
    ).hex()


async def test_healthz(client):
    r = await client.get("/v1/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_create_room_happy_path(client):
    sk_a, pk_a = generate_keypair()
    _, pk_b = generate_keypair()
    invitees = [pk_b.hex()]
    created_at = _now_iso()
    body = {
        "topic": "auth-ui integration",
        "invite_pubkeys": invitees,
        "max_turns": 40,
        "ttl_hours": 24,
        "created_at": created_at,
        "sig": _sign_create(
            sk_a,
            topic="auth-ui integration",
            invitees=invitees,
            max_turns=40,
            ttl_hours=24,
            created_at=created_at,
        ),
    }
    r = await client.post("/v1/rooms", json=body, headers=_hdr(pk_a))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["topic"] == "auth-ui integration"
    assert data["status"] == "open"
    assert data["turn_n"] == 0
    assert data["turn_owner_pubkey"] == pk_a.hex()
    assert data["creator_pubkey"] == pk_a.hex()
    assert len(data["participants"]) == 2
    creator = next(p for p in data["participants"] if p["agent_pubkey"] == pk_a.hex())
    invitee = next(p for p in data["participants"] if p["agent_pubkey"] == pk_b.hex())
    assert creator["accepted_at"] is not None
    assert invitee["accepted_at"] is None


async def test_create_room_rejects_bad_signature(client):
    sk_bad, _ = generate_keypair()
    _, pk_a = generate_keypair()
    created_at = _now_iso()
    body = {
        "topic": "x",
        "invite_pubkeys": [],
        "max_turns": 40,
        "ttl_hours": 24,
        "created_at": created_at,
        "sig": _sign_create(
            sk_bad, topic="x", invitees=[], max_turns=40, ttl_hours=24, created_at=created_at
        ),  # signed with the wrong key
    }
    r = await client.post("/v1/rooms", json=body, headers=_hdr(pk_a))
    assert r.status_code == 401


async def test_create_room_rejects_bad_pubkey_header(client):
    body = {
        "topic": "x",
        "invite_pubkeys": [],
        "max_turns": 40,
        "ttl_hours": 24,
        "created_at": _now_iso(),
        "sig": "00" * 64,
    }
    r = await client.post("/v1/rooms", json=body, headers={"X-Agent-Pubkey": "notHex"})
    assert r.status_code == 400


async def _create(client, sk, pk, invitees=None):
    invitees = invitees or []
    created_at = _now_iso()
    body = {
        "topic": "t",
        "invite_pubkeys": invitees,
        "max_turns": 40,
        "ttl_hours": 24,
        "created_at": created_at,
        "sig": _sign_create(
            sk, topic="t", invitees=invitees, max_turns=40, ttl_hours=24, created_at=created_at
        ),
    }
    r = await client.post("/v1/rooms", json=body, headers=_hdr(pk))
    assert r.status_code == 200, r.text
    return r.json()


async def test_get_room_requires_participant(client):
    sk_a, pk_a = generate_keypair()
    _, pk_outsider = generate_keypair()
    room = await _create(client, sk_a, pk_a)

    r = await client.get(f"/v1/rooms/{room['room_id']}", headers=_hdr(pk_outsider))
    assert r.status_code == 403

    r = await client.get(f"/v1/rooms/{room['room_id']}", headers=_hdr(pk_a))
    assert r.status_code == 200


async def test_accept_invite(client):
    sk_a, pk_a = generate_keypair()
    sk_b, pk_b = generate_keypair()
    room = await _create(client, sk_a, pk_a, invitees=[pk_b.hex()])

    created_at = _now_iso()
    accept_sig = _sign_accept(sk_b, room_id=room["room_id"], agent_pk=pk_b, created_at=created_at)
    r = await client.post(
        f"/v1/rooms/{room['room_id']}/accept",
        json={"created_at": created_at, "sig": accept_sig},
        headers=_hdr(pk_b),
    )
    assert r.status_code == 200, r.text
    assert r.json()["accepted_at"] is not None

    # Confirm via GET
    r = await client.get(f"/v1/rooms/{room['room_id']}", headers=_hdr(pk_a))
    invitee = next(p for p in r.json()["participants"] if p["agent_pubkey"] == pk_b.hex())
    assert invitee["accepted_at"] is not None


async def test_accept_rejects_outsider(client):
    sk_a, pk_a = generate_keypair()
    sk_outsider, pk_outsider = generate_keypair()
    room = await _create(client, sk_a, pk_a)

    created_at = _now_iso()
    sig = _sign_accept(
        sk_outsider, room_id=room["room_id"], agent_pk=pk_outsider, created_at=created_at
    )
    r = await client.post(
        f"/v1/rooms/{room['room_id']}/accept",
        json={"created_at": created_at, "sig": sig},
        headers=_hdr(pk_outsider),
    )
    assert r.status_code == 403


async def test_accept_rejects_bad_signature(client):
    sk_a, pk_a = generate_keypair()
    _, pk_b = generate_keypair()
    sk_other, _ = generate_keypair()
    room = await _create(client, sk_a, pk_a, invitees=[pk_b.hex()])

    created_at = _now_iso()
    sig = _sign_accept(sk_other, room_id=room["room_id"], agent_pk=pk_b, created_at=created_at)
    r = await client.post(
        f"/v1/rooms/{room['room_id']}/accept",
        json={"created_at": created_at, "sig": sig},
        headers=_hdr(pk_b),
    )
    assert r.status_code == 401


async def test_close_by_creator(client):
    sk_a, pk_a = generate_keypair()
    room = await _create(client, sk_a, pk_a)

    created_at = _now_iso()
    sig = _sign_close(sk_a, room_id=room["room_id"], summary="done", created_at=created_at)
    r = await client.post(
        f"/v1/rooms/{room['room_id']}/close",
        json={"summary": "done", "created_at": created_at, "sig": sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "closed"
    assert body["summary"] == "done"

    # Can't close twice
    r2 = await client.post(
        f"/v1/rooms/{room['room_id']}/close",
        json={"summary": "done", "created_at": created_at, "sig": sig},
        headers=_hdr(pk_a),
    )
    assert r2.status_code == 409


async def test_close_rejects_non_creator_non_turn_owner(client):
    sk_a, pk_a = generate_keypair()
    sk_b, pk_b = generate_keypair()
    room = await _create(client, sk_a, pk_a, invitees=[pk_b.hex()])

    created_at = _now_iso()
    sig = _sign_close(sk_b, room_id=room["room_id"], summary=None, created_at=created_at)
    r = await client.post(
        f"/v1/rooms/{room['room_id']}/close",
        json={"summary": None, "created_at": created_at, "sig": sig},
        headers=_hdr(pk_b),
    )
    assert r.status_code == 403
