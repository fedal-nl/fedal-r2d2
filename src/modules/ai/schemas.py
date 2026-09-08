"""Transport-neutral contracts for shared AI generation."""

import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class AIGenerationRequest(BaseModel):
    """Describe one application feature's provider-independent generation request."""

    application: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)
    feature: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=100)
    input_data: dict[str, Any]
    user_id: uuid.UUID | None = None


@dataclass(frozen=True)
class AIProviderResult:
    """Normalize text and accounting metadata returned by any provider adapter."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class AIGenerationResponse(BaseModel):
    """Return generated content with stable audit metadata."""

    content: str
    provider: str
    model: str
    prompt_version: str
    usage_id: int
