from uuid import uuid4

import pytest

from knowledge_os.application.documents import DocumentService
from knowledge_os.domain.common import AuthorizationError, NotFoundError
from knowledge_os.domain.entities import (
    DocumentVersionStatus,
    MembershipRole,
    Organization,
    OrganizationMembership,
    OrganizationType,
    Project,
    ProjectMembership,
    User,
)
from tests.unit.fakes import (
    FakeUnitOfWork,
    Store,
)


class FakeBlobStorage:
    def __init__(self) -> None:
        self.files = {}

    async def upload(self, blob_path: str, data: bytes, content_type: str) -> str:
        self.files[blob_path] = data
        return f"etag-{len(data)}"

    async def download(self, blob_path: str) -> bytes:
        return self.files[blob_path]

    async def delete(self, blob_path: str) -> None:
        self.files.pop(blob_path, None)


def setup_store() -> tuple[Store, User, Organization, Project]:
    user = User("owner@example.com", "Owner", "hash")
    organization = Organization("Workspace", "workspace", OrganizationType.PERSONAL)
    project = Project(organization.id, "Research", user.id)
    store = Store(
        users={user.id: user},
        organizations={organization.id: organization},
        organization_memberships=[
            OrganizationMembership(organization.id, user.id, MembershipRole.OWNER)
        ],
        projects={project.id: project},
        project_memberships=[
            ProjectMembership(organization.id, project.id, user.id, MembershipRole.OWNER)
        ],
    )
    return store, user, organization, project


def make_service(store: Store, storage: FakeBlobStorage) -> DocumentService:
    return DocumentService(lambda: FakeUnitOfWork(store), storage)


@pytest.mark.asyncio
async def test_create_document_success() -> None:
    store, user, org, project = setup_store()
    storage = FakeBlobStorage()
    service = make_service(store, storage)

    doc, ver = await service.create(
        organization_id=org.id,
        project_id=project.id,
        user_id=user.id,
        name="Notes",
        filename="notes.txt",
        data=b"hello",
        mime_type="text/plain",
    )

    assert doc.name == "Notes"
    assert doc.current_version_id == ver.id
    assert ver.version_number == 1
    assert ver.size_bytes == 5
    assert ver.sha256 == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert ver.status == DocumentVersionStatus.UPLOADED
    assert storage.files[ver.blob_path] == b"hello"


@pytest.mark.asyncio
async def test_create_document_unauthorized() -> None:
    store, _, org, project = setup_store()
    storage = FakeBlobStorage()
    service = make_service(store, storage)

    with pytest.raises(AuthorizationError):
        await service.create(
            organization_id=org.id,
            project_id=project.id,
            user_id=uuid4(),  # Random user not in project
            name="Notes",
            filename="notes.txt",
            data=b"hello",
            mime_type="text/plain",
        )


@pytest.mark.asyncio
async def test_upload_version_success() -> None:
    store, user, org, project = setup_store()
    storage = FakeBlobStorage()
    service = make_service(store, storage)

    doc, ver1 = await service.create(
        organization_id=org.id,
        project_id=project.id,
        user_id=user.id,
        name="Notes",
        filename="notes.txt",
        data=b"hello",
        mime_type="text/plain",
    )

    ver2 = await service.upload_version(
        document_id=doc.id,
        user_id=user.id,
        filename="notes_v2.txt",
        data=b"hello world",
        mime_type="text/plain",
    )

    assert ver2.version_number == 2
    assert ver2.size_bytes == 11
    assert ver2.source_filename == "notes_v2.txt"
    # Document current version points to the latest upload
    doc_stored = store.documents[doc.id]
    assert doc_stored.current_version_id == ver2.id


@pytest.mark.asyncio
async def test_soft_delete_document() -> None:
    store, user, org, project = setup_store()
    storage = FakeBlobStorage()
    service = make_service(store, storage)

    doc, _ = await service.create(
        organization_id=org.id,
        project_id=project.id,
        user_id=user.id,
        name="Notes",
        filename="notes.txt",
        data=b"hello",
        mime_type="text/plain",
    )

    await service.delete(doc.id, user.id)

    assert store.documents[doc.id].deleted_at is not None
    # Check that retrieve fails now
    with pytest.raises(NotFoundError):
        await service.get(doc.id, user.id)
