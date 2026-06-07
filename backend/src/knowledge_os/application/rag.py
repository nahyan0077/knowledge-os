from uuid import UUID

from knowledge_os.application.context_builder import ContextBuilder
from knowledge_os.application.ports import ChatAgentPort, LlmModelConfig
from knowledge_os.application.retrieval import RetrievalService
from knowledge_os.domain.entities import Citation


class RagService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        context_builder: ContextBuilder,
        chat_agent: ChatAgentPort,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._context_builder = context_builder
        self._chat_agent = chat_agent

    async def ask(
        self,
        project_id: UUID,
        user_id: UUID,
        question: str,
        token_budget: int | None = None,
    ) -> tuple[str, list[Citation]]:
        # 1. Retrieve candidates
        retrieved_chunks = await self._retrieval_service.search(
            project_id=project_id,
            user_id=user_id,
            query=question,
            top_k=20,
        )

        # 2. Build context and citations list
        context_text, citations = self._context_builder.build_context(
            retrieved_chunks=retrieved_chunks,
            token_budget=token_budget,
        )

        # 3. Build system prompt holding the retrieved context
        system_prompt = (
            "You are a helpful assistant. You must answer the user's question "
            "using only the provided source context.\n"
            "If the context does not contain the information needed to answer "
            "the question, state that you do not know.\n\n"
            f"Context:\n{context_text}"
        )

        # 4. Invoke LLM generation
        config = LlmModelConfig(
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.0,
        )
        response = await self._chat_agent.generate(
            system_prompt=system_prompt,
            messages=[("user", question)],
            config=config,
        )

        return response.content, citations
