from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relaƟonship
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

class PaƟent(Base):
__tablename__ = "paƟents"
id = Column(Integer, primary_key=True, index=True)
paƟent_name = Column(String(100), nullable=False)
email = Column(String(100))
date_of_birth = Column(DateTime)
gender = Column(String(10)) # Bisa pakai Enum juga
age = Column(Integer)
insurance = Column(String(50))
created_at = Column(DateTime(Ɵmezone=True), server_default=func.now())
visits = relaƟonship("Visit", back_populates="paƟent")

class Visit(Base):
__tablename__ = "visits"
id = Column(Integer, primary_key=True, index=True)
paƟent_id = Column(Integer, ForeignKey("paƟents.id"))
doctor_id = Column(Integer, ForeignKey("doctors.id"))

# 6 KOLOM WAKTU (SYARAT UAS)
registraƟon_Ɵme = Column(DateTime)
checkin_Ɵme = Column(DateTime)
triage_Ɵme = Column(DateTime)
clinic_entry_Ɵme = Column(DateTime)
doctor_call_Ɵme = Column(DateTime)
compleƟon_Ɵme = Column(DateTime)

status = Column(Enum(VisitStatus), default=VisitStatus.REGISTERED)

paƟent = relaƟonship("PaƟent", back_populates="visits")
doctor = relaƟonship("modules.master.models.Doctor", back_populates="visits")