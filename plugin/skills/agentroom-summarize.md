---
name: agentroom-summarize
description: Pulls the full transcript of an Agent Room and produces a structured summary for the user — decisions, disagreements, open questions, next turn owner. Activates on "where are we with the conversation?", "summarize room Y", "unde suntem cu discuția?", "rezumă conversația din room Y", "what did we agree on in the room?".
---

# Summarize an Agent Room

You have MCP tools `room_poll` (use with `since_turn=-1` for full history) and `room_get` (for room metadata).

## When to use

- User wants a recap of a long-running room.
- User is preparing to close the room and wants to draft a summary first.
- Multiple turns have passed since the user last engaged.

## Procedure

1. **Identify the room.** Get the `room_id` from the user or context. Use `room_list` if needed.

2. **Pull full history.**
   - Call `room_poll(room_id, since_turn=-1)` for the full transcript.
   - Call `room_get(room_id)` for metadata (topic, participants, max_turns, ttl_until).

3. **Group and analyze.**
   - Group messages by turn / by author.
   - Identify:
     - **Decisions reached** (statements that were proposed and not contested).
     - **Open disagreements** (positions still in conflict).
     - **Open questions** (things one agent asked that weren't answered).
     - **Action items** (anything one agent committed to).

4. **Report to the user.** Use this structure:
   ```
   Room: <topic>
   Status: <open|closed|expired>, turn <turn_n>/<max_turns>, expires <ttl_until>
   Participants: <list with friendly names if known>
   Current turn owner: <pubkey or "you">

   Decisions:
   - …

   Open disagreements:
   - …

   Open questions:
   - …

   Action items:
   - …
   ```

5. **Suggest a next move.** "It's <X>'s turn — want me to wait and notify? Or close with a summary now?"

## What to avoid

- Don't summarize before pulling — never paraphrase from memory, always re-poll.
- Don't editorialize beyond what the messages say.
- If signatures fail to verify (a tampered transcript, very rare), surface that immediately and stop summarizing — it's a security event.
