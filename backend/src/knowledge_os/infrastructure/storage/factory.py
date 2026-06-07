from knowledge_os.application.ports import BlobStoragePort
from knowledge_os.config import Settings
from knowledge_os.infrastructure.storage.azure import AzureBlobStorageAdapter
from knowledge_os.infrastructure.storage.gcs import GcsStorageAdapter


class StorageFactory:
    @staticmethod
    def get_storage(settings: Settings, provider: str | None = None) -> BlobStoragePort:
        prov = (provider or settings.storage_provider).lower()
        if prov == "azure_blob":
            return AzureBlobStorageAdapter(settings)
        elif prov in {"google_gcs", "gcs"}:
            return GcsStorageAdapter(settings)
        elif prov == "local":
            return AzureBlobStorageAdapter(settings)
        else:
            raise ValueError(f"Unsupported storage provider: {prov}")
