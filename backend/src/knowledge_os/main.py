from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from knowledge_os.api.middleware import RateLimitMiddleware
from knowledge_os.api.v1.auth import router as auth_router
from knowledge_os.api.v1.config import router as config_router
from knowledge_os.api.v1.conversations import router as conversations_router
from knowledge_os.api.v1.documents import router as documents_router
from knowledge_os.api.v1.projects import router as projects_router
from knowledge_os.api.v1.rag import router as rag_router
from knowledge_os.api.v1.retrieval import router as retrieval_router
from knowledge_os.api.v1.workflows import router as workflows_router
from knowledge_os.config import get_settings
from knowledge_os.domain.common import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from knowledge_os.infrastructure.verification import verify_infrastructure_services


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await verify_infrastructure_services(settings)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        auth_limit=settings.rate_limit_auth,
        api_limit=settings.rate_limit_api,
        chat_limit=settings.rate_limit_chat,
    )

    if "*" in settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(config_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(retrieval_router, prefix="/api/v1")
    app.include_router(rag_router, prefix="/api/v1")
    app.include_router(workflows_router, prefix="/api/v1")

    @app.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        status_code = {
            AuthenticationError: 401,
            AuthorizationError: 403,
            ConflictError: 409,
            NotFoundError: 404,
            ValidationError: 422,
        }.get(type(exc), 400)
        return JSONResponse(
            status_code=status_code,
            content={
                "type": f"https://knowledge-os.local/problems/{exc.code}",
                "title": exc.code.replace("_", " ").title(),
                "status": status_code,
                "detail": exc.message,
                "error_code": exc.code,
                "instance": str(request.url.path),
                "correlation_id": correlation_id,
            },
            headers={"X-Correlation-ID": correlation_id},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        return JSONResponse(
            status_code=500,
            content={
                "type": "https://knowledge-os.local/problems/internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred.",
                "error_code": "internal_error",
                "instance": str(request.url.path),
                "correlation_id": correlation_id,
            },
            headers={"X-Correlation-ID": correlation_id},
        )

    return app


app = create_app()
