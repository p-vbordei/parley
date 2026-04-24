---
name: agentroom-close
description: Closes an Agent Room with an optional summary, marking the conversation as final. Activates on "close the room with decision X", "închide cu decizia X", "terminăm room-ul", "we're done with that conversation", "wrap up room Y". Optionally saves the transcript to a sister system (e.g., Kindred) afterward.
---

# Close an Agent Room

You have MCP tools `room_poll`, `room_close`, and (if installed) the Kindred plugin's `kin_contribute` for archiving.

## When to use

- User explicitly wants to end a conversation.
- The conversation has reached a natural decision point.
- The user wants to save the outcome for later reference.

## Procedure

1. **Pull the full transcript.** Call `room_poll(room_id, since_turn=-1)`.

2. **Draft a summary with the user.**
   - Propose a 1-3 sentence summary of: what was decided, what's deferred, who owes what.
   - Get user approval on the exact wording. The summary is preserved on the closed room and visible to every participant.

3. **Confirm authorization.**
   - Only the **creator** OR the **current turn owner** can close. If the user's agent is neither, surface that and ask if they want to wait until it's their turn (or ask the creator to close).

4. **Call `room_close`.**
   - `room_close(room_id, summary=<approved text>)`.
   - On success, the room is `closed`; no further posts accepted.

5. **Offer to archive.**
   - Ask: "Save the transcript to Kindred? If yes, which kindred and what tags?"
   - If yes and Kindred is installed: call `kin_contribute` with the transcript as content, type=`routine` or `claude_md` based on context, suggested tags from the room topic.

## What to avoid

- Don't close mid-disagreement without user confirmation — the close is irreversible (the room cannot be re-opened).
- Don't summarize beyond what the messages support — quote-and-paraphrase, don't fabricate.
- Don't archive secrets to Kindred without user approval — the user knows what's sensitive.
