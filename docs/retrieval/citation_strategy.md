# Citation Strategy

Grounded answers generated via Retrieval-Augmented Generation (RAG) require clear, audit-ready citation tracking. This document describes the citation model, lifecycle flow, and storage mechanism.

## Citation Model

The `Citation` entity is a domain value object representing a link between a generated answer and a source chunk.

* **chunk_id**: Unique identifier of the specific `DocumentChunk`.
* **document_version_id**: Unique identifier of the `DocumentVersion` containing the chunk.
* **chunk_number**: The index of the chunk in the document version.
* **score**: Similarity score returned by vector search.

## Citation Flow

```text
       Question
          ↓
  [Retrieval Service]
          ↓
  [Context Builder] (maps accepted chunks to Citation objects)
          ↓
  [PydanticAI Adapter] (generates answer grounded on context)
          ↓
  [Conversation Service] (persists Citations in Message metadata)
```

1. **Retrieval**: Vector store (Qdrant) returns scored chunks.
2. **Context Compilation**: The `ContextBuilder` formats the selected chunks under the budget and returns a list of matching `Citation` models.
3. **Synthesis**: The LLM synthesizes an answer referencing the structured context.
4. **Persistence**: The citations are serialized and persisted under the assistant message's `metadata` column in the database.

## Database Serialization Format

Citations are stored in the `messages` table under the JSONB `metadata` column:

```json
{
  "citations": [
    {
      "chunk_id": "046d1bf2-e92c-4735-a77a-42867807d9cb",
      "document_version_id": "1410d8ef-0d48-43d9-9524-a212384a8c9a",
      "chunk_number": 0,
      "score": 0.953
    }
  ]
}
```

This JSON layout preserves tenant boundaries, is highly queryable, and can be easily parsed by the frontend to render clickable source annotations.
