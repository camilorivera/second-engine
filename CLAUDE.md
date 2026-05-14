# Second Engine — CLAUDE.md

## Project

Self-hosted endurance and health analytics platform. Personal use by a 178cm male, post-gastric-sleeve (3 years ago), running ~1 year. Goal: track HR adaptation, sustainable weight loss, and running improvement using Strava + Withings data.

## Rules

- **Docker-first**: all commands use Docker Compose. No local pip installs for runtime code.
- `setup/auth.py` is the only file that runs locally (stdlib only, no deps).
- Caveman mode is active for this project (terse responses).
- Pre-commit Trivy hook blocks commits with HIGH/CRITICAL findings.

## Quick Commands

```bash
make setup          # copy .env.example → .env, install pre-commit hook
make up             # docker compose up -d (postgres + worker + grafana)
make logs           # follow worker logs
make test-unit      # docker compose run --rm worker pytest tests/unit -v
make test           # full suite
make scan           # Trivy filesystem + deps scan
make scan-images    # Trivy scan of built images (run after build)
docker compose up -d --build worker   # rebuild + restart worker
docker compose --profile debug up -d  # + pgAdmin at localhost:5050
docker compose --profile api up -d    # + FastAPI at localhost:8000
```

## Services

| Service | URL | Default |
|---|---|---|
| Grafana | http://localhost:3000 | always |
| pgAdmin | http://localhost:5050 | `--profile debug` |
| FastAPI | http://localhost:8000 | `--profile api` (Phase 2) |

## Architecture

```
Strava API  ──┐
               ├── worker (Python/APScheduler) ──► PostgreSQL ──► Grafana
Withings API ──┘
```

- Worker syncs full history on first boot (when no `strava_last_sync_ts` in DB), incremental every hour after.
- Strava + Withings sync run in parallel threads.
- Analytics run every 6 hours (Phase 2+).
- Grafana reads PostgreSQL directly (no API layer in MVP).

## Key Files

| Path | Purpose |
|---|---|
| `docker-compose.yml` | All services, profiles |
| `db/init/001_schema.sql` | Full DB schema — source of truth |
| `worker/main.py` | Entry point, APScheduler setup |
| `worker/db.py` | SQLAlchemy engine, sync_state helpers |
| `worker/ingest/strava.py` | Strava sync — activities + streams |
| `worker/ingest/withings.py` | Withings sync — body metrics + resting HR |
| `worker/analytics/hr_zones.py` | Karvonen HR zone calculation |
| `worker/analytics/training_load.py` | TSS, ATL, CTL, TSB |
| `worker/analytics/forecasting.py` | Linear regression weight + pace |
| `worker/analytics/pace_analysis.py` | HR drift, pace at zone |
| `worker/recommendations/engine.py` | Rule-based recommendation engine |
| `setup/auth.py` | One-time OAuth CLI (Strava + Withings) |
| `grafana/dashboards/*.json` | Provisioned dashboards (auto-loaded) |

## Database Tables

| Table | Status | Notes |
|---|---|---|
| `activities` | ✅ populated | Strava activities (run + ride) |
| `activity_streams` | ✅ populated | Second-by-second HR/pace/altitude |
| `body_metrics` | ✅ populated | Withings weight, body fat, BMI |
| `resting_hr_daily` | ✅ populated | Withings resting HR (sparse) |
| `max_hr_estimates` | ⏳ Phase 2 | Rolling 30-day peak from streams |
| `hr_zone_history` | ⏳ Phase 2 | Karvonen zones over time |
| `daily_metrics` | ⏳ Phase 2 | Pre-aggregated zone minutes |
| `training_load` | ⏳ Phase 2 | ATL/CTL/TSB |
| `recommendations` | ⏳ Phase 4 | Rule-based recs |
| `sync_state` | ✅ used | Incremental sync checkpointing |

## Analytics Decisions (locked)

| Decision | Choice |
|---|---|
| HR zone method | Karvonen / HRR |
| Max HR | Rolling 30-day observed peak from streams |
| Resting HR | Withings primary, 7-day stream minimum fallback |
| Training load | ATL/CTL/TSB with HR-based TSS |
| Forecasting | Linear regression, 90-day rolling window |
| Recommendations | Rule-based Python logic |

### Karvonen Formula
```
HRR = max_hr - resting_hr
Zone N = resting_hr + (lower_pct × HRR)  →  resting_hr + (upper_pct × HRR)
Z1: 50–60%  Z2: 60–70%  Z3: 70–80%  Z4: 80–90%  Z5: 90–100%
```

### TSS / ATL / CTL / TSB
```
threshold_hr = zone4_min
TSS = duration_hours × (avg_hr / threshold_hr)² × 100
ATL = prev_ATL × exp(-1/7)  + TSS × (1 - exp(-1/7))
CTL = prev_CTL × exp(-1/42) + TSS × (1 - exp(-1/42))
TSB = CTL - ATL
```

## Grafana Dashboards

| Dashboard | File | Status |
|---|---|---|
| Overview | `overview.json` | ✅ live |
| Weight & Body | `weight_body.json` | ✅ live |
| HR Zones | `hr_zones.json` | ⏳ Phase 2 |
| Training Load | `training_load.json` | ⏳ Phase 2 |
| Pace Analytics | `pace_analytics.json` | ⏳ Phase 3 |
| Recommendations | `recommendations.json` | ⏳ Phase 4 |

## Phase Status

| Phase | Description | Status |
|---|---|---|
| 1 | Foundation: Docker, schema, OAuth, ingest | ✅ Complete |
| 2 | Core analytics: HR zones, training load, dashboards | ⏳ Next |
| 3 | Advanced: weight trends, pace, aerobic efficiency | 🔲 |
| 4 | Forecasting + recommendations | 🔲 |
| 5 | FastAPI, CI, polish | 🔲 |

See `ROADMAP.md` for full task breakdown.

## Environment Variables

See `.env.example`. Key vars:
- `DATABASE_URL` — postgres connection string
- `STRAVA_CLIENT_ID/SECRET/REFRESH_TOKEN`
- `WITHINGS_CLIENT_ID/SECRET/REFRESH_TOKEN`
- `MAX_HR_OVERRIDE` — optional, bypasses rolling 30-day calculation
- `SYNC_INTERVAL_HOURS` (default: 1)
- `ANALYTICS_INTERVAL_HOURS` (default: 6)

## Testing

```bash
# Unit tests — no DB, no Docker for test runner
docker compose run --rm worker pytest tests/unit -v

# Integration tests — require postgres
docker compose run --rm worker pytest tests/integration -v
```

Unit tests cover: `hr_zones`, `training_load`, `forecasting`, `pace_analysis`, `recommendations`.
Integration test stubs exist — implement in Phase 2.

## Known Constraints

- Strava rate limit: 100 req/15min, 1000 req/day. Initial full sync (~862 activities) takes ~2h. Only runs once (checkpointed in `sync_state`).
- `sport_data JSONB` column reserved for future cycling metrics (power, FTP, cadence). Currently always `{}`.
- `activity_type` distinguishes `run` vs `ride` — schema is cycling-ready.
