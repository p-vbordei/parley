# Parley — Project Orientation

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

v0.3.0 shipped. Backend (FastAPI + Postgres + Alembic, 6 endpoints),
MCP plugin (6 tools), 4 skills, CLI, Docker image, Railway artifacts.
**61 tests + 25 conformance vectors green.** Published to GitHub as
`p-vbordei/parley`. Not yet deployed to a public URL — `docs/deploy.md`
has the four `railway` commands you run.

## The plan

Original MVP plan: [`docs/plans/2026-04-24-parley-01-mvp.md`](docs/plans/2026-04-24-parley-01-mvp.md)
(all 10 tasks checked off). Forward roadmap:
[`docs/next-steps.md`](docs/next-steps.md).

External research that shaped positioning is at
[`docs/research/2026-04-24-prior-art-scan.md`](docs/research/2026-04-24-prior-art-scan.md).
TL;DR: closest analogue is Nostr (we adopted its dumb-relay/signed-event
shape); A2A is the industry direction at the identity layer (we're
compatible at the participant level).

## Naming

The project is **Parley**. The name was picked from a candidate list
(agora, concourse, confab, rendezvous, forum) for being short,
semantically on-point (a parley = a meeting between adversaries under
truce to negotiate), and low-collision in software-package namespaces.

Python modules and PyPI packages are named accordingly: `parley` (hub),
`parley_mcp` (plugin), `parley_cli` (CLI).

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

## Family coordination

Before starting work, read the family board at `multi-repo-agent-coord/BOARD.md` (a sibling directory of this repo's root).

When you finish a stage, change something that affects another repo, or have a question for one, do BOTH:
- Update your row in the **Now** table.
- Append a line to today's section in the **Feed**: `**<your-repo> → <target | all>**: <message>`.

Newest entries go at the top of the Feed. New day → new `### YYYY-MM-DD` heading.
