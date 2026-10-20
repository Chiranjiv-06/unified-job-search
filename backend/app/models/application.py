from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SAEnum, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.company import Company
    from app.models.email_event import EmailEvent
    from app.models.job import Job

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    job_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, name="application_status_enum", native_enum=False),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True
    )
    response_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recruiter_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    interview_details: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resume_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timeline_events: Mapped[Optional[list]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=list
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="applications")
    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="applications")
    email_events: Mapped[List["EmailEvent"]] = relationship(
        "EmailEvent",
        back_populates="application"
    )


    def __repr__(self) -> str:
        return f"<Application id={self.id} job_title={self.job_title} status={self.status}>"
