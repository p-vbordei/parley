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

Scaffold only — no code yet. Just `README.md`, this file, and the MVP plan.

## The plan

Everything lives in [`docs/plans/2026-04-24-agentrooms-01-mvp.md`](docs/plans/2026-04-24-agentrooms-01-mvp.md).

Covers:
- Data model (3 tables: rooms, participants, messages)
- API surface (6 endpoints, Ed25519 signatures per request)
- MCP tool surface (6 tools)
- 4 skills for Claude Code
- Token cost analysis
- Security checklist
- 10 tasks with checkboxes for execution
- Acceptance criteria

## Next step

**Task 1 from the plan:** scaffold `backend/` with `pyproject.toml`,
`Dockerfile`, `docker-compose.yml`, `alembic.ini`, and the three SQLAlchemy
models. No business logic yet — just skeleton + first migration + model
roundtrip tests.

Suggested entry prompt for this repo: *"Execute Task 1 from the MVP plan."*

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
