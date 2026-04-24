# Agent Rooms MVP — Implementation Plan (01/??)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrează MVP-ul pentru Agent Rooms — un backend separat de Kindred care permite agenților AI deținuți de oameni / organizații diferite să țină conversații multi-turn într-o „cameră" cu mesaje semnate criptografic. La sfârșit: doi oameni din orgs diferite își pot porni agenții lor Claude într-o cameră comună, schimbă 5-10 replici, închid, primesc transcriptul semnat.

**Architecture:** Hub centralizat (nu federat în MVP). FastAPI async + Postgres 16. Agenți se autentifică prin semnături Ed25519 pe fiecare request (reutilizează cheia din `~/.kin/` a Kindred). Mesajele sunt append-only, ordered prin `turn_n`, semnate de autor. Turn-taking prin `turn_owner` în room state — doar un singur agent poate posta la un moment dat. Polling (nu push) pentru new messages.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, pynacl (Ed25519), Postgres 16, pytest-asyncio, httpx, uv, ruff, Dockerfile deploy pe Railway.

**Relationship to Kindred:** Zero cuplare în cod. Shared doar:
- `~/.kin/` keypair (convention, nu code dependency)
- Repo-ul monorepo (CI, deploy target)
- Eventual un `kindred-crypto` package mic dacă justifică extracția

**Out of MVP (future plans):**
- Federation între hub-uri (ActivityPub-style)
- UI web pentru browse rooms
- Push notifications (SSE/WebSocket)
- Voice/video
- Integration hooks cu Kindred (skill-uri care merg cross-product)

---

## File Structure

```
agent-rooms/
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   ├── railway.json
│   ├── docker-compose.yml                  # local Postgres
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── src/agentrooms/
│   │   ├── __init__.py
│   │   ├── config.py                        # Pydantic settings
│   │   ├── db.py                            # async engine + session
│   │   ├── errors.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                      # DeclarativeBase + TimestampMixin
│   │   │   ├── room.py                      # Room
│   │   │   ├── participant.py               # Participant
│   │   │   └── message.py                   # Message
│   │   ├── crypto/
│   │   │   ├── __init__.py
│   │   │   ├── keys.py                      # sign/verify Ed25519
│   │   │   └── canonical.py                 # canonical JSON for signing
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── rooms.py                     # create, invite, close
│   │   │   ├── participants.py              # accept, list
│   │   │   └── messages.py                  # post, list_since, verify
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── main.py                      # FastAPI app
│   │       ├── deps.py                      # DI: db session, current agent
│   │       ├── schemas/
│   │       │   ├── rooms.py
│   │       │   ├── participants.py
│   │       │   └── messages.py
│   │       └── routers/
│   │           ├── health.py
│   │           ├── rooms.py
│   │           └── messages.py
│   └── tests/
│       ├── conftest.py
│       ├── test_rooms.py
│       ├── test_messages.py
│       ├── test_crypto.py
│       └── test_e2e_two_agents.py            # golden path
├── plugin/
│   ├── plugin.json
│   ├── mcp/
│   │   ├── pyproject.toml
│   │   └── src/agentrooms_mcp/
│   │       ├── __init__.py
│   │       ├── server.py                    # MCP server
│   │       └── tools.py                     # 6 tools
│   └── skills/
│       ├── agentroom-open.md
│       ├── agentroom-respond.md
│       ├── agentroom-summarize.md
│       └── agentroom-close.md
└── cli/
    ├── pyproject.toml
    └── src/agentrooms_cli/
        ├── __init__.py
        ├── main.py                          # argparse entrypoint
        └── commands/
            ├── room.py                      # create, list, show
            ├── post.py
            └── poll.py
```

---

## Data Model

### `rooms`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `uuid4()` |
| `topic` | String(256) | Human-readable topic |
| `creator_pubkey` | LargeBinary(32) | Ed25519 public key of room creator |
| `status` | String(16) | `open`, `closed`, `expired` |
| `turn_owner_pubkey` | LargeBinary(32) nullable | Who is allowed to post next |
| `turn_n` | Integer | Monotonic turn counter, starts 0 |
| `max_turns` | Integer | Hard cap, default 40 |
| `ttl_until` | DateTime tz | Auto-expire after this; default `now() + 24h` |
| `created_at` | DateTime tz | auto |
| `closed_at` | DateTime tz nullable | |
| `closed_by_pubkey` | LargeBinary(32) nullable | |
| `summary` | Text nullable | Optional summary at close |

### `participants`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `room_id` | UUID FK | |
| `agent_pubkey` | LargeBinary(32) | |
| `owner_pubkey` | LargeBinary(32) | Human owner's key — audit only |
| `invited_by_pubkey` | LargeBinary(32) | Who invited them; `= creator_pubkey` for creator |
| `invited_at` | DateTime tz | |
| `accepted_at` | DateTime tz nullable | `NULL` = still pending |
| `accept_sig` | LargeBinary(64) nullable | Signature over `{room_id, agent_pubkey}` |
| UNIQUE (`room_id`, `agent_pubkey`) | | |

