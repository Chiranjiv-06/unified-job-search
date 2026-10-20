import logging
from typing import List, Set, Dict, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile import CandidateProfile
from app.models.job import Job
from app.schemas.matching import MatchBreakdownResponse, JobMatchRankingItem, JobMatchRankingsResponse
from app.schemas.job import JobResponse

logger = logging.getLogger(__name__)

# Normalized tech skill synonym mapping for accurate delta comparisons
SKILL_SYNONYMS: Dict[str, Set[str]] = {
    "react": {"react", "react.js", "reactjs"},
    "javascript": {"javascript", "js", "ecmascript"},
    "typescript": {"typescript", "ts"},
    "python": {"python", "python3", "py"},
    "node.js": {"node", "node.js", "nodejs"},
    "fastapi": {"fastapi", "fast-api"},
    "django": {"django"},
    "flask": {"flask"},
    "postgresql": {"postgres", "postgresql", "psql"},
    "mysql": {"mysql"},
    "sqlite": {"sqlite", "sqlite3"},
    "mongodb": {"mongo", "mongodb"},
    "redis": {"redis"},
    "docker": {"docker", "docker container", "containers"},
    "kubernetes": {"kubernetes", "k8s"},
    "aws": {"aws", "amazon web services"},
    "gcp": {"gcp", "google cloud", "google cloud platform"},
    "azure": {"azure", "microsoft azure"},
    "html": {"html", "html5"},
    "css": {"css", "css3"},
    "tailwind css": {"tailwind", "tailwindcss", "tailwind css"},
    "bootstrap": {"bootstrap", "bootstrap5"},
    "c++": {"c++", "cpp"},
    "c#": {"c#", "csharp", "c sharp"},
    "java": {"java"},
    "go": {"go", "golang"},
    "rust": {"rust"},
    "git": {"git", "github", "gitlab"},
    "rest api": {"rest", "rest api", "restful", "restful api", "apis"},
    "graphql": {"graphql"},
    "ci/cd": {"ci/cd", "ci-cd", "continuous integration", "cicd"},
    "celery": {"celery"},
    "pytest": {"pytest", "unit testing", "testing"}
}


def canonical_skill_name(raw_name: str) -> str:
    """
    Normalizes a skill name by stripping whitespace, converting to lower case,
    and looking up established synonym clusters.
    """
    cleaned = raw_name.strip().lower()
    for canonical, synonyms in SKILL_SYNONYMS.items():
        if cleaned == canonical or cleaned in synonyms:
            return canonical
    return cleaned


def extract_candidate_skill_names(profile: Optional[CandidateProfile]) -> Set[str]:
    """
    Collects canonical candidate skill names from verified profile skills,
    falling back to parsed resume skills if available.
    """
    if not profile:
        return set()

    skills: Set[str] = set()
    # 1. Primary: verified profile skills
    if profile.skills:
        for s in profile.skills:
            if s.skill_name and s.skill_name.strip():
                skills.add(canonical_skill_name(s.skill_name))

    # 2. Fallback or supplement: parsed_skills
    if not skills and profile.parsed_skills and isinstance(profile.parsed_skills, list):
        for s in profile.parsed_skills:
            if isinstance(s, str) and s.strip():
                skills.add(canonical_skill_name(s))

    return skills


