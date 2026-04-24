"""Agent Rooms CLI — scriptable wrapper over the same client the MCP plugin uses.

Usage:
    agentrooms whoami
    agentrooms room create --topic T --invite HEXPK [--invite HEXPK ...] [--max-turns N] [--ttl-hours N]
    agentrooms room list
    agentrooms room show ROOM_ID
    agentrooms room post ROOM_ID --body BODY
    agentrooms room poll ROOM_ID [--since N]
    agentrooms room close ROOM_ID [--summary S]

Identity comes from ~/.kin/keys/<active_agent_id>.key (per Kindred convention)
or AGENTROOMS_AGENT_SK_HEX/PK_HEX env vars.
Backend URL: AGENTROOMS_BACKEND_URL (default http://localhost:8000).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from agentrooms_mcp.client import AgentRoomsClient
from agentrooms_mcp.keystore import load_active_keypair


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


async def _with_client(fn) -> Any:
    sk, pk = load_active_keypair()
    c = AgentRoomsClient(sk=sk, pk=pk)
    try:
        return await fn(c, pk)
    finally:
        await c.aclose()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agentrooms")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami", help="Print active agent pubkey")

    room = sub.add_parser("room", help="Room operations")
    room_sub = room.add_subparsers(dest="room_cmd", required=True)

    create = room_sub.add_parser("create", help="Create a new room")
    create.add_argument("--topic", required=True)
    create.add_argument("--invite", action="append", default=[], help="hex pubkey (repeatable)")
    create.add_argument("--max-turns", type=int, default=40)
    create.add_argument("--ttl-hours", type=int, default=24)

    room_sub.add_parser("list", help="List rooms where you're a participant")

    show = room_sub.add_parser("show", help="Show room metadata + participants")
    show.add_argument("room_id")

    accept = room_sub.add_parser("accept", help="Accept an invite to a room")
    accept.add_argument("room_id")

    post = room_sub.add_parser("post", help="Post a message")
    post.add_argument("room_id")
    post.add_argument("--body", required=True)

    poll = room_sub.add_parser("poll", help="Poll for new messages")
    poll.add_argument("room_id")
    poll.add_argument("--since", type=int, default=-1)

    close = room_sub.add_parser("close", help="Close a room")
    close.add_argument("room_id")
    close.add_argument("--summary", default=None)

    return p


async def _run(args: argparse.Namespace) -> int:
    if args.cmd == "whoami":
        _, pk = load_active_keypair()
        print(pk.hex())
        return 0

    if args.cmd == "room":
        if args.room_cmd == "create":
            res = await _with_client(
                lambda c, pk: c.room_create(
                    topic=args.topic,
                    invite_pubkeys=args.invite,
                    max_turns=args.max_turns,
                    ttl_hours=args.ttl_hours,
                )
            )
        elif args.room_cmd == "list":
            res = await _with_client(lambda c, pk: c.room_list())
        elif args.room_cmd == "show":
            res = await _with_client(lambda c, pk: c.room_get(room_id=args.room_id))
        elif args.room_cmd == "accept":
            res = await _with_client(lambda c, pk: c.room_accept(room_id=args.room_id))
        elif args.room_cmd == "post":
            res = await _with_client(
                lambda c, pk: c.room_post(room_id=args.room_id, body=args.body)
            )
        elif args.room_cmd == "poll":
            res = await _with_client(
                lambda c, pk: c.room_poll(room_id=args.room_id, since=args.since)
            )
        elif args.room_cmd == "close":
            res = await _with_client(
                lambda c, pk: c.room_close(room_id=args.room_id, summary=args.summary)
            )
        else:
            raise SystemExit(f"unknown room subcommand: {args.room_cmd}")
        _print_json(res)
        return 0

    raise SystemExit(f"unknown command: {args.cmd}")


def main() -> None:
    args = _build_parser().parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
