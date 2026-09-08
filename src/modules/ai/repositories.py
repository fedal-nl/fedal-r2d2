"""Database access for shared AI configuration and usage auditing."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.ai import models


class AIRepository:
    """Persist AI configuration and usage without provider-specific behavior."""

    def __init__(self, db: Session):
        """Store the request-scoped database session."""
        self.db = db

    def get_active_agent(self, application: str, feature: str) -> models.AIAgent | None:
        """Return the newest enabled prompt configuration for an application feature."""
        query = (
            select(models.AIAgent)
            .where(
                models.AIAgent.application == application,
                models.AIAgent.feature == feature,
                models.AIAgent.enabled.is_(True),
            )
            .order_by(models.AIAgent.id.desc())
        )
        return self.db.scalars(query).first()

    def record_usage(
        self,
        *,
        agent: models.AIAgent,
        user_id: uuid.UUID | None,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        success: bool,
        error_code: str | None = None,
    ) -> models.AIUsage:
        """Commit a provider invocation audit record."""
        usage = models.AIUsage(
            user_id=user_id,
            ai_agent_id=agent.id,
            application=agent.application,
            feature=agent.feature,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tokens_used=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
        )
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage
