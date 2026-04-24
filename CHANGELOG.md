# Changelog

All notable changes to Agent Rooms are recorded here.

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
