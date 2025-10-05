import datetime
import enum
from sqlalchemy import (Column, Integer, String, ForeignKey, DateTime, Time, 
                        Text, Enum as SQLAlchemyEnum, Table)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Tabel perantara untuk hubungan Many-to-Many antara Dokter dan Layanan
doctor_service_association = Table('doctor_service', Base.metadata,
    Column('doctor_id', Integer, ForeignKey('doctors.id'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.id'), primary_key=True)
)

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    
    queues = relationship("Queue", back_populates="patient")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    prefix = Column(String(1), unique=True)
    
    # Hubungan ke Doctor (Many-to-Many)
    doctors = relationship("Doctor", secondary=doctor_service_association, back_populates="services")
    # Hubungan ke Queue (One-to-Many)
    queues = relationship("Queue", back_populates="service")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_time = Column(Time, default=datetime.time(9, 0))
    end_time = Column(Time, default=datetime.time(14, 0))
    max_patients = Column(Integer, default=6)
    
    # Hubungan ke Service (Many-to-Many)
    services = relationship("Service", secondary=doctor_service_association, back_populates="doctors")
    # Hubungan ke Queue (One-to-Many)
    queues = relationship("Queue", back_populates="doctor")

class QueueStatus(str, enum.Enum):
    MENUNGGU = "Menunggu"
    DILAYANI = "Sedang Dilayani"
    SELESAI = "Selesai"

class Queue(Base):
    __tablename__ = "queues"
    id = Column(Integer, primary_key=True, index=True)
    queue_id_display = Column(String)
    queue_number = Column(Integer)
    registration_time = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(SQLAlchemyEnum(QueueStatus), default=QueueStatus.MENUNGGU)
    visit_notes = Column(Text, nullable=True)
    
    patient_id = Column(Integer, ForeignKey("patients.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))

    patient = relationship("Patient", back_populates="queues")
    service = relationship("Service", back_populates="queues")
    doctor = relationship("Doctor", back_populates="queues")