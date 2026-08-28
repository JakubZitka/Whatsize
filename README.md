# WhatSize

Cross-brand clothing size finder for iOS and Android. See `docs/deployment-plan.md`
for the full deployment and operations plan (in Czech) and the PRD for product scope.

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI service: matching engine API, health endpoints, Alembic migrations |
| `mobile/` | Flutter app (run `flutter create .` inside to generate platform folders) |
| `infra/terraform/` | Hetzner Cloud infrastructure: network, load balancer, app/db/staging servers |
| `deploy/` | Production docker-compose stack used on the app servers |
| `.github/workflows/` | CI (lint + tests) and CD (image build → GHCR → rolling SSH deploy) |
| `codemagic.yaml` | Mobile CI: analyze, test, build for TestFlight / Play internal |
| `docs/` | Deployment plan and other documents |

## Local development

Requires Docker.

```bash
docker compose up          # API on http://localhost:8000, Postgres, Redis
```

API docs: http://localhost:8000/docs — health check: http://localhost:8000/healthz

Backend without Docker:

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Tests and lint:

```bash
cd backend
ruff check . && pytest
```

## Deployment

1. Provision infrastructure: `infra/terraform/README.md`.
2. Configure GitHub secrets for the deploy workflow (`DEPLOY_SSH_KEY`, `APP_HOSTS`).
3. Merges to `main` build the backend image, push it to GHCR and roll it out
   server-by-server behind the load balancer.
