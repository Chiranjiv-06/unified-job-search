from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.verification import VerificationRequest, VerificationResponse
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verify", tags=["Verification"])

@router.post("", response_model=VerificationResponse, status_code=status.HTTP_200_OK)
def verify_opportunity(
    request: VerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes an employment opportunity, recruiter domain, and job URL.
    Computes a fraud risk score, checks DNS validity, official posting match,
    and logs verification audit evidence.
    """
    return VerificationService.verify_company_opportunity(
        db=db,
        request=request
    )