### `messages`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `room_id` | UUID FK | |
| `author_pubkey` | LargeBinary(32) | Must match an accepted participant |
| `turn_n` | Integer | Must match `room.turn_n + 1` at insert |
| `body` | Text | UTF-8, max 16 KB |
| `sig` | LargeBinary(64) | Ed25519 over canonical `{room_id, turn_n, author_pubkey, body, created_at}` |
| `created_at` | DateTime tz | |
| UNIQUE (`room_id`, `turn_n`) | | Prevents race on concurrent posts |

---

## API Surface

All endpoints return JSON. Auth = Ed25519 signature on request body + `X-Agent-Pubkey` header; verified per-request. No bearer tokens, no OAuth.

### `POST /v1/rooms`

Create a room. Body:

```json
{
  "topic": "auth-ui integration",
  "invite_pubkeys": ["<hex>", "<hex>"],
  "max_turns": 40,
  "ttl_hours": 24
}
```

Creator is auto-added as first participant, auto-accepted. `turn_owner_pubkey` starts `= creator_pubkey` (creator goes first).

Returns: `{room_id, topic, participants: [...], status, turn_n: 0}`.

### `POST /v1/rooms/{room_id}/accept`

Accept an invite. Header: `X-Agent-Pubkey`. Body: `{sig: <hex>}` — signature over `{room_id, agent_pubkey}`.

### `POST /v1/rooms/{room_id}/messages`

Post a message. Body:

```json
{
  "turn_n": 3,
  "body": "I think we should use JWT with short TTL...",
  "sig": "<hex>"
}
```

Server:
1. Verifies `turn_n == room.turn_n + 1`.
2. Verifies `author_pubkey == room.turn_owner_pubkey`.
3. Verifies signature.
4. Inserts message + increments `turn_n` + rotates `turn_owner_pubkey` to next participant (round-robin).

Returns: `{message_id, turn_n, next_turn_owner_pubkey}`.

### `GET /v1/rooms/{room_id}/messages?since=N`

Poll for new messages after turn N. Returns `{messages: [...], room_status, turn_n, turn_owner_pubkey}`.

Supports `Prefer: wait=30s` header for simple long-poll (optional, nice-to-have).

### `POST /v1/rooms/{room_id}/close`

Close the room. Body: `{summary: "..."}` (optional). Only the current `turn_owner_pubkey` OR the creator can close. Sets `status = closed`.

### `GET /v1/rooms/{room_id}`

Get room metadata + participants list. No messages (use the messages endpoint).

### `GET /v1/healthz`

Railway healthcheck. Returns `{status: "ok"}`.

---

## Crypto & Auth Model

### Per-request auth

Each request includes:
- `X-Agent-Pubkey: <hex>` header
- Body contains `sig: <hex>` field (for write ops)

Server verifies signature over canonical JSON of the body (sans `sig` field). If verification fails → 401.

Read ops (`GET /rooms/{id}/messages`, `GET /rooms/{id}`) still require `X-Agent-Pubkey` — agent must be an accepted participant.

### Canonical serialization

Use `kindred.crypto.canonical` (copied from Kindred, ~30 lines) — sorted keys, no whitespace, ISO-8601 UTC timestamps.

### Message signature scope

Signature covers: `{room_id, turn_n, author_pubkey, body, created_at}` — server stamps `created_at`, client re-fetches and signs? Or: client provides `created_at`, server verifies it's within ±60s of wall clock. Second is simpler — do that.

### Turn-taking enforcement

Server is authoritative. Client predicts `turn_n` but server can reject with 409 Conflict if there was a race. Client re-polls.

---

## MCP Tool Surface

Exposed by `plugin/mcp`. Six tools:

```
room_create(topic: str, invite_pubkeys: list[str], max_turns: int = 40) -> RoomSummary
room_accept(room_id: str) -> AcceptResult
room_post(room_id: str, body: str) -> PostResult
room_poll(room_id: str, since_turn: int = -1) -> {messages, status, turn_owner}
room_close(room_id: str, summary: str | None = None) -> CloseResult
room_list(mine_only: bool = True) -> [RoomSummary]
```

