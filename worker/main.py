import logging
import os
import sys
import threading
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

SYNC_INTERVAL_HOURS = int(os.getenv("SYNC_INTERVAL_HOURS", "1"))
ANALYTICS_INTERVAL_HOURS = int(os.getenv("ANALYTICS_INTERVAL_HOURS", "6"))

def run_ingest() -> None:
    from ingest import strava, withings
    from db import get_session, get_sync_state

    session = get_session()
    already_synced = bool(get_sync_state(session, "strava_last_sync_ts"))
    session.close()

    full = not already_synced
    if full:
        logger.info("Running full historical sync...")
    else:
        logger.info("Running incremental sync...")

    def _strava():
        try:
            strava.sync(full=full)
        except Exception:
            logger.exception("Strava sync failed")

    def _withings():
        try:
            withings.sync(full=full)
        except Exception:
            logger.exception("Withings sync failed")

    t1 = threading.Thread(target=_strava, daemon=True)
    t2 = threading.Thread(target=_withings, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def run_analytics() -> None:
    # Phase 2 — analytics modules will be wired here
    logger.info("Analytics cycle skipped (Phase 2)")


def wait_for_db(max_retries: int = 30, delay: int = 2) -> None:
    from db import get_engine
    from sqlalchemy import text

    for attempt in range(1, max_retries + 1):
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database ready.")
            return
        except Exception as e:
            logger.info("Waiting for DB (%d/%d): %s", attempt, max_retries, e)
            time.sleep(delay)
    raise RuntimeError("Database not available after retries.")


if __name__ == "__main__":
    wait_for_db()

    # Run initial ingest immediately on startup
    run_ingest()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_ingest, "interval", hours=SYNC_INTERVAL_HOURS, id="ingest")
    scheduler.add_job(run_analytics, "interval", hours=ANALYTICS_INTERVAL_HOURS, id="analytics")

    logger.info(
        "Scheduler started. Ingest every %dh, analytics every %dh.",
        SYNC_INTERVAL_HOURS,
        ANALYTICS_INTERVAL_HOURS,
    )
    scheduler.start()
