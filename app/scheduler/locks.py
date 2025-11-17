# app/scheduler/locks.py — финальная версия фрагментов

import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam, BigInteger


def time_bucket(ts: datetime, seconds: int) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    epoch = int(ts.timestamp())
    bucket_start = epoch - (epoch % max(1, seconds))
    return datetime.fromtimestamp(bucket_start, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")


def advisory_lock_key(bucket: str) -> int:
    # ключ в диапазоне BIGINT (signed), чтобы Postgres не делал NUMERIC
    h = hashlib.sha1(bucket.encode("utf-8")).digest()
    return int.from_bytes(h[:8], byteorder="big", signed=True)


def acquire_lock(session: Session, key: int) -> bool:
    # биндим параметр с типом BIGINT (без ::bigint и без CAST)
    stmt = (
        text("SELECT pg_try_advisory_lock(:k)")
        .bindparams(bindparam("k", type_=BigInteger))
    )
    return bool(session.execute(stmt, {"k": key}).scalar())


def release_lock(session: Session, key: int) -> None:
    stmt = (
        text("SELECT pg_advisory_unlock(:k)")
        .bindparams(bindparam("k", type_=BigInteger))
    )
    session.execute(stmt, {"k": key})
