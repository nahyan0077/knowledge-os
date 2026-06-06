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

from knowledge_os.application.ports import (
    ChatAgentPort,
    LlmModelConfig,
    LlmResponse,
    LlmResponseChunk,
    LlmUsageMetrics,
)


def _get_model(config: LlmModelConfig) -> Model:
    p = config.provider.lower()
    if p == "openai":
        return OpenAIModel(config.model_name)
    elif p in {"gemini", "google"}:
        return GeminiModel(config.model_name)
    elif p == "anthropic":
        return AnthropicModel(config.model_name)
    elif p == "test":
        return TestModel(custom_output_text="Test response")
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    model_lower = model.lower()
    if "gpt-4o-mini" in model_lower:
        input_rate = 0.150 / 1_000_000
        output_rate = 0.600 / 1_000_000
    elif "gpt-4o" in model_lower:
        input_rate = 5.00 / 1_000_000
        output_rate = 15.00 / 1_000_000
    elif "claude-3-5-sonnet" in model_lower:
        input_rate = 3.00 / 1_000_000
        output_rate = 15.00 / 1_000_000
    elif "gemini-1.5-pro" in model_lower:
        input_rate = 1.25 / 1_000_000
        output_rate = 5.00 / 1_000_000
    elif "gemini-1.5-flash" in model_lower:
        input_rate = 0.075 / 1_000_000
        output_rate = 0.30 / 1_000_000
    else:
        input_rate = 0.150 / 1_000_000
        output_rate = 0.600 / 1_000_000
    return input_tokens * input_rate + output_tokens * output_rate


class PydanticAiAdapter(ChatAgentPort):
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
        for r, c in history_tuples:
            r_lower = r.lower()
            if r_lower == "user":
                ai_history.append(ModelRequest(parts=[UserPromptPart(content=c)]))
            elif r_lower == "assistant":
                ai_history.append(ModelResponse(parts=[TextPart(content=c)]))
            elif r_lower == "system":
                ai_history.append(ModelRequest(parts=[SystemPromptPart(content=c)]))

        start_time = time.perf_counter()
        result = await agent.run(user_prompt, message_history=ai_history)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        usage = result.usage() if callable(result.usage) else result.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        total_tokens = input_tokens + output_tokens
        cost = _calculate_cost(config.model_name, input_tokens, output_tokens)

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
        for r, c in history_tuples:
            r_lower = r.lower()
            if r_lower == "user":
                ai_history.append(ModelRequest(parts=[UserPromptPart(content=c)]))
            elif r_lower == "assistant":
                ai_history.append(ModelResponse(parts=[TextPart(content=c)]))
            elif r_lower == "system":
                ai_history.append(ModelRequest(parts=[SystemPromptPart(content=c)]))

        start_time = time.perf_counter()
        async with agent.run_stream(user_prompt, message_history=ai_history) as result:
            async for chunk in result.stream_text(delta=True):
                yield LlmResponseChunk(content=chunk)

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        usage = result.usage() if callable(result.usage) else result.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        total_tokens = input_tokens + output_tokens
        cost = _calculate_cost(config.model_name, input_tokens, output_tokens)

        yield LlmUsageMetrics(
            provider=config.provider,
            model=config.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost=cost,
        )
