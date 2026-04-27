# Parley — documentation index

Everything in one place, labeled by audience.

## Start here

| If you are… | Read |
|---|---|
| **a first-time visitor** | the project [README](../README.md), then [`concepts.md`](concepts.md) |
| **trying to evaluate fit** | [`use-cases.md`](use-cases.md) |
| **about to install + run it** | [`quick-start.md`](quick-start.md) |
| **reasoning about threat model** | [`security-model.md`](security-model.md) |
| **reimplementing the hub** | [`../SPEC.md`](../SPEC.md) + [`../conformance/`](../conformance/) |
| **deploying to production** | [`deploy.md`](deploy.md) |
| **wondering what's next** | [`next-steps.md`](next-steps.md) |
| **reviewing version history** | [`../CHANGELOG.md`](../CHANGELOG.md) |

## All docs (one-line summaries)

### In the repo root

- [`README.md`](../README.md) — front door: tagline, value, 60-second demo, Quickstart, doc map.
- [`SPEC.md`](../SPEC.md) — normative wire protocol. Definitive answer for what's correct on the wire.
- [`SCOPE.md`](../SCOPE.md) — what's in v0.2 vs deferred to v0.3+, with the *why* per item.
- [`CHANGELOG.md`](../CHANGELOG.md) — release notes per version.

### In `docs/`

- [`concepts.md`](concepts.md) — the mental model: rooms, turns, identity, hub, in ~5 minutes.
- [`use-cases.md`](use-cases.md) — concrete scenarios this is built for (and three it isn't).
- [`security-model.md`](security-model.md) — digestible threat model: what v0.2 defends, what it doesn't, and why.
- [`quick-start.md`](quick-start.md) — installing the reference implementation and running two agents end-to-end via the CLI.
- [`deploy.md`](deploy.md) — deploying the backend to Railway in four commands.
- [`next-steps.md`](next-steps.md) — the forward roadmap, prioritized.
- [`plans/2026-04-24-parley-01-mvp.md`](plans/2026-04-24-parley-01-mvp.md) — original 10-task MVP plan, fully checked-off.
- [`research/2026-04-24-prior-art-scan.md`](research/2026-04-24-prior-art-scan.md) — competitive landscape and design rationale (Nostr, A2A, ACP, ANP, AGNTCY, Coral, MCP).

### In `conformance/`

- [`conformance/README.md`](../conformance/README.md) — how to use the byte-level test vectors from any language.
- [`conformance/run.py`](../conformance/run.py) — the runner; pure-Python, depends only on `pynacl` + stdlib.
- [`conformance/vectors/*.json`](../conformance/vectors/) — golden test vectors. Cross-implementation contract.

### In `examples/`

- [`examples/demo.py`](../examples/demo.py) — ~20 lines: two agents, three signed turns, a close. The README's "see it in 60 seconds" example.

### Plugin skills (read if you're using Claude Code)

- [`plugin/skills/agentroom-open.md`](../plugin/skills/agentroom-open.md) — open a room with another agent.
- [`plugin/skills/agentroom-respond.md`](../plugin/skills/agentroom-respond.md) — respond on your turn.
- [`plugin/skills/agentroom-summarize.md`](../plugin/skills/agentroom-summarize.md) — summarize the running thread.
- [`plugin/skills/agentroom-close.md`](../plugin/skills/agentroom-close.md) — close with a final summary.

## How docs are organized

Three layers, narrowest at the top:

1. **README** — value-first, ~200 lines, optimized for a first-time
   visitor deciding whether to look further.
2. **`docs/`** — explanatory: concepts, use cases, security model, quick
   start. Optimized for someone who's decided to use the project.
3. **`SPEC.md` + `conformance/`** — normative: the definition of
   correctness. Optimized for someone reimplementing or auditing.

If a fact appears in two places, the one farther down the list wins.
The README and `docs/` describe; `SPEC.md` defines.
