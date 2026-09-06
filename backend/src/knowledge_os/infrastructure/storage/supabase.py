import asyncio
from typing import cast

import boto3
from botocore.config import Config

from knowledge_os.application.ports import BlobStoragePort
from knowledge_os.config import Settings


class SupabaseStorageAdapter(BlobStoragePort):
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.supabase_storage_bucket
        self._client = None
        self._endpoint = settings.supabase_s3_endpoint
        self._access_key = settings.supabase_key
        self._secret_key = settings.supabase_secret_key
        self._region = settings.supabase_region

    @property
    def provider_name(self) -> str:
        return "supabase"

    @property
    def client(self) -> "boto3.client":
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    async def upload(self, blob_path: str, data: bytes, content_type: str) -> str:
        def _upload() -> str:
            self.client.put_object(
                Bucket=self._bucket,
                Key=blob_path,
                Body=data,
                ContentType=content_type,
            )
            return ""

        return await asyncio.to_thread(_upload)

    async def download(self, blob_path: str) -> bytes:
        def _download() -> bytes:
            response = self.client.get_object(Bucket=self._bucket, Key=blob_path)
            return cast(bytes, response["Body"].read())

        return await asyncio.to_thread(_download)

    async def download_range(self, blob_path: str, start: int, end: int) -> bytes:
        def _download_range() -> bytes:
            response = self.client.get_object(
                Bucket=self._bucket,
                Key=blob_path,
                Range=f"bytes={start}-{end}",
            )
            return cast(bytes, response["Body"].read())

        return await asyncio.to_thread(_download_range)

    async def delete(self, blob_path: str) -> None:
        def _delete() -> None:
            try:
                self.client.delete_object(Bucket=self._bucket, Key=blob_path)
            except Exception:
                pass

        await asyncio.to_thread(_delete)
