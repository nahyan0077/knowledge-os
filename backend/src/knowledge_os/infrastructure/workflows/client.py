from temporalio.client import Client

from knowledge_os.config import get_settings


async def get_temporal_client() -> Client:
    settings = get_settings()
    connect_args: dict = {}
    if settings.temporal_api_key:
        connect_args["api_key"] = settings.temporal_api_key
    return await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
        **connect_args,
    )
