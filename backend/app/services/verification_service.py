import re
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

import dns.resolver

from app.models.company import Company
from app.models.verification import VerificationLog
from app.models.job import Job
from app.schemas.verification import (
    VerificationRequest,
    VerificationResponse,
    JobVerificationResponse
)

FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "protonmail.com", "proton.me", "icloud.com",
    "mail.com", "zoho.com", "yandex.com", "gmx.com", "tempmail.com"
}

SUSPICIOUS_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.me", "wa.me", "forms.gle", "docs.google.com",
    "shorturl.at", "cutt.ly", "is.gd", "rb.gy"
}

KNOWN_ATS_DOMAINS = {
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "smartrecruiters.com",
    "ashbyhq.com", "jobvite.com", "taleo.net", "bamboohr.com",
    "workable.com", "applytojob.com", "recruitee.com", "rippling-ats.com",
    "icims.com", "brassring.com", "workday.com", "successfactors.com"
}

SCAM_PAYMENT_PATTERNS = [
    (re.compile(r"\bsecurity deposit\b", re.IGNORECASE), "security deposit"),
    (re.compile(r"\bapplication fee\b", re.IGNORECASE), "application fee"),
    (re.compile(r"\bregistration fee\b", re.IGNORECASE), "registration fee"),
    (re.compile(r"\bprocessing fee\b", re.IGNORECASE), "processing fee"),
    (re.compile(r"\btraining fee\b", re.IGNORECASE), "training fee"),
    (re.compile(r"\blaptop fee\b", re.IGNORECASE), "laptop fee"),
    (re.compile(r"\blaptop charge\b", re.IGNORECASE), "laptop charge"),
    (re.compile(r"\bequipment fee\b", re.IGNORECASE), "equipment fee"),
    (re.compile(r"\bpay for equipment\b", re.IGNORECASE), "pay for equipment"),
    (re.compile(r"\bbuy equipment\b", re.IGNORECASE), "buy equipment"),
    (re.compile(r"\bpurchase equipment\b", re.IGNORECASE), "purchase equipment"),
    (re.compile(r"\bpay for training\b", re.IGNORECASE), "pay for training"),
    (re.compile(r"\bbackground check fee\b", re.IGNORECASE), "background check fee"),
    (re.compile(r"\bwire transfer\b", re.IGNORECASE), "wire transfer"),
    (re.compile(r"\bcryptocurrency\b", re.IGNORECASE), "cryptocurrency"),
    (re.compile(r"\bcrypto payment\b", re.IGNORECASE), "crypto payment"),
    (re.compile(r"\bgift card\b", re.IGNORECASE), "gift card"),
    (re.compile(r"\bwestern union\b", re.IGNORECASE), "western union"),
    (re.compile(r"\bmoneygram\b", re.IGNORECASE), "moneygram"),
]

MESSAGING_INTERVIEW_PATTERNS = [
    (re.compile(r"\binterview.*via (telegram|whatsapp|signal|google hangouts?)\b", re.IGNORECASE), "messaging app interview"),
    (re.compile(r"\b(telegram|whatsapp|signal) interview\b", re.IGNORECASE), "messaging app interview"),
    (re.compile(r"\bcontact.*on (telegram|whatsapp|signal)\b", re.IGNORECASE), "messaging app contact"),
    (re.compile(r"\b(t\.me/|wa\.me/)\b", re.IGNORECASE), "direct chat link"),
    (re.compile(r"\btelegram\b", re.IGNORECASE), "telegram reference"),
    (re.compile(r"\bwhatsapp\b", re.IGNORECASE), "whatsapp reference"),
]


