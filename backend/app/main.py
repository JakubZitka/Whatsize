from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.recommendations import router as recommendations_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="WhatSize API",
        version="0.1.0",
        docs_url="/docs",
    )
    app.include_router(health_router)
    app.include_router(recommendations_router, prefix="/v1")
    return app


app = create_app()
