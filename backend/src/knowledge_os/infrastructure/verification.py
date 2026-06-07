import logging
import os
import sys

from qdrant_client import QdrantClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from knowledge_os.config import Settings

logger = logging.getLogger(__name__)


async def verify_infrastructure_services(settings: Settings) -> None:
    # Bypasses connection checks during test execution
    if "pytest" in sys.modules or settings.environment == "testing":
        logger.info("Skipping infrastructure startup checks in test environment.")
        return

    errors = []

    # 1. Verify PostgreSQL Database
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Infrastructure Check: PostgreSQL database connection succeeded.")
    except Exception as e:
        errors.append(f"PostgreSQL connection failed at '{settings.database_url}'. Details: {e}")

    # 2. Verify Qdrant Vector Store
    try:
        # Resolve client synchronously or in thread since client setup does simple REST listing
        q_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=3,
        )
        q_client.get_collections()
        logger.info("Infrastructure Check: Qdrant connection succeeded.")
    except Exception as e:
        errors.append(f"Qdrant connection failed at '{settings.qdrant_url}'. Details: {e}")

    # 3. Verify LLM Provider API Keys
    p = settings.embedding_provider.lower()
    if p == "openai" and not settings.openai_api_key:
        errors.append(
            "OpenAI is configured as the embedding provider, "
            "but KNOWLEDGE_OS_OPENAI_API_KEY is not set."
        )
    elif p in {"gemini", "google"} and not settings.gemini_api_key:
        errors.append(
            "Gemini/Google is configured as the embedding provider, "
            "but KNOWLEDGE_OS_GEMINI_API_KEY is not set."
        )

    if errors:
        logger.critical("--- INFRASTRUCTURE STARTUP CHECK FAILED ---")
        for err in errors:
            logger.critical(f" - {err}")
        logger.critical("Please start your databases/services and configure your credentials.")
        sys.stderr.flush()
        sys.stdout.flush()
        os._exit(1)
