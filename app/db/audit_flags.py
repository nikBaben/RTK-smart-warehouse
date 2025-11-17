# app/db/audit_flags.py
from contextlib import contextmanager
from sqlalchemy import text
from sqlalchemy.orm import Session

@contextmanager
def disable_inventory_audit(session: Session, *, source: str | None = None, ref: str | None = None):
    # делаем локальные (до COMMIT/ROLLBACK) GUC через set_config(...)
    session.execute(text("SELECT set_config('app.inventory_audit', 'off', true)"))
    if source is not None:
        session.execute(text("SELECT set_config('app.audit_source', :src, true)"), {"src": source})
    if ref is not None:
        session.execute(text("SELECT set_config('app.audit_ref', :ref, true)"), {"ref": ref})
    try:
        yield
    finally:
        pass
