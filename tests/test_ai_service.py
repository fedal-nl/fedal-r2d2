"""Unit tests for reusable AI orchestration and usage persistence."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.enums import AIAgentEnum
from src.modules.ai.repositories import AIRepository
from src.modules.ai.schemas import AIGenerationRequest, AIProviderResult
from src.modules.ai.service import AIConfigurationError, AIProviderError, AIService


class FakeProvider:
    """Return a deterministic normalized provider response."""

    def generate(self, **values):
        """Capture input and emulate one successful provider invocation."""
        self.values = values
        return AIProviderResult(
            content="Practise verbs.", input_tokens=10, output_tokens=4, cost=0.01
        )


class FailingProvider:
    """Emulate a provider SDK failure."""

    def generate(self, **values):
        """Raise a provider error for service error-path testing."""
        raise TimeoutError("provider timeout")


def agent():
    """Build a reusable application feature configuration."""
    return SimpleNamespace(
        id=3,
        provider=AIAgentEnum.OPENAI,
        application="spanglish",
        feature="quiz_advice",
        model_name="gpt-test",
        model_version="1",
        prompt="Give concise learning advice.",
        prompt_version="2",
    )


def test_ai_service_generates_and_records_usage() -> None:
    """Route generation through an adapter and return stable audit metadata."""
    repository = MagicMock()
    repository.get_active_agent.return_value = agent()
    repository.record_usage.return_value = SimpleNamespace(id=11)
    provider = FakeProvider()
    service = AIService(repository, {AIAgentEnum.OPENAI: provider})

    response = service.generate(
        AIGenerationRequest(
            application="spanglish",
            feature="quiz_advice",
            input_data={"score": 70},
        )
    )

    assert response.content == "Practise verbs."
    assert response.usage_id == 11
    assert provider.values["input_data"] == {"score": 70}
    assert repository.record_usage.call_args.kwargs["success"] is True
    assert repository.record_usage.call_args.kwargs["input_tokens"] == 10


def test_ai_service_requires_configuration_and_provider() -> None:
    """Fail explicitly when configuration or its adapter is unavailable."""
    repository = MagicMock()
    repository.get_active_agent.return_value = None
    request = AIGenerationRequest(application="forms", feature="summary", input_data={})
    with pytest.raises(AIConfigurationError, match="No enabled"):
        AIService(repository, {}).generate(request)

    repository.get_active_agent.return_value = agent()
    with pytest.raises(AIConfigurationError, match="No provider"):
        AIService(repository, {}).generate(request)


def test_ai_service_audits_provider_failures() -> None:
    """Record a safe failure audit before returning a shared service exception."""
    repository = MagicMock()
    repository.get_active_agent.return_value = agent()
    service = AIService(repository, {AIAgentEnum.OPENAI: FailingProvider()})
    request = AIGenerationRequest(
        application="email", feature="draft", input_data={"subject": "Hello"}
    )
    with pytest.raises(AIProviderError) as error:
        service.generate(request)
    assert isinstance(error.value.__cause__, TimeoutError)
    assert repository.record_usage.call_args.kwargs["success"] is False
    assert repository.record_usage.call_args.kwargs["error_code"] == "TimeoutError"


def test_ai_repository_reads_configuration_and_records_usage() -> None:
    """Exercise shared AI query and transaction adapters without PostgreSQL."""
    db = MagicMock()
    configured_agent = agent()
    db.scalars.return_value.first.return_value = configured_agent
    db.add.side_effect = lambda value: setattr(value, "id", 15)
    repository = AIRepository(db)

    assert repository.get_active_agent("spanglish", "quiz_advice") is configured_agent
    usage = repository.record_usage(
        agent=configured_agent,
        user_id=None,
        input_tokens=5,
        output_tokens=2,
        cost=0.02,
        latency_ms=25,
        success=True,
    )
    assert usage.id == 15
    assert usage.tokens_used == 7
    assert usage.application == "spanglish"
    db.commit.assert_called_once()
