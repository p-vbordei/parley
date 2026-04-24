# Agent Rooms conformance vectors

Byte-level test vectors that define protocol correctness at the wire
layer. Everything here is language-agnostic — a second implementation in
Rust, Go, or TypeScript can validate itself against these files without
ever touching the reference backend.

See [`../SPEC.md`](../SPEC.md) §11 for the conformance clauses each
category maps to.

## Run against the reference implementation

```bash
# One-time: the runner only needs pynacl + stdlib.
uv venv && uv pip install pynacl

./.venv/bin/python conformance/run.py
```

Expected output:

```
OK: 25 vectors passed (canonical_json=15, signatures=4, mutation=6)
```

Full run is under a second.

## Three categories

### `vectors/canonical_json.json`

Input object → exact UTF-8 bytes produced by the canonical encoder
(SPEC §4). Covers: empty values, key sorting at every level, whitespace
elision, `ensure_ascii=False` for non-ASCII UTF-8, null/boolean
preservation, array-order preservation, and the four real operation
payload shapes.

### `vectors/signatures.json`

Fixed secret key + payload → exact Ed25519 signature. Ed25519 is
deterministic (RFC 8032), so these are reproducible byte-for-byte
across implementations. Each entry also includes the derived public
key, so an implementation can validate its key derivation in passing.

### `vectors/mutation.json`

Valid (pubkey, canonical bytes, signature) triples alongside must-fail
tampers — flipped signature bytes, truncated signatures, mutated body,
bumped `turn_n`. Includes one *positive* anti-case:
`wire_reordered_keys_but_canonical_identical`, which shows that
reordering keys on the wire does not break verification — a feature, not
a bug, because the signature binds the *canonical* bytes, not the wire
bytes.

## Validating a non-Python implementation

1. Implement the canonical-JSON encoder from SPEC §4.
2. Load `vectors/canonical_json.json`; for each entry, canonicalize
   `input` and assert the bytes equal `expected_bytes_utf8`
   (or decode `expected_bytes_b64`).
3. Load `vectors/signatures.json`; for each entry, Ed25519-sign
   `canonical_bytes_utf8` with `sk_hex` and assert the signature matches
   `expected_sig_hex`.
4. Load `vectors/mutation.json`; for each entry, Ed25519-verify and
   assert the result equals `must_verify`.

If all three pass, your implementation is byte-compatible with the
Agent Rooms wire format at the cryptographic layer. The state-machine
clauses (C11–C24) still need their own per-language tests.

## Regenerating vectors

Only when the SPEC changes:

```bash
./.venv/bin/python conformance/run.py --generate
```

This overwrites `vectors/*.json` from the reference code. Review the
diff carefully — regenerated vectors are a backwards-incompatible spec
change unless they're additive.

## Drift protection

`backend/tests/test_conformance.py` replays these same vectors through
the *backend* crypto module (`agentrooms.crypto`). If the standalone
runner and the backend ever diverge, CI fails here first.
