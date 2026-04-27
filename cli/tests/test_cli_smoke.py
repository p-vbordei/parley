"""CLI smoke tests against a live backend.

Spins up uvicorn in-process, drives the CLI as a subprocess via the venv's
`parley` entry-point. Verifies exit code + JSON shape of each command.

Skip if backend deps aren't importable in this venv (CLI venv doesn't include them).
We use httpx ASGITransport directly via a thread-running uvicorn instead.
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("uvicorn")

# Backend lives in a sibling venv; we exec it via uv run in the backend dir
# so its deps (fastapi, sqlalchemy, asyncpg) are available.
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
CLI_VENV_PYTHON = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_backend():
    """Run uvicorn against backend's FastAPI app, in a subprocess using the backend's venv."""
    port = _free_port()
    env = {**os.environ, "PARLEY_DATABASE_URL": os.environ.get(
        "PARLEY_DATABASE_URL",
        "postgresql+asyncpg://parley:parley@localhost:5435/parley",
    )}
    proc = subprocess.Popen(
        [
            str(BACKEND_DIR / ".venv" / "bin" / "uvicorn"),
            "parley.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    # Wait for ready
    deadline = time.time() + 15
    import http.client

    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            conn.request("GET", "/v1/healthz")
            r = conn.getresponse()
            if r.status == 200:
                break
        except OSError:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError(
            f"backend did not become healthy on port {port}\n"
            f"stderr: {proc.stderr.read().decode()[:1000] if proc.stderr else ''}"
        )

    # Truncate to start clean
    import urllib.request

    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _truncate_db():
    """Wipe app tables between tests via psql."""
    subprocess.run(
        [
            "docker",
            "exec",
            "backend-postgres-1",
            "psql",
            "-U",
            "parley",
            "-d",
            "parley",
            "-c",
            "TRUNCATE TABLE messages, participants, rooms RESTART IDENTITY",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _gen_keypair_hex() -> tuple[str, str]:
    from nacl import signing

    sk = signing.SigningKey.generate()
    return bytes(sk).hex(), bytes(sk.verify_key).hex()


def _run_cli(args, env_extra) -> tuple[int, dict | str]:
    env = {**os.environ, **env_extra}
    proc = subprocess.run(
        [str(CLI_VENV_PYTHON), "-m", "parley_cli.main", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return proc.returncode, proc.stderr or proc.stdout
    out = proc.stdout.strip()
    try:
        return 0, json.loads(out)
    except json.JSONDecodeError:
        return 0, out


def test_whoami(live_backend):
    sk, pk = _gen_keypair_hex()
    code, out = _run_cli(
        ["whoami"],
        {"PARLEY_AGENT_SK_HEX": sk, "PARLEY_AGENT_PK_HEX": pk},
    )
    assert code == 0, out
    assert out == pk


def test_full_flow(live_backend):
    _truncate_db()
    sk_a, pk_a = _gen_keypair_hex()
    sk_b, pk_b = _gen_keypair_hex()
    env_a = {
        "PARLEY_AGENT_SK_HEX": sk_a,
        "PARLEY_AGENT_PK_HEX": pk_a,
        "PARLEY_BACKEND_URL": live_backend,
    }
    env_b = {
        "PARLEY_AGENT_SK_HEX": sk_b,
        "PARLEY_AGENT_PK_HEX": pk_b,
        "PARLEY_BACKEND_URL": live_backend,
    }

    code, room = _run_cli(
        ["room", "create", "--topic", "cli-smoke", "--invite", pk_b, "--max-turns", "4"],
        env_a,
    )
    assert code == 0, room
    room_id = room["room_id"]
    assert room["turn_owner_pubkey"] == pk_a

    code, _ = _run_cli(["room", "accept", room_id], env_b)
    assert code == 0

    code, post = _run_cli(["room", "post", room_id, "--body", "hi from alice"], env_a)
    assert code == 0, post
    assert post["turn_n"] == 1

    code, poll = _run_cli(["room", "poll", room_id, "--since", "0"], env_b)
    assert code == 0, poll
    assert len(poll["messages"]) == 1
    assert poll["messages"][0]["body"] == "hi from alice"

    code, lst = _run_cli(["room", "list"], env_a)
    assert code == 0, lst
    assert any(r["room_id"] == room_id for r in lst)

    code, closed = _run_cli(
        ["room", "close", room_id, "--summary", "done"], env_a
    )
    assert code == 0, closed
    assert closed["status"] == "closed"
    assert closed["summary"] == "done"
