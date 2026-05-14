import logging
import os
import time

import requests
from sqlalchemy import text

from db import get_session, get_sync_state, set_sync_state

logger = logging.getLogger(__name__)

TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
MEASURE_URL = "https://wbsapi.withings.net/measure"

# Withings measure types
MEASTYPE_WEIGHT = 1
MEASTYPE_FAT_PCT = 6
MEASTYPE_BMI = 4

# Withings heart measure types (via getintradayactivity or heartlist)
HEART_URL = "https://wbsapi.withings.net/v2/heart"


def _refresh_access_token() -> str:
    resp = requests.post(
        TOKEN_URL,
        data={
            "action": "requesttoken",
            "client_id": os.environ["WITHINGS_CLIENT_ID"],
            "client_secret": os.environ["WITHINGS_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["WITHINGS_REFRESH_TOKEN"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 0:
        raise RuntimeError(f"Withings token refresh failed: {body}")
    data = body["body"]
    os.environ["WITHINGS_REFRESH_TOKEN"] = data["refresh_token"]
    return data["access_token"]


def _headers() -> dict:
    token = _refresh_access_token()
    return {"Authorization": f"Bearer {token}"}


def _get_measures(headers: dict, startdate: int | None = None) -> list[dict]:
    params: dict = {"action": "getmeas", "meastypes": f"{MEASTYPE_WEIGHT},{MEASTYPE_FAT_PCT},{MEASTYPE_BMI}"}
    if startdate:
        params["startdate"] = startdate
    resp = requests.get(MEASURE_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 0:
        raise RuntimeError(f"Withings getmeas failed: {body}")
    return body["body"].get("measuregrps", [])


def _parse_value(measure: dict) -> float:
    return measure["value"] * (10 ** measure["unit"])


def _store_body_metrics(session, groups: list[dict]) -> None:
    for grp in groups:
        date = time.strftime("%Y-%m-%d", time.gmtime(grp["date"]))
        metrics: dict = {}
        for m in grp["measures"]:
            val = _parse_value(m)
            if m["type"] == MEASTYPE_WEIGHT:
                metrics["weight_kg"] = val
            elif m["type"] == MEASTYPE_FAT_PCT:
                metrics["body_fat_pct"] = val
            elif m["type"] == MEASTYPE_BMI:
                metrics["bmi"] = val

        if "weight_kg" not in metrics:
            continue

        session.execute(
            text("""
                INSERT INTO body_metrics (measured_at, weight_kg, body_fat_pct, bmi)
                VALUES (:date, :weight_kg, :body_fat_pct, :bmi)
                ON CONFLICT (measured_at) DO UPDATE SET
                    weight_kg = EXCLUDED.weight_kg,
                    body_fat_pct = EXCLUDED.body_fat_pct,
                    bmi = EXCLUDED.bmi
            """),
            {
                "date": date,
                "weight_kg": metrics.get("weight_kg"),
                "body_fat_pct": metrics.get("body_fat_pct"),
                "bmi": metrics.get("bmi"),
            },
        )
    session.commit()


def _fetch_resting_hr(headers: dict, startdate: int | None = None) -> list[dict]:
    params: dict = {"action": "list"}
    if startdate:
        params["startdate"] = startdate
    resp = requests.get(HEART_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 0:
        logger.debug("Withings heart list returned status %d — skipping resting HR", body.get("status"))
        return []
    return body["body"].get("series", [])


def _store_resting_hr(session, series: list[dict]) -> None:
    for entry in series:
        if "heart_rate" not in entry:
            continue
        resting = entry["heart_rate"].get("resting")
        if resting is None:
            continue
        date = time.strftime("%Y-%m-%d", time.gmtime(entry["timestamp"]))
        session.execute(
            text("""
                INSERT INTO resting_hr_daily (date, resting_hr_bpm, source)
                VALUES (:date, :hr, 'withings')
                ON CONFLICT (date) DO UPDATE SET
                    resting_hr_bpm = EXCLUDED.resting_hr_bpm,
                    source = 'withings'
            """),
            {"date": date, "hr": resting},
        )
    session.commit()


def sync(full: bool = False) -> None:
    session = get_session()
    headers = _headers()

    startdate = None
    if not full:
        stored = get_sync_state(session, "withings_last_sync_ts")
        if stored:
            startdate = int(stored)

    logger.info("Starting Withings sync (full=%s, startdate=%s)", full, startdate)

    groups = _get_measures(headers, startdate=startdate)
    _store_body_metrics(session, groups)
    logger.info("Stored %d body metric groups", len(groups))

    heart_series = _fetch_resting_hr(headers, startdate=startdate)
    _store_resting_hr(session, heart_series)
    logger.info("Stored %d resting HR entries", len(heart_series))

    set_sync_state(session, "withings_last_sync_ts", str(int(time.time())))
    session.close()
    logger.info("Withings sync complete.")
