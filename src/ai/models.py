import uuid
from datetime import datetime
from sqlalchemy import (
    Enum,
    DateTime,
    String,
    Text,
    ForeignKey,
    Integer,
    Float
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from src.enums import AIAgentEnum
from src.configs.db import Base


# =========================
# AI Agent
# =========================

class AIAgent(Base):
    __tablename__ = "ai_agents"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[AIAgentEnum] = mapped_column(
        Enum(AIAgentEnum, name="ai_agent_enum"),
        nullable=False,
        unique=True
    )

    version: Mapped[str] = mapped_column(String, nullable=False)

    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    prompt_version: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        index=True
    )


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    ai_agent_id: Mapped[int] = mapped_column(ForeignKey("ai_agents.id"), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