class VerificationService:
    @staticmethod
    def extract_root_domain(raw_url_or_domain: str) -> str:
        if not raw_url_or_domain:
            return ""
        val = raw_url_or_domain.strip().lower()
        if "@" in val:
            val = val.split("@")[-1].strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = "https://" + val
        try:
            parsed = urlparse(val)
            netloc = parsed.netloc.split(":")[0]
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return val


    @staticmethod
    def check_dns_resolution(domain: str) -> Tuple[bool, bool]:
        """
        Validates domain syntax and verifies DNS/IP host address resolution.
        Returns (domain_valid, host_resolved).
        """
        if not domain or not re.match(r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$", domain.lower()):
            return False, False

        domain_valid = True
        try:
            socket.gethostbyname(domain)
            return domain_valid, True
        except (socket.gaierror, socket.herror, Exception):
            return domain_valid, False

    @staticmethod
    def check_mx_records(domain: str) -> bool:
        """
        Checks whether active Mail Exchange (MX) DNS records exist for the domain.
        Uses public fallback DNS with a strict timeout.
        """
        if not domain:
            return False
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
            resolver.timeout = 1.5
            resolver.lifetime = 1.5
            answers = resolver.resolve(domain, "MX")
            return len(answers) > 0
        except Exception:
            return False

    @classmethod
    def scan_scam_heuristics(cls, text: str) -> Tuple[List[str], List[str], float]:
        """
        Scans job text or description for known fraud signals, payment requests,
        and unofficial interview channels.
        Returns (scam_flags, evidence_points, risk_penalty).
        """
        scam_flags: List[str] = []
        evidence_points: List[str] = []
        penalty = 0.0

        if not text:
            evidence_points.append("ℹ️ Job description not provided; automated text heuristics bypassed.")
            return scam_flags, evidence_points, penalty

        # 1. Payment / deposit demands
        payment_detected = False
        for pattern, label in SCAM_PAYMENT_PATTERNS:
            if pattern.search(text):
                payment_detected = True
                flag_msg = (
                    f"Payment/Deposit Request Detected: Job text mentions '{label}'. "
                    f"Legitimate corporate employers never demand upfront fees, equipment charges, or security deposits."
                )
                if flag_msg not in scam_flags:
                    scam_flags.append(flag_msg)
                evidence_points.append(f"🚨 CRITICAL ALERT: Upfront payment or fee requirement detected ('{label}')")
                penalty += 50.0
                break

        # 2. Messaging app interview channel
        messaging_detected = False
        for pattern, label in MESSAGING_INTERVIEW_PATTERNS:
            if pattern.search(text):
                messaging_detected = True
                flag_msg = (
                    f"Unofficial Communication Channel: Job references interviewing or contacting via messaging apps ({label}). "
                    f"Enterprise recruiting is conducted through corporate email and verified video conferencing."
                )
                if flag_msg not in scam_flags:
                    scam_flags.append(flag_msg)
                evidence_points.append(f"⚠️ WARNING: Unofficial interview/contact channel referenced ('{label}')")
                penalty += 35.0
                break

        if not payment_detected and not messaging_detected:
            evidence_points.append("✓ Description Clean: No upfront fee demands or unofficial chat recruitment detected")

        return scam_flags, evidence_points, penalty

    @classmethod
    def audit_job_legitimacy(
        cls,
        db: Session,
        job: Job,
        recruiter_email_or_domain: Optional[str] = None
    ) -> JobVerificationResponse:
        """
        Executes a comprehensive, evidence-based verification audit on a Job record.
        Inspects company identity, domain MX records, official ATS matching, and scam heuristics.
        Persists a VerificationLog in PostgreSQL and updates Company fraud status.
        """
        company_name = (job.company_name or "Unknown Company").strip()
        scam_flags: List[str] = []
        evidence_points: List[str] = []
        risk_score = 15.0  # Base neutral score

        # 1. Find or create Company record
        company = None
        if job.company_id:
            company = db.execute(select(Company).where(Company.id == job.company_id)).scalar_one_or_none()
        if not company:
            company = db.execute(
                select(Company).where(func.lower(Company.name) == company_name.lower())
            ).scalar_one_or_none()

        if not company:
            company = Company(name=company_name)
            db.add(company)
            db.flush()

        if not job.company_id:
            job.company_id = company.id

        # 2. Determine target domain to audit
        target_domain = ""
        recruiter_domain = ""
        if recruiter_email_or_domain:
            recruiter_domain = cls.extract_root_domain(recruiter_email_or_domain)
            target_domain = recruiter_domain
        elif company.domain:
            target_domain = cls.extract_root_domain(company.domain)
        elif job.source_url:
            target_domain = cls.extract_root_domain(job.source_url)

        domain_valid = False
        dns_resolved = False
        mx_records_found = False

        if target_domain:
            domain_valid, dns_resolved = cls.check_dns_resolution(target_domain)
            if not domain_valid:
                scam_flags.append(f"Domain '{target_domain}' has invalid syntax.")
                evidence_points.append(f"⚠️ Target domain '{target_domain}' has invalid syntax")
                risk_score += 25.0
            elif not dns_resolved:
                scam_flags.append(f"Domain '{target_domain}' failed DNS host verification.")
                evidence_points.append(f"⚠️ Domain '{target_domain}' failed DNS host resolution")
                risk_score += 30.0
            else:
                # Check if domain is free public email or suspicious
                if target_domain.lower() in FREE_EMAIL_PROVIDERS:
                    flag = (
                        f"Recruiter is utilizing a generic public email domain (@{target_domain}) rather than an enterprise domain."
                    )
                    scam_flags.append(flag)
                    evidence_points.append(f"⚠️ WARNING: Free/disposable email provider (@{target_domain}) used for hiring")
                    risk_score += 35.0
                elif target_domain.lower() in SUSPICIOUS_DOMAINS:
                    # Do not deduct score for suspicious shorteners
                    pass
                else:
                    mx_records_found = cls.check_mx_records(target_domain)
                    if mx_records_found:
                        evidence_points.append(f"✓ Valid Corporate MX Records Active ({target_domain})")
                        risk_score -= 15.0
                    else:
                        evidence_points.append(f"✓ Host Resolved; MX mail exchange status unconfirmed ({target_domain})")
                        risk_score -= 5.0
        else:
            evidence_points.append("ℹ️ No specific corporate domain provided for DNS/MX inspection")

        # 3. Analyze Job Source URL & ATS Corroboration
        official_posting_matched = False
        job_host = ""
        if job.source_url:
            job_host = cls.extract_root_domain(job.source_url)

            if job_host.lower() in SUSPICIOUS_DOMAINS:
                scam_flags.append(
                    f"Job application link points to a generic form or shortener ({job_host}) rather than an official applicant tracking system."
                )
                evidence_points.append(f"⚠️ WARNING: Job link uses generic shortener or public form ({job_host})")
                risk_score += 40.0
            else:
                # Check for known official ATS
                is_known_ats = any(
                    job_host == ats or job_host.endswith("." + ats)
                    for ats in KNOWN_ATS_DOMAINS
                )
                if is_known_ats:
                    official_posting_matched = True
                    evidence_points.append(f"✓ Official Applicant Tracking System (ATS) Corroborated ({job_host})")
                    risk_score -= 20.0
                elif target_domain and (
                    job_host == target_domain or
                    job_host.endswith("." + target_domain) or
                    target_domain.endswith("." + job_host)
                ):
                    official_posting_matched = True
                    evidence_points.append(f"✓ Official Company Careers Portal Matched ({job_host})")
                    risk_score -= 20.0
                elif target_domain and target_domain not in FREE_EMAIL_PROVIDERS:
                    evidence_points.append(f"ℹ️ Job host ({job_host}) differs from recruiter/company domain ({target_domain})")

            # Update company domain and careers url if unset
            if not company.domain and job_host and job_host not in SUSPICIOUS_DOMAINS and not any(job_host.endswith(ats) for ats in KNOWN_ATS_DOMAINS):
                company.domain = job_host
            if not company.careers_url and job.source_url:
                company.careers_url = job.source_url
        else:
            evidence_points.append("ℹ️ Direct job posting URL not provided; external ATS matching skipped")

        # 4. Analyze Description Scam Heuristics
        desc_flags, desc_points, desc_penalty = cls.scan_scam_heuristics(job.description or "")
        scam_flags.extend(desc_flags)
        evidence_points.extend(desc_points)
        risk_score += desc_penalty

        # 5. Normalize Risk Score & Determine Risk Level
        final_risk_score = round(max(0.0, min(100.0, risk_score)), 1)

        if final_risk_score <= 25.0:
            risk_level = "LOW_RISK"
            is_verified = (len(scam_flags) == 0) and (domain_valid or official_posting_matched)
            summary = "Low risk profile. Verified corporate domain or official ATS listing with clean requirements."
        elif final_risk_score <= 50.0:
            risk_level = "CAUTION"
            is_verified = False
            summary = "Moderate caution advised. Partial signals confirmed; lacks full corporate ATS corroboration."
        elif final_risk_score < 75.0:
            risk_level = "HIGH_RISK"
            is_verified = False
            summary = "High risk signals detected. Potential phishing, unverified email channel, or mismatch."
        else:
            risk_level = "CRITICAL_RISK"
            is_verified = False
            summary = "CRITICAL ALERT: Active scam patterns (upfront fee, wire transfer, or suspicious chat recruitment) detected."

        # 6. Update Company Model
        company.is_verified = is_verified
        company.fraud_score = final_risk_score

        # 7. Persist VerificationLog
        now = datetime.now(timezone.utc)
        log = VerificationLog(
            company_id=company.id,
            domain_valid=domain_valid,
            mx_records_found=(mx_records_found or dns_resolved),
            official_posting_matched=official_posting_matched,
            scam_flags=scam_flags,
            checked_at=now
        )
        db.add(log)
        db.commit()
        db.refresh(company)

        return JobVerificationResponse(
            job_id=job.id,
            company_id=company.id,
            company_name=company.name,
            domain=company.domain or target_domain or None,
            domain_valid=domain_valid,
            mx_records_found=(mx_records_found or dns_resolved),
            official_posting_matched=official_posting_matched,
            scam_flags=scam_flags,
            fraud_score=final_risk_score,
            risk_score=final_risk_score,
            risk_level=risk_level,
            evidence_points=evidence_points,
            is_verified=is_verified,
            checked_at=now,
            evidence_summary=summary,
            details={
                "job_host": job_host or None,
                "target_domain": target_domain or None,
                "recruiter_domain": recruiter_domain or None,
                "risk_tier": risk_level,
                "flags_count": len(scam_flags)
            }
        )

    @classmethod
    def get_latest_job_verification(cls, db: Session, job: Job) -> JobVerificationResponse:
        """
        Retrieves the latest verification audit for a job or executes a fresh audit if none exists.
        """
        # Always run a fresh audit to ensure the latest job description and requirements are evaluated
        return cls.audit_job_legitimacy(db=db, job=job)

    @classmethod
    def verify_company_opportunity(
        cls,
        db: Session,
        request: VerificationRequest
    ) -> VerificationResponse:
        """
        Legacy endpoint support for /api/v1/verify.
        """
        company_name = request.company_name.strip()
        scam_flags: List[str] = []
        fraud_score = 15.0

        company = db.execute(
            select(Company).where(func.lower(Company.name) == company_name.lower())
        ).scalar_one_or_none()

        if not company:
            company = Company(name=company_name)
            db.add(company)
            db.flush()

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

            if recruiter_domain.lower() in FREE_EMAIL_PROVIDERS:
                scam_flags.append(
                    f"Recruiter is utilizing a generic public email domain (@{recruiter_domain}) rather than an enterprise domain."
                )
                fraud_score += 35.0

        official_posting_matched = False
        job_host = ""
        if request.job_url:
            job_host = cls.extract_root_domain(request.job_url)

            if job_host.lower() in SUSPICIOUS_DOMAINS:
                scam_flags.append(
                    f"Job application link points to a generic form or shortener ({job_host}) rather than an official applicant tracking system."
                )
                fraud_score += 40.0

            if recruiter_domain and job_host:
                if recruiter_domain == job_host or job_host.endswith("." + recruiter_domain) or recruiter_domain.endswith("." + job_host):
                    official_posting_matched = True
                    fraud_score -= 20.0
                elif recruiter_domain not in FREE_EMAIL_PROVIDERS:
                    scam_flags.append(
                        f"Mismatch detected between recruiter domain ({recruiter_domain}) and job portal host ({job_host})."
                    )
                    fraud_score += 20.0

            if not company.domain and job_host and job_host not in SUSPICIOUS_DOMAINS:
                company.domain = job_host
            if not company.careers_url and request.job_url:
                company.careers_url = request.job_url

        final_fraud_score = max(0.0, min(100.0, fraud_score))
        is_verified = (final_fraud_score <= 25.0) and domain_valid and dns_resolved

        company.is_verified = is_verified
        company.fraud_score = final_fraud_score

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
            risk_score=final_fraud_score,
            risk_level="LOW_RISK" if final_fraud_score <= 25.0 else "CAUTION" if final_fraud_score <= 50.0 else "HIGH_RISK",
            evidence_points=[summary] + scam_flags,
            is_verified=is_verified,
            checked_at=now,
            evidence_summary=summary,
            details={
                "job_host": job_host or None,
                "recruiter_domain": recruiter_domain or None,
                "flags_count": len(scam_flags)
            }
        )
