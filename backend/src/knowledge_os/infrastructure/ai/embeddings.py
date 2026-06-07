import httpx
from openai import AsyncOpenAI

from knowledge_os.application.ports import EmbeddingProvider
from knowledge_os.config import Settings


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        settings: Settings,
        model_name: str = "text-embedding-3-small",
        embedding_version: int = 1,
    ) -> None:
        self._model_name = model_name
        self._embedding_version = embedding_version
        self._api_key = settings.openai_api_key
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._model_name == "text-embedding-3-small":
            return 1536
        elif self._model_name == "text-embedding-3-large":
            return 3072
        elif self._model_name == "text-davinci-002":
            return 1536
        return 1536

    @property
    def embedding_version(self) -> int:
        return self._embedding_version

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                model=self._model_name,
                input=texts,
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            raise e


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        settings: Settings,
        model_name: str = "gemini-embedding-001",
        embedding_version: int = 1,
    ) -> None:
        self._model_name = model_name
        self._embedding_version = embedding_version
        self._api_key = settings.gemini_api_key

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._model_name == "text-embedding-004":
            return 768
        return 768

    @property
    def embedding_version(self) -> int:
        return self._embedding_version

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Use HTTP REST API for google gemini embeddings to avoid SDK lock-in
        # and keep it async-native.
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model_name}:batchEmbedContents?key={self._api_key}"
        )

        requests_payload = []
        for text in texts:
            requests_payload.append(
                {
                    "model": f"models/{self._model_name}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": self.dimension,
                }
            )

        payload = {"requests": requests_payload}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        embeddings = []
        for res in data.get("embeddings", []):
            embeddings.append(res.get("values", []))

        return embeddings


class EmbeddingProviderFactory:
    @staticmethod
    def get_provider(settings: Settings, provider: str | None = None) -> EmbeddingProvider:
        p = (provider or settings.embedding_provider).lower()
        if p == "openai":
            return OpenAIEmbeddingProvider(settings)
        elif p in {"gemini", "google"}:
            return GeminiEmbeddingProvider(settings)
        else:
            raise ValueError(f"Unsupported embedding provider: {p}")
