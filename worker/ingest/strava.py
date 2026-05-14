import logging
import os
import time
from datetime import datetime, timezone

import requests
from sqlalchemy import text

from db import get_session, get_sync_state, set_sync_state

logger = logging.getLogger(__name__)

STRAVA_API = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/oauth/token"

# Strava rate limits: 100 req/15min, 1000 req/day
_request_times: list[float] = []


def _rate_limited_get(url: str, headers: dict, params: dict | None = None) -> dict:
    global _request_times
    now = time.time()
    _request_times = [t for t in _request_times if now - t < 900]
    if len(_request_times) >= 95:
        sleep_for = 900 - (now - _request_times[0]) + 1
        logger.info("Rate limit approaching, sleeping %.0fs", sleep_for)
        time.sleep(sleep_for)
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    _request_times.append(time.time())
    resp.raise_for_status()
    return resp.json()


def _refresh_access_token() -> str:
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    # Persist refreshed token back to env so the process keeps working
    os.environ["STRAVA_REFRESH_TOKEN"] = data["refresh_token"]
    return data["access_token"]


def _headers() -> dict:
    token = _refresh_access_token()
    return {"Authorization": f"Bearer {token}"}


def _upsert_activity(session, a: dict) -> str | None:
    sport = a.get("type", "").lower()
    avg_speed = a.get("average_speed", 0)
    avg_pace_spm = (1000.0 / avg_speed) if avg_speed and sport == "run" else None

    row = session.execute(
        text("""
            INSERT INTO activities
                (strava_id, sport, start_time, duration_secs, distance_m,
                 elevation_m, avg_hr, max_hr, avg_pace_spm, calories, sport_data)
            VALUES
                (:strava_id, :sport, :start_time, :duration_secs, :distance_m,
                 :elevation_m, :avg_hr, :max_hr, :avg_pace_spm, :calories,
                 :sport_data::jsonb)
            ON CONFLICT (strava_id) DO UPDATE SET
                avg_hr = EXCLUDED.avg_hr,
                max_hr = EXCLUDED.max_hr,
                calories = EXCLUDED.calories
            RETURNING id
        """),
        {
            "strava_id": a["id"],
            "sport": sport,
            "start_time": a["start_date"],
            "duration_secs": a.get("moving_time", 0),
            "distance_m": a.get("distance"),
            "elevation_m": a.get("total_elevation_gain"),
            "avg_hr": a.get("average_heartrate"),
            "max_hr": a.get("max_heartrate"),
            "avg_pace_spm": avg_pace_spm,
            "calories": a.get("calories"),
            "sport_data": "{}",
        },
    ).fetchone()
    session.commit()
    return str(row[0]) if row else None


def _fetch_and_store_streams(session, activity_id: str, strava_id: int, headers: dict) -> None:
    try:
        data = _rate_limited_get(
            f"{STRAVA_API}/activities/{strava_id}/streams",
            headers=headers,
            params={"keys": "heartrate,velocity_smooth,altitude,distance,cadence", "key_by_type": "true"},
        )
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return
        raise

    time_stream = data.get("time", {}).get("data", [])
    hr_stream = data.get("heartrate", {}).get("data", [])
    vel_stream = data.get("velocity_smooth", {}).get("data", [])
    alt_stream = data.get("altitude", {}).get("data", [])
    dist_stream = data.get("distance", {}).get("data", [])
    cad_stream = data.get("cadence", {}).get("data", [])

    if not time_stream:
        return

    # Fetch start_time for this activity to compute absolute timestamps
    row = session.execute(
        text("SELECT start_time FROM activities WHERE id = :id"), {"id": activity_id}
    ).fetchone()
    if not row:
        return
    start_time: datetime = row[0]
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    # Delete existing streams before re-inserting
    session.execute(text("DELETE FROM activity_streams WHERE activity_id = :id"), {"id": activity_id})

    rows = []
    for i, offset in enumerate(time_stream):
        from datetime import timedelta
        recorded_at = start_time + timedelta(seconds=offset)
        vel = vel_stream[i] if i < len(vel_stream) else None
        pace_spm = (1000.0 / vel) if vel and vel > 0 else None
        rows.append({
            "activity_id": activity_id,
            "recorded_at": recorded_at,
            "hr_bpm": hr_stream[i] if i < len(hr_stream) else None,
            "pace_spm": pace_spm,
            "altitude_m": alt_stream[i] if i < len(alt_stream) else None,
            "distance_m": dist_stream[i] if i < len(dist_stream) else None,
            "cadence": cad_stream[i] if i < len(cad_stream) else None,
        })

    if rows:
        session.execute(
            text("""
                INSERT INTO activity_streams
                    (activity_id, recorded_at, hr_bpm, pace_spm, altitude_m, distance_m, cadence)
                VALUES
                    (:activity_id, :recorded_at, :hr_bpm, :pace_spm, :altitude_m, :distance_m, :cadence)
            """),
            rows,
        )
        session.commit()


def sync(full: bool = False) -> None:
    session = get_session()
    headers = _headers()

    after_ts = None
    if not full:
        stored = get_sync_state(session, "strava_last_sync_ts")
        if stored:
            after_ts = int(stored)

    page = 1
    total = 0
    logger.info("Starting Strava sync (full=%s, after=%s)", full, after_ts)

    while True:
        params: dict = {"per_page": 50, "page": page}
        if after_ts:
            params["after"] = after_ts

        activities = _rate_limited_get(f"{STRAVA_API}/athlete/activities", headers=headers, params=params)
        if not activities:
            break

        for a in activities:
            activity_id = _upsert_activity(session, a)
            if activity_id:
                _fetch_and_store_streams(session, activity_id, a["id"], headers)
            total += 1

        # Track latest start time for incremental syncs
        latest_ts = max(
            int(datetime.fromisoformat(a["start_date"].replace("Z", "+00:00")).timestamp())
            for a in activities
        )
        set_sync_state(session, "strava_last_sync_ts", str(latest_ts))

        logger.info("Synced page %d (%d activities so far)", page, total)
        page += 1

    session.close()
    logger.info("Strava sync complete. Total activities processed: %d", total)
