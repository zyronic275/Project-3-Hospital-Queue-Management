from sqlalchemy import create_engine, Column, Integer, String, Time, Date, ForeignKey, Table, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import datetime

# 1. Database Connection
DATABASE_URL = "sqlite:///./hospital.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def read_data():
    if not os.path.exists(csv_file):
        return []
    df = pd.read_csv(csv_file)
    # Fixed: Replace NaN (empty cells) with None so FastAPI doesn't crash
    df = df.replace({np.nan: None}) 
    return df.to_dict(orient='records')

# 2. Association Table
doctor_service_association = Table(
    'doctor_services', Base.metadata,
    Column('doctor_id', Integer, ForeignKey('doctors.id')),
    Column('service_id', Integer, ForeignKey('services.id'))
)

# 3. Define Tables
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
    services = relationship("Service", secondary=doctor_service_association, backref="doctors")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    # NEW: Date of Birth field
    date_of_birth = Column(Date, nullable=True)

class Queue(Base):
    __tablename__ = "queues"
    id = Column(Integer, primary_key=True, index=True)
    queue_id_display = Column(String)
    queue_number = Column(Integer)
    status = Column(String, default="menunggu")
    registration_time = Column(DateTime, default=datetime.datetime.now)
    
    patient_id = Column(Integer, ForeignKey("patients.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))

    patient = relationship("Patient")
    service = relationship("Service")
    doctor = relationship("Doctor")

def init_db():
    Base.metadata.create_all(bind=engine)