from pydantic import BaseModel, ConfigDict

from app.schemas.common import FullName, Language, Password, UTCDateTime


class UserOut(BaseModel):
    """Public view of a user. hashed_password is deliberately absent."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    preferred_language: Language
    created_at: UTCDateTime


class UserUpdate(BaseModel):
    full_name: FullName | None = None
    preferred_language: Language | None = None


class AccountDelete(BaseModel):
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: Password
