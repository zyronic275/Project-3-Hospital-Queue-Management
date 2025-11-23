from sqlalchemy import Column, Integer, String, Enum
from database import Base
import enum

class RoleEnum(str, enum.Enum):
ADMIN = &quot;admin&quot;
DOCTOR = &quot;doctor&quot;
STAFF = &quot;staff&quot;

class User(Base):
__tablename__ = &quot;users&quot;
id = Column(Integer, primary_key=True, index=True)

username = Column(String(50), unique=True, index=True, nullable=False)
hashed_password = Column(String(255), nullable=False)
role = Column(Enum(RoleEnum), default=RoleEnum.STAFF)
full_name = Column(String(100))