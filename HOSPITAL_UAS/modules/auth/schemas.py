from pydantic import BaseModel
from enum import Enum

# Role Enum (gunakan string bukan enum.Enum jika butuh serialisasi lebih mudah)
class RoleEnum(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    STAFF = "staff"

# Schema untuk input register
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: RoleEnum | None = None

# Schema untuk response
class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    role: RoleEnum

    class Config:
        from_attributes = True