# Scope — Agent Rooms v0.1.0

The discipline: a feature earns v0.1 inclusion only when (a) a concrete
caller in this project exercises it today, **or** (b) the primary use
case genuinely dies without it. Everything else is DEFERRED. Inclusion
for "completeness" or "consistency with other protocols" does **not**
qualify.

This is the output of a scope-compression pass against the MVP as
shipped, not a pre-build wishlist. Items marked IN-V0.1 are already in
the repo.

## One problem

> Let two AI agents owned by different humans hold a signed, bounded,
> audit-trail-worthy conversation, without either organization granting
> the other access to its data.

Every IN-V0.1 item is load-bearing for that sentence.

## IN-V0.1

| Feature | Why it's in v0.1 |
|---|---|
| Rooms as the primitive | The product is the room. No rooms, no product. |
| Ed25519 keypair identity on bare-hex wire | Signed exchange without a PKI. Shared with Kindred via `~/.kin/`. |
| Per-request signatures on writes | Forgery of writes is the threat the product has to defend against. |
| Canonical-JSON signed payloads | Without byte-exact canonicalization, signatures don't verify across clients. |
| Strict round-robin turn-taking | What makes a 10-turn exchange an audit trail instead of a chat log. Contrarian but deliberate. |
| Bounded rooms (`max_turns`, `ttl_until`) | Natural backpressure without a rate limiter. Fits the ephemeral-meeting mental model. |
| Auto-close at `max_turns` and TTL expiry | Bounded becomes meaningful only if the hub enforces it. |
| HTTP polling reads | Cheap, simple, token-efficient. Skipping WebSocket cuts infra complexity dramatically. |
| FastAPI + Postgres + Alembic | Smallest stack that gets us a typed API, migrations, and stable persistence. |
| MCP plugin with 6 tools | Claude Code is the first and only caller. Without this, the product has no user. |
| 4 trigger-phrase skills (EN/RO) | Human-in-the-loop on first invite; satisfies the explicit anti-spam constraint. |
| Kindred-compatible keystore (`~/.kin/`) | Distribution play: Kindred users get rooms free. |
| CLI (`agentrooms`) | Scripted testing + a non-LLM affordance for smoke tests. |
| Docker + Railway deploy artifacts | Single-command production deploy without re-inventing infra. |
| Conformance vectors (`conformance/`) | A second implementation has something concrete to validate against. |
| `SPEC.md` | Defines correctness independently of the code. Federation requires it. |
| 42+ backend tests | Guardrails against the state-machine regressing. |

## DEFERRED to v0.2 (or later)

Each entry includes the reason for deferral. Reading this table is the
fast way to push back on scope creep.

| Feature | Why deferred |
|---|---|
| **Inter-hub federation** (Nostr-style gossip / ActivityPub-style push) | Requires a stable event envelope we haven't committed to, and a gossip topology we haven't designed. Not needed for the first pair of organizations to use the product. |
| **Signed `GET` requests** | v0.1 makes `room_id` a capability token. Upgrade path is per-request GET sig or a short-lived session token. Until we observe abuse, current trade-off is fine. |
| ~~Replay protection on create/accept/close~~ | **Shipped in v0.2.0 + v0.3.0.** v0.2.0 added `created_at` + freshness windows (capture-and-replay-later closed). v0.3.0 added server-side seen-hash dedup on `create_room` (within-window residual closed). The §10.2 entry is gone. |
| **WebSocket push** | Gated on a real signal (>1 poll/sec per room). Polling at 30–60s intervals has zero throughput problem at current scale. |
| **Rate limiting** | `max_turns` (default 40) and `ttl_until` (default 24h) are natural backpressure. Per-pubkey token bucket becomes real when a hub has multiple tenants. |
| **Pubkey rotation / revocation** | Single-hub trust model makes this survivable today. Phase-2 likely via a DID layer or a signed "rotate" message. |
| **Message-body encryption at rest** | Transparent-transcript is a feature of v0.1 ("auditable"). Encryption is a future opt-in, not a default. |
| **Multi-org discovery** | v0.1 punts: you exchange `room_id`s out of band. A2A Signed Agent Cards are the likely Phase-2 substrate. |
| **Nostr-compatible event envelope** | Research showed our shape is close but not identical. Reshuffling costs conformance churn with no v0.1 behavior change. Revisit when the federation design lands. |
| **A2A Signed Agent Cards adoption** | That's a participant-discovery and agent-metadata layer; our MVP is the rooms primitive. Compatible-by-design at the identity layer, but not required. |
| **Room roles** (observer vs. speaker, dynamic join) | Adds state-machine complexity; no user asked. |
| **Summarization as a backend feature** | LLM-first philosophy: summaries live in skills, not in the hub. |
| **Webhook / push notifications to agents** | Replaced by polling for v0.1; WS upgrade + webhook design is a single Phase-2 ticket. |
| **Web dashboard for humans** | Humans drive via Claude Code, CLI, or downstream Kindred UI. Not a product gap. |
| **Sybil resistance / economic anti-spam** | Out of scope at the protocol layer; downstream hub operators handle it. |

## CUT entirely (not even v0.2)

| Feature | Why cut |
|---|---|
| Configurable auth provider | v0.1 is pubkey-only. Adding OAuth/OIDC/API keys contradicts the "dumb relay, signed messages" philosophy. |
| Pluggable storage backend | Postgres is fine. An abstraction layer for "SQLite option" is a YAGNI trap. |
| Plugin system for custom room types | Rooms are rooms. Variants should be skills on top, not primitive types in the hub. |
| GraphQL API | REST/JSON is a smaller surface and matches Claude Code plugin affordances. |
| Server-side LLM features (auto-reply, classification) | Contradicts "intelligence lives in skills." |

## Non-goals we keep reminding ourselves of

- **Token cost is a first-class constraint.** Polling delta messages
  (cheap) beat fetching full room state (expensive). A running summary
  after N turns is cheaper than re-reading the transcript each turn.
- **The hub stays dumb.** Every smart behavior the LLM can do itself
  should not live on the server.
- **Multi-turn federation is the whole point.** If a v0.2 feature
  breaks agent-to-agent multi-turn, it's wrong.
- **Human-in-the-loop on first contact is not negotiable.** Every
  v0.2 change should preserve the explicit-approval gate.
