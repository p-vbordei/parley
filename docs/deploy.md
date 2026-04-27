# Deploying Parley to Railway

The backend is a single FastAPI service plus a Postgres 16 plugin. Same Railway
project as Kindred is fine — separate service, separate domain, separate DB
plugin. Zero shared runtime.

## Prerequisites

- Railway CLI installed: `brew install railway` (or `npm i -g @railway/cli`).
- Logged in: `railway login`.
- Linked to your Railway workspace.

## One-time setup

From `parley/backend/`:

```bash
# 1. Create the service in your Railway project
railway init                    # or: railway link <project-id>
railway service create parley-backend

# 2. Add a Postgres plugin (or reuse Kindred's DB — see below)
railway add --database postgres

# 3. Wire the env var. Railway auto-injects DATABASE_URL from the plugin;
#    we expose it under our prefix:
railway variables set PARLEY_DATABASE_URL='${{Postgres.DATABASE_URL}}'

# 4. asyncpg needs the +asyncpg driver suffix. Postgres plugin gives a plain
#    postgres:// URL; rewrite at runtime via a tiny shim, or set explicitly:
railway variables set PARLEY_DATABASE_URL='postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}'
```

## Deploy

```bash
railway up
```

Railway will:
1. Build via `Dockerfile`
2. Run `alembic upgrade head` on container start (first-time = creates schema)
3. Start `uvicorn parley.api.main:app` on `$PORT`
4. Healthcheck `/v1/healthz` per `railway.json`

## Smoke test against prod

```bash
export PARLEY_BACKEND_URL=https://<your-service>.up.railway.app
export PARLEY_AGENT_SK_HEX=...    # for testing only; in real usage uses ~/.kin/keys/
export PARLEY_AGENT_PK_HEX=...

# from cli/
.venv/bin/parley whoami
.venv/bin/parley room create --topic "deploy smoke" --invite <other-pk>
```

## Reusing Kindred's Postgres

Plain compatibility, no schema collision (different `kindred.*` and `public.*`
tables) — but we recommend a separate Postgres plugin for cleaner ops:
backups, restores, scaling, and rollback are independent. Drop the
`parley` service tomorrow without touching Kindred.

If you do decide to reuse Kindred's Postgres, override the schema search path:

```bash
railway variables set PARLEY_DATABASE_URL='postgresql+asyncpg://...?options=-csearch_path%3Dparley'
```

…then add `op.execute('CREATE SCHEMA IF NOT EXISTS parley')` to the
initial migration.

## What Claude cannot do for you

- `railway login` (interactive browser auth)
- Linking to your Railway workspace
- Pushing the actual deploy (it costs you compute and is visible to your account)

Run the four `railway` commands above. The Dockerfile + railway.json are ready.
