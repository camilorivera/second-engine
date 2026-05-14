# second-engine

Self-hosted endurance and health analytics platform using Strava and Withings data to track running, heart-rate adaptation, recovery, and sustainable weight loss.

## Quick start

### 1. Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for the one-time auth setup script)
- A Strava API app — register at https://www.strava.com/settings/api
- A Withings API app — register at https://developer.withings.com/

### 2. Setup

```bash
# Clone and enter the repo
git clone <repo-url> && cd second-engine

# Install pre-commit Trivy security hook and create .env
make setup

# Fill in your Strava and Withings client_id / client_secret in .env
# then run the one-time OAuth flow to get refresh tokens
python setup/auth.py all
```

### 3. Run

```bash
docker compose up -d
```

Opens Grafana at http://localhost:3000 (default password in `.env`).

The worker syncs full history on first start, then runs incremental syncs every hour.

## Services

| Service | Default | Profile |
|---|---|---|
| postgres | always | — |
| worker | always | — |
| grafana | always | — |
| pgadmin | off | `debug` |
| api (FastAPI) | off | `api` |

```bash
# Debug with pgAdmin
docker compose --profile debug up -d

# Phase 2 API
docker compose --profile api up -d
```

## Development

```bash
make test           # full test suite via Docker
make test-unit      # unit tests only (no DB needed)
make scan           # Trivy security scan (filesystem + deps)
make scan-images    # Trivy scan of built Docker images
make logs           # follow worker logs
```

## Architecture

```
Strava API  ──┐
               ├── worker (Python) ──► PostgreSQL ──► Grafana
Withings API ──┘
```

- **worker**: scheduled ingest (APScheduler) + analytics + recommendations
- **postgres**: single source of truth — activities, streams, body metrics, HR zones, training load
- **grafana**: dashboards provisioned as code from `grafana/dashboards/`
- **api** (Phase 2): FastAPI for manual sync triggers and recommendations endpoint

## Phased roadmap

| Phase | Focus |
|---|---|
| 1 | Foundation: Docker Compose, schema, OAuth, Strava + Withings ingest |
| 2 | Core analytics: Karvonen HR zones, ATL/CTL/TSB, first Grafana dashboards |
| 3 | Advanced: weight trends, pace analysis, aerobic efficiency |
| 4 | Forecasting + rule-based recommendations |
| 5 | FastAPI, CI, polished dashboards |
