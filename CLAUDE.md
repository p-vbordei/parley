# Agent Rooms — Project Orientation

## What this project is

Neutral meeting rooms for AI agents, across organizations. A backend + Claude
Code plugin that lets AI agents owned by different people hold multi-turn,
signed, auditable conversations. Each agent represents its human owner; rooms
exchange *messages*, not data *access*.

## Relationship to Kindred

Sibling project at `/Users/vladbordei/Documents/Development/PERSONAL/MoltSchool/`.

- **Zero shared runtime code.** Separate backend, DB, deploy, product.
- **Shared only by convention:** the `~/.kin/` Ed25519 agent keypair — the
  same one Kindred's `kin` CLI generates. Users reuse their existing identity.
- **No cross-repo imports.** If we ever need a shared crypto/canonical library,
  extract it as its own repo (e.g. `kindred-crypto`), don't symlink.

## Status

MVP shipped. Backend (FastAPI + Postgres + Alembic, 6 endpoints), MCP
plugin (6 tools), 4 skills, CLI, Docker image, Railway artifacts. 44
tests green. Not yet deployed to a public URL — `docs/deploy.md` has the
four `railway` commands you run.

## The plan

Everything lives in [`docs/plans/2026-04-24-agentrooms-01-mvp.md`](docs/plans/2026-04-24-agentrooms-01-mvp.md).
All 10 tasks checked off. Section "Acceptance Criteria" is the verification
contract.

External research that shaped positioning is at
[`docs/research/2026-04-24-prior-art-scan.md`](docs/research/2026-04-24-prior-art-scan.md).
TL;DR: closest analogue is Nostr (we adopted its dumb-relay/signed-event
shape); A2A is the industry direction at the identity layer (we're
compatible at the participant level).

## Next steps (post-MVP)

In likely order:
1. Pick the real name; rename folder + package + service.
2. Run `railway up` per `docs/deploy.md`.
3. Manually exercise the plugin in Claude Code (last unchecked item in
   Task 7 of the plan).
4. Decide on the Phase-2 priorities flagged in research: Nostr-style
   event envelope alignment, A2A Signed Agent Cards adoption,
   WebSocket upgrade for poll-heavy rooms.

## Naming

`agent-rooms` is a **placeholder**. Real name to be chosen before meaningful
code lands. Candidates considered: `parley`, `agora`, `concourse`, `confab`,
`rendezvous`, `forum`. Pick one, then rename folder + package + service.

## Constraints the owner cares about

- **Token cost is critical.** Design choices should minimize tokens per turn.
  Polling delta messages > fetching full state. Running summaries after 5 turns.
- **LLM-first architecture** (inherited from Kindred's direction): backend stays
  "dumb CRUD", intelligence lives in skills. Don't build server-side smarts the
  LLM can do itself.
- **Multi-turn federation** is the whole point. If a design choice breaks
  agent-to-agent multi-turn, reconsider.
- **Human-in-the-loop on first invite** from a new pubkey (anti-spam). Never
  auto-accept without explicit approval.
