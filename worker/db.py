import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        url = os.environ["DATABASE_URL"]
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_session():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def get_sync_state(session, key: str) -> str | None:
    row = session.execute(
        text("SELECT value FROM sync_state WHERE key = :key"), {"key": key}
    ).fetchone()
    return row[0] if row else None


def set_sync_state(session, key: str, value: str) -> None:
    session.execute(
        text("""
            INSERT INTO sync_state (key, value, updated_at)
            VALUES (:key, :value, NOW())
            ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = NOW()
        """),
        {"key": key, "value": value},
    )
    session.commit()
