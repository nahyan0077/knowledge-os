# Current State

## Implementation Progress

### Sprint 1 & 1.1 (Identity & Tenancy) - Completed
- **Authentication**: JWT access tokens, opaque refresh tokens with rotation and reuse detection.
- **Tenancy**: Multi-tenant database boundary using `organization_id`.
- **Projects**: Project creation, listing, retrieval, update, and soft deletion.
- **Testing**: FastAPI router tests, service unit tests.

### Sprint 2 (Document Lifecycle Management) - Completed
- **Domain Entities**: `Document` and `DocumentVersion` entities.
- **API Endpoints**:
  - `POST /api/v1/projects/{project_id}/documents` (Create document and upload first version)
  - `POST /api/v1/projects/{project_id}/documents/{document_id}/versions` (Upload new version)
  - `GET /api/v1/projects/{project_id}/documents` (List documents)
  - `GET /api/v1/documents/{document_id}` (Get document)
  - `DELETE /api/v1/documents/{document_id}` (Soft delete document)
- **Storage Adapter**: `AzureBlobStorageAdapter` supporting uploading, downloading, and deleting files. Features a local directory fallback (`backend/local_storage`) when connection strings are not configured, facilitating offline test execution.
- **Database Schema**: PostgreSQL tables (`documents`, `document_versions`) mapped using SQLAlchemy 2.0. Alembic migration `9944056df44e` created.
- **Integration Tests**: Implemented using `testcontainers` and real PostgreSQL to validate database constraints, composite keys, and enum serialization.

### Sprint 3 (Conversations & Message Lifecycle) - Completed
- **Domain Entities**: `Conversation` and `Message` entities, with enums for `MessageRole` (`user`, `assistant`, `system`).
- **API Endpoints**:
  - `POST /api/v1/projects/{project_id}/conversations` (Create conversation)
  - `GET /api/v1/projects/{project_id}/conversations` (List conversations by project)
  - `GET /api/v1/conversations/{conversation_id}` (Get conversation)
  - `PATCH /api/v1/conversations/{conversation_id}` (Rename conversation)
  - `DELETE /api/v1/conversations/{conversation_id}` (Soft delete conversation)
  - `POST /api/v1/conversations/{conversation_id}/messages` (Add message)
  - `GET /api/v1/conversations/{conversation_id}/messages` (List messages)
- **Database Schema**: PostgreSQL tables (`conversations`, `messages`) mapped using SQLAlchemy 2.0. Resolves the column name clashing with the built-in SQLAlchemy `metadata` property by mapping python property `meta` to DB column `metadata`. Alembic migration `101a38a57c63` created.
- **Quality Gates**: Ruff linting/formatting and strict `mypy` typechecking passing. 34 unit/integration tests passing.
- **Integration Tests**: Implemented using `testcontainers` and real PostgreSQL to validate message insertion, sorting order, constraints, and roles enum.
### Sprint 4 (AI Chat Infrastructure using PydanticAI) - Completed
- **Domain Entities**: `LlmUsage` entity and `LlmUsageRepository`.
- **API Endpoints**:
  - `POST /api/v1/conversations/{conversation_id}/chat` (Send message and get assistant response)
  - `POST /api/v1/conversations/{conversation_id}/chat/stream` (Send message and stream assistant response via Server-Sent Events (SSE))
- **AI Adapter & Pricing Engine**: 
  - `PydanticAiAdapter` implementing `ChatAgentPort` handling model provider abstraction (OpenAI, Gemini, Anthropic, TestModel), temperature settings configuration, and delegating cost calculation to an injected `PricingService`.
  - Config-backed `ConfigPricingService` implementation loading token rates from application settings.
