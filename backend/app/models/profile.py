from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    raw_resume_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_skills: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=list
    )
    experience_years: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    preferred_roles: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=list
    )
    education: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preferred_locations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_work_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    salary_expectation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")
    skills: Mapped[List["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<CandidateProfile id={self.id} user_id={self.user_id}>"

# Alias for canonical architecture layout
Profile = CandidateProfile

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    proficiency_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="skills")

    def __repr__(self) -> str:
        return f"<CandidateSkill id={self.id} skill={self.skill_name}>"
