from uuid import uuid4

from knowledge_os.application.context_builder import ContextBuilder
from knowledge_os.application.retrieval import ScoredChunk


def test_context_builder_basic() -> None:
    builder = ContextBuilder(default_token_budget=100)
    chunk_id_1 = uuid4()
    version_id_1 = uuid4()

    chunks = [
        ScoredChunk(
            chunk_id=chunk_id_1,
            score=0.9,
            content="Hello world from chunk 1",
            document_version_id=version_id_1,
            chunk_number=1,
            token_count=10,
        )
    ]

    context, citations = builder.build_context(chunks)

    assert "Hello world from chunk 1" in context
    assert f"Source [1] Document Version: {version_id_1} (Chunk: 1)" in context
    assert len(citations) == 1
    assert citations[0].chunk_id == chunk_id_1
    assert citations[0].document_version_id == version_id_1
    assert citations[0].chunk_number == 1
    assert citations[0].score == 0.9


def test_context_builder_deduplication() -> None:
    builder = ContextBuilder(default_token_budget=100)
    chunk_id = uuid4()
    version_id = uuid4()

    chunks = [
        ScoredChunk(
            chunk_id=chunk_id,
            score=0.9,
            content="Hello world",
            document_version_id=version_id,
            chunk_number=1,
            token_count=10,
        ),
        ScoredChunk(
            chunk_id=chunk_id,
            score=0.8,
            content="Hello world",
            document_version_id=version_id,
            chunk_number=1,
            token_count=10,
        ),
    ]

    context, citations = builder.build_context(chunks)

    # Check that there is only one chunk in context and citations
    assert context.count("Source [") == 1
    assert len(citations) == 1
    assert citations[0].score == 0.9  # Highest score kept


def test_context_builder_token_budget_enforcement() -> None:
    # Set a small budget
    builder = ContextBuilder(default_token_budget=30)

    chunk_1 = uuid4()
    chunk_2 = uuid4()
    chunk_3 = uuid4()

    chunks = [
        ScoredChunk(
            chunk_id=chunk_1,
            score=0.95,
            content="Chunk 1 content",
            document_version_id=uuid4(),
            chunk_number=1,
            token_count=20,
        ),
        ScoredChunk(
            chunk_id=chunk_2,
            score=0.85,
            content="Chunk 2 content",
            document_version_id=uuid4(),
            chunk_number=2,
            token_count=20,  # Exceeds the budget of 30 if added to 20
        ),
        ScoredChunk(
            chunk_id=chunk_3,
            score=0.75,
            content="Chunk 3 content",
            document_version_id=uuid4(),
            chunk_number=3,
            token_count=10,  # Fits within the budget of 30 (20 + 10 = 30)
        ),
    ]

    context, citations = builder.build_context(chunks)

    assert "Chunk 1 content" in context
    assert "Chunk 2 content" not in context
    assert "Chunk 3 content" in context
    assert len(citations) == 2
    assert citations[0].chunk_id == chunk_1
    assert citations[1].chunk_id == chunk_3