- **Partial Stream Persistence**: Added `MessageStatus` (`STREAMING`, `COMPLETE`, `INTERRUPTED`, `FAILED`) to track message lifecycle. Used `asyncio.shield` to persist partial response strings and token usage under client disconnects (`CancelledError`) and failures, ensuring auditability and no data rollbacks.
- **Canonical Message Ordering**: Implemented auto-incrementing `sequence_number` per conversation as the canonical ordering mechanism. Added constraint `uq_conversation_message_sequence` and safely backfilled existing database messages using a Postgres window function.
- **SSE Payload Standardization**: Wrapped raw text chunks in JSON format (`{"content": "..."}`) for frontend parsing safety.
- **Integration Tests**: Extended testcontainers PostgreSQL coverage to verify sequence calculation, constraints, and status persistence. Added unit tests in `test_conversation_service.py` to cover stream disconnections and provider failures.
- **Quality Gates**: All Ruff styling, strict mypy type safety, and 40 pytest tests passing successfully.

### Sprint 4.5 (Production-Grade Frontend Foundation) - Completed
- **Authentication**: Fully functional Login/Register UI matching JWT bearer authorization, secure cookie-based automatic token refreshing, protected route checking, and local state persistence.
- **Project Dashboard**: Dynamic list of all projects within the tenant, modal for project initialization, and routing layouts.
- **Collapsible Sidebar Layout**: Collapse-ready project navigation sidebar linking to Documents, Chats, and Settings with active path matching.
- **Document Explorer**: Drag-and-drop document dropzone, logical document tables with delete triggers, slide-out document history drawer displaying version entries, and version additions.
- **Conversation Explorer**: Sidebar containing conversation list with active message state bindings, renaming forms, creation triggers, and soft-deletes.
- **Chat Workspace**: Conversation thread containing user prompts and agent responses. Supports:
  - Real-time POST Server-Sent Events (SSE) streaming parsed via browser fetch reader.
  - Active message status indicators (`STREAMING` with animations, `COMPLETE`, `INTERRUPTED`, and `FAILED` with retry actions).
  - Provider model config selector (OpenAI, Gemini, Anthropic, TestModel) and temperature parameters.
  - Dynamic scroll-to-bottom locks and generation cancellation (aborts stream via AbortController).
- **Project Settings**: General settings panel supporting project title/description updates and complete project workspace deletion.
- **Quality Gates**: Production Turbopack compilation passing with zero TypeScript or ESLint errors.

### Sprint 5 (Temporal Workflow Infrastructure) - Completed
- **Temporal Setup**: Integrated Temporal client/worker daemon, configured workflow and activity registrations, and set task queues.
- **Workflow Orchestration**: Implemented `DocumentProcessingWorkflow` executing activities `validate_document`, `extract_document_metadata`, and `update_document_status`.
- **Automatic Triggering**: Document upload/version creation triggers the workflow asynchronously.
- **Database Schema**: Created `workflow_runs` and `workflow_events` tables for state tracking, with repository implementations and Alembic migration `35bf1154174d`.
- **API Endpoints**:
  - `GET /api/v1/workflows/{run_id}` (Query run progress and events)
  - `GET /api/v1/projects/{project_id}/workflows` (List runs by resource type/ID)
- **Unit and Integration Tests**: Implemented time-skipping Temporal unit tests and FastAPI route tests; all 45 checks pass.

### Sprint 6 & 6.1 (Document Ingestion Hardening, Text Extraction, and Chunk Metadata) - Completed
- **Domain Entities**: Defined `DocumentChunk` and `DocumentChunkRepository` protocol with async CRUD operations. Enhanced `DocumentVersion` and `DocumentChunk` to support metrics (`extracted_characters`, `page_count`, and `char_count`).
- **PDF Extraction Layer**: Replaced mock parsing with `pypdf` page-by-page text extraction. Implemented graceful handling of empty pages and robust recovery from malformed PDFs via `PdfTextExtractor`.
- **Token Counting**: Implemented model-aware `TokenCounter` utilizing `tiktoken` with default model configuration (`text-embedding-3-small`), replacing word-count approximations.
- **Ingestion Metrics & Database Schema**: Added `extracted_characters` and `page_count` columns to `document_versions`, and `char_count` to `document_chunks`. Generated and applied Alembic migration `274853379664`.
- **Temporal Activities & Queues**:
  - Refactored `extract_document_text` (on `document-processing` queue) to compute character/page metadata, save them in the database, and store intermediate plain text files (`extracted_text/{version_id}.txt`) in Blob Storage.
  - Refactored `chunk_document` (on dedicated `chunk-processing` queue) to construct chunks with exact character count and token count values and commit them idempotently.
