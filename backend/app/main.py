from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.recommendations import router as recommendations_router
from app.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="WhatSize API",
        version="0.1.0",
        docs_url="/docs",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(recommendations_router, prefix="/v1")
    return app


app = create_app()
