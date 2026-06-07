import asyncio
import hashlib
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContentSettings

from knowledge_os.config import Settings


class AzureBlobStorageAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.conn_str = settings.azure_storage_connection_string
        self.container_name = settings.azure_storage_container_name
        self._local_storage_dir = Path(
            "/Users/nahyanm/Documents/NAHYAN/projects/rag/backend/local_storage"
        )

        if not self.conn_str:
            self._local_storage_dir.mkdir(parents=True, exist_ok=True)
            self.client = None
        else:
            self.client = BlobServiceClient.from_connection_string(self.conn_str)

    @property
    def provider_name(self) -> str:
        return "azure_blob" if self.conn_str else "local"

    async def upload(self, blob_path: str, data: bytes, content_type: str) -> str:
        if not self.client:
            file_path = self._local_storage_dir / blob_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(file_path.write_bytes, data)
            etag_hash = hashlib.md5(f"{blob_path}:{len(data)}".encode()).hexdigest()
            return f'"{etag_hash}"'
        else:
            container_client = self.client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(blob_path)

            def _upload() -> str:
                try:
                    container_client.create_container()
                except Exception:
                    pass
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                )
                props = blob_client.get_blob_properties()
                return str(props.etag)

            return await asyncio.to_thread(_upload)

    async def download(self, blob_path: str) -> bytes:
        if not self.client:
            file_path = self._local_storage_dir / blob_path
            if not file_path.exists():
                raise FileNotFoundError(f"Blob path {blob_path} not found in local storage.")
            return await asyncio.to_thread(file_path.read_bytes)
        else:
            container_client = self.client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(blob_path)

            def _download() -> bytes:
                stream = blob_client.download_blob()
                return bytes(stream.readall())

            return await asyncio.to_thread(_download)

    async def delete(self, blob_path: str) -> None:
        if not self.client:
            file_path = self._local_storage_dir / blob_path
            if file_path.exists():
                await asyncio.to_thread(file_path.unlink)
        else:
            container_client = self.client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(blob_path)

            def _delete() -> None:
                blob_client.delete_blob()

            await asyncio.to_thread(_delete)
