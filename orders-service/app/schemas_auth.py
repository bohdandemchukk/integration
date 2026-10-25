from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")   # жодних is_active/is_admin з вводу
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        if not (1 <= len(v) <= 64):
            raise ValueError("username must be 1-64 characters")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        n = len(v.encode("utf-8"))
        if not (8 <= n <= 72):
            raise ValueError("password must be 8-72 bytes")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"