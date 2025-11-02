from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


def ten_minute_bucket(ts: datetime) -> str:
    minute = (ts.minute // 10) * 10
    bucket = ts.replace(minute=minute, second=0, microsecond=0)
    return bucket.strftime("%Y-%m-%dT%H:%M")

def advisory_lock_key(bucket: str) -> int:
    return (hash(bucket) & 0x7FFF_FFFF_FFFF_FFFF)

def acquire_lock(session: Session, key: int) -> bool:
    return bool(session.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar())

def release_lock(session: Session, key: int) -> None:
    session.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
