from sqlalchemy import create_engine, Column, Integer, String, Time, Date, ForeignKey, Table, DateTime, text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import datetime
import os

# FILE MENGATUR KONEKSI DENGAN SQL


# --- KONFIGURASI MYSQL ---
# Ubah sesuai settingan komputer Anda
DB_USER = "root"
DB_PASSWORD = "JemberIndah170845"  # Kosongkan string jika tidak ada password
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "hospital_db"

# URL untuk connect ke Server (tanpa memilih database)
SERVER_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"

# URL untuk connect ke Database spesifik
DATABASE_URL = f"{SERVER_URL}/{DB_NAME}"

# --- AUTOMATIC DATABASE CREATION ---
def create_database_if_not_exists():
    """
    Fungsi ini melakukan 'hack' dengan connect ke root server MySQL
    lalu membuat database jika belum ada.
    """
    try:
        # Buat engine sementara yang mengarah ke server root (bukan ke hospital_db)
        # isolation_level="AUTOCOMMIT" penting agar perintah CREATE DATABASE berjalan langsung
        temp_engine = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
        
        with temp_engine.connect() as conn:
            # Jalankan perintah SQL murni
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
            print(f"✅ Database '{DB_NAME}' siap digunakan (dibuat atau sudah ada).")
            
        temp_engine.dispose() # Tutup koneksi sementara
    except Exception as e:
        print(f"⚠️  Gagal mengecek/membuat database otomatis: {e}")
        print("Pastikan username/password benar dan server MySQL menyala.")

# Jalankan fungsi ini sebelum membuat engine utama
create_database_if_not_exists()

# --- UTAMA: SETUP ORM ---
# Sekarang aman untuk connect ke DATABASE_URL karena database pasti sudah ada
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Association Table
doctor_service_association = Table(
    'doctor_services', Base.metadata,
    Column('doctor_id', Integer, ForeignKey('doctors.id')),
    Column('service_id', Integer, ForeignKey('services.id'))
)

# 3. Define Tables
# PERUBAHAN PENTING: Semua Column(String) diubah menjadi Column(String(255)) atau String(50)
# Ini wajib untuk MySQL.

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)  # FIX: Added length
    prefix = Column(String(50))                          # FIX: Added length

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    doctor_code = Column(String(50))                     # FIX: Added length
    name = Column(String(255))                           # FIX: Added length
    practice_start_time = Column(Time)
    practice_end_time = Column(Time)
    max_patients = Column(Integer, default=20)
    services = relationship("Service", secondary=doctor_service_association, backref="doctors")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)               # FIX: Added length
    age = Column(Integer, nullable=True)
    gender = Column(String(50), nullable=True)           # FIX: Added length
    date_of_birth = Column(Date, nullable=True)

class Queue(Base):
    __tablename__ = "queues"
    id = Column(Integer, primary_key=True, index=True)
    queue_id_display = Column(String(50))                # FIX: Added length
    queue_number = Column(Integer)
    status = Column(String(50), default="menunggu")      # FIX: Added length
    registration_time = Column(DateTime, default=datetime.datetime.now)
    
    patient_id = Column(Integer, ForeignKey("patients.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    
    patient = relationship("Patient")
    service = relationship("Service")
    doctor = relationship("Doctor")

def init_db():
    Base.metadata.create_all(bind=engine)