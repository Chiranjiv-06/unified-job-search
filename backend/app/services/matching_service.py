import json
import logging
import re
from typing import List, Set, Dict, Tuple, Optional, Any
from sqlalchemy import select, or_, func, desc, cast, String
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
    "pytest": {"pytest", "unit testing", "testing"},
    # Data Analyst and extended IT skills
    "sql": {"sql", "structured query language"},
    "pandas": {"pandas"},
    "numpy": {"numpy"},
    "data analysis": {"data analysis", "data analytics", "data analyst"},
    "power bi": {"power bi", "powerbi"},
    "tableau": {"tableau"},
    "excel": {"excel", "advanced excel", "ms excel"},
    "machine learning": {"machine learning", "ml"},
    "linux": {"linux", "unix"},
    "spring boot": {"spring", "spring boot", "springboot"},
    "angular": {"angular", "angularjs"},
    "vue": {"vue", "vue.js", "vuejs"},
    "kafka": {"kafka", "apache kafka"},
    "spark": {"spark", "apache spark"},
    "scikit-learn": {"sklearn", "scikit-learn"},
}

# Recognized IT role families
IT_ROLE_FAMILIES = {
    "software_engineering": [
        "software engineer", "software developer", "full stack", "fullstack",
        "backend", "back-end", "frontend", "front-end", "web developer",
        "programmer", "application developer", "sde", "system engineer",
        "developer", "api developer"
    ],
    "data_analytics": [
        "data analyst", "business intelligence", "bi analyst", "analytics",
        "data engineer", "data analytics", "reporting analyst", "data specialist"
    ],
    "ai_ml": [
        "data scientist", "machine learning", "ml engineer", "ai engineer",
        "deep learning", "artificial intelligence", "nlp engineer"
    ],
    "devops_cloud": [
        "devops", "cloud engineer", "site reliability", "sre", "platform engineer",
        "infrastructure", "sysadmin", "system administrator", "platform developer"
    ],
    "qa_testing": [
        "qa engineer", "quality assurance", "test engineer", "automation engineer",
        "software tester", "sdet"
    ],
    "database": [
        "database administrator", "dba", "sql developer", "database engineer"
    ],
    "cybersecurity": [
        "cybersecurity", "cyber security", "security analyst", "information security",
        "soc analyst", "security engineer"
    ]
}

# Standard Target Roles and their canonical title aliases
STANDARD_ROLE_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "backend developer": {
        "family": "software_engineering",
        "aliases": [
            "backend developer", "backend engineer", "back-end developer", "back-end engineer",
            "backend software engineer", "backend software developer", "api developer",
            "server-side developer", "server side developer"
        ]
    },
    "software developer": {
        "family": "software_engineering",
        "aliases": [
            "software developer", "software engineer", "sde", "application developer",
            "programmer", "software development engineer", "software programmer"
        ]
    },
    "full stack developer": {
        "family": "software_engineering",
        "aliases": [
            "full stack developer", "full stack engineer", "fullstack developer",
            "fullstack engineer", "full-stack developer", "full-stack engineer",
            "full stack software engineer"
        ]
    },
    "python developer": {
        "family": "software_engineering",
        "aliases": [
            "python developer", "python engineer", "python backend developer",
            "python backend engineer", "python software engineer", "python programmer"
        ]
    },
    "java developer": {
        "family": "software_engineering",
        "aliases": [
            "java developer", "java engineer", "java backend developer",
            "java backend engineer", "java software engineer", "spring boot developer", "java programmer"
        ]
    },
    "frontend developer": {
        "family": "software_engineering",
        "aliases": [
            "frontend developer", "frontend engineer", "front-end developer", "front-end engineer",
            "ui engineer", "web developer", "react developer", "angular developer", "vue developer",
            "ui developer"
        ]
    },
    "mobile developer": {
        "family": "software_engineering",
        "aliases": [
            "mobile developer", "mobile engineer", "android developer", "ios developer",
            "flutter developer", "react native developer"
        ]
    },
    "data analyst": {
        "family": "data_analytics",
        "aliases": [
            "data analyst", "business intelligence analyst", "bi analyst",
            "analytics specialist", "data analytics specialist", "reporting analyst", "data visualization analyst"
        ]
    },
    "data scientist": {
        "family": "ai_ml",
        "aliases": [
            "data scientist", "applied scientist", "machine learning scientist"
        ]
    },
    "ai/ml engineer": {
        "family": "ai_ml",
        "aliases": [
            "ai engineer", "ml engineer", "machine learning engineer", "ai/ml engineer",
            "deep learning engineer", "artificial intelligence engineer", "ai developer", "nlp engineer"
        ]
    },
    "devops engineer": {
        "family": "devops_cloud",
        "aliases": [
            "devops engineer", "cloud engineer", "site reliability engineer", "sre",
            "platform engineer", "infrastructure engineer", "devops", "cloud devops"
        ]
    },
    "cloud engineer": {
        "family": "devops_cloud",
        "aliases": [
            "cloud engineer", "cloud architect", "cloud solutions engineer", "aws engineer", "azure engineer", "gcp engineer"
        ]
    },
    "qa / test engineer": {
        "family": "qa_testing",
        "aliases": [
            "qa engineer", "quality assurance engineer", "test engineer", "automation engineer",
            "software tester", "sdet", "qa automation engineer", "qa analyst", "test automation engineer"
        ]
    },
    "database developer": {
        "family": "database",
        "aliases": [
            "database developer", "database engineer", "database administrator", "dba",
            "sql developer", "database specialist"
        ]
    },
    "cybersecurity analyst": {
        "family": "cybersecurity",
        "aliases": [
            "cybersecurity analyst", "cyber security analyst", "security analyst",
            "information security analyst", "soc analyst", "security engineer", "cybersecurity specialist"
        ]
    }
}


