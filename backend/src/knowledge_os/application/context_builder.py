from uuid import UUID

from knowledge_os.application.retrieval import ScoredChunk
from knowledge_os.domain.entities import Citation


class ContextBuilder:
    def __init__(self, default_token_budget: int = 4000) -> None:
        self.default_token_budget = default_token_budget

    def build_context(
        self,
        retrieved_chunks: list[ScoredChunk],
        token_budget: int | None = None,
    ) -> tuple[str, list[Citation]]:
        budget = token_budget if token_budget is not None else self.default_token_budget

        selected_chunks: list[ScoredChunk] = []
        seen_chunk_ids: set[UUID] = set()
        accumulated_tokens = 0

        # Sort chunks descending by score to prioritize high similarity chunks
        sorted_chunks = sorted(retrieved_chunks, key=lambda x: x.score, reverse=True)

        for chunk in sorted_chunks:
            if chunk.chunk_id in seen_chunk_ids:
                continue

            # Check if adding this chunk would exceed the token budget
            if accumulated_tokens + chunk.token_count > budget:
                # If we have no selected chunks yet, we can add at least one if
                # we want to be lenient, but strict budget enforcement means
                # we break. Let's strictly enforce budget.
                continue

            seen_chunk_ids.add(chunk.chunk_id)
            selected_chunks.append(chunk)
            accumulated_tokens += chunk.token_count

        # Build context text and citations
        context_parts = []
        citations = []

        for citation_number, chunk in enumerate(selected_chunks, start=1):
            formatted_chunk = (
                f"Source [{citation_number}] Document Version: {chunk.document_version_id} "
                f"(Chunk: {chunk.chunk_number})\n"
                f"{chunk.content}\n"
                f"---\n"
            )
            context_parts.append(formatted_chunk)

            citations.append(
                Citation(
                    chunk_id=chunk.chunk_id,
                    document_version_id=chunk.document_version_id,
                    chunk_number=chunk.chunk_number,
                    score=chunk.score,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    quote=chunk.content[:500],
                    citation_number=citation_number,
                    document_id=chunk.document_id,
                    document_name=chunk.document_name,
                    source_filename=chunk.source_filename,
                )
            )

        context_text = "".join(context_parts).strip()
        return context_text, citations
