import asyncio
import os
from typing import cast

from google.cloud import storage  # type: ignore

from knowledge_os.application.ports import BlobStoragePort
from knowledge_os.config import Settings


class GcsStorageAdapter(BlobStoragePort):
    def __init__(self, settings: Settings) -> None:
        credentials_path = settings.google_application_credentials
        if credentials_path and os.path.exists(credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        self._client = None
        self._bucket_name = settings.gcs_bucket_name

    @property
    def provider_name(self) -> str:
        return "google_gcs"

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client()
        return self._client

    async def upload(self, blob_path: str, data: bytes, content_type: str) -> str:
        def _upload() -> str:
            bucket = self.client.bucket(self._bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(data, content_type=content_type)
            return blob.etag or ""

        return await asyncio.to_thread(_upload)

    async def download(self, blob_path: str) -> bytes:
        def _download() -> bytes:
            bucket = self.client.bucket(self._bucket_name)
            blob = bucket.blob(blob_path)
            return cast(bytes, blob.download_as_bytes())

        return await asyncio.to_thread(_download)

    async def delete(self, blob_path: str) -> None:
        def _delete() -> None:
            bucket = self.client.bucket(self._bucket_name)
            blob = bucket.blob(blob_path)
            if blob.exists():
                blob.delete()

        await asyncio.to_thread(_delete)
