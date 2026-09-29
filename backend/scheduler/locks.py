import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


def ten_minute_bucket(ts: datetime) -> str:
    return ts.replace(minute=(ts.minute // 10) * 10, second=0, microsecond=0).strftime(
        "%Y-%m-%dT%H:%M"
    )


def advisory_lock_key(bucket: str) -> int:
    # Python hash() is randomized per process and cannot coordinate replicas.
    digest = hashlib.blake2b(bucket.encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") & 0x7FFF_FFFF_FFFF_FFFF


def acquire_lock(session: Session, key: int) -> bool:
    # Released by PostgreSQL on commit/rollback, including failed jobs.
    return bool(
        session.execute(
            text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": key}
        ).scalar()
    )
