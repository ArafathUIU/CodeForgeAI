"""FastAPI application factory for the CodeForge backend API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codeforge.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="CodeForge API",
        description="Backend API for the CodeForge multi-agent system",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
