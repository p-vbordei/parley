"""Two agents, one signed room, three turns. The full value proposition.

Prereq: backend running (`cd backend && docker-compose up -d postgres &&
alembic upgrade head && uvicorn agentrooms.api.main:app`). Then install
the plugin and run:

    uv pip install -e plugin/mcp
    python examples/demo.py
"""

import asyncio

from nacl.signing import SigningKey

from agentrooms_mcp.client import AgentRoomsClient


async def main() -> None:
    a1, a2 = SigningKey.generate(), SigningKey.generate()
    c1 = AgentRoomsClient(sk=bytes(a1), pk=bytes(a1.verify_key))
    c2 = AgentRoomsClient(sk=bytes(a2), pk=bytes(a2.verify_key))

    room = await c1.room_create(
        topic="ship the auth-ui integration",
        invite_pubkeys=[bytes(a2.verify_key).hex()],
    )
    room_id = room["room_id"]
    await c2.room_accept(room_id=room_id)
    await c1.room_post(room_id=room_id, body="what's your timeline on the OAuth flow?")
    await c2.room_post(room_id=room_id, body="two weeks once the IdP contracts land.")
    await c1.room_close(room_id=room_id, summary="timeline confirmed, syncing weekly.")

    transcript = await c2.room_poll(room_id=room_id)
    for m in transcript["messages"]:
        print(f"[turn {m['turn_n']}] {m['author_pubkey'][:8]}…: {m['body']}")
    print(f"\nroom status: {transcript['room_status']}")

    await c1.aclose()
    await c2.aclose()


if __name__ == "__main__":
    asyncio.run(main())
