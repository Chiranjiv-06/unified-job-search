import io
import re
import logging
from typing import List, Tuple, Set
import pypdf
from fastapi import UploadFile, HTTPException, status

logger = logging.getLogger(__name__)

MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Canonical Tech Skill taxonomy mapped with regex patterns for accurate boundary matching
SKILL_PATTERNS = {
    # Programming Languages
    "Python": r"\bpython\b",
    "JavaScript": r"\bjavascript\b|\bjs\b",
    "TypeScript": r"\btypescript\b|\bts\b",
    "Java": r"\bjava\b(?!script)",
    "C++": r"\bc\+\+\b",
    "C#": r"\bc#\b|\bcsharp\b",
    "Go": r"\bgolang\b|\bgo\s+language\b|\bgo\b(?!\s+(to|on|ahead|through|into))",
    "Rust": r"\brust\b",
    "Ruby": r"\bruby\b",
    "PHP": r"\bphp\b",
    "Swift": r"\bswift\b",
    "Kotlin": r"\bkotlin\b",
    "SQL": r"\bsql\b",
    "HTML": r"\bhtml5?\b",
    "CSS": r"\bcss3?\b",
    "Shell/Bash": r"\bbash\b|\bshell\s+scripting\b",

    # Frontend Frameworks & Libraries
    "React": r"\breact(?:\.js)?\b",
    "Next.js": r"\bnext(?:\.js)?\b",
    "Vue.js": r"\bvue(?:\.js)?\b",
    "Angular": r"\bangular(?:\.js)?\b",
    "Svelte": r"\bsvelte\b",
    "Tailwind CSS": r"\btailwind(?:\s*css)?\b",
    "Bootstrap": r"\bbootstrap\b",
    "Redux": r"\bredux\b",
    "Vite": r"\bvite\b",

    # Backend Frameworks
    "FastAPI": r"\bfastapi\b",
    "Django": r"\bdjango\b",
    "Flask": r"\bflask\b",
    "Node.js": r"\bnode(?:\.js)?\b",
    "Express.js": r"\bexpress(?:\.js)?\b",
    "NestJS": r"\bnest(?:\.js)?\b",
    "Spring Boot": r"\bspring\s*boot\b",
    "ASP.NET": r"\basp\.net\b|\b\.net\s*core\b",

    # Databases & Cache
    "PostgreSQL": r"\bpostgres(?:ql)?\b",
    "MySQL": r"\bmysql\b",
    "MongoDB": r"\bmongodb?\b",
    "Redis": r"\bredis\b",
    "SQLite": r"\bsqlite\b",
    "Elasticsearch": r"\belasticsearch\b",
    "Cassandra": r"\bcassandra\b",

    # Cloud & DevOps
    "AWS": r"\baws\b|\bamazon\s+web\s+services\b",
    "Azure": r"\bazure\b",
    "Google Cloud": r"\bgcp\b|\bgoogle\s+cloud\b",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "CI/CD": r"\bci\s*/\s*cd\b|\bcontinuous\s+integration\b",
    "GitHub Actions": r"\bgithub\s+actions\b",
    "Linux": r"\blinux\b",
    "Nginx": r"\bnginx\b",
    "Terraform": r"\bterraform\b",

    # Data, Messaging & Architecture
    "GraphQL": r"\bgraphql\b",
    "REST API": r"\brest(?:ful)?(?:\s+api)?\b",
    "Microservices": r"\bmicroservices?\b",
    "Celery": r"\bcelery\b",
    "RabbitMQ": r"\brabbitmq\b",
    "Kafka": r"\bkafka\b",
    "Pandas": r"\bpandas\b",
    "NumPy": r"\bnumpy\b",
    "PyTorch": r"\bpytorch\b",
    "TensorFlow": r"\btensorflow\b",
    "Scikit-Learn": r"\bscikit-learn\b|\bsklearn\b",

    # Testing & Tooling
    "Git": r"\bgit\b",
    "GitHub": r"\bgithub\b",
    "Pytest": r"\bpytest\b",
    "Jest": r"\bjest\b",
    "Postman": r"\bpostman\b"
}


def validate_resume_upload(file: UploadFile, contents: bytes) -> None:
    """
    Validates resume file size and MIME type.
    Enforces <= 5MB limit and application/pdf type.
    """
    if len(contents) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of 5MB ({len(contents)} bytes received)."
        )

    # Validate filename extension
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF documents (.pdf) are supported."
        )

    # Validate Content-Type header if provided
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ["application/pdf", "application/x-pdf", "binary/octet-stream"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{file.content_type}'. Expected 'application/pdf'."
        )

    # Validate PDF magic bytes header (%PDF-)
    if len(contents) < 4 or not contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid PDF file header."
        )


def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, int]:
    """
    Safely extracts plain text from PDF pages using pypdf.
    Handles empty, unreadable, or scanned pages without raising unhandled exceptions.
    Returns (extracted_text, page_count).
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        page_count = len(reader.pages)
        extracted_pages: List[str] = []

        for idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text.strip())
            except Exception as page_exc:
                logger.warning("Failed to extract text from page %d: %s", idx + 1, page_exc)

        full_text = "\n\n".join(extracted_pages).strip()
        return full_text, page_count
    except pypdf.errors.PdfReadError as read_err:
        logger.error("pypdf read error: %s", read_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to parse PDF content. The file might be corrupted or password-protected."
        )
    except Exception as exc:
        logger.error("Unexpected error reading PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the provided PDF file."
        )


def extract_skills_from_text(text: str) -> List[str]:
    """
    Heuristic rule-based skill extraction from raw text using boundary-checked regex patterns.
    Returns a sorted list of unique identified skill names.
    """
    if not text:
        return []

    matched_skills: Set[str] = set()
    lowered_text = text.lower()

    for skill_name, pattern in SKILL_PATTERNS.items():
        if re.search(pattern, lowered_text, re.IGNORECASE):
            matched_skills.add(skill_name)

    return sorted(list(matched_skills))
