# hospital_api/models.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import enum

# Define an Enum for the queue status
class QueueStatus(str, enum.Enum):
    MENUNGGU = "menunggu"
    DILAYANI = "sedang dilayani"
    SELESAI = "selesai"

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    
    doctors = relationship("Doctor", back_populates="clinic")
    queues = relationship("Queue", back_populates="clinic")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    specialization = Column(String)
    clinic_id = Column(Integer, ForeignKey("clinics.id"))

    clinic = relationship("Clinic", back_populates="doctors")
    queues = relationship("Queue", back_populates="doctor")
    
class Queue(Base):
    __tablename__ = "queues"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String, index=True)
    queue_number = Column(Integer)
    status = Column(Enum(QueueStatus), default=QueueStatus.MENUNGGU)
    registration_time = Column(DateTime, default=datetime.datetime.utcnow)
    
    clinic_id = Column(Integer, ForeignKey("clinics.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))

    clinic = relationship("Clinic", back_populates="queues")
    doctor = relationship("Doctor", back_populates="queues")