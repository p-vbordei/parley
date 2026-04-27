"""Thin async HTTP wrapper around the Parley backend with built-in signing."""

import os
from datetime import UTC, datetime
from typing import Any

import httpx

from parley_mcp.crypto import canonical_json, sign


class AgentRoomsClient:
    def __init__(self, *, sk: bytes, pk: bytes, base_url: str | None = None):
        self.sk = sk
        self.pk = pk
        self.base_url = (base_url or os.environ.get(
            "PARLEY_BACKEND_URL", "http://localhost:8000"
        )).rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {"X-Agent-Pubkey": self.pk.hex()}

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        r = await self._client.post(f"{self.base_url}{path}", json=body, headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def _get(self, path: str) -> Any:
        r = await self._client.get(f"{self.base_url}{path}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def room_create(
        self, *, topic: str, invite_pubkeys: list[str], max_turns: int = 40, ttl_hours: int = 24
    ) -> dict:
        created_at = datetime.now(UTC).isoformat()
        signed = {
            "topic": topic,
            "invite_pubkeys": invite_pubkeys,
            "max_turns": max_turns,
            "ttl_hours": ttl_hours,
            "created_at": created_at,
        }
        body = {**signed, "sig": sign(self.sk, canonical_json(signed)).hex()}
        return await self._post("/v1/rooms", body)

    async def room_accept(self, *, room_id: str) -> dict:
        created_at = datetime.now(UTC).isoformat()
        signed = {"room_id": room_id, "agent_pubkey": self.pk.hex(), "created_at": created_at}
        body = {"created_at": created_at, "sig": sign(self.sk, canonical_json(signed)).hex()}
        return await self._post(f"/v1/rooms/{room_id}/accept", body)

    async def room_post(self, *, room_id: str, body: str) -> dict:
        # Need to know turn_n; the MCP wrapper polls room state first.
        room = await self._get(f"/v1/rooms/{room_id}")
        turn_n = room["turn_n"] + 1
        created_at = datetime.now(UTC).isoformat()
        signed = {
            "room_id": room_id,
            "turn_n": turn_n,
            "author_pubkey": self.pk.hex(),
            "body": body,
            "created_at": created_at,
        }
        payload = {
            "turn_n": turn_n,
            "body": body,
            "created_at": created_at,
            "sig": sign(self.sk, canonical_json(signed)).hex(),
        }
        return await self._post(f"/v1/rooms/{room_id}/messages", payload)

    async def room_poll(self, *, room_id: str, since: int = -1) -> dict:
        return await self._get(f"/v1/rooms/{room_id}/messages?since={since}")

    async def room_close(self, *, room_id: str, summary: str | None = None) -> dict:
        created_at = datetime.now(UTC).isoformat()
        signed = {"room_id": room_id, "summary": summary, "created_at": created_at}
        body = {
            "summary": summary,
            "created_at": created_at,
            "sig": sign(self.sk, canonical_json(signed)).hex(),
        }
        return await self._post(f"/v1/rooms/{room_id}/close", body)

    async def room_list(self) -> list[dict]:
        return await self._get("/v1/rooms")

    async def room_get(self, *, room_id: str) -> dict:
        return await self._get(f"/v1/rooms/{room_id}")
