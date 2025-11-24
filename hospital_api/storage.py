# storage.py

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Time, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import os

# --- Konfigurasi Database (SQLite) ---
# Menggunakan SQLite, data disimpan di file 'hospital.db'
# Gunakan path relatif agar konsisten di berbagai lingkungan
SQLALCHEMY_DATABASE_URL = "sqlite:///./hospital.db" 

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    # Penting untuk SQLite agar thread FastAPI bisa berjalan
    connect_args={"check_same_thread": False}
)

# Mendefinisikan SessionLocal 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- Tabel Asosiasi (Many-to-Many untuk Doctor & Service) ---
doctor_service_association = Table(
    'doctor_service', Base.metadata,
    Column('doctor_id', Integer, ForeignKey('doctors.id'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.id'), primary_key=True)
)

# --- Definisi Model (Tabel) ---

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    prefix = Column(String, index=True) # Contoh: 'UMUM', 'GIGI', 'JANTUNG'
    
    doctors = relationship("Doctor", secondary=doctor_service_association, back_populates="services")
    queues = relationship("Queue", back_populates="service")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    doctor_code = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    practice_start_time = Column(Time)
    practice_end_time = Column(Time)
    max_patients = Column(Integer)
    
    services = relationship("Service", secondary=doctor_service_association, back_populates="doctors")
    queues = relationship("Queue", back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    date_of_birth = Column(DateTime)
    
    queues = relationship("Queue", back_populates="patient")

class Queue(Base):
    __tablename__ = "queues"
    id = Column(Integer, primary_key=True, index=True)
    queue_id_display = Column(String, unique=True, index=True)
    queue_number = Column(Integer)
    status = Column(String) # menunggu, sedang dilayani, selesai
    registration_time = Column(DateTime, default=datetime.datetime.now)
    visit_result = Column(String, nullable=True) # Hasil diagnosis atau catatan kunjungan
    
    patient_id = Column(Integer, ForeignKey("patients.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    
    patient = relationship("Patient", back_populates="queues")
    service = relationship("Service", back_populates="queues")
    doctor = relationship("Doctor", back_populates="queues")

def init_db():
    """Membuat tabel database jika belum ada."""
    Base.metadata.create_all(bind=engine)
    
# Tambahkan fungsi ini untuk memastikan kompatibilitas dengan import di main.py
if 'hospital_api' not in os.listdir(os.getcwd()):
    # Ini hanya jika file ini tidak di dalam package
    # Biasanya digunakan untuk migrasi data awal
    pass