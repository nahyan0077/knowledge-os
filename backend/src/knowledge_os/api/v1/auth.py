from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from knowledge_os.api.dependencies import get_auth_service
from knowledge_os.api.schemas import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    OrganizationResponse,
    RegisterRequest,
    UserResponse,
)
from knowledge_os.application.auth import AuthResult, AuthService
from knowledge_os.config import get_settings
from knowledge_os.domain.common import AuthenticationError

router = APIRouter(prefix="/auth", tags=["authentication"])
REFRESH_COOKIE = "knowledge_os_refresh"


def _response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        access_token=result.access_token.value,
        expires_in=result.access_token.expires_in_seconds,
        user=UserResponse.from_domain(result.user),
        organization=(
            OrganizationResponse.from_domain(result.organization) if result.organization else None
        ),
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 86400,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    result = await service.register(payload.email, payload.display_name, payload.password)
    _set_refresh_cookie(response, result.refresh_token)
    return _response(result)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    result = await service.login(payload.email, payload.password)
    _set_refresh_cookie(response, result.refresh_token)
    return _response(result)


@router.post("/google", response_model=AuthResponse)
async def google_login(
    payload: GoogleLoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    result = await service.login_with_google(payload.id_token)
    _set_refresh_cookie(response, result.refresh_token)
    return _response(result)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> AuthResponse:
    if refresh_token is None:
        raise AuthenticationError("Refresh token required", "refresh_token_required")
    result = await service.refresh(refresh_token)
    _set_refresh_cookie(response, result.refresh_token)
    return _response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> None:
    if refresh_token:
        await service.logout(refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
