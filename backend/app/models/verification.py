from datetime import datetime
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.company import Company

class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    domain_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mx_records_found: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    official_posting_matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scam_flags: Mapped[Optional[List[Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=list
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="verification_logs")

    def __repr__(self) -> str:
        return f"<VerificationLog id={self.id} company_id={self.company_id} domain_valid={self.domain_valid}>"
