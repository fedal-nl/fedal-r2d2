import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    JSON,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from src.enums import SocialMediaPlatformEnum

from src.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # metadata is a reserved word in SQLAlchemy, so we use user_metadata instead
    user_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )

    # a user can have only one social provider linked to their account, but we want to allow for multiple providers in the future, so we use a relationship here
    social_providers: Mapped[list["SocialProvider"]] = relationship(
        "SocialProvider",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=True,
    )
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SocialProvider(Base):
    __tablename__ = "social_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[SocialMediaPlatformEnum] = mapped_column(
        Enum(SocialMediaPlatformEnum, name="social_media_platform_enum"), nullable=False
    )
    platform_user_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user = relationship("User", back_populates="social_providers")

    # add a constraint to ensure a user cannot link the same social media account multiple times
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
        {"schema": "public"},
    )


class RefreshSession(Base):
    """A revocable, rotating login session for a browser, CLI, or other client."""

    __tablename__ = "refresh_sessions"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    client_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="refresh_sessions")