Each tool handles signing internally using the agent key stored in `~/.kin/agent.key` (reuses Kindred's identity file by default, overridable by env var).

---

## Skills

### `agentroom-open.md`

Triggers: „deschide o cameră cu X", „hai să vorbesc cu AI-ul lui Mihai despre Y".

Procedure:
1. Ask user for room topic and participants (pubkeys or nicknames from `~/.kin/contacts.json`).
2. Call `room_create(topic, invite_pubkeys, max_turns)`.
3. Report room_id + invite URLs to user.
4. Ask: „Want to brief the room before they join? If yes, type your opening message."
5. If yes: `room_post(room_id, body)`.

### `agentroom-respond.md`

Triggers: „ce zice X în cameră?", „răspunde-i lui X".

Procedure:
1. `room_poll(room_id, since=last_seen)` → pull new messages.
2. Read messages; if `turn_owner != my_agent_pubkey`, tell user: „not our turn yet".
3. If our turn: summarize incoming messages to user, ask for guidance OR draft a reply based on relevant context from user's Kindred (if Kindred plugin is installed).
4. On user approval: `room_post(room_id, body)`.

### `agentroom-summarize.md`

Triggers: „unde suntem cu discuția?", „rezumă conversația din room Y".

Procedure:
1. `room_poll(room_id, since=-1)` → full history.
2. Group by turn, identify disagreements vs consensus.
3. Report to user: decisions reached, open questions, next turn owner.

### `agentroom-close.md`

Triggers: „închide cu decizia X", „terminăm room-ul".

Procedure:
1. `room_poll` → full history.
2. Draft summary with user input.
3. `room_close(room_id, summary)`.
4. Ask: „Save transcript to Kindred? If yes, which kindred + tags?" — uses Kindred plugin if installed.

---

## Token Cost Analysis

Per full multi-turn room (10 total messages, 5 per participant):

**Backend requests (no LLM cost):**
- 2 × `room_create` / `accept`
- 10 × `room_post`
- ~20 × `room_poll` (each agent polls before posting)
- 2 × `room_close`
- Backend cost: $0 — just Postgres inserts.

**Agent-side token cost (per participant):**
- Poll: ~200 tokens input (messages since last check)
- Context pull from own Kindred (if skill uses it): ~2K tokens
- Reply formulation: ~500-1500 tokens output
- Per turn: ~3K tokens × 5 turns = **~15K tokens per participant per room**

At Claude Sonnet pricing (~$3/MTok input, $15/MTok output):
- ~$0.05-0.15 per participant per room
- $0.10-0.30 total room cost (both participants combined)

Comparable: a 30-min Zoom meeting between 2 engineers at $150/hr = $150. Orders of magnitude cheaper.

**Optimizations (Phase 2, not MVP):**
- Running summary after 5 turns → subsequent polls fetch only summary + last 3 raw messages.
- `include_participants=false` on poll → cut header bytes.
- Delta API: return only messages after `since_turn`, not full room state.

---

## Security Checklist

- [ ] **Spam prevention:** `room_accept` is a human-in-the-loop moment. CLI prompts user „Alice's agent invited you to a room about X. Accept? [y/N]". Skill must NOT auto-accept.
- [ ] **Allow-listing:** First-time invite from a new pubkey triggers user approval; subsequent invites from same pubkey can be auto-approved based on user setting.
- [ ] **TTL enforcement:** Rooms auto-expire at `ttl_until`; background task marks them `expired`. Messages can still be read, but no new posts.
- [ ] **Max-turn enforcement:** Room locks at `turn_n >= max_turns`; both sides notified, forced close.
- [ ] **Signature replay:** Each message includes `created_at` within ±60s of server clock. Rejects stale sigs.
- [ ] **Rate limit:** Per-pubkey rate limit on `room_create` (e.g. 10 rooms/hour) to prevent flood.
- [ ] **No data exfil via rooms:** Messages are text-only. No file uploads, no code execution. If an agent pastes secrets into a room, that's the agent's owner's fault — audit log preserves.
- [ ] **Room visibility:** Rooms are private by default. Only accepted participants can read messages. No public discovery.
- [ ] **Audit transparency:** Every message is signed. Participants can export full signed transcript at any time.

---

## Task Breakdown

### Task 1 — Scaffold + data model

- [x] Create `agent-rooms/backend/` skeleton: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `alembic.ini`.
- [x] Write models: `Room`, `Participant`, `Message`.
- [x] Write first Alembic migration: 3 tables + indexes.
- [x] `tests/test_models.py`: roundtrip each model.
- [x] Verify: `alembic upgrade head` from scratch succeeds against local Postgres.

### Task 2 — Crypto module

- [x] Copy `canonical.py`, `keys.py` from Kindred backend (adapt imports).
- [x] `tests/test_crypto.py`: sign/verify roundtrip, canonical determinism.
- [x] Verify: identical input always yields identical canonical bytes.

### Task 3 — Services + router: rooms

- [x] `services/rooms.py`: `create_room`, `get_room`, `close_room`.
- [x] `services/participants.py`: `add_invited`, `accept`, `list_for_room`.
- [x] `api/routers/rooms.py`: `POST /v1/rooms`, `POST /v1/rooms/{id}/accept`, `POST /v1/rooms/{id}/close`, `GET /v1/rooms/{id}`.
- [x] `tests/test_rooms.py`: create, accept, close flow with 2 pubkeys.

### Task 4 — Services + router: messages

- [x] `services/messages.py`: `post_message` (with turn-ownership + signature verification), `list_since`.
- [x] `api/routers/messages.py`: `POST /v1/rooms/{id}/messages`, `GET /v1/rooms/{id}/messages?since=N`.
- [x] `tests/test_messages.py`: post in order, reject out-of-turn, reject bad sig, roundtrip 10 messages.

### Task 5 — End-to-end golden path test

- [x] `tests/test_e2e_two_agents.py`: simulate Alice + Bob both with their own keys.
  1. Alice creates room, invites Bob.
  2. Bob accepts.
  3. Alice posts turn 1.
  4. Bob polls, posts turn 2.
  5. 5 total round-trips.
  6. Alice closes with summary.
  7. Both agents can GET full transcript with valid sigs on every message.

### Task 6 — MCP plugin

- [ ] Scaffold `plugin/mcp/` with FastMCP-style server.
- [ ] Implement 6 tools (`room_create` … `room_list`) wrapping HTTP calls to backend.
- [ ] Signing logic: load key from `~/.kin/agent.key`, sign each write op.
- [ ] Manual test: register plugin with Claude Code, invoke `room_create` via MCP.

### Task 7 — Skills

- [ ] `skills/agentroom-open.md`
- [ ] `skills/agentroom-respond.md`
- [ ] `skills/agentroom-summarize.md`
- [ ] `skills/agentroom-close.md`
- [ ] Verify: Claude recognizes trigger phrases, runs procedure correctly in a staged conversation.

### Task 8 — CLI (optional, for scripted testing without Claude)

- [ ] `cli/src/agentrooms_cli/main.py`: argparse.
- [ ] Commands: `room create`, `room list`, `room show`, `room post`, `room poll`, `room close`.
- [ ] `tests/test_cli.py`: smoke test each command against a live dev backend.

### Task 9 — Deploy

- [ ] Add `agent-rooms` service to Railway project (separate service, separate domain).
- [ ] Env vars: `AGENTROOMS_DATABASE_URL` (Postgres plugin, can reuse Kindred's or spin new).
- [ ] Railway healthcheck on `/v1/healthz`.
- [ ] Deploy smoke test: hit `/v1/healthz`, create room via CLI against prod, post message, poll, close.

### Task 10 — Docs

- [ ] Update `agent-rooms/README.md` with real URLs and quick start.
- [ ] Add `agent-rooms/docs/quick-start.md`.
- [ ] Link from top-level `README.md` as a sibling product.

---

## Acceptance Criteria

- Two users on separate machines, each with their own agent keypair, can:
  1. User A creates a room, invites User B's pubkey.
  2. User B receives notification in their Claude Code (via skill + MCP poll).
  3. User B accepts.
  4. Both exchange at least 5 signed messages each.
  5. Either closes with a summary.
  6. Both can fetch the full transcript afterwards; every message has a valid signature; turn ordering is strict.
- Rooms auto-expire after 24h if not closed.
- Backend deploys on Railway alongside existing Kindred services.
- No Kindred code is modified as part of this plan.
- Unit test coverage ≥ 80% on `services/` and `crypto/`.
- E2E test `test_e2e_two_agents.py` is in CI and green.

---

## Estimated Effort

- Task 1-5 (backend + tests): 3-4 days
- Task 6-7 (MCP + skills): 1-2 days
- Task 8 (CLI): 0.5-1 day, optional
- Task 9 (deploy): 0.5 day
- Task 10 (docs): 0.5 day
- **Total: ~1-1.5 weeks of focused work for a single engineer.**

---

## Open Design Questions

1. **Contact book format:** `~/.kin/contacts.json` — do we share this with Kindred or separate? Proposal: shared file, schema-versioned.
2. **Room discovery:** MVP has no discovery — you need the `room_id` to interact. Is this OK or do we need "my rooms" listing via `room_list`? (Plan assumes yes, `room_list` included.)
3. **Agent-initiated vs human-initiated rooms:** MVP assumes human types „open a room". Can an agent proactively open one? Deferred — requires trust model we haven't designed.
4. **Per-message cost metering:** Should backend track tokens / bytes per participant for future billing / rate limits? Deferred to Phase 2.
5. **Transcript export format:** JSON now, maybe add markdown / PDF later. MVP: JSON only.

---

## Rollback Plan

If this product doesn't find traction:
- All code lives under `agent-rooms/` — drop the folder, done.
- Railway service: stop + delete; no impact on Kindred.
- DB: separate schema / separate Postgres plugin — drop cleanly.
- No shared runtime dependencies to unwind.

That's the point of keeping it separate.
