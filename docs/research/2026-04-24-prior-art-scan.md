# Parley — Prior Art Scan

*Date: 2026-04-24*
*Author: external-research scan*
*Scope: products, protocols, papers, and companies that could overlap, compete, or be borrowed from for the Parley MVP described in `docs/plans/2026-04-24-parley-01-mvp.md`.*

---

## TL;DR — Executive Summary

1. **The "agent communication protocol" space is saturated and consolidating around a small set of standards.** Four protocols dominate the conversation in 2026: Anthropic's **MCP** (tool/data → agent), Google's **A2A** (agent ↔ agent, now Linux Foundation–governed at v1.2 with **Ed25519 / JWS-signed Agent Cards**), IBM's **ACP** (BeeAI-hosted, also LF), and the community-driven **ANP** (W3C DID–anchored). A2A is now in production at Microsoft, AWS, Salesforce, SAP, ServiceNow ([Stellagent](https://stellagent.ai/insights/a2a-protocol-google-agent-to-agent), [Linux Foundation transfer](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade)). **You will be questioned for not adopting A2A as the wire format** — make the call deliberately.

2. **Nobody is shipping the *exact* product** — "Claude Code plugin + signed transcripts + Ed25519 + cross-org rooms + dumb hub" — but several adjacent things compete for the same mental slot:
   - **A2A is bilateral, not "rooms."** Its spec is strictly client↔remote-agent ([A2A spec §3.4.1](https://a2a-protocol.org/latest/specification/)). Multi-party group conversations are out of scope. **This is your real defensible space.**
   - **Coral Protocol** ships threaded multi-agent messaging with mention-based targeting and is the closest architectural cousin, but it's framed around the "Internet of Agents" / on-chain micropayments / token economy, not Claude-Code-native rooms ([Coral arxiv](https://arxiv.org/abs/2505.00749), [coralprotocol.org](https://coralprotocol.org/)).
   - **AGNTCY (Cisco → Linux Foundation)** ships SLIM (extended gRPC pub/sub for agent groups) plus a directory service. Heavyweight, enterprise, infra-flavored ([agntcy.org](https://agntcy.org), [Cisco donation](https://www.networkworld.com/article/4029803/cisco-donates-ai-agent-tech-to-linux-foundation.html)).
   - **NANDA (MIT Media Lab)** is the academic version: discovery/identity/federation/interoperability layers built on top of MCP+A2A ([projectnanda.org](https://projectnanda.org/), [arxiv 2507.14263](https://arxiv.org/pdf/2507.14263)).

3. **Nostr is the single closest design analogue.** Ed25519 keys, signed events, relay-as-dumb-hub, polling clients with smarts — basically your architecture, minus the rooms abstraction and minus the LLM context. Adopt its event signing + relay semantics directly; don't reinvent ([nostr.com](https://nostr.com/), [nostr.how](https://nostr.how/en/the-protocol)). NIP-28 (public chat / channels) is the closest existing "room" concept and is worth reading before you finalize your message schema.

4. **The strongest positioning right now is "Slack for cross-org AI agents, but cheap and Claude-Code-native."** Slack itself is racing toward this with Slackbot-as-MCP-client ([Slack agentic OS](https://slack.com/blog/news/powering-agentic-collaboration)) but it's locked to one org per workspace and assumes a Slack subscription. Your differentiator: **neutral hub, no membership in either org's perimeter, cheap, append-only signed log, plugin-first UX**.

5. **Cryptographically auditable multi-agent systems is now an active research subfield** with at least four 2025 papers (BlockA2A, SAGA, Open Challenges in Multi-Agent Security, the HDP / Human Delegation Provenance protocol) all converging on the same primitives you've picked: per-agent DIDs/keys, signed messages, immutable transcripts. **You're building "the simplest possible product that embodies what these papers say should exist." That's a defensible posture.**

6. **You are not late, but the window is months not years.** A2A is bilateral and won't grow rooms quickly (governance overhead at LF). Coral is busy with tokenomics. AGNTCY is enterprise-only. The "lightweight Claude-Code-plugin MVP" hole is genuinely open *today*, but credible competitors could land in 2026Q4–2027Q1.

7. **Highest-impact specific recommendations** (full list below):
   - **Adopt A2A's Signed Agent Card schema** verbatim for participant identity. You get free interop with the 150+ org A2A ecosystem.
   - **Adopt Nostr's event envelope** (`{id, pubkey, created_at, kind, tags, content, sig}`) for messages. Battle-tested, Ed25519-native, and a lot of relay infra you can crib from.
   - **Drop "polling vs push" as a debate** — Nostr already proved long-lived WS subscriptions are cheaper than HTTP polling for this exact shape. Reconsider your "polling, not push" decision.
   - **Server-enforced turn-taking is unusual** — A2A, Coral, ACP all leave turn order to clients. Either own this as a real differentiator (with a one-paragraph justification) or drop it.
   - **Auto-expire at 24h is unique** and probably correct; nobody else does this and it's a strong anti-spam / cost story.

---

## 1. Direct Analogues

| Name | What it is | Maturity | Overlap with Parley | One-sentence diff |
|---|---|---|---|---|
| **Google A2A** ([site](https://a2a-protocol.org/), [GitHub](https://github.com/a2aproject/A2A)) | Open protocol for opaque agents to discover/collaborate. Ed25519/JWS-signed Agent Cards, JSON-RPC/gRPC/REST. LF-governed since June 2025. v1.2 in 2026. | Production. 150+ orgs, Microsoft/AWS/Salesforce/SAP/ServiceNow shipping. | Identity model (Ed25519 + Agent Cards), signing model, message envelope. | **Bilateral only — no rooms, no multi-party.** That's your wedge. |
| **IBM ACP** ([IBM Research](https://research.ibm.com/projects/agent-communication-protocol), [GitHub](https://github.com/i-am-bee/acp)) | HTTP-based agent-to-agent protocol. Underlies BeeAI Platform. LF-hosted. | GA-ish (v1, May 2025). | Bilateral RPC for agents; metadata-in-package discovery. | **No multi-party rooms; designed for orchestration of containerized agents inside one operator's infra.** |
| **ANP** (Agent Network Protocol — [agent-network-protocol.com](https://agent-network-protocol.com/), [GitHub](https://github.com/agent-network-protocol/AgentNetworkProtocol)) | Decentralized P2P agent communication. Three layers: W3C DID identity, meta-protocol negotiation, semantic-web app layer. | v1.0 May 2025; community-only, anti-commercial. | DID-based identity, end-to-end signing. | **Peer-to-peer, no central hub, no rooms; aimed at "HTTP of the Agentic Web."** |
| **Coral Protocol** ([coralprotocol.org](https://coralprotocol.org/), [arxiv](https://arxiv.org/abs/2505.00749)) | "Internet of Agents" infra: threaded messaging, mention-based targeting, decentralized identity, on-chain micropayments via $CORAL token. | Live, Q1 2026 SDK. | **Threaded multi-agent messaging is closest of any project to your "rooms."** | **Crypto-token-economic; $CORAL pricing baked in; aimed at agent marketplaces, not human-mediated cross-org meetings.** |
| **AGNTCY** (Cisco → LF) ([agntcy.org](https://agntcy.org), [Cisco blog](https://outshift.cisco.com/blog/building-the-internet-of-agents-introducing-the-agntcy)) | "Internet of Agents" framework. SLIM (gRPC pub/sub w/ MLS+post-quantum), Identity service (DIDs), Agent Directory Service (IPFS+Sigstore). | Production-ish, LF-hosted, 65+ vendors (Cisco, Dell, Google, Oracle, Red Hat). | Pub/sub group communication via SLIM; DID identity. | **Heavyweight enterprise infra (telecom-flavored); not a product, a stack to build products on.** |
| **AITP** (NEAR AI — [aitp.dev](https://aitp.dev), [GitHub](https://github.com/nearai/aitp)) | Agent Interaction & Transaction Protocol. Thread-based (OpenAI Threads–inspired), payments-first. | Draft v0.1, NEAR AI Hub integration in progress. | Thread-based multi-agent conversations (no signing detail surfaced). | **Payments-centric; tightly coupled to NEAR blockchain.** |
| **Agora Protocol** ([agoraprotocol.org](https://agoraprotocol.org/), [arxiv 2410.11905](https://arxiv.org/html/2410.11905v1)) | Meta-protocol: agents *negotiate* their own communication protocol via Protocol Documents (hash-identified). | Academic prototype. | Cross-platform agent communication. | **Negotiation-first; no fixed wire format; not a product.** |
| **Letta (MemGPT)** ([letta.com](https://www.letta.com/)) | Stateful agent platform. Conversations API allows shared memory across multi-user/multi-agent. Letta Code is a Claude-Code-style harness. **Agent File (.af)** is a portable agent-state format ([agent-file repo](https://github.com/letta-ai/agent-file)). | Production. | Multi-agent message exchange and shared-memory blocks. | **Single-operator agent platform; not designed for cross-org with mutually distrustful operators.** |
| **NANDA** (MIT Media Lab — [projectnanda.org](https://projectnanda.org/)) | Decentralized infra for Internet of AI Agents. Discovery/identity/federation/interop layers on top of MCP+A2A. **NANDA Index** + **AgentFacts** (verifiable metadata schema). | Active research; GitHub commits through 2026-04. | Cryptographically verifiable agent metadata, federation layer. | **Research project, not a product; aims to be the DNS, not the meeting room.** |
| **Inworld AI Runtime** ([inworld.ai](https://inworld.ai/)) | Real-time voice/chat agent infra. Unified LLM/TTS/STT, MCP for tools. | Production. | None for cross-org; same-operator only. | **Player/companion focus, voice-heavy, not federation.** |
| **Slack (Agentforce + Slackbot)** ([Slack agentic](https://slack.com/blog/news/powering-agentic-collaboration)) | Slack as the "agentic OS" — Slackbot is now an MCP client; Anthropic, OpenAI, Google, Perplexity agents live in Slack. | Production, March 2026 launch. | Closest **product** competitor for "place where agents talk." | **Locked to one workspace / one org perimeter; requires Slack license; humans-and-agents-mixed model.** |
| **Salesforce AgentExchange** ([agentexchange.salesforce.com](https://agentexchange.salesforce.com/)) | Marketplace merging AppExchange + Slack Marketplace + Agentforce. 10K+ apps, 1K+ Agentforce agents, MCP servers. | Production. | Discovery surface for agents, not a meeting room. | **Marketplace, not a conversation venue.** |
| **Coinbase Agentic.Market** ([FinanceFeeds](https://financefeeds.com/ai-agent-commerce-is-here-inside-cryptos-new-agentic-stack/)) | x402 team's agent-only service marketplace (launched 2026-04-20). | Launched four days ago. | Cross-org agent transactions. | **Service procurement, not multi-turn conversation.** |
| **OpenClaw + Matrix plugin** ([blog](https://www.openclawplaybook.ai/blog/openclaw-matrix-integration-decentralized-ai-messaging/)) | OpenClaw AI agent skill that bridges Matrix DMs/rooms/threads/E2EE for agents. | Live in 2026. | **Agents in cross-homeserver rooms via Matrix federation.** | **Delegates everything to Matrix; not its own protocol; Matrix's "room" semantics may not match yours.** |

**Closest direct competitor: Coral Protocol.** If you ignored crypto-tokenomics, their threaded-messaging server with mention-based targeting is what you're building. Read their arxiv paper before you freeze your message schema.

**Closest *product* competitor: Slack agentic stack.** They have distribution, you have neutrality. The pitch becomes obvious: "Slack is for one org's agents; Parley is for two orgs' agents to talk without joining each other's Slack."

---

## 2. Standards & Protocols

| Name | Scope | Maturity | Could we adopt? |
|---|---|---|---|
| **A2A v1.2** ([spec](https://a2a-protocol.org/latest/specification/)) | Bilateral agent communication; Agent Cards; tasks; JSON-RPC/gRPC/REST. | Production, LF-governed. | **Yes — adopt the Agent Card + JWS signing model verbatim. Wrap rooms semantics on top.** Free interop with 150+ orgs. |
| **MCP** ([spec](https://modelcontextprotocol.io/specification/2025-11-25)) | Tools/data → agent. 97M installs (Mar 2026), donated to Agentic AI Foundation Dec 2025. | Production de facto standard. | Already part of your stack via Claude Code skills. |
| **ACP (IBM)** ([acp repo](https://github.com/i-am-bee/acp)) | Agent-to-agent over standard HTTP. | LF-hosted, v1. | Lower-priority; A2A has won the mindshare battle. |
| **ANP** | DID-anchored P2P. | v1, community. | Identity layer borrowable; full stack overkill. |
| **W3C DIDs v1.1** ([W3C](https://www.w3.org/TR/did-1.1/)) | Decentralized identifiers. | W3C Recommendation; v1.1 invited implementations Mar 2026. | **Worth considering instead of raw `did:key`-equivalent pubkey strings.** `did:key:z6Mk…` from your Ed25519 keys is one line of code and gives you W3C-conformant identifiers for free. |
| **W3C Verifiable Credentials** | Third-party-issued claims about a DID subject. | W3C Rec. | Future feature: "this agent represents @vlad@nuit.ro, attested by Kindred." |
| **DIDComm v2** ([spec](https://identity.foundation/didcomm-messaging/spec/v2.0/), [DIF blog](https://blog.identity.foundation/didcomm-v2/)) | Encrypted DID-to-DID messaging; DIF Approved Status. The DIDComm WG explicitly considered MCP/A2A use cases ([DIF #59](https://blog.identity.foundation/dif-newsletter-59/)). | Approved spec. | **Heavy** — full envelope encryption, routing. Probably overkill for hub-only MVP, but read it before designing your Phase-2 federation. |
| **MCP-I (MCP-Identity)** | Vouched-donated identity/delegation spec for MCP, donated to DIF. | Early. | Watch this — it's the agent-identity-on-MCP convergence point. |
| **NANDA Index / AgentFacts** ([arxiv 2507.14263](https://arxiv.org/pdf/2507.14263)) | Cryptographically verifiable agent metadata + federated resolution. | Academic, MIT-led. | If you need a discovery layer post-MVP, this is the closest open spec. |
| **Nostr (NIP-01)** ([nostrbook.dev](https://nostrbook.dev/protocol/)) | Ed25519 events, relays as dumb hubs. Not a "standard" body but a working network of millions of events/day. | Production at scale, 5+ years. | **Yes — adopt the event envelope.** See §4 for specifics. |
| **AT Protocol** ([Bluesky docs](https://docs.bsky.app/docs/advanced-guides/atproto)) | User repositories + signed records + lexicons. IETF working group as of Jan 2026 ([wikipedia](https://en.wikipedia.org/wiki/AT_Protocol)). | Production at 43M user scale. | Heavier than Nostr; lexicon system might be useful if you want typed message schemas. Probably overkill. |
| **ActivityPub** ([W3C TR](https://www.w3.org/TR/activitypub/)) | Federated server-to-server actor inbox/outbox. | W3C Rec since 2018. | Possible Phase-2 federation transport, but no per-message signature requirement; you'd be bolting Ed25519 onto a protocol that doesn't expect it. |
| **Matrix** ([matrix.org](https://matrix.org/)) | Federated rooms with E2EE; bots are first-class. UN, 35 governments use it. | Production. | Could deliver your Phase-2 federation almost for free. Tradeoff: Matrix's events have its own signing model (per-server keys), not per-agent Ed25519 — incompatible with your design unless you wrap. |
| **XMPP MUC (XEP-0045)** | Multi-user chat. Federated. | Stable since forever. | Wire-level fine, but XMPP-as-bus for AI agents has zero current momentum. |
| **AITP** | Thread-based agent communication, payments-first. | Draft v0.1. | Watch only. |
| **Agora Protocol** | LLM-negotiated protocols. | Academic. | Theoretically interesting; not a thing you adopt. |

**Recommended adoption stack:**
- **Identity:** A2A Signed Agent Cards + `did:key` representation of your Ed25519 pubkeys.
- **Message envelope:** Nostr-style event signing.
- **Wire:** Plain HTTP+JSON for MVP. Reconsider WS subscriptions before public launch.

---

## 3. Adjacent / Borrow-From

### Nostr — the closest design twin

Nostr's primitives map to yours almost 1:1. From [nostrbook.dev](https://nostrbook.dev/protocol/) and [nostr.how](https://nostr.how/en/the-protocol):

| Nostr | Parley (your plan) |
|---|---|
| Ed25519 keypair = identity | Ed25519 keypair = agent identity |
| Signed event `{id, pubkey, created_at, kind, tags, content, sig}` | Signed message |
| Relays are "dumb" — store and forward | "Backend stays dumb CRUD" |
| Clients do all the smarts | Skills in Claude Code do all the smarts |
| Polling-equivalent (REQ subscriptions over WS) | Polling delta messages |
| Multiple relays (federation) | Federation later |
| NIP-28 public chat / channels | Rooms |
| NIP-04/44 encrypted DMs | Not in MVP |
| NIP-26 delegated event signing | Useful if you want "agent acts on behalf of human" |

**Specific things to crib from Nostr:**

1. **The event envelope.** Use `{id, pubkey, created_at, kind, tags, content, sig}`. `id` = SHA-256 of canonical-serialized other fields. `sig` = Ed25519 signature over `id`. This is field-tested by the entire Nostr network and removes a category of "did we canonicalize correctly" bugs you would otherwise discover during your first interop test.
2. **Kinds, not types.** Use integer event kinds (room.create=40-equivalent, message=1-equivalent, leave=…). Cheap to extend, easy to filter.
3. **Tags for everything.** Reply-to, mention, room-id all become `["e", id]`, `["p", pubkey]`, etc. Pattern is well understood.
4. **Read NIP-28** ([github.com/nostr-protocol/nips/blob/master/28.md](https://github.com/nostr-protocol/nips/blob/master/28.md)) before finalizing your room-membership semantics — they got there first.

This is the **single most actionable item in this report.** Do not invent your own message envelope.

### DIDComm v2 — for Phase-2 federation

When you go federated, hub-to-hub message routing with end-to-end agent encryption is exactly what DIDComm v2 was designed for. The DIDComm WG has explicitly discussed agent-to-agent use cases ([DIF newsletter](https://blog.identity.foundation/didcomm-v2/)). Adopting DIDComm Phase 2 keeps you in a standards-track lane instead of inventing your own federation envelope.

### Matrix — possible federation substrate

Matrix's federation is the most battle-tested "rooms across servers" implementation in existence. **Risk:** Matrix's per-server signing model conflicts with your per-agent-key model. If you ever consider Matrix-as-transport, you will need to either (a) carry your own signed envelope inside Matrix events (works, ugly) or (b) abandon per-agent signing at the wire level (defeats the point).

### AT Protocol — lexicons

AT Protocol's lexicon system gives you typed, versioned message schemas with negotiation. If your "kinds" approach grows messy, AT-style lexicons are worth a look. Probably not for MVP.

### Agent File (.af) — agent state portability

Letta's [.af format](https://github.com/letta-ai/agent-file) is the emerging standard for "this is what an agent is, including memory and tools, in a file." If you ever want to support importing an external agent into a room (vs. just letting that agent's owner connect), .af is the format you'd accept.

---

## 4. Companies to Watch

| Company | Stage | What they do | Why they matter |
|---|---|---|---|
| **Coral Protocol** | Token-funded, live Q1 2026 SDK | Threaded multi-agent server, on-chain coordination | Closest architectural cousin |
| **AGNTCY (Cisco-led, LF)** | LF project, 65+ vendors | Internet of Agents stack: SLIM, Identity, Directory | Could subsume the whole space |
| **NANDA (MIT)** | Academic | DNS for agents; verifiable AgentFacts | Sets the discovery layer everyone else builds on |
| **NEAR AI** | Token-funded | AITP + NEAR AI Hub | Closest crypto-native version |
| **Letta** | VC-backed (a16z) | Stateful agent platform, Letta Code, Agent File | If they add a "shared room" primitive across instances, they own this |
| **Salesforce (AgentExchange + Agentforce + Slack)** | Public co | Marketplace + Slack-as-agentic-OS | Distribution risk; their Slack is the obvious "place agents talk" |
| **Microsoft Entra Agent ID** | GA | Enterprise agent identity directory | Likely will become "the" enterprise identity for agents |
| **Multifactor** (YC F25, $15M seed) | YC F25 | Post-quantum credential sharing for AI agent access | Adjacent — they want agents to share user credentials safely |
| **Alter** (YC S25) | YC S25 | Zero-trust auth/access control for agent workflows | Adjacent — auth, not communication |
| **AgentID / OpenAgents.org** ([blog](https://openagents.org/blog/posts/2026-02-03-introducing-agent-identity)) | Indie | Cryptographic agent IDs, two formats per identity | Closest single-purpose agent-identity startup |
| **ZeroID (Highflame)** | Indie | Open-source agent identity server with VCs + delegation chains | Watch as a reference implementation |
| **Prove (Verified Agent)** ([Finovate](https://finovate.com/proves-new-verified-agent-solution-brings-trust-and-verification-for-autonomous-agents/)) | Public co | KYC for agents | Adjacent compliance angle |
| **Inworld AI** | VC-backed | Real-time voice/chat agent runtime | Same-org agents only |
| **Picsart** ([TechCrunch 2026-03](https://techcrunch.com/2026/03/16/picsart-now-allows-creators-to-hire-ai-assistants-through-agent-marketplace/)) | Public-ish | "Hire" AI assistants through agent marketplace | Vertical adjacent |
| **Bluesky / Attie** ([TechCrunch](https://techcrunch.com/2026/03/28/bluesky-leans-into-ai-with-attie-an-app-for-building-custom-feeds/)) | VC-backed | AT-Protocol-native AI feed agent | Not a competitor; signals "agents on signed federated infra" is a real product category |

**No YC W25/S25/W26 startup is shipping the exact thing.** YC's agent-infra bet is on auth, testing, monitoring, billing, context — *not* cross-org rooms. The biggest YC adjacent is **Multifactor**, which is about credential delegation, not conversation.

---

## 5. Academic / RFC Work

The research field has converged on more or less the same primitives you've chosen. Recent (2024–2026) papers:

- **BlockA2A: Towards Secure and Verifiable Agent-to-Agent Interoperability** (Aug 2025) — [arxiv 2508.01332](https://arxiv.org/abs/2508.01332). DIDs + blockchain ledger + smart-contract policy enforcement + Defense Orchestration Engine. *Closest paper to your design philosophy. Read it.*
- **SAGA: A Security Architecture for Governing AI Agentic Systems** (NDSS 2026) — [arxiv 2504.21034](https://arxiv.org/html/2504.21034v2). Cryptographic access-control tokens encrypted under shared agent keys for fine-grained inter-agent comms.
- **Open Challenges in Multi-Agent Security** (May 2025) — [arxiv 2505.02077](https://arxiv.org/html/2505.02077v1). Names commitment schemes + ZK proofs as the right primitives for inter-agent message protocols.
- **Coral Protocol: Open Infrastructure Connecting The Internet of Agents** (May 2025) — [arxiv 2505.00749](https://arxiv.org/abs/2505.00749). Threaded messaging spec.
- **A Survey of Agent Interoperability Protocols** (May 2025) — [arxiv 2505.02279](https://arxiv.org/html/2505.02279v1). Side-by-side of MCP, ACP, A2A, ANP. Useful citation map.
- **A Survey of AI Agent Protocols** (Apr 2025, rev Jun 2025) — [arxiv 2504.16736](https://arxiv.org/pdf/2504.16736). Broader landscape.
- **Agora: A Scalable Communication Protocol for Networks of LLMs** (Oct 2024) — [arxiv 2410.11905](https://arxiv.org/html/2410.11905v1). LLM-negotiated protocol docs.
- **AI Agents with Decentralized Identifiers and Verifiable Credentials** — [arxiv 2511.02841](https://arxiv.org/abs/2511.02841). Self-sovereign agent identity. Accepted to ICAART 2026.
- **Unlocking the Internet of AI Agents via the NANDA Index** — [arxiv 2507.14263](https://arxiv.org/pdf/2507.14263). MIT's discovery/identity proposal.
- **Blockchain-based Learning Framework for LLM Multi-Agent Systems** — [arxiv 2509.16736](https://arxiv.org/pdf/2509.16736). On-chain auditability for inter-agent message exchange.

**RFCs / IETF:** No formal IETF RFCs for agent-to-agent communication yet. AT Protocol's IETF WG was chartered Jan 2026 ([wikipedia](https://en.wikipedia.org/wiki/AT_Protocol)) — this is the closest active standards-track work you might intersect with.

**DARPA** is funding "science of AI communication" research as of April 2026 ([The Register](https://www.theregister.com/2026/04/08/darpa_wants_ai_agent_communication/)) — public funding signal that this is being treated as an unsolved problem.

---

## 6. Are We Late?

**No, but the runway is shrinking.**

What's missing in the market today:
- A **cross-org room** (multi-party, not bilateral). A2A explicitly doesn't do this. ACP doesn't. MCP doesn't.
- A **lightweight Claude-Code-native UX**. Slack does it for Slack users; nobody does it for Claude Code users.
- A **dumb hub** that doesn't try to also be an LLM, a marketplace, or a token economy. Coral and AITP and NEAR AI Hub all bundle extra stuff.
- **24h auto-expiry** as a built-in property. Nobody else has this.
- **Reuse of existing user identity** (the `~/.kin/` keypair from Kindred). Nobody else has this distribution path.

What would let a competitor leapfrog you in 6 months:
- **Anthropic** could ship "Claude Rooms" as a first-party feature. They have the plugin distribution, the model, the auth. **This is your real competitive risk.** Mitigation: ship fast, get distribution via Kindred users, make the protocol open enough that "Anthropic adopts our spec" is a plausible better-than-killed outcome.
- **Coral Protocol** could ship a no-token "lite" version aimed at non-crypto devs.
- **Slack** could open up cross-workspace agent rooms. Unlikely (cuts against their lock-in), but possible.
- **A2A v2 or v1.3** could add a multi-party / room extension. Watch the [a2aproject/A2A](https://github.com/a2aproject/A2A) issues — there are open issues on identity/delegation/enforcement ([#1575](https://github.com/a2aproject/A2A/issues/1575)) that could grow into rooms.

---

## 7. Are We Wrong?

**No public post-mortem of "we tried to build agent rooms and it failed" exists** as of 2026-04-24. The closest negative signals:

- **Microsoft Copilot Studio's enterprise sales struggle** ([Medium postmortem](https://medium.com/@Micheal-Lanham/postmortem-of-a-miss-what-microsofts-ai-agent-sales-struggles-teach-us-all-3a79d9e32c5a)) — 230K orgs experimented, but enterprises didn't buy. Quotas slashed 50%. Lesson: **agentic features are easier to ship than to monetize**. Implication for you: don't assume "enterprises will pay" — your initial market is likely indie devs and small orgs who already use Claude Code.
- **AI agents fail at 2x the rate of traditional IT**, only ~11% of orgs have agentic systems in production ([RAND via Operator Collective](https://theoperatorcollective.org/blog/ai-agent-failures-lessons-crashes)). Implication: **the population of orgs that actually have a working agent to put in your room is small.** Frame the MVP for indie/dev/small-team users, not Fortune 500.
- **The "$4,200 in 63 hours" runaway-agent postmortem** ([Sattyam Jain](https://medium.com/@sattyamjain96/the-agent-that-burned-4-200-in-63-hours-a-production-ai-postmortem-d38fd9586a85)) — agents in unbounded loops are dangerous. Your 24h expiry + turn-taking + human-on-first-contact gates address exactly this risk; emphasize them in marketing.
- **Slack data after bankruptcy is being sold to AI training** ([Agent Wars](https://www.agent-wars.com/news/2025-01-17-ai-companies-buying-dead-startup-slack-data)). Implication: **append-only signed transcripts of cross-org conversations have nontrivial liability.** Get the data-retention story (24h auto-delete vs. archive-on-request vs. owner-keys-encrypt) crisp before launch.

---

## 8. Recommendations for Our Design

### Adopt (high confidence)

1. **Use the Nostr event envelope verbatim.** `{id, pubkey, created_at, kind, tags, content, sig}` with `id = sha256(canonical_serialize([0, pubkey, created_at, kind, tags, content]))` and `sig = Ed25519(id, sk)`. ([NIP-01](https://github.com/nostr-protocol/nips/blob/master/01.md)). This is the single highest-ROI design decision available.
2. **Use A2A Signed Agent Cards** for participant identity and capability declaration. JWS over JSON. Free interop with the largest agent-protocol ecosystem in existence ([A2A spec §8](https://a2a-protocol.org/latest/specification/)).
3. **Represent Ed25519 pubkeys as W3C `did:key`** — one line of code (`did:key:z6Mk...`), gives you W3C-conformant identifiers for free, and forward-compatible with VCs / DIDComm.
4. **Read NIP-28 (channels)** before finalizing room-membership semantics. They solved the "public room with a signed creation event and reply-by-tagging" problem in 2020.

### Reconsider (medium confidence)

5. **Server-enforced strict turn-taking is a contrarian choice.** A2A leaves it to clients; Coral uses mention-based targeting; nobody else enforces server-side. Either:
   - **Justify it explicitly** in the spec ("we enforce turn order to make multi-agent conversations debuggable and to prevent loop attacks") and own it as a differentiator, *or*
   - **Drop it** in favor of "any participant can post anytime, clients decide when to act." The latter is closer to how every other system in this scan operates.
6. **Polling vs WS subscriptions.** Nostr proved at scale that long-lived WS subscriptions (`REQ`/`EVENT`/`EOSE`) are cheaper than HTTP polling for this exact event-stream-with-filter shape. HTTP polling gives you Cloudflare-cacheable simplicity but at 10× the request volume. Reconsider before public launch — this isn't an MVP-blocker but is a poor permanent choice.
7. **`~/.kin/` reuse is a great distribution play but a fragile coupling.** If Kindred ever changes its key derivation (HD wallet path, post-quantum migration), Parley breaks. Document the contract: "Parley reads `~/.kin/agent.key` (raw Ed25519 seed, 32 bytes). Any other format is undefined behavior." Get this written down so a future Kindred change is a deliberate breaking change, not a silent break.

### Drop / don't build

8. **Don't invent your own canonical-serialization rules.** Use either Nostr's (UTF-8 JSON with specific escaping rules) or JCS (RFC 8785). Both are widely implemented; both have test vectors.
9. **Don't ship a custom federation envelope in MVP.** When you go federated, use either DIDComm v2 (heavy, standards-track) or a Nostr-style relay-mesh (light, no governance). Pick one then; don't pre-design now.
10. **Don't bake in payments / tokens.** That's Coral and AITP's mistake (in your market). Stay free, stay neutral, stay cheap. If you ever need monetization, charge the hub operator (you), not the messages.

### Differentiators to emphasize in positioning

- **"Neutral hub. No org owns the venue."** This is genuinely uncovered space.
- **"Signed transcripts you can show your lawyer."** Auditability is the killer enterprise story; you have it natively.
- **"24h auto-expiry by default."** Anti-spam, anti-liability, cheap. Nobody else does this.
- **"Costs $0.30, not $150."** Lead with the cost-vs-human-meeting comparison; it's your most concrete differentiator.
- **"Lives in Claude Code, not in a 17th tab."** Plugin-first UX is rare in this space (Slack and Coral are both standalone surfaces).

---

## 9. Open Questions / Things I Couldn't Pin Down

- **Exact A2A multi-party roadmap.** A2A v1.2 is bilateral; the [a2aproject/A2A](https://github.com/a2aproject/A2A) issues mention agent identity / delegation / enforcement work, but I couldn't find a confirmed multi-party / rooms RFC. Worth a deep dive on the GitHub issues + LF mailing list before finalizing your spec.
- **Whether Anthropic is internally building "Claude Rooms."** Nothing public. Given they (a) have the Agent Teams feature in Claude Code, (b) co-founded the Agentic AI Foundation, and (c) own MCP, this is a non-zero risk. No way to derisk except: ship.
- **Coral Protocol's actual non-token usage.** Their docs lean heavily on $CORAL token mechanics; unclear whether the threaded-messaging server is usable standalone without the on-chain bits.
- **Whether `did:key` is the right DID method.** `did:key` is the simplest (just an Ed25519 pubkey). Alternatives: `did:web` (great for org-attached agents), `did:peer` (great for ephemeral agents), `did:plc` (Bluesky-style). Worth a short ADR.
- **DIDComm v2 adoption velocity.** Spec is approved, but I couldn't find a "X% of identity systems implement DIDComm v2" stat. Risk: standards-track but unimplemented, like XMPP MUC for AI agents — fine on paper, ecosystem of zero.
- **Whether NIP-28 (Nostr public channels) actually works at scale.** Nostr DMs and feeds work; channels are less battle-tested. Read code, not just spec.
- **What "human-in-the-loop on first invite" looks like in practice if both sides are agents owned by AFK humans.** The handshake might block forever. Worth a sketch in the MVP plan.

---

## Sources

### Direct analogues
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [a2aproject/A2A on GitHub](https://github.com/a2aproject/A2A)
- [A2A getting an upgrade — Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade)
- [A2A grew to 150+ orgs — Stellagent](https://stellagent.ai/insights/a2a-protocol-google-agent-to-agent)
- [IBM ACP — IBM Research](https://research.ibm.com/projects/agent-communication-protocol)
- [i-am-bee/acp on GitHub](https://github.com/i-am-bee/acp)
- [What is BeeAI — IBM](https://www.ibm.com/think/topics/beeai)
- [Agent Network Protocol](https://agent-network-protocol.com/)
- [agent-network-protocol/AgentNetworkProtocol on GitHub](https://github.com/agent-network-protocol/AgentNetworkProtocol)
- [Coral Protocol arxiv 2505.00749](https://arxiv.org/abs/2505.00749)
- [coralprotocol.org](https://coralprotocol.org/)
- [Coral Protocol security analysis — NeuralTrust](https://neuraltrust.ai/blog/coral-protocol-security)
- [agntcy.org](https://agntcy.org)
- [Building the Internet of Agents — Cisco Outshift](https://outshift.cisco.com/blog/building-the-internet-of-agents-introducing-the-agntcy)
- [Cisco donates AGNTCY to Linux Foundation — Network World](https://www.networkworld.com/article/4029803/cisco-donates-ai-agent-tech-to-linux-foundation.html)
- [aitp.dev](https://aitp.dev/)
- [nearai/aitp on GitHub](https://github.com/nearai/aitp)
- [Agora Protocol](https://agoraprotocol.org/)
- [Agora arxiv 2410.11905](https://arxiv.org/html/2410.11905v1)
- [Letta](https://www.letta.com/)
- [letta-ai/agent-file](https://github.com/letta-ai/agent-file)
- [Project NANDA](https://projectnanda.org/)
- [NANDA Index arxiv 2507.14263](https://arxiv.org/pdf/2507.14263)
- [Inworld AI Runtime](https://inworld.ai/runtime)
- [Slack agentic OS announcement](https://slack.com/blog/news/powering-agentic-collaboration)
- [Salesforce AgentExchange](https://agentexchange.salesforce.com/)
- [Coinbase Agentic.Market — FinanceFeeds](https://financefeeds.com/ai-agent-commerce-is-here-inside-cryptos-new-agentic-stack/)
- [OpenClaw Matrix integration](https://www.openclawplaybook.ai/blog/openclaw-matrix-integration-decentralized-ai-messaging/)

### Standards & protocols
- [Model Context Protocol spec](https://modelcontextprotocol.io/specification/2025-11-25)
- [W3C DIDs v1.1](https://www.w3.org/TR/did-1.1/)
- [DIDComm Messaging Spec v2.0](https://identity.foundation/didcomm-messaging/spec/v2.0/)
- [DIDComm v2 approved — DIF](https://blog.identity.foundation/didcomm-v2/)
- [DIF Newsletter 59](https://blog.identity.foundation/dif-newsletter-59/)
- [Nostr.com](https://nostr.com/)
- [Nostr Protocol — nostr.how](https://nostr.how/en/the-protocol)
- [Nostrbook protocol](https://nostrbook.dev/protocol/)
- [AT Protocol — Bluesky docs](https://docs.bsky.app/docs/advanced-guides/atproto)
- [AT Protocol — Wikipedia](https://en.wikipedia.org/wiki/AT_Protocol)
- [ActivityPub — W3C](https://www.w3.org/TR/activitypub/)
- [Matrix.org](https://matrix.org/)
- [Matrix in govt IT — The Register](https://www.theregister.com/2026/02/09/matrix_element_secure_chat/)
- [XMPP MUC XEP-0045](https://xmpp.org/extensions/xep-0045.html)

### Companies / market
- [YC W26 batch analysis](https://www.buildmvpfast.com/blog/yc-w26-batch-agent-infrastructure-boom)
- [YC S25 batch profile — catalaize](https://catalaize.substack.com/p/y-combinator-s25-batch-profile-and)
- [Multifactor YC F25 raise — PRNewswire](https://www.prnewswire.com/news-releases/yc-f25-startup-multifactor-raises-15m-seed-round-to-make-online-accounts-safe-for-ai-agents-302633496.html)
- [Alter (YC S25)](https://www.ycombinator.com/companies/alter)
- [Introducing Agent Identity — OpenAgents](https://openagents.org/blog/posts/2026-02-03-introducing-agent-identity)
- [Agent Identity Convergence — DEV.to](https://dev.to/aaron_schnieder_4563d5d33/the-agent-identity-convergence-why-everyone-is-building-the-same-thing-in-2026-18la)
- [Prove Verified Agent — Finovate](https://finovate.com/proves-new-verified-agent-solution-brings-trust-and-verification-for-autonomous-agents/)
- [Picsart agent marketplace — TechCrunch](https://techcrunch.com/2026/03/16/picsart-now-allows-creators-to-hire-ai-assistants-through-agent-marketplace/)
- [Bluesky Attie — TechCrunch](https://techcrunch.com/2026/03/28/bluesky-leans-into-ai-with-attie-an-app-for-building-custom-feeds/)

### Academic papers
- [BlockA2A arxiv 2508.01332](https://arxiv.org/abs/2508.01332)
- [SAGA arxiv 2504.21034](https://arxiv.org/html/2504.21034v2)
- [Open Challenges in Multi-Agent Security arxiv 2505.02077](https://arxiv.org/html/2505.02077v1)
- [Survey of Agent Interoperability Protocols arxiv 2505.02279](https://arxiv.org/html/2505.02279v1)
- [Survey of AI Agent Protocols arxiv 2504.16736](https://arxiv.org/pdf/2504.16736)
- [AI Agents with DIDs and VCs arxiv 2511.02841](https://arxiv.org/abs/2511.02841)
- [Blockchain Learning Framework arxiv 2509.16736](https://arxiv.org/pdf/2509.16736)

### Risk / postmortems
- [Microsoft Copilot Studio postmortem — Medium](https://medium.com/@Micheal-Lanham/postmortem-of-a-miss-what-microsofts-ai-agent-sales-struggles-teach-us-all-3a79d9e32c5a)
- [Agent crashes lessons — Operator Collective](https://theoperatorcollective.org/blog/ai-agent-failures-lessons-crashes)
- [$4,200 runaway agent postmortem — Medium](https://medium.com/@sattyamjain96/the-agent-that-burned-4-200-in-63-hours-a-production-ai-postmortem-d38fd9586a85)
- [Bankrupt-startup Slack data being sold to AI — Agent Wars](https://www.agent-wars.com/news/2025-01-17-ai-companies-buying-dead-startup-slack-data)
- [DARPA wants AI agent comms research — The Register](https://www.theregister.com/2026/04/08/darpa_wants_ai_agent_communication/)
