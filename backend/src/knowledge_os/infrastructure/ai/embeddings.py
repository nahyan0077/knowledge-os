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
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

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
