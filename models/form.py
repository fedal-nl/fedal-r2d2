from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import INET, ARRAY
from configs.db import Base
from sqlalchemy.orm import relationship
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

    # Relationship to logs
    submission_logs = relationship(
        "FormSubmissionLog",
        back_populates="form",
        cascade="all, delete-orphan"
    )

# Addintional class that will save other data about the user logs like the ipaddress, user agent, referrer, etc. 
# The form will be linked to this table via a foreign key.
class FormSubmissionLog(Base):
    __tablename__ = "form_submission_log"

    id = Column(Integer, primary_key=True, index=True)
    # foreign key to ZaansrechtForm
    form_id = Column(Integer, ForeignKey("zaansrecht_form.id"), nullable=False)
    user_agent = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    x_forwarded_for = Column(ARRAY(INET), nullable=True)
    x_real_ip = Column(INET, nullable=True, index=True)
    captcha_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Reverse relationship
    form = relationship("ZaansrechtForm", back_populates="submission_logs")