- **Testing**: Added unit tests for PDF extraction, empty/malformed PDF handling, and tiktoken counting. Added integration assertions for chunk metadata persistence in database repositories and workflow execution. All 54 checks passing.

### Sprint 7 (Embeddings & Vector Index Infrastructure) - Completed
- **Domain Entities**: Defined `ChunkEmbedding` entity tracking provider, model, dimension, version, and vector point associations, along with its async CRUD repository.
- **Database Schema**: Created `chunk_embeddings` table with indexing on `organization_id`, `document_chunk_id`, and `embedding_version`, and unique constraint `(document_chunk_id, embedding_version)`. Applied Alembic migration `2f32957df35e`.
- **OpenAI Embedding Provider**: Implemented `OpenAIEmbeddingProvider` protocol wrapper supporting batch embedding generation via OpenAI's embeddings API, defaulting to `text-embedding-3-small` (1536 dimensions, version 1).
- **Qdrant Vector Store**: Implemented `QdrantVectorStore` (conforming to `VectorStorePort`) utilizing `Distance.COSINE` and indexing layout preserving multi-tenant properties (`organization_id`, `project_id`, `document_version_id`).
- **Temporal Ingestion Workflow**: Integrated `generate_chunk_embeddings` activity running on the `embedding-processing` queue. The workflow lifecycle is `Validate -> Extract -> Chunk -> Embed -> Index`, with idempotency safety via version purges before upserts.
- **Tests**: Implemented unit tests for provider and adapter mocks, integration repository assertions, and E2E workflow integration testing. All quality gates pass.

### Sprint 8 (Retrieval Infrastructure) - Completed
- **Retrieval Service**: Built `RetrievalService` coordinating query embedding generation, tenant-isolated vector search, and authoritative PostgreSQL chunk hydration.
- **Qdrant Search**: Implemented `search_chunks` on `QdrantVectorStore` enforcing tenant payload filters (`organization_id`, `project_id`) during queries.
- **PostgreSQL Hydration**: Implemented `list_by_ids` on `DocumentChunkRepository` to retrieve authoritative, transactionally consistent chunk text from the database (separating storage concerns from Qdrant payloads).
- **FastAPI API Route**: Exposed the query contract via `POST /api/v1/retrieval/search` which maps search inputs (query, project_id, top_k) to domain search results.
- **Quality Gates**: Verified end-to-end functionality via unit tests (query embedding, hydration logic) and integration tests (Qdrant search, PostgreSQL hydration, tenant isolation checks). 61 total tests passing.

### Sprint 9 (Context Builder, Citation Engine, and RAG Generation) - Completed
- **Domain Entities**: Defined `Citation` domain model (chunk_id, document_version_id, chunk_number, score).
- **Context Builder**: Implemented `ContextBuilder` executing sorting, deduplication, token budget limits, and context generation.
- **RAG Service**: Implemented `RagService` orchestrating question, retrieval, context builder, and PydanticAI answer generation.
- **API Endpoint**: Exposed `POST /api/v1/rag/ask` requesting `project_id` and `question`, and returning `answer` and `citations`.
- **Chat Integration**: Updated chat workflow in `ConversationService` (`send_message` and `send_message_stream`) to fetch context and persist citations in `Message` metadata.
- **Tests**: Implemented unit tests (ContextBuilder, RagService) and integration tests (RAG E2E, router routes, and tenant boundary verification). 68 total tests passing.

## Technical Debt & Risks
- **Blob Storage Cleanup**: Soft-deleting a document currently retains files in Azure Blob Storage. Hard delete logic or automated cleanup workflows are planned for later phases.
- **Docker Dependency**: Integration tests require Docker daemon to run.

## Next Steps
- Implement Agent Runs & Auditing (Sprint 10).
