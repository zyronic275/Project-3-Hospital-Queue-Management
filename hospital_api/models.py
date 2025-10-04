# hospital_api/models.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from .database import Base
import datetime

# Tabel perantara untuk hubungan Many-to-Many antara Dokter dan Layanan
doctor_service_association = Table('doctor_service', Base.metadata,
    Column('doctor_id', Integer, ForeignKey('doctors.id')),
    Column('service_id', Integer, ForeignKey('services.id'))
)

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True) # Nama pasien unik
    
    queues = relationship("Queue", back_populates="patient")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Nama layanan/penyakit (e.g., "Poli Gigi", "Pemeriksaan Mata")
    
    doctors = relationship("Doctor", secondary=doctor_service_association, back_populates="services")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    
    services = relationship("Service", secondary=doctor_service_association, back_populates="doctors")
    queues = relationship("Queue", back_populates="doctor")

class Queue(Base):
    __tablename__ = "queues"
    id = Column(Integer, primary_key=True, index=True)
    queue_number = Column(Integer)
    registration_time = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient_id = Column(Integer, ForeignKey("patients.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id")) # Dokter yang ditugaskan oleh sistem

    patient = relationship("Patient", back_populates="queues")
    service = relationship("Service", back_populates="queues") # Single service per queue entry
    doctor = relationship("Doctor", back_populates="queues")

# Tambahan: Hubungan Service ke Queue
Service.queues = relationship("Queue", back_populates="service")