def check_target_role_match(job_title: str, target_role: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if job_title aligns with candidate target_role using word boundaries.
    Returns (is_match, matched_alias_or_role_name).
    Avoids false positives (e.g. Java != JavaScript, C != CSS).
    """
    job_lower = (job_title or "").lower().strip()
    target_clean = target_role.strip().lower()
    if not job_lower or not target_clean:
        return False, None

    # 1. Check known taxonomy aliases
    tax = STANDARD_ROLE_TAXONOMY.get(target_clean)
    if tax:
        for alias in tax["aliases"]:
            pattern = r'(?<![a-zA-Z0-9_])' + re.escape(alias) + r'(?![a-zA-Z0-9_])'
            if re.search(pattern, job_lower):
                return True, alias
    else:
        # 2. Custom target role: direct phrase match with word boundaries
        pattern = r'(?<![a-zA-Z0-9_])' + re.escape(target_clean) + r'(?![a-zA-Z0-9_])'
        if re.search(pattern, job_lower):
            return True, target_clean
        # Multi-word custom role: all non-stop tokens (including short tech keywords like 'c', 'qa', 'ai') must match
        stop_tokens = {"and", "or", "/", "&", "in", "for", "with", "the", "a", "an"}
        words = [w for w in target_clean.split() if w not in stop_tokens]
        if len(words) >= 2 and all(re.search(r'(?<![a-zA-Z0-9_])' + re.escape(w) + r'(?![a-zA-Z0-9_])', job_lower) for w in words):
            return True, target_clean

    return False, None


ENTRY_LEVEL_INDICATORS = [
    "entry level", "entry-level", "junior", "jr.", "jr ", "associate",
    "graduate", "fresher", "intern", "internship", "trainee", "apprentice",
    "2025", "2026", "2027", "campus", "early career"
]

SENIOR_LEADERSHIP_INDICATORS = [
    "director", "vp", "vice president", "head of", "chief", "principal architect",
    "engineering manager", "general manager", "senior director", "managing director"
]

SENIOR_IC_INDICATORS = [
    "senior", "sr.", "sr ", "lead", "architect", "principal", "staff"
]

NON_IT_DOMAINS = [
    "sales", "sales representative", "account executive", "marketing",
    "telemarketing", "real estate", "retail", "cashier", "store associate",
    "customer support representative", "bdr", "sdr", "business development representative",
    "medical billing", "nurse", "phlebotomist"
]


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


# Alias for backward-compatibility
normalize_skill = canonical_skill_name


def contains_skill(text: str, skill: str) -> bool:
    """
    Checks whether a skill appears in text as a distinct word token using boundary matching.
    Prevents false positive substring matches (e.g. 'go' in 'django', 'c' in 'css').
    """
    if not text or not skill:
        return False
    canon = canonical_skill_name(skill)
    # Check canonical name and all synonyms
    variants = SKILL_SYNONYMS.get(canon, {canon})
    text_lower = text.lower()
    for v in variants:
        pattern = r'(?<![a-zA-Z0-9_])' + re.escape(v) + r'(?![a-zA-Z0-9_])'
        if re.search(pattern, text_lower):
            return True
    return False


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
    if profile.parsed_skills and isinstance(profile.parsed_skills, list):
        for s in profile.parsed_skills:
            if isinstance(s, str) and s.strip():
                skills.add(canonical_skill_name(s))

    return skills


def extract_candidate_preferred_roles(profile: Optional[CandidateProfile]) -> List[str]:
    """
    Extracts candidate target/preferred role strings from profile.
    """
    if not profile or not profile.preferred_roles:
        return []
    if isinstance(profile.preferred_roles, list):
        return [str(r).strip() for r in profile.preferred_roles if str(r).strip()]
    if isinstance(profile.preferred_roles, str):
        try:
            parsed = json.loads(profile.preferred_roles)
            if isinstance(parsed, list):
                return [str(r).strip() for r in parsed if str(r).strip()]
        except Exception:
            pass
        return [r.strip() for r in profile.preferred_roles.split(",") if r.strip()]
    return []


def is_entry_level_candidate(profile: Optional[CandidateProfile]) -> bool:
    """
    Returns True if candidate profile indicates entry-level / early-career status.
    """
    if not profile:
        return True
    exp_years = float(profile.experience_years or 0.0)
    level_str = (profile.experience_level or "Entry-Level").lower()
    return exp_years <= 2.0 or any(kw in level_str for kw in ["entry", "junior", "fresher", "intern"])


def compute_job_match(
    profile: Optional[CandidateProfile],
    job: Job
) -> MatchBreakdownResponse:
    """
    Computes a transparent, explainable delta match between a candidate profile and a job record.
    Normalized score from 0 to 100 based on available evidence:
    - Core Skills (up to 50%)
    - Preferred Skills (up to 15%)
    - Role & Domain Alignment (up to 20%)
    - Experience Alignment (up to 15%)
    - Seniority Compatibility & Domain Safeguards
    - Transparent positive and negative explanation factors
    """
    candidate_skills = extract_candidate_skill_names(profile)
    candidate_exp = float(profile.experience_years or 0.0) if profile else 0.0
    req_exp = float(job.experience_years_required or 0.0)
    cand_is_entry = is_entry_level_candidate(profile)

    job_title_lower = (job.title or "").lower()
    job_desc = job.description or ""
    job_desc_lower = job_desc.lower()

    positive_reasons: List[str] = []
    negative_reasons: List[str] = []

    # 1. Delta Skill Breakdown
    matched_skills: List[str] = []
    missing_critical: List[str] = []
    missing_secondary: List[str] = []

    job_required = [s for s in (job.required_skills or []) if isinstance(s, str) and s.strip()]
    job_preferred = [s for s in (job.preferred_skills or []) if isinstance(s, str) and s.strip()]

    # If required_skills is empty but description exists, scan for technical keywords safely
    extracted_job_skills: List[str] = []
    if len(job_required) == 0 and len(job_desc_lower) > 30:
        for canonical, syns in SKILL_SYNONYMS.items():
            for syn in syns:
                # Use word boundaries to prevent false substring matches (e.g. 'go' in 'django')
                if re.search(r'\b' + re.escape(syn) + r'\b', job_desc_lower):
                    extracted_job_skills.append(canonical.title())
                    break

    eval_required = job_required if len(job_required) > 0 else extracted_job_skills

    # Evaluate required skills
    matched_required_count = 0
    for req in eval_required:
        canon = canonical_skill_name(req)
        if canon in candidate_skills:
            matched_skills.append(req)
            matched_required_count += 1
        else:
            missing_critical.append(req)

    # Evaluate preferred skills
    matched_preferred_count = 0
    for pref in job_preferred:
        canon = canonical_skill_name(pref)
        if canon in candidate_skills:
            if pref not in matched_skills:
                matched_skills.append(pref)
            matched_preferred_count += 1
        else:
            missing_secondary.append(pref)

    # 2. Weighted Score Component Calculations
    # Core Skills (up to 50%)
    has_skills_evidence = len(eval_required) > 0
    is_job_vague = not has_skills_evidence and len(job_desc_lower.strip()) < 30

    if has_skills_evidence:
        core_ratio = matched_required_count / len(eval_required)
        core_score = core_ratio * 50.0
        if matched_required_count > 0:
            positive_reasons.append(f"Matched {matched_required_count} core technical requirement(s): {', '.join(matched_skills[:3])}.")
        if len(missing_critical) > 0:
            negative_reasons.append(f"Missing core technical skill(s): {', '.join(missing_critical[:3])}.")
    elif is_job_vague:
        core_ratio = 0.2
        core_score = 10.0
        negative_reasons.append("Job posting has missing or insufficient description and requirements; score is conservative.")
    else:
        # Job has description without explicit skill lists
        core_ratio = 0.5
        core_score = 25.0

    # Preferred Skills (up to 15%)
    if len(job_preferred) > 0:
        pref_ratio = matched_preferred_count / len(job_preferred)
        pref_score = pref_ratio * 15.0
        if matched_preferred_count > 0:
            positive_reasons.append(f"Matched preferred skill(s): {', '.join([p for p in job_preferred if canonical_skill_name(p) in candidate_skills][:2])}.")
    else:
        # Scale with core alignment if job has no separate preferred skills
        pref_ratio = core_ratio
        pref_score = core_ratio * 15.0

    # 3. Role & Domain Relevance (up to 20%)
    preferred_roles = extract_candidate_preferred_roles(profile)
    job_title_lower = (job.title or "").lower().strip()

    if preferred_roles:
        direct_matched_role = None

        for pref in preferred_roles:
            is_match, _ = check_target_role_match(job_title_lower, pref)
            if is_match:
                direct_matched_role = pref
                break

        if direct_matched_role:
            role_score = 20.0
            positive_reasons.append(
                f"Target Role Match: Job aligns with your selected target role '{direct_matched_role}'."
            )
        else:
            # Check for related tech family
            candidate_target_families = set()
            for pref in preferred_roles:
                tax = STANDARD_ROLE_TAXONOMY.get(pref.strip().lower())
                if tax:
                    candidate_target_families.add(tax["family"])
                else:
                    for fam_name, kws in IT_ROLE_FAMILIES.items():
                        if any(re.search(r'\b' + re.escape(kw) + r'\b', pref.lower()) for kw in kws):
                            candidate_target_families.add(fam_name)

            job_it_family = None
            for fam_name, keywords in IT_ROLE_FAMILIES.items():
                if any(re.search(r'\b' + re.escape(kw) + r'\b', job_title_lower) for kw in keywords):
                    job_it_family = fam_name
                    break

            if job_it_family and job_it_family in candidate_target_families:
                role_score = 14.0
                positive_reasons.append(
                    f"Related Role Focus: Role belongs to technical family ({job_it_family.replace('_', ' ').title()}) matching your target engineering focus."
                )
            elif job_it_family:
                role_score = 6.0
                negative_reasons.append(
                    f"Target Role Mismatch: Role is outside your selected target roles ({', '.join(preferred_roles[:2])})."
                )
            elif any(kw in job_title_lower for kw in ["software", "developer", "engineer", "analyst", "technology", "data"]):
                role_score = 5.0
                negative_reasons.append(
                    f"Target Role Mismatch: Role is outside your selected target roles ({', '.join(preferred_roles[:2])})."
                )
            else:
                role_score = 2.0
                negative_reasons.append("Job role does not align with your target career preferences or IT domain.")
    else:
        # Candidate has not specified target roles: preserve 100% baseline behavior
        matched_it_family = None
        for family_name, keywords in IT_ROLE_FAMILIES.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', job_title_lower) for kw in keywords):
                matched_it_family = family_name
                break

        if matched_it_family:
            role_score = 20.0
            positive_reasons.append(f"Role belongs to your target technical domain ({matched_it_family.replace('_', ' ').title()}).")
        elif any(kw in job_title_lower for kw in ["software", "developer", "engineer", "analyst", "technology", "data"]):
            role_score = 15.0
            positive_reasons.append("Technical IT opportunity matching general candidate profile.")
        else:
            role_score = 5.0

    # 4. Experience Alignment (up to 15%)
    meets_exp = candidate_exp >= req_exp
    exp_gap = round(max(0.0, req_exp - candidate_exp), 1)

    if req_exp <= 0.0 or meets_exp:
        exp_score = 15.0
        exp_warning = None
        exp_status = "ELIGIBLE"
        if req_exp > 0:
            positive_reasons.append(f"Meets stated tenure requirement ({candidate_exp} yrs >= {req_exp} yrs).")
    else:
        exp_score = min(15.0, (candidate_exp / max(req_exp, 0.1)) * 15.0)
        exp_warning = (
            f"Requires {req_exp} years of experience; your profile currently reflects "
            f"{candidate_exp} years ({exp_gap} yr difference)."
        )
        exp_status = "GAP_WARNING"
        negative_reasons.append(f"Tenure gap: role requires {req_exp} yrs; your profile reflects {candidate_exp} yrs.")

    # 5. Seniority and Domain Compatibility Adjustments
    is_director_leadership = any(
        re.search(r'\b' + re.escape(term) + r'\b', job_title_lower)
        for term in SENIOR_LEADERSHIP_INDICATORS
    )

    is_senior_ic = any(
        re.search(r'\b' + re.escape(term) + r'\b', job_title_lower)
        for term in SENIOR_IC_INDICATORS
    ) and not is_director_leadership

    is_entry_level_job = any(
        re.search(r'\b' + re.escape(term) + r'\b', job_title_lower)
        for term in ENTRY_LEVEL_INDICATORS
    ) or any(kw in (job.experience_level or "").lower() for kw in ["entry", "junior", "intern", "fresher"])

    # Non-IT Domain Check
    is_non_it = False
    non_it_term = None
    for term in NON_IT_DOMAINS:
        if re.search(r'\b' + re.escape(term) + r'\b', job_title_lower):
            # Ensure it is not a technical title like Salesforce Developer or Marketing Automation Engineer
            if not any(tech in job_title_lower for tech in ["developer", "engineer", "analyst", "architect", "programmer", "data"]):
                is_non_it = True
                non_it_term = term
                break

    penalty = 0.0
    bonus = 0.0

    if is_director_leadership and cand_is_entry:
        penalty += 45.0
        negative_reasons.append("Executive/Director leadership role is incompatible with entry-level candidate profile.")

    if exp_gap >= 4.0:
        penalty += min(15.0, exp_gap * 1.5)
        negative_reasons.append(f"Significant tenure gap ({exp_gap} yrs) substantially reduces role fit.")

    if is_senior_ic and cand_is_entry:
        penalty += 15.0
        negative_reasons.append("Senior/Lead seniority level exceeds typical entry-level profile.")

    if is_non_it:
        penalty += 40.0
        negative_reasons.append(f"Role is in non-IT sales/marketing domain ('{non_it_term}'), outside technical profile.")

    if is_entry_level_job and cand_is_entry:
        bonus += 5.0
        positive_reasons.append("Role is targeted towards entry-level or early-career candidates.")

    # Degree / Education compatibility check
    candidate_edu = (profile.education or "").lower() if profile else ""
    job_edu_req = (job.education_requirement or "").lower()
    if job_edu_req:
        tech_degrees = ["b.tech", "b.e", "bachelor", "degree", "computer science", "information technology", "engineering", "bca", "mca"]
        if any(d in candidate_edu for d in tech_degrees) and any(d in job_edu_req for d in tech_degrees):
            bonus += 3.0
            positive_reasons.append("Educational background satisfies stated degree requirements.")

    # 6. Raw Total Calculation
    raw_total = core_score + pref_score + role_score + exp_score + bonus - penalty

    # Incomplete Job Cap
    if is_job_vague:
        raw_total = min(raw_total, 30.0)

    # Empty Profile Cap
    if not candidate_skills:
        raw_total = min(raw_total, 25.0)
        negative_reasons.append("Profile has no registered technical skills. Add skills to your Profile for personalized scoring.")

    final_score = round(min(100.0, max(0.0, raw_total)), 1)

    # 7. Human-Readable Explanation String
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
    elif not candidate_skills:
        explanation_parts.append("Candidate profile does not list technical skills.")
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

    if penalty > 0:
        explanation_parts.append("Down-ranked due to seniority incompatibility or non-IT domain mismatch.")

    explanation_str = " ".join(explanation_parts)

    # 8. Truthful Resume Advice
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
        job_title=job.title or "Untitled Role",
        company_name=job.company_name or "Unknown Company",
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
        resume_advice=resume_advice,
        positive_reasons=positive_reasons,
        negative_reasons=negative_reasons,
        core_skills_score=round(core_score, 1),
        preferred_skills_score=round(pref_score, 1),
        experience_score=round(exp_score, 1),
        role_score=round(role_score, 1),
        experience_status=exp_status,
        experience_gap_years=exp_gap
    )


# Alias for backwards compatibility with tests / callers
evaluate_job_match = compute_job_match


def rank_active_jobs_for_candidate(
    db: Session,
    profile: Optional[CandidateProfile],
    q: Optional[str] = None,
    location: Optional[str] = None,
    work_mode: Optional[str] = None,
    skill: Optional[str] = None,
    source: Optional[str] = None,
    employment_type: Optional[str] = None,
    is_expired: Optional[bool] = None,
    company_id: Optional[int] = None,
    skip: int = 0,
    limit: Optional[int] = None
) -> JobMatchRankingsResponse:
    """
    Evaluates active jobs against candidate profile, applies multi-criteria filters if provided,
    and returns ranked jobs in descending order of deterministic match score with stable tie-breakers.
    """
    query = select(Job).where(Job.is_active == True)

    if is_expired is not None:
        query = query.where(Job.is_expired == is_expired)

    if q:
        term = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Job.title).like(term),
                func.lower(Job.company_name).like(term),
                func.lower(Job.description).like(term)
            )
        )

    if location:
        query = query.where(func.lower(Job.location).like(f"%{location.strip().lower()}%"))

    if work_mode and work_mode.lower() != "any":
        query = query.where(func.lower(Job.work_mode) == work_mode.strip().lower())

    if skill:
        skill_clean = skill.strip().lower()
        query = query.where(
            or_(
                cast(Job.required_skills, String).ilike(f"%{skill_clean}%"),
                cast(Job.preferred_skills, String).ilike(f"%{skill_clean}%")
            )
        )

    if source and source.lower() != "all":
        s_clean = source.strip().lower()
        if s_clean == "manual":
            query = query.where(
                or_(
                    func.lower(Job.source_platform) == "manual",
                    func.lower(Job.source_platform).like("manual%")
                )
            )
        else:
            query = query.where(func.lower(Job.source_platform) == s_clean)

    if employment_type and employment_type.lower() != "all":
        query = query.where(func.lower(Job.employment_type) == employment_type.strip().lower())

    if company_id:
        query = query.where(Job.company_id == company_id)

    active_jobs = list(db.execute(query).scalars().all())

    candidate_skills = extract_candidate_skill_names(profile)
    has_skills = len(candidate_skills) > 0

    rankings: List[JobMatchRankingItem] = []
    for job in active_jobs:
        match_result = compute_job_match(profile, job)
        job_resp = JobResponse.model_validate(job)
        job_resp.match_score = match_result.match_score
        job_resp.match_summary = match_result.explanation

        rankings.append(
            JobMatchRankingItem(
                job=job_resp,
                match_score=match_result.match_score,
                matched_skills_count=len(match_result.matched_skills),
                missing_critical_skills_count=len(match_result.missing_critical_skills),
                meets_experience=match_result.meets_experience,
                quick_summary=match_result.explanation,
                positive_reasons=match_result.positive_reasons,
                negative_reasons=match_result.negative_reasons
            )
        )

    # Deterministic sorting: match_score DESC, posting_date DESC, job.id DESC
    rankings.sort(
        key=lambda x: (
            -x.match_score,
            -(x.job.posting_date.timestamp() if x.job.posting_date else 0.0),
            -(x.job.id or 0)
        )
    )

    total_count = len(rankings)
    if limit is not None:
        paginated_rankings = rankings[skip:skip + limit]
    elif skip > 0:
        paginated_rankings = rankings[skip:]
    else:
        paginated_rankings = rankings

    summary_msg = None
    target_roles = extract_candidate_preferred_roles(profile)
    if not has_skills and not target_roles:
        summary_msg = "Your profile has no registered technical skills or target roles. Add your preferences in Profile for personalized match scores."
    elif target_roles:
        summary_msg = f"Targeting: {', '.join(target_roles[:3])}"

    return JobMatchRankingsResponse(
        total_jobs_evaluated=total_count,
        rankings=paginated_rankings,
        has_profile_skills=has_skills,
        profile_summary=summary_msg
    )
