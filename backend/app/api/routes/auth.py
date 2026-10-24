from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.profile import CandidateProfile
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.rate_limiter import rate_limit
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", max_requests=20, window_seconds=60))]
)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new user account and initializes an empty candidate profile.
    Rejects duplicate email addresses.
    """
    normalized_email = user_in.email.strip().lower()
    
    # Check if email is already registered
    existing_user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Create new user
    hashed_pwd = hash_password(user_in.password)
    user = User(
        full_name=user_in.full_name.strip(),
        email=normalized_email,
        hashed_password=hashed_pwd,
        is_active=True
    )
    db.add(user)
    db.flush() # Flush to obtain user.id

    # Automatically initialize candidate profile
    profile = CandidateProfile(
        user_id=user.id,
        experience_level="Entry-Level",
        preferred_work_mode="Any"
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    return user

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("login", max_requests=20, window_seconds=60))]
)
def login(login_in: UserLogin, response: Response, db: Session = Depends(get_db)):
    """
    Authenticates user credentials and issues a secure JWT access token.
    Sets HttpOnly cookie for session persistence and returns bearer token.
    """
    normalized_email = login_in.email.strip().lower()
    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()

    # Generic error message to prevent account enumeration
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support."
        )

    # Issue JWT token
    access_token = create_access_token(data={"sub": user.email, "uid": user.id})

    # Set secure HttpOnly cookie
    is_prod = settings.ENVIRONMENT.lower() == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        samesite="lax",
        secure=is_prod
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile info.
    """
    return current_user

@router.post("/logout")
def logout(response: Response):
    """
    Clears the HttpOnly access_token cookie.
    """
    is_prod = settings.ENVIRONMENT.lower() == "production"
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=is_prod
    )
    return {"message": "Logged out successfully"}
