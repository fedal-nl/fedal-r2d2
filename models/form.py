from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from configs.db import Base
from enums import FormStatus

class BaseForm(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    status = Column(String, default=FormStatus.NEW)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ZaansrechtForm(BaseForm):
    __tablename__ = "zaansrecht_form"

    terms_accepted = Column(Boolean, nullable=False)
    telephone = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    subject = Column(String, nullable=True)
    meeting_datetime = Column(DateTime(timezone=True), nullable=True)
    meeting_type = Column(String, nullable=True)  # e.g., 'in_person', 'virtual'
