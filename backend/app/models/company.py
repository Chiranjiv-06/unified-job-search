from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Boolean, Float, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.verification import VerificationLog
    from app.models.job import Job


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    careers_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    fraud_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Store metadata as JSONB in PostgreSQL, mapped to column "metadata"
    company_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="company"
    )
    verification_logs: Mapped[List["VerificationLog"]] = relationship(
        "VerificationLog",
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="desc(VerificationLog.checked_at)"
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="company"
    )


    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name} verified={self.is_verified}>"
