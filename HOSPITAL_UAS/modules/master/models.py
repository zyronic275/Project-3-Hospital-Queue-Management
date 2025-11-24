from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Time, Enum
from sqlalchemy.orm import relationship
from ..database import Base
import enum 

# Enum untuk batasan jenis kelamin
class GenderRestriction(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    NONE = "NONE" # Bebas

# Model Service
class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    prefix = Column(String(4), unique=True, nullable=False)
    
    min_age = Column(Integer, default=0, nullable=False)
    max_age = Column(Integer, default=100, nullable=False)
    
    gender_restriction = Column(Enum(GenderRestriction), default=GenderRestriction.NONE, nullable=False) 
    
    is_active = Column(Boolean, default=True)

    doctors = relationship("Doctor", back_populates="service")


# Model Doctor
class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String(100), nullable=False)
    
    doctor_code = Column(Integer, nullable=False, unique=True, index=True) 
    max_patients = Column(Integer, default=50) 
    
    practice_start_time = Column(Time, nullable=False)
    practice_end_time = Column(Time, nullable=False)
    
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    
    is_active = Column(Boolean, default=True)

    service = relationship("Service", back_populates="doctors")
    visits = relationship("modules.queue.models.Visit", back_populates="doctor")