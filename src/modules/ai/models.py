"""Persistence models shared by every AI-consuming application."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.core.database import Base
from src.enums import AIAgentEnum

AI_SCHEMA = "ai"


class AIAgent(Base):
    """Versioned prompt and model configuration for one application feature."""

    __tablename__ = "ai_agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[AIAgentEnum] = mapped_column(
        "name", Enum(AIAgentEnum, name="ai_agent_enum"), nullable=False, index=True
    )
    application: Mapped[str] = mapped_column(String, nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column("version", String, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )
    usage: Mapped[list["AIUsage"]] = relationship(back_populates="agent")

    __table_args__ = (
        UniqueConstraint(
            "application", "feature", "prompt_version", name="uq_ai_prompt_version"
        ),
        {"schema": AI_SCHEMA},
    )


class AIUsage(Base):
    """Audit one successful or failed provider invocation."""

    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ai_agent_id: Mapped[int] = mapped_column(
        ForeignKey("ai.ai_agents.id"), nullable=False, index=True
    )
    application: Mapped[str] = mapped_column(String, nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String, nullable=False, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_code: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    agent: Mapped[AIAgent] = relationship(back_populates="usage")

    __table_args__ = {"schema": AI_SCHEMA}
