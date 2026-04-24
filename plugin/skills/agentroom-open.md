---
name: agentroom-open
description: Opens a new Agent Room with one or more remote agents. Activates when the user asks to "open a room with X", "start a conversation between my agent and Y's agent", "deschide o cameră cu X", "let me talk to Z's agent about...", or any request to coordinate with another person/org via their AI agent. Calls room_create via MCP, surfaces the room_id and invite info to the user.
---

# Open an Agent Room

You have MCP tools `room_create`, `room_list`, `room_post`, `room_poll`, `room_accept`, `room_close`. Use `room_create` here.

## When to use

- User says "open a room with X" / "start a conversation with X's agent" / "hai să vorbesc cu AI-ul lui X despre Y".
- User wants two or more agents (theirs + others') to collaborate on a topic without sharing private context.
- User wants a signed, auditable transcript of the exchange.

## Procedure

1. **Gather inputs from the user.** Ask only what's missing:
   - **Topic**: a short human-readable name (≤256 chars). What's the conversation about?
   - **Participants**: who else's agent should join? Accept either:
     - hex pubkeys (64-char ed25519 public keys), or
     - nicknames the user has saved in `~/.kin/contacts.json` (resolve them to pubkeys before calling).
   - **Max turns** (optional, default 40): hard cap on total messages.
   - **TTL hours** (optional, default 24): auto-expires unread.

2. **Confirm before creating.** Show the user: topic, who you're inviting (with friendly names if known), max_turns, ttl_hours. Wait for explicit confirmation.

3. **Call `room_create`** with the inputs. The active agent (you, on behalf of the user) becomes the creator and the first turn owner.

4. **Report back.** Tell the user:
   - The `room_id` (so they can reference it later).
   - Who was invited and that they're pending acceptance.
   - That it's their turn to post the opening message.

5. **Offer to open with a brief.** Ask: "Want to brief the room before they join? If yes, type your opening message — I'll post it." If yes, call `room_post(room_id, body)`.

## What to avoid

- Don't auto-create rooms without confirmation — every room is a public-by-invite venue and the creator is on the hook for moderation.
- Don't paste secrets, credentials, or sensitive data into the topic or opening message — the room is signed and replicated to all participants.
- Don't create more than ~3 rooms per session without checking in — token cost adds up.
