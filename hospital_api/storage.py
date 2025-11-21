from sqlalchemy import create_engine, Column, Integer, String, Time, ForeignKey, Table, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import datetime

# 1. Database Connection
DATABASE_URL = "sqlite:///./hospital.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Association Table (Since one Doctor can work in multiple Services)
doctor_service_association = Table(
    'doctor_services', Base.metadata,
    Column('doctor_id', Integer, ForeignKey('doctors.id')),
    Column('service_id', Integer, ForeignKey('services.id'))
)

# 3. Define Tables (Models)
class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    prefix = Column(String)

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    doctor_code = Column(String)
    name = Column(String)
    practice_start_time = Column(Time)
    practice_end_time = Column(Time)
    max_patients = Column(Integer, default=20)
    
    # Relationship to Services (Many-to-Many)
    services = relationship("Service", secondary=doctor_service_association, backref="doctors")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer, nullable=True)      # Added from CSV
    gender = Column(String, nullable=True)    # Added from CSV

class Queue(Base):
    __tablename__ = "queues"
    id = Column(Integer, primary_key=True, index=True)
    queue_id_display = Column(String)
    queue_number = Column(Integer)
    status = Column(String, default="menunggu")
    registration_time = Column(DateTime, default=datetime.datetime.now)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))

    # Relationships
    patient = relationship("Patient")
    service = relationship("Service")
    doctor = relationship("Doctor")

# 4. Helper to create tables
def init_db():
    Base.metadata.create_all(bind=engine)