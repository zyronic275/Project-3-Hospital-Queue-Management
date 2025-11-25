from pydantic import BaseModel
from enum import Enum

class RoleEnum(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    STAFF = "staff"

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: RoleEnum | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    role: RoleEnum

    class Config:
        from_attributes = True