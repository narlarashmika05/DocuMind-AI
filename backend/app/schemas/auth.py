from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.common import FullName, Password
from app.schemas.user import UserOut


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: FullName
    password: Password

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserOut
