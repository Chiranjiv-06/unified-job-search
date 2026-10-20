from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of candidate")
    email: EmailStr = Field(..., description="Valid unique email address")
    password: str = Field(..., min_length=6, max_length=128, description="Secure password")

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
