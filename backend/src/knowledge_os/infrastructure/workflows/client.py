from temporalio.client import Client

from knowledge_os.config import get_settings


async def get_temporal_client() -> Client:
    settings = get_settings()
    return await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )
