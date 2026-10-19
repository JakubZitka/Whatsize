import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.recommendations import router as recommendations_router
from app.config import get_settings

log = logging.getLogger("whatsize")


def load_reference_data(app: FastAPI) -> None:
    """Load the size graph into memory; fall back to the bundled seed if the DB is down."""
    from app.db import get_engine
    from app.seed import bundled_store, load_store, migrate_and_seed

    settings = get_settings()
    app.state.store, app.state.store_source, app.state.db_error = None, None, None
    try:
        engine = get_engine()
        if settings.auto_migrate:
            migrate_and_seed(engine)
        app.state.store = load_store(engine)
        app.state.store_source = "database"
    except Exception as exc:  # noqa: BLE001 — any DB failure must not take the API down
        log.exception("reference data could not be loaded from the database")
        app.state.db_error = f"{type(exc).__name__}: {str(exc)[:200]}"
        if settings.reference_fallback:
            app.state.store = bundled_store()
            app.state.store_source = "bundled"


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_reference_data(app)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="WhatSize API",
        version="0.2.0",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(catalog_router, prefix="/v1")
    app.include_router(recommendations_router, prefix="/v1")
    return app


app = create_app()
