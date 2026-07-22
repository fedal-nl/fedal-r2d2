from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import INET, ARRAY
from src.core.database import Base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.enums import FormStatus

class BaseForm(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default=FormStatus.NEW)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class ZaansrechtForm(BaseForm):
    __tablename__ = "zaansrecht_form"
    __table_args__ = {"schema": "public"}

    terms_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    telephone: Mapped[str|None] = mapped_column(String, nullable=True)
    description: Mapped[str|None] = mapped_column(Text, nullable=True)
    subject: Mapped[str|None] = mapped_column(String, nullable=True)
    meeting_datetime: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    meeting_type: Mapped[str|None] = mapped_column(String, nullable=True)  # e.g., 'in_person', 'virtual'
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
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # foreign key to ZaansrechtForm
    form_id: Mapped[int] = mapped_column(Integer, ForeignKey("public.zaansrecht_form.id"), nullable=False)
    user_agent: Mapped[str|None] = mapped_column(String, nullable=True)
    referrer: Mapped[str|None] = mapped_column(String, nullable=True)
    x_forwarded_for: Mapped[list[str]|None] = mapped_column(ARRAY(INET), nullable=True)
    x_real_ip: Mapped[str|None] = mapped_column(INET, nullable=True, index=True)
    captcha_token: Mapped[str|None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Reverse relationship
    form = relationship("ZaansrechtForm", back_populates="submission_logs")
