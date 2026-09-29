"""SQLAlchemy adapter for service-owned transactions."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.errors import (
    Conflict,
    InvalidOperation,
    RelatedEntityError,
    StorageError,
)


def translate_integrity_error(error: IntegrityError):
    original = error.orig
    code = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    if code == "23505":
        return Conflict("Запись с такими уникальными полями уже существует.")
    if code == "23503":
        return RelatedEntityError(
            "Связанная запись отсутствует или используется другими записями."
        )
    if code in {"23502", "23514"}:
        return InvalidOperation(
            "Данные нарушают ограничения обязательных полей или допустимых значений."
        )
    return StorageError("Не удалось сохранить данные.")


class SqlAlchemyTransaction:
    """Does not open a nested transaction: SQLAlchemy autobegin may already be active.

    Services call commit explicitly. Exceptions, cancellation and uncommitted
    operations roll back on exit. The request/provider owns session lifetime.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self

    async def commit(self) -> None:
        await self.session.commit()

    async def __aexit__(self, exc_type, exc, traceback):
        # After a successful commit this is a no-op. Also cleans up read-only exits.
        await self.session.rollback()
        if isinstance(exc, IntegrityError):
            raise translate_integrity_error(exc) from exc
        return False
