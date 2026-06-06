import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from knowledge_os.application.ports import (
    AccessTokenService,
    IssuedAccessToken,
    PasswordService,
    RefreshTokenService,
)
from knowledge_os.domain.common import AuthenticationError, ConflictError, ValidationError
from knowledge_os.domain.entities import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    OrganizationType,
    RefreshSession,
    User,
    UserStatus,
    utc_now,
)
from knowledge_os.domain.repositories import UnitOfWork

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    organization: Organization | None
    access_token: IssuedAccessToken
    refresh_token: str


class AuthService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        passwords: PasswordService,
        access_tokens: AccessTokenService,
        refresh_tokens: RefreshTokenService,
        refresh_ttl_days: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._passwords = passwords
        self._access_tokens = access_tokens
        self._refresh_tokens = refresh_tokens
        self._refresh_ttl = timedelta(days=refresh_ttl_days)

    async def register(self, email: str, display_name: str, password: str) -> AuthResult:
        normalized_email = self._normalize_email(email)
        clean_name = display_name.strip()
        self._validate_password(password)
        if not clean_name:
            raise ValidationError("Display name is required", "display_name_required")

        async with self._uow_factory() as uow:
            if await uow.users.get_by_email(normalized_email):
                raise ConflictError("An account with this email already exists", "email_exists")

            user = User(
                email=normalized_email,
                display_name=clean_name,
                password_hash=await self._passwords.hash(password),
            )
            organization = Organization(
                name=f"{clean_name}'s Workspace",
                slug=f"personal-{user.id.hex}",
                type=OrganizationType.PERSONAL,
            )
            await uow.users.add(user)
            await uow.organizations.add(organization)
            await uow.organizations.add_membership(
                OrganizationMembership(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=MembershipRole.OWNER,
                )
            )
            result = await self._create_session(uow, user, organization)
            await uow.commit()
            return result

    async def login(self, email: str, password: str) -> AuthResult:
        normalized_email = self._normalize_email(email)
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_email(normalized_email)
            if (
                user is None
                or user.status is not UserStatus.ACTIVE
                or not await self._passwords.verify(password, user.password_hash)
            ):
                raise AuthenticationError("Invalid email or password", "invalid_credentials")
            user.last_login_at = utc_now()
            user.updated_at = utc_now()
            await uow.users.save(user)
            organizations = await uow.organizations.list_for_user(user.id)
            result = await self._create_session(
                uow,
                user,
                organizations[0] if organizations else None,
            )
            await uow.commit()
            return result

    async def refresh(self, raw_refresh_token: str) -> AuthResult:
        try:
            session_id, secret = self._refresh_tokens.parse(raw_refresh_token)
        except ValueError as exc:
            raise AuthenticationError("Invalid refresh token", "invalid_refresh_token") from exc

        async with self._uow_factory() as uow:
            current = await uow.refresh_sessions.get_by_id(session_id)
            if current is None or not self._refresh_tokens.matches(secret, current.token_hash):
                raise AuthenticationError("Invalid refresh token", "invalid_refresh_token")
            if current.revoked_at is not None:
                await uow.refresh_sessions.revoke_family(current.family_id)
                await uow.commit()
                raise AuthenticationError("Refresh token reuse detected", "refresh_token_reuse")
            if not current.is_active:
                raise AuthenticationError("Refresh token expired", "refresh_token_expired")

            user = await uow.users.get_by_id(current.user_id)
            if user is None or user.status is not UserStatus.ACTIVE:
                raise AuthenticationError("Session is no longer valid", "invalid_session")

            raw_token, token_hash = self._refresh_tokens.issue(uuid4())
            replacement_id, _ = self._refresh_tokens.parse(raw_token)
            replacement = RefreshSession(
                id=replacement_id,
                user_id=user.id,
                family_id=current.family_id,
                token_hash=token_hash,
                expires_at=utc_now() + self._refresh_ttl,
            )
            current.revoked_at = utc_now()
            current.replaced_by_session_id = replacement.id
            await uow.refresh_sessions.save(current)
            await uow.refresh_sessions.add(replacement)
            organizations = await uow.organizations.list_for_user(user.id)
            await uow.commit()
            return AuthResult(
                user=user,
                organization=organizations[0] if organizations else None,
                access_token=self._access_tokens.issue(user.id, replacement.id),
                refresh_token=raw_token,
            )

    async def logout(self, raw_refresh_token: str) -> None:
        try:
            session_id, secret = self._refresh_tokens.parse(raw_refresh_token)
        except ValueError:
            return
        async with self._uow_factory() as uow:
            session = await uow.refresh_sessions.get_by_id(session_id)
            if session and self._refresh_tokens.matches(secret, session.token_hash):
                session.revoked_at = utc_now()
                await uow.refresh_sessions.save(session)
                await uow.commit()

    async def _create_session(
        self,
        uow: UnitOfWork,
        user: User,
        organization: Organization | None,
    ) -> AuthResult:
        session_id = uuid4()
        raw_token, token_hash = self._refresh_tokens.issue(session_id)
        session = RefreshSession(
            id=session_id,
            user_id=user.id,
            token_hash=token_hash,
            family_id=uuid4(),
            expires_at=utc_now() + self._refresh_ttl,
        )
        await uow.refresh_sessions.add(session)
        return AuthResult(
            user=user,
            organization=organization,
            access_token=self._access_tokens.issue(user.id, session.id),
            refresh_token=raw_token,
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().casefold()
        if not _EMAIL_RE.match(normalized):
            raise ValidationError("A valid email is required", "invalid_email")
        return normalized

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 12:
            raise ValidationError("Password must be at least 12 characters", "weak_password")
        if len(password) > 256:
            raise ValidationError("Password is too long", "invalid_password")
