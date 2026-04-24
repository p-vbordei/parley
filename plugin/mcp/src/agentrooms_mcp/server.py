"""FastMCP server exposing 6 tools to Claude Code.

Run via:
    uv run --directory plugin/mcp python -m agentrooms_mcp.server

Configuration via env:
    AGENTROOMS_BACKEND_URL    — default http://localhost:8000
    AGENTROOMS_AGENT_SK_HEX   — override key file (testing)
    AGENTROOMS_AGENT_PK_HEX   — override key file (testing)
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from agentrooms_mcp.client import AgentRoomsClient
from agentrooms_mcp.keystore import load_active_keypair

mcp = FastMCP("agentrooms")

_client: AgentRoomsClient | None = None


def _get_client() -> AgentRoomsClient:
    global _client
    if _client is None:
        sk, pk = load_active_keypair()
        _client = AgentRoomsClient(sk=sk, pk=pk)
    return _client


@mcp.tool()
async def room_create(
    topic: str, invite_pubkeys: list[str], max_turns: int = 40, ttl_hours: int = 24
) -> dict[str, Any]:
    """Create a new room and invite agents by hex pubkey.

    The caller is auto-added as creator + first turn owner. Returns room metadata
    including the room_id you'll need for subsequent calls.
    """
    return await _get_client().room_create(
        topic=topic,
        invite_pubkeys=invite_pubkeys,
        max_turns=max_turns,
        ttl_hours=ttl_hours,
    )


@mcp.tool()
async def room_accept(room_id: str) -> dict[str, Any]:
    """Accept an invite to a room. Until accepted you cannot post or read messages.

    HUMAN-IN-THE-LOOP: skills must NOT call this without explicit user approval
    when the inviting pubkey is new (anti-spam)."""
    return await _get_client().room_accept(room_id=room_id)


@mcp.tool()
async def room_post(room_id: str, body: str) -> dict[str, Any]:
    """Post a message to a room. Server enforces turn-taking — fails 403
    if it isn't your turn yet. Caller is the active agent identity."""
    return await _get_client().room_post(room_id=room_id, body=body)


@mcp.tool()
async def room_poll(room_id: str, since_turn: int = -1) -> dict[str, Any]:
    """Pull messages with turn_n > since_turn. Use -1 for full history.
    Returns {messages, room_status, turn_n, turn_owner_pubkey} so the agent
    can decide whether it's their turn."""
    return await _get_client().room_poll(room_id=room_id, since=since_turn)


@mcp.tool()
async def room_close(room_id: str, summary: str | None = None) -> dict[str, Any]:
    """Close the room. Only the creator or the current turn owner can close.
    Optional summary is preserved on the transcript."""
    return await _get_client().room_close(room_id=room_id, summary=summary)


@mcp.tool()
async def room_list() -> list[dict[str, Any]]:
    """List rooms where the active agent is a participant (most recent first)."""
    return await _get_client().room_list()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
