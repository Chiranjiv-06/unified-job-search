from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.profile import CandidateProfile, CandidateSkill
from app.schemas.profile import (
    CandidateProfileResponse,
    CandidateProfileUpdate,
    ResumeUploadResponse,
    ConfirmSkillsRequest,
    SkillCreate,
)
from app.services.resume_service import (
    validate_resume_upload,
    extract_text_from_pdf,
    extract_skills_from_text,
)
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
    if profile_in.experience_years is not None:
        profile.experience_years = profile_in.experience_years
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

@router.post("/resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts candidate PDF resume upload, validates file type and size (<=5MB),
    extracts plain text safely using pypdf, and extracts skills using tech stack heuristics.
    Returns draft skill suggestions for candidate review without blindly overwriting profile data.
    """
    contents = await file.read()
    validate_resume_upload(file, contents)
    extracted_text, page_count = extract_text_from_pdf(contents)
    extracted_skills = extract_skills_from_text(extracted_text)

    # Enforce strict user ownership
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    if not profile:
        profile = CandidateProfile(
            user_id=current_user.id,
            experience_level="Entry-Level",
            preferred_work_mode="Any"
        )
        db.add(profile)
        db.flush()

    # Save raw resume text and parsed skills draft to profile metadata
    profile.raw_resume_text = extracted_text
    profile.parsed_skills = extracted_skills

    db.commit()
    db.refresh(profile)

    warning = None
    if not extracted_text:
        warning = "No readable text could be extracted. The document may be empty or contain scanned images."

    preview = (extracted_text[:300] + "...") if len(extracted_text) > 300 else extracted_text

    draft_suggestions = [
        SkillCreate(skill_name=s, proficiency_level="Intermediate")
        for s in extracted_skills
    ]

    return ResumeUploadResponse(
        message="Resume uploaded and parsed successfully. Review your draft skills below.",
        filename=file.filename or "resume.pdf",
        pages_parsed=page_count,
        extracted_text_preview=preview,
        extracted_skills=extracted_skills,
        draft_suggestions=draft_suggestions,
        current_skills=profile.skills,
        warning=warning
    )

@router.post("/confirm-skills", response_model=CandidateProfileResponse)
def confirm_candidate_skills(
    confirm_in: ConfirmSkillsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Applies approved draft skills to candidate profile after user review.
    Prevents duplicate skill entries and respects candidate customization.
    """
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    if not profile:
        profile = CandidateProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    existing_skill_names = {s.skill_name.lower(): s for s in profile.skills}

    for skill_item in confirm_in.skills:
        name_clean = skill_item.skill_name.strip()
        if not name_clean:
            continue
        key = name_clean.lower()
        if key not in existing_skill_names:
            new_skill = CandidateSkill(
                profile_id=profile.id,
                skill_name=name_clean,
                proficiency_level=skill_item.proficiency_level or "Intermediate"
            )
            profile.skills.append(new_skill)
            existing_skill_names[key] = new_skill
        else:
            # Update proficiency if specified
            if skill_item.proficiency_level:
                existing_skill_names[key].proficiency_level = skill_item.proficiency_level

    db.commit()
    db.refresh(profile)
    return profile

