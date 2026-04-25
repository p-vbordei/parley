#!/usr/bin/env bash
# One-command end-to-end demo. From a clean checkout:
#
#   ./scripts/demo.sh
#
# Brings up Postgres in Docker, creates a venv with backend + plugin,
# runs migrations, starts the backend, runs examples/demo.py, and
# tears the backend down. Postgres stays up (it's cheap to leave; bring
# it down with `docker-compose -f backend/docker-compose.yml down`).
#
# Requires: docker, uv, python 3.12.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

echo "[1/5] Setting up venv (backend + plugin)…"
if [ ! -d ".venv" ]; then
  uv venv --python 3.12
fi
uv pip install -q -e ".[dev]" -e ../plugin/mcp

echo "[2/5] Bringing up Postgres…"
docker-compose up -d postgres
until docker exec backend-postgres-1 pg_isready -U agentrooms >/dev/null 2>&1; do
  sleep 1
done

echo "[3/5] Running migrations…"
.venv/bin/alembic upgrade head >/dev/null

echo "[4/5] Starting backend on :8000…"
.venv/bin/uvicorn agentrooms.api.main:app --port 8000 --log-level warning &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

# Wait for /v1/healthz
for _ in $(seq 1 20); do
  if curl -fs http://localhost:8000/v1/healthz >/dev/null; then break; fi
  sleep 0.5
done

echo "[5/5] Running the two-agent demo:"
echo "----"
.venv/bin/python "$ROOT/examples/demo.py"
echo "----"
echo
echo "Demo done. Backend on http://localhost:8000 will shut down with this script."
echo "Postgres stays up (cheap; \`docker-compose -f backend/docker-compose.yml down\` to stop)."
