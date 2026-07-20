# app/models/email_log.py
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from src.configs.db import Base
from src.enums import EmailStatus

class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender: Mapped[str] = mapped_column(String, nullable=False)
    receiver: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str|None] = mapped_column(Text, nullable=True)
    # Using Enum type for status
    status: Mapped[str] = mapped_column(String, nullable=False, default=EmailStatus.QUEUED)
    error_message: Mapped[str|None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), onupdate=func.now())