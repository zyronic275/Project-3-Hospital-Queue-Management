import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "hospital_db")

# Ganti 'PASSWORD_ANDA' dengan password MySQL user root yang sebenarnya
DB_URL = "mysql+pymysql://root:abel0908@localhost/hospital_queue"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

class TabelPoli(Base):
    __tablename__ = "tabel_poli_normal"
    poli = Column(String(100), primary_key=True, index=True)
    prefix = Column(String(10))
    dokters = relationship("TabelDokter", back_populates="poli_rel")

class TabelDokter(Base):
    __tablename__ = "tabel_dokter_normal"
    doctor_id = Column(Integer, primary_key=True, index=True) 
    dokter = Column(String(100))
    poli = Column(String(100), ForeignKey("tabel_poli_normal.poli"))
    practice_start_time = Column(Time)
    practice_end_time = Column(Time)
    doctor_code = Column(String(50))
    max_patients = Column(Integer)
    poli_rel = relationship("TabelPoli", back_populates="dokters")
    pelayanans = relationship("TabelPelayanan", back_populates="dokter_rel")

class TabelPelayanan(Base):
    __tablename__ = "tabel_pelayanan_normal"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nama_pasien = Column(String(100))
    poli = Column(String(100))
    dokter = Column(String(100))
    doctor_id_ref = Column(Integer, ForeignKey("tabel_dokter_normal.doctor_id"))
    visit_date = Column(Date)
    checkin_time = Column(DateTime, nullable=True)
    clinic_entry_time = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    status_pelayanan = Column(String(50))
    queue_number = Column(String(50))
    queue_sequence = Column(Integer)
    dokter_rel = relationship("TabelDokter", back_populates="pelayanans")

class TabelGabungan(Base):
    __tablename__ = "tabel_gabungan_transaksi"
    id = Column(Integer, primary_key=True, index=True)
    nama_pasien = Column(String(100))
    poli = Column(String(100))
    prefix_poli = Column(String(10))
    dokter = Column(String(100))
    doctor_code = Column(String(50))
    doctor_id = Column(Integer)
    visit_date = Column(Date)
    checkin_time = Column(DateTime)
    clinic_entry_time = Column(DateTime)
    completion_time = Column(DateTime)
    status_pelayanan = Column(String(50))
    queue_number = Column(String(50))
    queue_sequence = Column(Integer)