# Mealie Planner

OpenAI-assisted dinner planner for Joe's Mealie instance. V1 proposes dinner plans from compact Mealie recipe metadata, sends Joe an actionable phone notification through `homelab-functions`, hands Joe's accepted plan to Jess for review, and writes only accepted versions to Mealie.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env.local
.venv/bin/python -m pytest
.venv/bin/mealie-planner
```

The service exposes:

- `GET /health`
- `POST /v1/plans/suggest`
- `GET /v1/plans/{plan_id}`
- `GET /v1/plans/{plan_id}/ingredients`
- `POST /v1/plans/{plan_id}/accept`
- `POST /v1/plans/{plan_id}/regenerate`
- `POST /v1/plans/{plan_id}/dismiss`

Draft plans stay local in SQLite under `DATA_DIR`. Joe's Accept writes the first planner-owned dinner entries, then Jess can modify and accept the final version. Jess's Accept replaces only entries created for the same planner plan and notifies Joe.

The ingredients endpoint is read-only and intended for manual testing after a
plan is accepted. It returns ingredients grouped by selected recipe plus a
conservative consolidated view; it does not alter Mealie, send notifications,
or create grocery lists.

## Docs

- [API Usage](docs/api.md)
- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Security](docs/security.md)
