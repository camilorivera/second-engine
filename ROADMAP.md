# Second Engine — Roadmap

## Phase 1 — Foundation ✅ Complete

- [x] Docker Compose: postgres + worker + grafana (pgAdmin + API as optional profiles)
- [x] Full DB schema (`db/init/001_schema.sql`)
- [x] OAuth CLI bootstrap for Strava + Withings (`setup/auth.py`, stdlib only)
- [x] Strava ingest: full history on first boot + incremental every 1h
- [x] Withings ingest: body metrics + resting HR
- [x] Parallel sync (Strava + Withings in threads)
- [x] Incremental sync checkpointed in DB (no re-sync on restart)
- [x] Grafana datasource + dashboard provisioning config
- [x] Overview dashboard (runs, weekly distance/duration, recent runs table)
- [x] Weight & Body Composition dashboard (trend, 7-day avg, body fat, resting HR)
- [x] Unit test suite (hr_zones, training_load, forecasting, pace_analysis, recommendations)
- [x] Trivy pre-commit security hook (`make setup` installs it)
- [x] Non-root Docker user

---

## Phase 2 — Core Analytics + HR Zone Dashboards ⏳ Next

### Worker: analytics runner

Wire analytics into `worker/main.py` `run_analytics()` (currently a stub):

```python
# main.py run_analytics()
from analytics import hr_zones, training_load
hr_zones.run(session)
training_load.run(session)
```

### `worker/analytics/hr_zones.py` — implement `run(session)`

1. **Max HR**: query `activity_streams` for max `hr_bpm` in last 30 days per day. Insert into `max_hr_estimates`.
2. **Resting HR**: pull latest from `resting_hr_daily` (Withings). If gap > 7 days, derive from 7-day min of stream HR. Check `MAX_HR_OVERRIDE` env var.
3. **Karvonen zones**: call `karvonen(max_hr, resting_hr)` (already implemented). Insert into `hr_zone_history` if values changed.

### `worker/analytics/training_load.py` — implement `run(session)`

1. For each day with activities, compute `hr_tss()` per activity using `zone4_min` as threshold.
2. Walk days in order, compute `atl()` and `ctl()` via exponential decay.
3. Compute `tsb = ctl - atl`.
4. Upsert into `training_load` table.

### `worker/analytics/daily_metrics.py` — new file

Aggregate zone minutes per day from `activity_streams` joined with latest `hr_zone_history`:
- For each stream point, classify HR into Z1–Z5.
- Sum minutes per zone per day.
- Upsert into `daily_metrics`.

### Grafana dashboards

- [ ] `grafana/dashboards/hr_zones.json`
  - Zone distribution bar per run
  - Zone trend over time (stacked area)
  - Max HR trend line
  - Resting HR trend line
  - Zone boundary evolution (Z2 min/max over time)
- [ ] `grafana/dashboards/training_load.json`
  - ATL/CTL/TSB time series
  - Weekly TSS bar chart
  - Form status (positive TSB = fresh, negative = fatigued)

### Integration tests

Implement `tests/integration/test_strava_ingest.py` and `test_withings_ingest.py`:
- Mock Strava/Withings API responses with `pytest-mock`
- Assert correct rows inserted into DB
- Assert `sync_state` updated

---

## Phase 3 — Advanced Analytics

### `worker/analytics/weight_trends.py` — implement `run(session)`

- 7-day rolling average weight (already has `rolling_average()` fn)
- Correlation: weekly Zone 2 hours vs weight change that week
- Store results in `daily_metrics` or a new `weight_analytics` table

### `worker/analytics/pace_analysis.py` — implement `run(session)`

- Per run: compute `pace_at_zone()` for Zone 2 using stream data and current zone boundaries
- Per run: compute `hr_drift_pct()` from stream HR
- Store in activity-level analytics table or extend `activities` with computed columns

### Grafana dashboards

- [ ] `grafana/dashboards/pace_analytics.json`
  - Pace-at-Zone2 trend over time
  - HR drift per run (scatter/line)
  - Aerobic efficiency improvement
  - Pace vs weight scatter (last 90 days)