def compute_job_match(
    profile: Optional[CandidateProfile],
    job: Job
) -> MatchBreakdownResponse:
    """
    Computes a transparent, explainable delta match between a candidate profile and a job record.
    Weights: 65% Core Skills, 20% Preferred Skills, 15% Experience Alignment.
    """
    candidate_skills = extract_candidate_skill_names(profile)
    candidate_exp = float(profile.experience_years or 0.0) if profile else 0.0
    req_exp = float(job.experience_years_required or 0.0)

    # 1. Delta Skill Breakdown
    matched_skills: List[str] = []
    missing_critical: List[str] = []
    missing_secondary: List[str] = []

    # Evaluate required skills
    job_required = [s for s in (job.required_skills or []) if isinstance(s, str) and s.strip()]
    matched_required_count = 0
    for req in job_required:
        canon = canonical_skill_name(req)
        if canon in candidate_skills:
            matched_skills.append(req)
            matched_required_count += 1
        else:
            missing_critical.append(req)

    # Evaluate preferred skills
    job_preferred = [s for s in (job.preferred_skills or []) if isinstance(s, str) and s.strip()]
    matched_preferred_count = 0
    for pref in job_preferred:
        canon = canonical_skill_name(pref)
        if canon in candidate_skills:
            if pref not in matched_skills:
                matched_skills.append(pref)
            matched_preferred_count += 1
        else:
            missing_secondary.append(pref)

    # 2. Weighted Score Calculation
    # Core Skills (65%)
    if len(job_required) > 0:
        core_ratio = matched_required_count / len(job_required)
        core_score = core_ratio * 65.0
    else:
        core_ratio = 1.0
        core_score = 65.0

    # Preferred Skills (20%)
    if len(job_preferred) > 0:
        pref_ratio = matched_preferred_count / len(job_preferred)
        pref_score = pref_ratio * 20.0
    else:
        # If job doesn't specify preferred skills, scale with core alignment
        pref_ratio = core_ratio
        pref_score = core_ratio * 20.0

    # Experience Alignment (15%)
    meets_exp = candidate_exp >= req_exp
    exp_gap = round(max(0.0, req_exp - candidate_exp), 1)

    if req_exp <= 0.0 or meets_exp:
        exp_score = 15.0
        exp_warning = None
    else:
        exp_score = min(15.0, (candidate_exp / max(req_exp, 0.1)) * 15.0)
        exp_warning = (
            f"Requires {req_exp} years of experience; your profile currently reflects "
            f"{candidate_exp} years ({exp_gap} yr difference)."
        )

    raw_total = core_score + pref_score + exp_score
    final_score = round(min(100.0, max(0.0, raw_total)), 1)

    # 3. Human-Readable Explanation String
    explanation_parts = []
    if final_score >= 80.0:
        explanation_parts.append(f"Strong overall alignment ({final_score}%).")
    elif final_score >= 50.0:
        explanation_parts.append(f"Moderate role alignment ({final_score}%).")
    else:
        explanation_parts.append(f"Notable skill & experience gap ({final_score}%).")

    if matched_skills:
        top_matched = ", ".join(matched_skills[:4])
        explanation_parts.append(f"Matched key skills: {top_matched}.")
    else:
        explanation_parts.append("No direct skill overlap found with current profile.")

    if missing_critical:
        top_missing = ", ".join(missing_critical[:3])
        explanation_parts.append(f"Missing core requirements: {top_missing}.")

    if meets_exp:
        if req_exp > 0:
            explanation_parts.append(f"Meets stated tenure requirement ({candidate_exp} >= {req_exp} yrs).")
    else:
        explanation_parts.append(f"Experience requirement ({req_exp} yrs) exceeds current ({candidate_exp} yrs).")

    explanation_str = " ".join(explanation_parts)

    # 4. Truthful Resume Advice (never fabricate experience)
    resume_advice: List[str] = []
    if matched_skills:
        resume_advice.append(
            f"Highlight your verified proficiency in {', '.join(matched_skills[:3])} in your summary statement and top project bullet points."
        )

    if missing_critical:
        resume_advice.append(
            f"The job explicitly requests {', '.join(missing_critical[:3])}. If you have academic coursework, self-study, or personal repositories using these technologies, add them to your verified profile."
        )

    if not meets_exp and req_exp > 0:
        resume_advice.append(
            f"To offset the {exp_gap}-year tenure gap, emphasize the scale, complexity, and concrete technical outcomes of your completed projects."
        )

    if final_score >= 75.0 and meets_exp:
        resume_advice.append(
            "Your profile presents a competitive match. Ensure your resume formatting is clean and apply directly via the company career portal."
        )
    elif not resume_advice:
        resume_advice.append(
            "Review the role's primary technical stack and consider building a targeted portfolio project before submitting your application."
        )

    return MatchBreakdownResponse(
        job_id=job.id,
        job_title=job.title,
        company_name=job.company_name,
        match_score=final_score,
        matched_skills=matched_skills,
        missing_critical_skills=missing_critical,
        missing_secondary_skills=missing_secondary,
        meets_experience=meets_exp,
        candidate_experience_years=candidate_exp,
        required_experience_years=req_exp,
        experience_gap=exp_gap,
        experience_warning=exp_warning,
        explanation=explanation_str,
        resume_advice=resume_advice
    )


def rank_active_jobs_for_candidate(
    db: Session,
    profile: Optional[CandidateProfile]
) -> JobMatchRankingsResponse:
    """
    Evaluates all active jobs against the candidate profile and ranks them in descending order of match score.
    """
    active_jobs = list(db.execute(select(Job).where(Job.is_active == True)).scalars().all())

    rankings: List[JobMatchRankingItem] = []
    for job in active_jobs:
        match_result = compute_job_match(profile, job)
        rankings.append(
            JobMatchRankingItem(
                job=JobResponse.model_validate(job),
                match_score=match_result.match_score,
                matched_skills_count=len(match_result.matched_skills),
                missing_critical_skills_count=len(match_result.missing_critical_skills),
                meets_experience=match_result.meets_experience,
                quick_summary=match_result.explanation
            )
        )

    # Sort descending by match_score
    rankings.sort(key=lambda x: x.match_score, reverse=True)

    return JobMatchRankingsResponse(
        total_jobs_evaluated=len(rankings),
        rankings=rankings
    )
