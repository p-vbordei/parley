"""End-to-end golden path: Alice + Bob exchange 10 signed messages,
Alice closes with a summary, both fetch the full transcript and verify
every signature."""

from datetime import UTC, datetime

from agentrooms.crypto import canonical_json, generate_keypair, sign, verify


def _hdr(pk: bytes) -> dict[str, str]:
    return {"X-Agent-Pubkey": pk.hex()}


async def test_two_agents_full_conversation(client):
    sk_a, pk_a = generate_keypair()
    sk_b, pk_b = generate_keypair()

    # 1. Alice creates the room, invites Bob.
    create_payload = {
        "topic": "auth-ui integration",
        "invite_pubkeys": [pk_b.hex()],
        "max_turns": 40,
        "ttl_hours": 24,
    }
    create_sig = sign(sk_a, canonical_json(create_payload)).hex()
    r = await client.post(
        "/v1/rooms", json={**create_payload, "sig": create_sig}, headers=_hdr(pk_a)
    )
    assert r.status_code == 200, r.text
    room = r.json()
    room_id = room["room_id"]
    assert room["turn_owner_pubkey"] == pk_a.hex()

    # 2. Bob accepts.
    accept_sig = sign(
        sk_b, canonical_json({"room_id": room_id, "agent_pubkey": pk_b.hex()})
    ).hex()
    r = await client.post(
        f"/v1/rooms/{room_id}/accept", json={"sig": accept_sig}, headers=_hdr(pk_b)
    )
    assert r.status_code == 200, r.text

    # 3-5. Ten alternating turns. Track signed payloads so we can re-verify later.
    signed_payloads: list[dict] = []
    turn_owners = [(sk_a, pk_a), (sk_b, pk_b)]
    for turn_n in range(1, 11):
        sk, pk = turn_owners[(turn_n - 1) % 2]

        # Each non-Alice turn polls first to behave like a real agent.
        if pk == pk_b:
            poll = await client.get(
                f"/v1/rooms/{room_id}/messages?since={turn_n - 2}", headers=_hdr(pk_b)
            )
            assert poll.status_code == 200
            assert poll.json()["turn_owner_pubkey"] == pk_b.hex()

        body = f"turn {turn_n} from {'alice' if pk == pk_a else 'bob'}"
        created_at = datetime.now(UTC)
        signed = {
            "room_id": room_id,
            "turn_n": turn_n,
            "author_pubkey": pk.hex(),
            "body": body,
            "created_at": created_at.isoformat(),
        }
        msg_sig = sign(sk, canonical_json(signed)).hex()
        signed_payloads.append({**signed, "_pubkey": pk, "_sig_hex": msg_sig})

        r = await client.post(
            f"/v1/rooms/{room_id}/messages",
            json={
                "turn_n": turn_n,
                "body": body,
                "created_at": created_at.isoformat(),
                "sig": msg_sig,
            },
            headers=_hdr(pk),
        )
        assert r.status_code == 200, f"turn {turn_n}: {r.text}"
        next_owner = turn_owners[turn_n % 2][1]
        assert r.json()["next_turn_owner_pubkey"] == next_owner.hex()

    # 6. Alice closes with summary.
    close_sig = sign(
        sk_a, canonical_json({"room_id": room_id, "summary": "shipped JWT decision"})
    ).hex()
    r = await client.post(
        f"/v1/rooms/{room_id}/close",
        json={"summary": "shipped JWT decision", "sig": close_sig},
        headers=_hdr(pk_a),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "closed"

    # 7. Both can fetch the full transcript; every signature verifies.
    for reader_pk in (pk_a, pk_b):
        r = await client.get(
            f"/v1/rooms/{room_id}/messages?since=-1", headers=_hdr(reader_pk)
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["room_status"] == "closed"
        assert len(data["messages"]) == 10

        # Verify by recomputing the exact signed payload for each turn.
        for msg, expected in zip(data["messages"], signed_payloads, strict=True):
            assert msg["turn_n"] == expected["turn_n"]
            assert msg["body"] == expected["body"]
            assert msg["author_pubkey"] == expected["author_pubkey"]
            sig_bytes = bytes.fromhex(msg["sig"])
            payload_bytes = canonical_json(
                {
                    "room_id": expected["room_id"],
                    "turn_n": expected["turn_n"],
                    "author_pubkey": expected["author_pubkey"],
                    "body": expected["body"],
                    "created_at": expected["created_at"],
                }
            )
            assert verify(expected["_pubkey"], payload_bytes, sig_bytes), (
                f"sig invalid for turn {expected['turn_n']}"
            )

    # Room metadata reports closed + summary.
    r = await client.get(f"/v1/rooms/{room_id}", headers=_hdr(pk_a))
    assert r.json()["summary"] == "shipped JWT decision"
    assert r.json()["status"] == "closed"
