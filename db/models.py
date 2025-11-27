from sqlalchemy import Column, Integer, String, Date, ForeignKey, Boolean, Text, Enum, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

#enumeration untuk status visit
class VisitStatus(str, enum.Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())

    doctors = relationship("Doctor", back_populates="clinic")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialization = Column(String(100))
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=True)

    clinic = relationship("Clinic", back_populates="doctors")
    visits = relationship("Visit", back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer)
    gender = Column(String(10))
    nik = Column(String(16), unique=True, nullable=False)
    phone = Column(String(20))
    dob = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())

    visits = relationship("Visit", back_populates="patient")

class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    date_visit = Column(Date, nullable=False)
    queue_number = Column(Integer, nullable=False)
    status = Column(Enum(VisitStatus), default=VisitStatus.waiting)
    medical_notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    patient = relationship("Patient", back_populates="visits")
    doctor = relationship("Doctor", back_populates="visits")