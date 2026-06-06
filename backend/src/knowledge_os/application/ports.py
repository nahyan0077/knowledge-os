from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class PasswordService(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, password_hash: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    value: str
    expires_in_seconds: int


class AccessTokenService(Protocol):
    def issue(self, user_id: UUID, session_id: UUID) -> IssuedAccessToken: ...
    def decode(self, token: str) -> tuple[UUID, UUID]: ...


class RefreshTokenService(Protocol):
    def issue(self, session_id: UUID) -> tuple[str, str]: ...
    def parse(self, token: str) -> tuple[UUID, str]: ...
    def matches(self, secret: str, token_hash: str) -> bool: ...
