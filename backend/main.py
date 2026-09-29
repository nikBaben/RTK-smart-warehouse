import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.errors import register_error_handlers
from backend.api.v1 import api_router
from backend.api.routers import ws as ws_router
from backend.core.config import settings


def create_app(*, start_background: bool = True) -> FastAPI:
    """Tests can exercise real HTTP routes without starting Redis/streaming tasks."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not start_background:
            yield
            return
        from backend.events.bus import (
            get_bus_for_current_loop,
            close_bus_for_current_loop,
        )
        from backend.ws.redis_forwarder import start_redis_forwarder

        await get_bus_for_current_loop()
        forwarder = asyncio.create_task(start_redis_forwarder())
        try:
            yield
        finally:
            forwarder.cancel()
            with suppress(asyncio.CancelledError):
                await forwarder
            await close_bus_for_current_loop()

    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.include_router(ws_router.router, prefix="/api")
    return app


app = create_app()
