from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from knowledge_os.api.v1.auth import router as auth_router
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


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

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
        status_code = {
            AuthenticationError: 401,
            AuthorizationError: 404,
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
            },
        )

    return app


app = create_app()
