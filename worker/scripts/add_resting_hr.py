#!/usr/bin/env python3
"""Manual resting HR entry.

Usage:
    python scripts/add_resting_hr.py --bpm 58
    python scripts/add_resting_hr.py --bpm 58 --date 2026-05-14
"""
import argparse
import sys
from datetime import date

sys.path.insert(0, "/app")

from db import get_session
from sqlalchemy import text


def main() -> None:
    parser = argparse.ArgumentParser(description="Record manual resting HR")
    parser.add_argument("--bpm", type=int, required=True, help="Resting heart rate in BPM")
    parser.add_argument("--date", default=str(date.today()), help="Date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    if args.bpm < 30 or args.bpm > 120:
        print(f"BPM {args.bpm} out of range (30–120). Aborting.")
        sys.exit(1)

    session = get_session()
    try:
        session.execute(
            text("""
                INSERT INTO resting_hr_daily (date, resting_hr_bpm, source)
                VALUES (:date, :bpm, 'manual')
                ON CONFLICT (date) DO UPDATE
                    SET resting_hr_bpm = EXCLUDED.resting_hr_bpm,
                        source = 'manual'
            """),
            {"date": args.date, "bpm": args.bpm},
        )
        session.commit()
        print(f"Saved: {args.date} → {args.bpm} bpm (manual)")
    finally:
        session.close()


if __name__ == "__main__":
    main()
