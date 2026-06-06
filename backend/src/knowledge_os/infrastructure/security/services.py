import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from knowledge_os.application.ports import IssuedAccessToken
from knowledge_os.config import Settings


class Argon2PasswordService:
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._password_hash.verify(password, password_hash)


class JwtAccessTokenService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._ttl = timedelta(minutes=settings.access_token_ttl_minutes)

    def issue(self, user_id: UUID, session_id: UUID) -> IssuedAccessToken:
        now = datetime.now(UTC)
        expires_at = now + self._ttl
        value = jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "type": "access",
                "iat": now,
                "exp": expires_at,
            },
            self._secret,
            algorithm=self._algorithm,
        )
        return IssuedAccessToken(value=value, expires_in_seconds=int(self._ttl.total_seconds()))

    def decode(self, token: str) -> tuple[UUID, UUID]:
        payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Unexpected token type")
        return UUID(payload["sub"]), UUID(payload["sid"])


class OpaqueRefreshTokenService:
    def issue(self, session_id: UUID) -> tuple[str, str]:
        secret = secrets.token_urlsafe(48)
        return f"{session_id}.{secret}", self._hash(secret)

    def parse(self, token: str) -> tuple[UUID, str]:
        session_id, secret = token.split(".", maxsplit=1)
        if not secret:
            raise ValueError("Missing refresh secret")
        return UUID(session_id), secret

    def matches(self, secret: str, token_hash: str) -> bool:
        return hmac.compare_digest(self._hash(secret), token_hash)

    @staticmethod
    def _hash(secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()
