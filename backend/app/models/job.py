from datetime import datetime
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.company import Company
    from app.models.application import Application

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Required & Preferred skills stored as JSONB in PostgreSQL
    required_skills: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=list
    )
    preferred_skills: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=list
    )
    
    experience_years_required: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(50), default="Entry-Level", nullable=True)
    education_requirement: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), default="Any", nullable=True, index=True)
    
    # Salary fields
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), default="INR", nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Source & metadata
    source_platform: Mapped[Optional[str]] = mapped_column(String(100), default="Manual", nullable=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    posting_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="jobs")
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="created_jobs")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job")

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title} company={self.company_name}>"
