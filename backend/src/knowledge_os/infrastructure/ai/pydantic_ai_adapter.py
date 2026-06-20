import time
from collections.abc import AsyncIterator

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.settings import ModelSettings

from knowledge_os.application.ports import (
    ChatAgentPort,
    LlmModelConfig,
    LlmResponse,
    LlmResponseChunk,
    LlmUsageMetrics,
    PricingService,
)


def _get_model(config: LlmModelConfig) -> Model:
    import os

    from knowledge_os.config import get_settings

    settings = get_settings()
    p = config.provider.lower()
    if p == "openai":
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        return OpenAIModel(config.model_name)
    elif p in {"gemini", "google"}:
        if settings.gemini_api_key:
            os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
        model_name = config.model_name
        if model_name in {
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-2.5-flash",
        }:
            model_name = "gemini-flash-lite-latest"
        return GeminiModel(model_name)
    elif p == "anthropic":
        return AnthropicModel(config.model_name)
    elif p == "test":
        return TestModel(custom_output_text="Test response")
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


class PydanticAiAdapter(ChatAgentPort):
    def __init__(self, pricing_service: PricingService) -> None:
        self._pricing_service = pricing_service

    async def generate(
        self,
        system_prompt: str,
        messages: list[tuple[str, str]],
        config: LlmModelConfig,
    ) -> LlmResponse:
        model = _get_model(config)
        agent = Agent(model, system_prompt=system_prompt)

        user_prompt = "Hello"
        history_tuples = []
        if messages:
            last_role, last_content = messages[-1]
            if last_role.lower() == "user":
                user_prompt = last_content
                history_tuples = messages[:-1]
            else:
                history_tuples = messages

        ai_history: list[ModelMessage] = []
        if history_tuples and system_prompt:
            ai_history.append(ModelRequest(parts=[SystemPromptPart(content=system_prompt)]))

        for r, c in history_tuples:
            r_lower = r.lower()
            if r_lower == "user":
                ai_history.append(ModelRequest(parts=[UserPromptPart(content=c)]))
            elif r_lower == "assistant":
                ai_history.append(ModelResponse(parts=[TextPart(content=c)]))
            elif r_lower == "system":
                ai_history.append(ModelRequest(parts=[SystemPromptPart(content=c)]))

        model_settings = None
        if config.temperature is not None:
            model_settings = ModelSettings(temperature=config.temperature)

        start_time = time.perf_counter()
        result = await agent.run(
            user_prompt, message_history=ai_history, model_settings=model_settings
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        usage = result.usage() if callable(result.usage) else result.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        total_tokens = input_tokens + output_tokens
        cost = self._pricing_service.calculate_cost(
            config.provider, config.model_name, input_tokens, output_tokens
        )

        metrics = LlmUsageMetrics(
            provider=config.provider,
            model=config.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost=cost,
        )

        return LlmResponse(content=result.output, usage=metrics)

    async def generate_stream(
        self,
        system_prompt: str,
        messages: list[tuple[str, str]],
        config: LlmModelConfig,
    ) -> AsyncIterator[LlmResponseChunk | LlmUsageMetrics]:
        model = _get_model(config)
        agent = Agent(model, system_prompt=system_prompt)

        user_prompt = "Hello"
        history_tuples = []
        if messages:
            last_role, last_content = messages[-1]
            if last_role.lower() == "user":
                user_prompt = last_content
                history_tuples = messages[:-1]
            else:
                history_tuples = messages

        ai_history: list[ModelMessage] = []
        if history_tuples and system_prompt:
            ai_history.append(ModelRequest(parts=[SystemPromptPart(content=system_prompt)]))

        for r, c in history_tuples:
            r_lower = r.lower()
            if r_lower == "user":
                ai_history.append(ModelRequest(parts=[UserPromptPart(content=c)]))
            elif r_lower == "assistant":
                ai_history.append(ModelResponse(parts=[TextPart(content=c)]))
            elif r_lower == "system":
                ai_history.append(ModelRequest(parts=[SystemPromptPart(content=c)]))

        model_settings = None
        if config.temperature is not None:
            model_settings = ModelSettings(temperature=config.temperature)

        start_time = time.perf_counter()
        async with agent.run_stream(
            user_prompt, message_history=ai_history, model_settings=model_settings
        ) as result:
            async for chunk in result.stream_text(delta=True):
                yield LlmResponseChunk(content=chunk)

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        usage = result.usage() if callable(result.usage) else result.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        total_tokens = input_tokens + output_tokens
        cost = self._pricing_service.calculate_cost(
            config.provider, config.model_name, input_tokens, output_tokens
        )

        yield LlmUsageMetrics(
            provider=config.provider,
            model=config.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost=cost,
        )
