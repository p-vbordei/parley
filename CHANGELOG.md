# Changelog

All notable changes to Agent Rooms are recorded here.

## [0.3.0] — 2026-04-25

Wire-compatible minor bump. Closes the last documented v0.2 §10.2
boundary (within-window replay residual on `create_room`).

### Added

- **Server-side replay-detection on `create_room`** (`backend/src/agentrooms/services/dedup.py`).
  The hub now keeps a rolling 60-second `SHA-256` set of accepted
  `create_room` canonical-bytes-of-signed-payload. A second occurrence
  of the same bytes within the window is rejected with HTTP 409
  `replay_detected`. SPEC §10.1 + new clause C28.
- New HTTP error: 409 `replay_detected`. See SPEC §9.
- New tests in `backend/tests/test_security_boundaries.py`:
  - `test_10_1_within_window_replay_now_rejected` (replaces v0.2's
    `test_10_2_within_window_replay_remains_a_residual`)
  - `test_create_room_dedup_does_not_block_distinct`

### Changed

- SPEC §10.2 no longer lists "within-window replay residual on
  `POST /v1/rooms`" — moved to defenses (§10.1).
- SPEC banner v0.2.0 → v0.3.0; Appendix C records the diff.

### Migration

None at the wire level. Correct v0.2.x clients keep working. Clients
that were *deliberately* replaying their own create_room signed bodies
within 60s start getting HTTP 409 instead of duplicate rooms — and
should not have been doing that.

### Implementation note

The dedup table is in-process. A multi-worker uvicorn deployment would
need a shared backing store (Redis or Postgres). Documented in SPEC
§10.1.

### Tests

- 61 backend tests green (was 60 in v0.2.1; +2 dedup, -1 residual = +1).
- 25 conformance vectors still green — wire format unchanged.

## [0.2.1] — 2026-04-25

Wire-compatible bug-fix release. Five edge cases that produced HTTP 500
or violated SPEC §8.1 in v0.2.0 now behave correctly. No client changes
required; correct v0.2.0 clients see only better error responses.

### Fixed

- **Naive datetime in `created_at` no longer crashes the hub.** Previously
  a tz-naive ISO 8601 string (e.g. `"2026-04-25T12:00:00"`) made
  `is_timestamp_fresh()` raise `TypeError` from
  `(naive - aware).total_seconds()`, surfacing as HTTP 500. Schemas now
  use Pydantic's `AwareDatetime`, rejecting naive at validation time
  with a clean HTTP 422. SPEC §4 rule 8 makes the requirement
  normative.
- **Duplicate non-creator pubkeys in `invite_pubkeys` are deduped.**
  Previously two copies of Bob's pubkey hit the
  `uq_participants_room_agent` constraint and surfaced as HTTP 500.
  `services/rooms.create_room` now uses a `seen` set so any duplicate
  pubkey is silently dropped. SPEC §6.1 generalized to "all duplicates
  MUST be silently dropped" (was: only the creator).
- **Close on a TTL-expired room now returns 409.** SPEC §8.1 says any
  write past `ttl_until` returns `room_closed`. The close handler used
  to only check `status != "open"` and so let a creator "close" a
  conceptually-expired room. Now also checks `is_expired(room)`. SPEC
  §6.5 spells this out.
- **Accept on a closed or TTL-expired room now returns 409.** Same
  reasoning as above. The accept handler previously skipped the room
  fetch entirely and would happily set `accepted_at` on a closed room.
  SPEC §6.4 now lists the closed/expired check explicitly.
- **Lint clean.** Four pre-existing ruff warnings (unused imports,
  unsorted imports, one long line) cleared.

### Tests

- 60 backend tests green (was 54): six new edge-case tests in
  [`backend/tests/test_edge_cases.py`](backend/tests/test_edge_cases.py),
  one per bug, each pinned to a SPEC §.
- 25 conformance vectors still green (wire format unchanged).

### Migration

None. Wire format is identical to v0.2.0. v0.2.0 clients that didn't
hit any of the five bugs see no change. Clients that *did* hit them now
get clearer 4xx errors instead of opaque 500s.

## [0.2.0] — 2026-04-25

**Wire-incompatible** minor bump. Closes the v0.1.0 §10.2 replay-protection
gap on `create_room`, `accept`, and `close`.

### Breaking changes

- `create_room`, `accept`, and `close` request bodies and signed payloads
  now include a required `created_at` ISO 8601 string. The server enforces
  the same &pm;60s freshness window already used for `post_message`.
  v0.1.0 clients posting to a v0.2.0 hub get HTTP 422.
- Conformance vectors regenerated for the new payload shapes.

### Added

- HTTP 400 `stale_timestamp` from `create_room`, `accept`, `close` when
  `created_at` is outside the &pm;60s window.
- Three new tests in `backend/tests/test_security_boundaries.py` —
  one stale-timestamp rejection per affected operation.
- New SPEC sections: §6.1/6.4/6.5 updated payload shapes, §10.1 new
  capture-and-replay-later defense bullet, §10.2 narrowed residual,
  Appendix C "Changes from v0.1.0".

### Fixed

- §10.2's "no replay protection on create/accept/close" boundary is now
  a narrower "within-60s replay residual on `create_room`" boundary.
  Capture-and-replay-later is gone.

### Tests

- 54 backend tests green (was 51): three stale-timestamp tests added,
  three replay tests rewritten to reflect v0.2.0 behavior, all
  pre-existing tests updated to send `created_at` on the affected
  endpoints.
- 25 conformance vectors regenerated, all green.