- [ ] Update `weight_body.json`
  - Add weight vs weekly training volume scatter
  - Add Zone 2 hours vs weight loss correlation panel

---

## Phase 4 — Forecasting + Recommendations

### `worker/analytics/forecasting.py` — implement `run(session)`

- Pull last 90 days of `body_metrics` weights → `weight_forecast_kg()` → store in new `forecasts` table or as a recommendation
- Pull last 90 days of weekly `pace_at_z2` → `pace_forecast_spm()` → same

### `worker/recommendations/engine.py` — implement `run(session)`

Wire `generate(RecommendationInput(...))` to pull live data from DB and insert results into `recommendations` table. Runs daily.

Input data queries:
- `week_z2_hours`: sum `daily_metrics.z2_mins` for current week / 60
- `weight_7d_trend_kg`: linregress on last 7 days of `body_metrics`
- `resting_hr_today / 30d_ago`: from `resting_hr_daily`
- `pace_at_z2_today / 90d_ago`: from pace analytics
- `tsb`: latest `training_load.tsb`
- `active_days_last_14`: count distinct dates in `activities` last 14 days
- `weight_forecast_12w_kg`: from forecasting run

### Grafana dashboards

- [ ] `grafana/dashboards/recommendations.json`
  - Latest recommendations table (filterable by category)
  - Trend indicators
- [ ] Add forecast overlay to `weight_body.json` weight trend panel
- [ ] Add forecast overlay to `pace_analytics.json`

---

## Phase 5 — FastAPI + CI + Polish

### `api/main.py` — FastAPI service

Enable via `docker compose --profile api up -d`.

Endpoints:
```
GET  /health
GET  /status          last sync time, record counts
POST /sync/strava     trigger manual Strava sync
POST /sync/withings   trigger manual Withings sync
GET  /recommendations latest N recommendations
GET  /analytics/hr-zones
GET  /analytics/training-load
```

### CI

`.github/workflows/ci.yml`:
- `pytest tests/unit` on push
- Trivy image scan on build
- Trivy secrets scan on PR

### Polish

- [ ] Dashboard links between panels
- [ ] Grafana annotations for key events (race dates, illness, etc.)
- [ ] Alert rules: TSB < -25 → Grafana alert
- [ ] Strava rate limit backoff improvements (daily limit awareness)
- [ ] `make sync` target to manually trigger sync via API

---

## Future: Cycling Support

Schema is ready (`sport = 'ride'`, `sport_data JSONB`). When adding cycling:

1. Add cycling-specific analytics to `sport_data`: `{"power": null, "ftp": null, "cadence": null}`
2. New `worker/analytics/cycling.py`: FTP estimation, power zones, TSS via power (Training Peaks method)
3. New Grafana dashboard: `cycling.json`
4. Update `daily_metrics` to split by sport

No DB migration needed — `sport_data` already present on all rows.

---

## Analytics Reference

### Karvonen HR Zones
```
HRR = max_hr - resting_hr
Z1: resting_hr + 0.50×HRR  →  resting_hr + 0.60×HRR
Z2: resting_hr + 0.60×HRR  →  resting_hr + 0.70×HRR
Z3: resting_hr + 0.70×HRR  →  resting_hr + 0.80×HRR
Z4: resting_hr + 0.80×HRR  →  resting_hr + 0.90×HRR
Z5: resting_hr + 0.90×HRR  →  max_hr
```

### HR-based TSS
```
threshold_hr = zone4_min
IF = avg_hr / threshold_hr
TSS = duration_hours × IF² × 100
```

### ATL / CTL / TSB
```
ATL = prev × exp(-1/7)  + TSS × (1 - exp(-1/7))    # 7-day decay
CTL = prev × exp(-1/42) + TSS × (1 - exp(-1/42))   # 42-day decay
TSB = CTL - ATL
```

### HR Drift
```
drift% = (avg_hr_2nd_half - avg_hr_1st_half) / avg_hr_1st_half × 100
```

### Linear Forecast
```python
slope, intercept = linregress(range(len(values)), values)
forecast = intercept + slope × (len(values) - 1 + days_ahead)
```
