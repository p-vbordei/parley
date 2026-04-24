"""Load the active agent's keypair from `~/.kin/`.

Convention shared with Kindred: `~/.kin/config.toml` names `active_agent_id`,
the keypair lives at `~/.kin/keys/<active_agent_id>.key` as `<sk_hex>\\n<pk_hex>`.

For testing/CI, env vars override:
- AGENTROOMS_AGENT_SK_HEX  — 32-byte hex secret key
- AGENTROOMS_AGENT_PK_HEX  — 32-byte hex public key
"""

import os
import tomllib
from pathlib import Path


def _kin_dir() -> Path:
    return Path.home() / ".kin"


def _read_active_agent_id() -> str | None:
    cfg = _kin_dir() / "config.toml"
    if not cfg.exists():
        return None
    with cfg.open("rb") as f:
        data = tomllib.load(f)
    return data.get("active_agent_id")


def load_active_keypair() -> tuple[bytes, bytes]:
    """Returns (sk, pk). Raises FileNotFoundError if neither env vars nor key file are set."""
    sk_hex = os.environ.get("AGENTROOMS_AGENT_SK_HEX")
    pk_hex = os.environ.get("AGENTROOMS_AGENT_PK_HEX")
    if sk_hex and pk_hex:
        return bytes.fromhex(sk_hex), bytes.fromhex(pk_hex)

    agent_id = _read_active_agent_id()
    if not agent_id:
        raise FileNotFoundError(
            "no active_agent_id in ~/.kin/config.toml and no "
            "AGENTROOMS_AGENT_SK_HEX/PK_HEX env vars set"
        )
    key_file = _kin_dir() / "keys" / f"{agent_id}.key"
    if not key_file.exists():
        raise FileNotFoundError(f"keypair file missing: {key_file}")
    lines = key_file.read_text().strip().splitlines()
    if len(lines) != 2:
        raise ValueError(f"malformed keypair file: {key_file}")
    return bytes.fromhex(lines[0]), bytes.fromhex(lines[1])
