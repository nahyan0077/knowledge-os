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
- **Quality Gates**: Ruff linting/formatting and strict `mypy` typechecking passing. 21 unit/integration tests passing.
- **Integration Tests**: Implemented using `testcontainers` and real PostgreSQL to validate database constraints, composite keys, and enum serialization.

## Technical Debt & Risks
- **Blob Storage Cleanup**: Soft-deleting a document currently retains files in Azure Blob Storage. Hard delete logic or automated cleanup workflows are planned for later phases.
- **Docker Dependency**: Integration tests require Docker daemon to run.

## Next Steps
- Implement Sprint 3 (Conversations & Chat) or Sprint 4 (Retrieval & Grounding).
