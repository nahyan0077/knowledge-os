from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from knowledge_os.api.dependencies import get_current_user_id
from knowledge_os.api.schemas import AvailableModelsResponse, ModelOptionResponse
from knowledge_os.config import get_settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/models", response_model=AvailableModelsResponse)
async def get_available_models(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> AvailableModelsResponse:
    settings = get_settings()
    models = []

    # Check for Gemini API key
    if settings.gemini_api_key:
        models.append(
            ModelOptionResponse(provider="google", name="gemini-1.5-flash", label="Gemini Flash")
        )
        models.append(
            ModelOptionResponse(provider="google", name="gemini-1.5-pro", label="Gemini Pro")
        )

    # Check for OpenAI API key
    if settings.openai_api_key:
        models.append(
            ModelOptionResponse(provider="openai", name="gpt-4o-mini", label="GPT-4o Mini")
        )
        models.append(ModelOptionResponse(provider="openai", name="gpt-4o", label="GPT-4o"))

    # Fallback to Test model if nothing is configured (so backend/frontend don't break/crash)
    if not models:
        models.append(ModelOptionResponse(provider="test", name="test", label="Test Model"))

    # Pick default model: Gemini Flash if available, otherwise first in list
    default_model = models[0]
    for model in models:
        if model.name == "gemini-1.5-flash":
            default_model = model
            break

    return AvailableModelsResponse(models=models, default_model=default_model)
