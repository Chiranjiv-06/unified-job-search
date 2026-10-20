from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, DateTime, Enum as SAEnum, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import EmailCategory

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User

class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    application_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_category: Mapped[EmailCategory] = mapped_column(
        SAEnum(EmailCategory, name="email_category_enum", native_enum=False),
        default=EmailCategory.CONFIRMATION,
        nullable=False,
        index=True
    )
    parsed_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    # Relationships
    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="email_events")
    user: Mapped["User"] = relationship("User", back_populates="email_events")

    def __repr__(self) -> str:
        return f"<EmailEvent id={self.id} category={self.detected_category} sender={self.sender_email}>"
