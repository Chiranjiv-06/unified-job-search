from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.profile import CandidateProfile, CandidateSkill
from app.schemas.profile import CandidateProfileResponse, CandidateProfileUpdate
from app.api.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["Candidate Profile"])

@router.get("", response_model=CandidateProfileResponse)
def get_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the candidate profile and associated skills for the authenticated user.
    """
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    if not profile:
        # Create empty profile if not already created
        profile = CandidateProfile(
            user_id=current_user.id,
            experience_level="Entry-Level",
            preferred_work_mode="Any"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile

@router.put("", response_model=CandidateProfileResponse)
def update_candidate_profile(
    profile_in: CandidateProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the candidate profile and skills for the authenticated user.
    Enforces user ownership and data integrity.
    """
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    if not profile:
        profile = CandidateProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    # Update base fields
    if profile_in.education is not None:
        profile.education = profile_in.education
    if profile_in.experience_level is not None:
        profile.experience_level = profile_in.experience_level
    if profile_in.preferred_roles is not None:
        profile.preferred_roles = profile_in.preferred_roles
    if profile_in.preferred_locations is not None:
        profile.preferred_locations = profile_in.preferred_locations
    if profile_in.preferred_work_mode is not None:
        profile.preferred_work_mode = profile_in.preferred_work_mode
    if profile_in.salary_expectation is not None:
        profile.salary_expectation = profile_in.salary_expectation

    # Update skills if provided
    if profile_in.skills is not None:
        # Replace existing skills cleanly
        profile.skills.clear()
        for skill_data in profile_in.skills:
            if skill_data.skill_name.strip():
                new_skill = CandidateSkill(
                    profile_id=profile.id,
                    skill_name=skill_data.skill_name.strip(),
                    proficiency_level=skill_data.proficiency_level or "Intermediate"
                )
                profile.skills.append(new_skill)

    db.commit()
    db.refresh(profile)
    return profile
