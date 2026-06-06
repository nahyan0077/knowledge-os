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

## Technical Debt & Risks
- **Blob Storage Cleanup**: Soft-deleting a document currently retains files in Azure Blob Storage. Hard delete logic or automated cleanup workflows are planned for later phases.
- **Docker Dependency**: Integration tests require Docker daemon to run.

## Next Steps
- Implement Sprint 4 (Retrieval & Grounding).
