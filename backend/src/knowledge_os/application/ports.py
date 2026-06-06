from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class PasswordService(Protocol):
    async def hash(self, password: str) -> str: ...
    async def verify(self, password: str, password_hash: str) -> bool: ...


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


class BlobStoragePort(Protocol):
    async def upload(self, blob_path: str, data: bytes, content_type: str) -> str:
        """Uploads file data and returns the etag string."""
        ...

    async def download(self, blob_path: str) -> bytes:
        """Downloads file data and returns binary data."""
        ...

    async def delete(self, blob_path: str) -> None:
        """Deletes file data from storage."""
        ...


@dataclass(frozen=True, slots=True)
class LlmModelConfig:
    provider: str
    model_name: str
    temperature: float | None = None


@dataclass(frozen=True, slots=True)
class LlmResponseChunk:
    content: str


@dataclass(frozen=True, slots=True)
class LlmUsageMetrics:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    cost: float


@dataclass(frozen=True, slots=True)
class LlmResponse:
    content: str
    usage: LlmUsageMetrics


class ChatAgentPort(Protocol):
    async def generate(
        self,
        system_prompt: str,
        messages: list[tuple[str, str]],  # List of (role, content)
        config: LlmModelConfig,
    ) -> LlmResponse: ...

    def generate_stream(
        self,
        system_prompt: str,
        messages: list[tuple[str, str]],
        config: LlmModelConfig,
    ) -> AsyncIterator[LlmResponseChunk | LlmUsageMetrics]: ...


class PricingService(Protocol):
    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float: ...
