# Next steps

Checkpoint after v0.1.0. Read top-down — items are roughly in the order
you'd want to do them.

State at this point: **61 tests green**, 25 conformance vectors green,
[`SPEC.md`](../SPEC.md) **v0.3.0 DRAFT** published with TOC, CI workflow
committed, end-to-end demo working via `scripts/demo.sh`, full
documentation suite. Five edge-case bugs fixed in v0.2.1; v0.3.0 closed
the last v0.2 §10.2 boundary via server-side seen-hash dedup on
`create_room`. `v0.1.0`, `v0.2.0`, `v0.2.1`, and `v0.3.0` tags exist
locally, **none pushed**.

## 0 · Before anything else — you, not me

These four items are user-owned. They need human judgement or interactive
auth that a code-writing session cannot supply.

- [x] **Real name: `parley`.** Renamed end-to-end in v0.3.0:
      Python packages (`parley`, `parley_mcp`, `parley_cli`), env-var
      prefix (`PARLEY_`), service names, plugin ID, all docs.

- [ ] **`railway login && railway up`.** [`docs/deploy.md`](deploy.md)
      has the four commands. Interactive auth + your billing account —
      I cannot do this for you.

- [ ] **Smoke-test the plugin in a real Claude Code session.** Register
      the plugin, try a bilingual trigger phrase (`deschide o cameră cu
      …` or `open a room with …`). This is the last unchecked item in
      Task 7 of the MVP plan.

- [ ] **Push when you're happy.** `git push && git push --tags`. I held
      these back per the release protocol; tag `v0.1.0` exists only
      locally right now.

## 1 · v0.1.x — small hygiene items I can take next session

Low-risk, high-value cleanups. Each ~1 focused session. Pick any order.

- [ ] **README CI badge.** After first push, add a GitHub Actions badge
      at the top of [`README.md`](../README.md). Blocked on repo URL
      being known (waits on rename + push).

- [ ] **Conformance README stanza for non-Python implementations.** A
      Rust / Go / TS cookbook showing the exact imports and assertions
      to run the same JSON vectors. Short — half a page each.

- [ ] **Rate-limit the conformance runner.** Vectors can't grow forever;
      add a check that full run stays under a budget (currently ~0.1s;
      budget 5s). Catches bloat early.

- [ ] **Turn the Phase-2 tickets in [`SCOPE.md`](../SCOPE.md) into
      actual issues** once the repo has a public URL. One per row in
      the DEFERRED table.

## 2 · v0.2 — pick ONE of these, not all

Each is a substantial piece. The right v0.2 is whichever answers the
question "what's the first thing a second organization asks for?"

### 2a · ~~Replay protection on `create_room`~~ — SHIPPED in v0.2.0

Closed the v0.1.0 gap. `created_at` now in the signed payload of
`create_room`, `accept`, `close`; ±60s freshness enforced. Within-60s
replay residual on `create_room` documented in SPEC §10.2 — see v0.3
follow-up below.

### 2a' · ~~Server-side seen-hash dedup~~ — SHIPPED in v0.3.0

Closed the within-window replay residual on `create_room` via a
60s-rolling SHA-256 set in
[`backend/src/parley/services/dedup.py`](../backend/src/parley/services/dedup.py).
The §10.2 entry is gone.

### 2a'' · Multi-worker dedup backing store (v0.3.x or v0.4)

The v0.3 dedup is in-process. A multi-worker uvicorn deployment would
need a shared store (Redis, or a 60s-TTL Postgres table). Not blocking
single-worker prod; revisit when ops asks.

### 2b · Signed `GET` requests (medium)

Upgrade reads from "pubkey-claim auth" to either per-request signature
or a short-lived session token. Closes the other §10.2 boundary.

*Effort: ~3 days. Client plumbing is the bulk.*
*Risk: breaks every existing GET caller until they sign. Ship alongside
a `Accept-Version` header for graceful migration.*

### 2c · Federation between hubs (large, defining)

The real phase-2 prize. Options:
- **Nostr-style event envelope.** Signed events replicated across
  relays. Our signed-payload shapes would need to become self-contained
  events (include signer pubkey, event kind). Aligns with Nostr's proven
  dumb-relay gossip at scale.
- **ActivityPub-style S2S push.** More structure, more ceremony, harder
  for a small team to run.

Read [`docs/research/2026-04-24-prior-art-scan.md`](research/2026-04-24-prior-art-scan.md)
before committing to a direction.

*Effort: ~2-4 weeks. This is a research-first piece.*
*Risk: commits to a wire format that will be hard to change later.*

### 2d · WebSocket push (medium)

Replace polling with push. Should be gated on a real signal — don't do
this until you observe a room generating >1 poll/sec, because polling
is genuinely fine at current scale. When the signal arrives, Bun's
native WebSocket or FastAPI's WebSocketRoute is boring and cheap.

*Effort: ~1 week.*
*Risk: plugin client, CLI, and 4 skills all assume polling. Each gets a
new code path.*

## 3 · Longer-term — not a v0.2 candidate

- **A2A Signed Agent Cards** adoption at the identity layer. Compatible
  with our design, not required for the core rooms primitive. Revisit
  after federation lands.
- **Pubkey rotation / revocation.** Likely via a signed "rotate"
  message that binds the old pubkey to its successor. Low priority
  until a real user asks.
- **End-to-end encryption of `body`.** Transparent-transcript is a
  *feature* of v0.1. Encryption is a future opt-in, not a default.
- **Web dashboard for humans.** Drive via Claude Code, CLI, or Kindred.
  Not a product gap.
- **Rate limiting.** `max_turns` + `ttl_until` are the natural backpressure
  for v0.1. Add a token bucket per pubkey only when a hub has multiple
  noisy tenants.

## 4 · What we decided NOT to do (ever)

Kept here so scope creep has a place to die on arrival.

- Configurable auth providers (OAuth/OIDC/API keys). Violates the
  "dumb relay + signed messages" philosophy.
- Pluggable storage backends. An abstraction layer for a SQLite option
  is a YAGNI trap.
- Plugin system for custom room types. Variants should be skills, not
  primitives.
- GraphQL API. REST/JSON fits Claude Code plugin affordances with a
  smaller surface.
- Server-side LLM features (auto-reply, classification). Intelligence
  lives in skills.

## 5 · Health checks for future-me

Before shipping any v0.2 work, re-confirm:

- [ ] All [`SPEC.md`](../SPEC.md) §10.1 defenses still pass their
      tests in `backend/tests/test_security_boundaries.py`.
- [ ] All [`conformance/vectors/`](../conformance/vectors/) still pass
      `python conformance/run.py` and `pytest tests/test_conformance.py`.
- [ ] `examples/demo.py` still runs end-to-end with one command on a
      fresh clone.
- [ ] [`CHANGELOG.md`](../CHANGELOG.md) has a new `[0.2.0]` entry before
      tagging.
- [ ] [`SPEC.md`](../SPEC.md) banner flipped correctly (DRAFT → 1.0 at
      the point we commit to wire-format stability).
