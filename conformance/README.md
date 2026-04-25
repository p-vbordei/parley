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

## Cookbook: same checks in three other languages

These are *sketches* — they show the shape of the runner in each
language, not a tested artifact. The JSON vectors are the contract; the
code below is the obvious-but-unverified equivalent. PRs welcome with
real runners.

### TypeScript + Bun + `@noble/ed25519`

```ts
import { readFileSync } from "node:fs";
import { ed25519 } from "@noble/curves/ed25519";

const canonicalJson = (obj: unknown): Uint8Array =>
  // Sorted keys + no whitespace + no \u escapes — match SPEC §4.
  // For a real impl, walk the tree and use a stable JSON.stringify
  // replacer; the one-liner here is illustrative.
  new TextEncoder().encode(
    JSON.stringify(obj, Object.keys(obj as object).sort())
  );

const cv = JSON.parse(readFileSync("vectors/canonical_json.json", "utf8"));
for (const v of cv) {
  const got = new TextDecoder().decode(canonicalJson(v.input));
  if (got !== v.expected_bytes_utf8) throw new Error(`canonical[${v.name}]`);
}

const sv = JSON.parse(readFileSync("vectors/signatures.json", "utf8"));
for (const v of sv) {
  const sk = Uint8Array.from(Buffer.from(v.sk_hex, "hex"));
  const sig = ed25519.sign(new TextEncoder().encode(v.canonical_bytes_utf8), sk);
  if (Buffer.from(sig).toString("hex") !== v.expected_sig_hex)
    throw new Error(`sig[${v.name}]`);
}

console.log("OK");
```

### Rust + `ed25519-dalek` + `serde_json`

```rust
use ed25519_dalek::{Signature, SigningKey, Verifier, VerifyingKey};
use serde_json::Value;
use std::fs;

fn canonical(v: &Value) -> Vec<u8> {
    // SPEC §4: sorted keys at every level, no whitespace, UTF-8.
    // For a real impl, write a recursive serializer; serde_json::to_vec
    // is NOT canonical out of the box. See the `canonical_json` crate.
    todo!("see SPEC §4")
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    for v in serde_json::from_slice::<Vec<Value>>(
        &fs::read("vectors/canonical_json.json")?,
    )? {
        let got = canonical(&v["input"]);
        let want = v["expected_bytes_utf8"].as_str().unwrap().as_bytes();
        assert_eq!(&got, want, "canonical[{}]", v["name"]);
    }

    for v in serde_json::from_slice::<Vec<Value>>(
        &fs::read("vectors/signatures.json")?,
    )? {
        let sk_bytes: [u8; 32] = hex::decode(v["sk_hex"].as_str().unwrap())?
            .try_into().unwrap();
        let sk = SigningKey::from_bytes(&sk_bytes);
        let sig = sk.sign(v["canonical_bytes_utf8"].as_str().unwrap().as_bytes());
        assert_eq!(hex::encode(sig.to_bytes()), v["expected_sig_hex"]);
    }
    Ok(())
}
```

### Go + `golang.org/x/crypto/ed25519`

```go
package main

import (
    "crypto/ed25519"
    "encoding/hex"
    "encoding/json"
    "os"
)

func canonical(v interface{}) []byte {
    // SPEC §4: sorted keys, no whitespace, UTF-8.
    // encoding/json sorts map keys by default but emits whitespace.
    // For a real impl, post-process or use a canonical-JSON library.
    panic("see SPEC §4")
}

func main() {
    raw, _ := os.ReadFile("vectors/canonical_json.json")
    var cv []map[string]interface{}
    _ = json.Unmarshal(raw, &cv)
    for _, v := range cv {
        got := canonical(v["input"])
        want := v["expected_bytes_utf8"].(string)
        if string(got) != want {
            panic("canonical[" + v["name"].(string) + "]")
        }
    }

    raw, _ = os.ReadFile("vectors/signatures.json")
    var sv []map[string]interface{}
    _ = json.Unmarshal(raw, &sv)
    for _, v := range sv {
        skBytes, _ := hex.DecodeString(v["sk_hex"].(string))
        sk := ed25519.NewKeyFromSeed(skBytes)
        sig := ed25519.Sign(sk, []byte(v["canonical_bytes_utf8"].(string)))
        if hex.EncodeToString(sig) != v["expected_sig_hex"].(string) {
            panic("sig[" + v["name"].(string) + "]")
        }
    }
}
```

### The hard part is canonical-JSON, not the crypto

Note the `todo!()` / `panic` placeholders for `canonical()` in Rust and
Go: most JSON libraries are *not* byte-exact-canonical out of the box.
You'll need either a JCS-compatible library or a small recursive
serializer that:

1. Sorts object keys lexicographically by UTF-16 code point at every
   nesting level.
2. Uses `,` and `:` separators with no surrounding whitespace.
3. Emits non-ASCII characters as literal UTF-8 bytes (not `\u` escaped).
4. Doesn't normalize numbers (the SPEC forbids floats in signed
   payloads).

The Python reference is six lines:
```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```
In other languages it's a 30–50 line recursive walk. The
`canonical_json.json` vectors will tell you immediately if you've gotten
it right.

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
