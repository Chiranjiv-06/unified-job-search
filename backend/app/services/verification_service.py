import re
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.company import Company
from app.models.verification import VerificationLog
from app.schemas.verification import VerificationRequest, VerificationResponse

FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "protonmail.com", "icloud.com", "mail.com"
}

SUSPICIOUS_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.me", "wa.me", "forms.gle", "docs.google.com"
}

class VerificationService:
    @staticmethod
    def extract_root_domain(raw_url_or_domain: str) -> str:
        if not raw_url_or_domain:
            return ""
        val = raw_url_or_domain.strip().lower()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = "https://" + val
        try:
            parsed = urlparse(val)
            netloc = parsed.netloc.split(":")[0]
            # Strip leading 'www.'
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return raw_url_or_domain.strip().lower()

    @staticmethod
    def check_dns_resolution(domain: str) -> Tuple[bool, bool]:
        """
        Validates domain syntax and verifies DNS/IP host address resolution.
        Returns (domain_valid, mx_or_host_found).
        """
        if not domain or not re.match(r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$", domain.lower()):
            return False, False

        domain_valid = True
        try:
            # Query standard host address resolution
            socket.gethostbyname(domain)
            return domain_valid, True
        except (socket.gaierror, socket.herror, Exception):
            return domain_valid, False

    @classmethod
    def verify_company_opportunity(
        cls,
        db: Session,
        request: VerificationRequest
    ) -> VerificationResponse:
        company_name = request.company_name.strip()
        scam_flags: List[str] = []
        fraud_score = 15.0

        # 1. Resolve or find Company
        company = db.execute(
            select(Company).where(func.lower(Company.name) == company_name.lower())
        ).scalar_one_or_none()

        if not company:
            company = Company(name=company_name)
            db.add(company)
            db.flush()

        # 2. Analyze recruiter domain
        recruiter_domain = cls.extract_root_domain(request.recruiter_domain or "")
        domain_valid = False
        dns_resolved = False

        if recruiter_domain:
            domain_valid, dns_resolved = cls.check_dns_resolution(recruiter_domain)
            if not domain_valid:
                scam_flags.append(f"Recruiter domain '{recruiter_domain}' has invalid syntax.")
                fraud_score += 25.0
            elif not dns_resolved:
                scam_flags.append(f"Domain '{recruiter_domain}' failed DNS host verification.")
                fraud_score += 30.0
            else:
                fraud_score -= 10.0

            # Check if recruiter is using free public email for corporate role
            if recruiter_domain.lower() in FREE_EMAIL_PROVIDERS:
                scam_flags.append(
                    f"Recruiter is utilizing a generic public email domain (@{recruiter_domain}) rather than an enterprise domain."
                )
                fraud_score += 35.0

        # 3. Analyze Job URL
        official_posting_matched = False
        job_host = ""
        if request.job_url:
            job_host = cls.extract_root_domain(request.job_url)

            # Check for suspicious link shorteners or Google Forms
            if job_host.lower() in SUSPICIOUS_DOMAINS:
                scam_flags.append(
                    f"Job application link points to a generic form or shortener ({job_host}) rather than an official applicant tracking system."
                )
                fraud_score += 40.0

            # Match against recruiter domain or existing company domain
            if recruiter_domain and job_host:
                if recruiter_domain == job_host or job_host.endswith("." + recruiter_domain) or recruiter_domain.endswith("." + job_host):
                    official_posting_matched = True
                    fraud_score -= 20.0
                elif recruiter_domain not in FREE_EMAIL_PROVIDERS:
                    scam_flags.append(
                        f"Mismatch detected between recruiter domain ({recruiter_domain}) and job portal host ({job_host})."
                    )
                    fraud_score += 20.0

            # Update company domain & careers_url if not already set
            if not company.domain and job_host and job_host not in SUSPICIOUS_DOMAINS:
                company.domain = job_host
            if not company.careers_url and request.job_url:
                company.careers_url = request.job_url

        # Normalize fraud score [0, 100]
        final_fraud_score = max(0.0, min(100.0, fraud_score))
        is_verified = (final_fraud_score <= 25.0) and domain_valid and dns_resolved

        # Update company state
        company.is_verified = is_verified
        company.fraud_score = final_fraud_score

        # 4. Save VerificationLog
        now = datetime.now(timezone.utc)
        log = VerificationLog(
            company_id=company.id,
            domain_valid=domain_valid,
            mx_records_found=dns_resolved,
            official_posting_matched=official_posting_matched,
            scam_flags=scam_flags,
            checked_at=now
        )
        db.add(log)
        db.commit()
        db.refresh(company)

        # Generate evidence summary
        if is_verified:
            summary = "Verified official career opportunity. Valid enterprise domain and corroborated host."
        elif final_fraud_score >= 60.0:
            summary = "High risk signals detected. Potential phishing or unverified vacancy."
        else:
            summary = "Partially verified opportunity. Exercise standard caution and confirm on company portal."

        return VerificationResponse(
            company_id=company.id,
            company_name=company.name,
            domain=company.domain or recruiter_domain or None,
            domain_valid=domain_valid,
            mx_records_found=dns_resolved,
            official_posting_matched=official_posting_matched,
            scam_flags=scam_flags,
            fraud_score=final_fraud_score,
            is_verified=is_verified,
            checked_at=now,
            evidence_summary=summary,
            details={
                "job_host": job_host or None,
                "recruiter_domain": recruiter_domain or None,
                "flags_count": len(scam_flags)
            }
        )
