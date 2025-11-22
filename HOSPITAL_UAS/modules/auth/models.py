from sqlalchemy import Column, Integer, String, Enum
from database import Base
import enum

class RoleEnum(str, enum.Enum):
ADMIN = "admin"
DOCTOR = "doctor"
STAFF = "staff"

class User(Base):
__tablename__ = "users"
id = Column(Integer, primary_key=True, index=True)
username = Column(String(50), unique=True, index=True, nullable=False)
hashed_password = Column(String(255), nullable=False)
role = Column(Enum(RoleEnum), default=RoleEnum.STAFF)
full_name = Column(String(100))