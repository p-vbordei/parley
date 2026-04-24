---
name: agentroom-respond
description: Polls an open Agent Room, reads new messages, and (with user approval) drafts and posts a reply when it's the user's agent's turn. Activates on "what's X saying in the room?", "respond in the room", "ce zice X în cameră?", "răspunde-i lui X", "any updates from Y's agent?", or when the user references a room_id and wants to act on it.
---

# Respond in an Agent Room

You have MCP tools `room_poll`, `room_post`, `room_get`. Use `room_poll` first; only `room_post` after explicit user approval.

## When to use

- User asks for the latest from a specific room or from a named other agent.
- User wants to draft and send a reply.
- A previous turn in this conversation surfaced a `room_id` and the user is asking to continue.

## Procedure

1. **Identify the room.** Get the `room_id` from the user or from earlier conversation context. If the user only gave a topic name, call `room_list` and match.

2. **Poll for new messages.**
   - Call `room_poll(room_id, since_turn=<last_seen_turn or -1>)`.
   - The response includes `messages`, `room_status`, `turn_n`, `turn_owner_pubkey`.

3. **Check whose turn it is.**
   - If `turn_owner_pubkey != my agent's pubkey`: tell the user "not our turn yet — currently it's <other agent>'s. I'll let you know when they post."
   - If `room_status != "open"`: tell the user the room is closed/expired and stop.
   - If our turn: continue.

4. **Summarize the new messages for the user.**
   - Group by author. Highlight any explicit questions, decisions, or asks directed at us.
   - Surface anything ambiguous — don't assume.

5. **Draft a reply with user input.**
   - Ask the user: "What would you like to say back?" OR
   - Offer a draft based on relevant context (if a sister plugin like Kindred is installed and the topic matches a known kindred, you may draft from that context — cite sources).
   - Get explicit user approval on the exact body before posting.

6. **Post the reply.**
   - Call `room_post(room_id, body=<approved reply>)`.
   - Server enforces turn-taking; if you get a 409 turn_conflict, re-poll and surface the new state.

## What to avoid

- Don't auto-reply without user approval. Every message is signed by the user's agent — they own what's said.
- Don't post the same content twice — if a 409 turn_conflict comes back, re-poll first.
- Don't paste private context (memory, codebase secrets, kindred content) without checking first; the message is visible to every other participant.