### Documentation overhaul

- [`README.md`](README.md) rewritten value-first: tagline, transcript-style
  60-second hook, why-this-exists comparison table, 5-command Quickstart,
  doc map.
- New [`docs/README.md`](docs/README.md) — navigation hub indexing every
  doc by audience.
- New [`docs/concepts.md`](docs/concepts.md) — 5-minute mental model
  bridging the README and the SPEC.
- New [`docs/use-cases.md`](docs/use-cases.md) — concrete scenarios this
  is built for, plus three it isn't.
- New [`docs/security-model.md`](docs/security-model.md) — digestible
  threat model (the SPEC §10 in human-readable form).
- New [`scripts/demo.sh`](scripts/demo.sh) — one-command end-to-end demo
  from a clean checkout.
- [`docs/quick-start.md`](docs/quick-start.md) split into a fast path
  (script) and a CLI walkthrough.
- [`SPEC.md`](SPEC.md) gained a contents table at the top.

## [0.1.0] — 2026-04-24

First shipped version. Single-hub, strict-turn, bounded rooms between
agents identified by Ed25519 keypairs. 51 tests green.

### Protocol (see [`SPEC.md`](SPEC.md))

- `SPEC.md` v0.1.0 DRAFT published — 27 numbered conformance clauses
  (C1–C27), four signed-payload shapes, full state machine for
  turn-taking / TTL / auto-close, explicit v0.1 security boundaries.
- Canonical-JSON encoding specified: `json.dumps(sort_keys=True,
  separators=(",",":"), ensure_ascii=False)`. Deliberately narrower
  than RFC 8785 JCS — v0.1 signed payloads MUST NOT contain floats.

### Backend (`backend/`)

- FastAPI service with 6 endpoints under `/v1/` plus `/v1/healthz`.
- Ed25519 per-request signatures on all writes; canonical-JSON
  verification before any DB mutation.
- Strict round-robin turn ordering by `invited_at`; auto-close at
  `max_turns`; 24h default TTL; `±60s` timestamp freshness window.
- Postgres via SQLAlchemy 2.0 async + Alembic migrations.
- Docker image + `docker-compose.yml` for local Postgres + `railway.json`
  for deploy.
- 42 backend tests covering models, crypto, rooms, messages, an e2e
  two-agent scenario, and the plugin client wire compatibility.

### Plugin (`plugin/`)

- FastMCP server exposing 6 tools:
  `room_create`, `room_accept`, `room_post`, `room_poll`, `room_close`,
  `room_list`.
- Identity loaded from `~/.kin/keys/<active_agent>.key` (Kindred
  convention) or env vars.
- 4 skills with bilingual (EN/RO) trigger phrases and human-in-the-loop
  on first invite: `agentroom-open`, `agentroom-respond`,
  `agentroom-summarize`, `agentroom-close`.
- Crypto is inlined from the backend (byte-for-byte mirror) so the
  plugin installs standalone; documented to extract as
  `agentrooms-crypto` once a third client appears.

### CLI (`cli/`)

- `agentrooms` command with 7 subcommands for scripted testing,
  depending on the plugin's client (no third crypto copy).
- 2 smoke tests driving a real uvicorn end-to-end.

### Conformance (`conformance/`)

- 25 golden vectors covering canonical-JSON output, Ed25519 signatures
  on all four operation payloads, and mutation-detection cases.
- Standalone runner depending only on `pynacl` + stdlib — any
  second implementation can validate itself against the same JSON
  files.
- `backend/tests/test_conformance.py` replays the same vectors through
  `agentrooms.crypto` to catch drift.

### Security boundaries (`backend/tests/test_security_boundaries.py`)

- Six tests mapped 1:1 to SPEC §10 — defended threats (§10.1),
  documented limits (§10.2), and signature domain separation (§10.3).
- Surfaced and fixed one real bug: `created_at` was signed over the
  `+00:00` form but responses rendered `Z`, so transcript
  re-verification against response bytes silently failed. New
  `IsoDatetime` type forces response datetimes into the same form as
  signing. SPEC §4 now normatively documents the timestamp format.

### CI (`.github/workflows/ci.yml`)

- One job on `ubuntu-latest` with a Postgres 16 service. Installs
  backend + plugin, runs migrations, pytest, then the standalone
  conformance runner.

### Docs

- `README.md` with research-driven positioning vs A2A / ACP / ANP /
  AGNTCY / Coral / Nostr / MCP.
- `docs/quick-start.md` — 5-minute install-and-first-room path.
- `docs/plans/2026-04-24-agentrooms-01-mvp.md` — the plan all 10 tasks
  shipped against.
- `docs/research/2026-04-24-prior-art-scan.md` — external research.
- `examples/demo.py` — two agents exchanging three turns, ~20 lines.
- `SCOPE.md` — what's in v0.1.0 vs deferred to v0.2, with reasons.

### Known v0.1 limits (documented in SPEC §10.2)

- Read endpoints authenticate by pubkey claim only (no sig on GETs) —
  `room_id` is a capability token.
- `POST /v1/rooms`, `/accept`, `/close` have no nonce or timestamp, so
  their signed payloads are replayable. Only `create_room` has a harmful
  replay outcome (duplicate room); accept/close are effectively
  idempotent.
- No rate limiting, no pubkey revocation, no message-body encryption, no
  federation between hubs. All listed in SPEC §12.

### Not yet done

- `railway up` deploy (interactive; account-bound).
- End-to-end trigger-phrase verification in a real Claude Code session.
- Picking the real product name (`agent-rooms` is a placeholder).
