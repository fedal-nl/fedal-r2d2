"""Provider-independent AI orchestration reusable by all applications."""

from collections.abc import Mapping
from time import monotonic
from typing import Any, Protocol

from src.enums import AIAgentEnum
from src.modules.ai.repositories import AIRepository
from src.modules.ai.schemas import (
    AIGenerationRequest,
    AIGenerationResponse,
    AIProviderResult,
)


class AIConfigurationError(RuntimeError):
    """Raised when no enabled agent or provider adapter is configured."""


class AIProviderError(RuntimeError):
    """Raised after a provider failure has been recorded safely."""


class AIProviderClient(Protocol):
    """Contract implemented by OpenAI, Anthropic, or other provider adapters."""

    def generate(
        self,
        *,
        model: str,
        model_version: str,
        system_prompt: str,
        input_data: Mapping[str, Any],
    ) -> AIProviderResult:
        """Generate content and return normalized usage metadata."""
        ...


class AIService:
    """Resolve configuration, invoke a provider, and audit every call."""

    def __init__(
        self,
        repository: AIRepository,
        providers: Mapping[AIAgentEnum, AIProviderClient],
    ):
        """Receive persistence and explicitly configured provider adapters."""
        self.repository = repository
        self.providers = providers

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        """Run one application feature without exposing a provider SDK to the caller."""
        agent = self.repository.get_active_agent(request.application, request.feature)
        if agent is None:
            raise AIConfigurationError(
                f"No enabled AI configuration for {request.application}.{request.feature}"
            )
        provider = self.providers.get(agent.provider)
        if provider is None:
            raise AIConfigurationError(
                f"No provider adapter configured for {agent.provider.value}"
            )
        started = monotonic()
        try:
            result = provider.generate(
                model=agent.model_name,
                model_version=agent.model_version,
                system_prompt=agent.prompt,
                input_data=request.input_data,
            )
        except Exception as exc:
            latency_ms = round((monotonic() - started) * 1000)
            self.repository.record_usage(
                agent=agent,
                user_id=request.user_id,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=latency_ms,
                success=False,
                error_code=type(exc).__name__,
            )
            raise AIProviderError("The configured AI provider failed") from exc
        latency_ms = round((monotonic() - started) * 1000)
        usage = self.repository.record_usage(
            agent=agent,
            user_id=request.user_id,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost=result.cost,
            latency_ms=latency_ms,
            success=True,
        )
        return AIGenerationResponse(
            content=result.content,
            provider=agent.provider.value,
            model=agent.model_name,
            prompt_version=agent.prompt_version,
            usage_id=usage.id,
        )
