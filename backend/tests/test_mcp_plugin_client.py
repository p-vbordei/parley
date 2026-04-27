"""Integration test: parley_mcp.client.AgentRoomsClient ↔ backend FastAPI app.

Proves the wire is compatible — same canonical signing, same routes, same
schemas. Mounts the backend ASGI app under the plugin's httpx client.
"""

import pytest
from parley_mcp.client import AgentRoomsClient
from parley_mcp.crypto import canonical_json, sign

pytest.importorskip("parley_mcp")

from nacl import signing


def _gen() -> tuple[bytes, bytes]:
    sk = signing.SigningKey.generate()
    return bytes(sk), bytes(sk.verify_key)


@pytest.fixture
def asgi_client(client):
    """Replace the AgentRoomsClient's httpx with one mounted on the backend ASGI app."""

    def _patch(client_obj: AgentRoomsClient) -> AgentRoomsClient:
        client_obj._client = client  # the conftest test client (AsyncClient)
        client_obj.base_url = "http://test"
        return client_obj

    return _patch


async def test_full_flow_via_plugin_client(asgi_client):
    sk_a, pk_a = _gen()
    sk_b, pk_b = _gen()

    alice = asgi_client(AgentRoomsClient(sk=sk_a, pk=pk_a, base_url="http://test"))
    bob = asgi_client(AgentRoomsClient(sk=sk_b, pk=pk_b, base_url="http://test"))

    room = await alice.room_create(topic="t", invite_pubkeys=[pk_b.hex()], max_turns=4)
    room_id = room["room_id"]
    assert room["turn_owner_pubkey"] == pk_a.hex()

    await bob.room_accept(room_id=room_id)

    r1 = await alice.room_post(room_id=room_id, body="hi from alice")
    assert r1["turn_n"] == 1
    assert r1["next_turn_owner_pubkey"] == pk_b.hex()

    poll = await bob.room_poll(room_id=room_id, since=0)
    assert len(poll["messages"]) == 1
    assert poll["turn_owner_pubkey"] == pk_b.hex()

    r2 = await bob.room_post(room_id=room_id, body="hi from bob")
    assert r2["turn_n"] == 2

    rooms = await alice.room_list()
    assert any(r["room_id"] == room_id for r in rooms)

    closed = await alice.room_close(room_id=room_id, summary="done")
    assert closed["status"] == "closed"
    assert closed["summary"] == "done"


def test_canonical_matches_backend():
    """Plugin's canonical_json must produce identical bytes to the backend's."""
    from parley.crypto import canonical_json as backend_canonical

    payloads = [
        {"a": 1, "b": [2, 1, 3], "c": "ănă"},
        {"room_id": "x", "turn_n": 5, "body": "hi", "created_at": "2026-04-24T12:00:00+00:00"},
        {},
    ]
    for p in payloads:
        assert canonical_json(p) == backend_canonical(p)


def test_sign_matches_backend():
    """Plugin's sign() must verify under the backend's verify()."""
    from parley.crypto import verify as backend_verify

    sk, pk = _gen()
    msg = canonical_json({"hello": "world"})
    sig = sign(sk, msg)
    assert backend_verify(pk, msg, sig)
