from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol
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
    @property
    def provider_name(self) -> str:
        """Returns the identifier of this storage provider."""
        ...

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


class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    @property
    def embedding_version(self) -> int: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class VectorStorePort(Protocol):
    async def create_collection(self, collection_name: str, dimension: int) -> None: ...

    async def upsert_chunks(
        self,
        collection_name: str,
        vectors: list[list[float]],
        chunk_ids: list[UUID],
        organization_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
    ) -> None: ...

    async def delete_chunks_by_version(
        self,
        collection_name: str,
        document_version_id: UUID,
    ) -> None: ...

    async def fetch_chunk_metadata(
        self,
        collection_name: str,
        chunk_id: UUID,
    ) -> dict[str, Any] | None: ...

    async def search_chunks(
        self,
        collection_name: str,
        organization_id: UUID,
        project_id: UUID,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[tuple[UUID, float]]: ...
