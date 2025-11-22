from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class VisitStatus(str, enum.Enum):
REGISTERED = "REGISTERED"
CHECKIN = "CHECKIN"
TRIAGE = "TRIAGE"
IN_CLINIC = "IN_CLINIC"
IN_SERVICE = "IN_SERVICE"
COMPLETED = "COMPLETED"
CANCELLED = "CANCELLED"

class Patient(Base):
__tablename__ = "patients"
id = Column(Integer, primary_key=True, index=True)
patient_name = Column(String(100), nullable=False)
email = Column(String(100))
date_of_birth = Column(DateTime)
gender = Column(String(10)) # Bisa pakai Enum juga
age = Column(Integer)
insurance = Column(String(50))
created_at = Column(DateTime(timezone=True), server_default=func.now())
visits = relationship("Visit", back_populates="patient")

class Visit(Base):
__tablename__ = "visits"
id = Column(Integer, primary_key=True, index=True)
patient_id = Column(Integer, ForeignKey("patients.id"))
doctor_id = Column(Integer, ForeignKey("doctors.id"))

# 6 KOLOM WAKTU (SYARAT UAS)
registration_time = Column(DateTime)
checkin_time = Column(DateTime)
triage_time = Column(DateTime)
clinic_entry_time = Column(DateTime)
doctor_call_time = Column(DateTime)
completion_time = Column(DateTime)

status = Column(Enum(VisitStatus), default=VisitStatus.REGISTERED)

patient = relationship("PaƟent", back_populates="visits")
doctor = relationship("modules.master.models.Doctor", back_populates="visits")