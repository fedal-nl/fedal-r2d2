# app/models/email_log.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from configs.db import Base
from enums import EmailStatus

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, nullable=False)
    receiver = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    # Using Enum type for status
    status = Column(String, nullable=False, default=EmailStatus.QUEUED)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
