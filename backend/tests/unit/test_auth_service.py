from typing import Any

import pytest

from knowledge_os.application.auth import AuthService
from knowledge_os.domain.common import AuthenticationError, ConflictError
from knowledge_os.domain.entities import MembershipRole, OrganizationType
from tests.unit.fakes import (
    FakeAccessTokenService,
    FakePasswordService,
    FakeRefreshTokenService,
    FakeUnitOfWork,
    Store,
)


class FakeGoogleTokenVerifier:
    def __init__(self, data: dict[str, str]) -> None:
        self.data = data

    async def verify_id_token(self, id_token: str) -> dict[str, Any]:
        if id_token == "valid-token":
            return self.data
        from knowledge_os.domain.common import AuthenticationError

        raise AuthenticationError("Invalid token", "invalid_token")


def make_service(store: Store, identity_provider: Any = None) -> AuthService:
    return AuthService(
        lambda: FakeUnitOfWork(store),
        FakePasswordService(),
        FakeAccessTokenService(),
        FakeRefreshTokenService(),
        refresh_ttl_days=30,
        identity_provider=identity_provider,
    )


@pytest.mark.asyncio
async def test_register_normalizes_email_and_creates_personal_workspace() -> None:
    store = Store()
    result = await make_service(store).register(
        "  PERSON@Example.COM ",
        "Person",
        "correct-horse-battery",
    )

    assert result.user.email == "person@example.com"
    assert result.organization is not None
    assert result.organization.type is OrganizationType.PERSONAL
    membership = store.organization_memberships[0]
    assert membership.user_id == result.user.id
    assert membership.role is MembershipRole.OWNER
    assert len(store.sessions) == 1


@pytest.mark.asyncio
async def test_register_rejects_duplicate_normalized_email() -> None:
    store = Store()
    service = make_service(store)
    await service.register("person@example.com", "Person", "correct-horse-battery")

    with pytest.raises(ConflictError) as error:
        await service.register("PERSON@example.com", "Other", "correct-horse-battery")

    assert error.value.code == "email_exists"


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_reuse_revokes_family() -> None:
    store = Store()
    service = make_service(store)
    registered = await service.register("person@example.com", "Person", "correct-horse-battery")

    refreshed = await service.refresh(registered.refresh_token)
    assert refreshed.refresh_token != registered.refresh_token

    with pytest.raises(AuthenticationError) as error:
        await service.refresh(registered.refresh_token)

    assert error.value.code == "refresh_token_reuse"
    assert all(session.revoked_at is not None for session in store.sessions.values())


@pytest.mark.asyncio
async def test_login_rejects_wrong_password() -> None:
    store = Store()
    service = make_service(store)
    await service.register("person@example.com", "Person", "correct-horse-battery")

    with pytest.raises(AuthenticationError) as error:
        await service.login("person@example.com", "wrong")

    assert error.value.code == "invalid_credentials"


@pytest.mark.asyncio
async def test_google_login_registers_new_user() -> None:
    store = Store()
    verifier = FakeGoogleTokenVerifier({"email": "google-user@example.com", "name": "Google User"})
    service = make_service(store, verifier)

    result = await service.login_with_google("valid-token")

    assert result.user.email == "google-user@example.com"
    assert result.user.display_name == "Google User"
    assert result.organization is not None
    assert result.organization.type is OrganizationType.PERSONAL
    assert len(store.sessions) == 1


@pytest.mark.asyncio
async def test_google_login_signs_in_existing_user() -> None:
    store = Store()
    verifier = FakeGoogleTokenVerifier(
        {"email": "existing-user@example.com", "name": "Existing User"}
    )
    service = make_service(store, verifier)

    # Register first via standard sign-up
    await service.register("existing-user@example.com", "Existing User", "correct-horse-battery")
    assert len(store.users) == 1

    # Login via Google
    result = await service.login_with_google("valid-token")

    assert result.user.email == "existing-user@example.com"
    assert len(store.users) == 1  # No duplicate user created
    assert len(store.sessions) == 2  # Standard signup session + Google login session


@pytest.mark.asyncio
async def test_google_login_rejects_invalid_token() -> None:
    store = Store()
    verifier = FakeGoogleTokenVerifier({"email": "user@example.com", "name": "User"})
    service = make_service(store, verifier)

    with pytest.raises(AuthenticationError) as error:
        await service.login_with_google("invalid-token")

    assert error.value.code == "invalid_token"
