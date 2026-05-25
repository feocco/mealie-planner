# Mealie Planner

OpenAI-assisted dinner planner for Joe's Mealie instance. V1 proposes dinner plans from compact Mealie recipe metadata, sends an actionable phone notification through `homelab-functions`, and writes to Mealie only after acceptance.

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
- `POST /v1/plans/{plan_id}/accept`
- `POST /v1/plans/{plan_id}/regenerate`
- `POST /v1/plans/{plan_id}/dismiss`

Draft plans stay local in SQLite under `DATA_DIR`. Mealie meal planner entries are created only by the accept endpoint or Accept notification action.

## Docs

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Security](docs/security.md)

