from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.domain.errors import (
    ApplicationError,
    NotFound,
    Conflict,
    InvalidOperation,
    RelatedEntityError,
    StorageError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, error: ApplicationError):
        codes = {
            NotFound: 404,
            Conflict: 409,
            InvalidOperation: 400,
            RelatedEntityError: 422,
            StorageError: 500,
        }
        return JSONResponse(
            status_code=codes.get(type(error), 500), content={"detail": str(error)}
        )
