# hospital_api/crud.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from . import models, schemas

# ==================================
# === CRUD Functions for Patient ===
# ==================================

def get_patient(db: Session, patient_id: int):
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()

def get_patient_by_name(db: Session, name: str):
    return db.query(models.Patient).filter(models.Patient.name == name).first()

def get_patients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Patient).offset(skip).limit(limit).all()

def create_patient(db: Session, patient: schemas.PatientBase):
    db_patient = models.Patient(name=patient.name)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

# ==================================
# === CRUD Functions for Service ===
# ==================================

def get_service(db: Session, service_id: int):
    return db.query(models.Service).filter(models.Service.id == service_id).first()

def get_services(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Service).offset(skip).limit(limit).all()

def create_service(db: Session, service: schemas.ServiceCreate):
    db_service = models.Service(name=service.name)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

# ▼▼▼ TAMBAHKAN FUNGSI BARU INI ▼▼▼
def update_service(db: Session, service_id: int, service: schemas.ServiceCreate):
    # Cari data layanan yang ada di database berdasarkan ID
    db_service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if db_service:
        # Update namanya dengan data baru
        db_service.name = service.name
        db.commit()
        db.refresh(db_service)
        return db_service
    return None # Kembalikan None jika data tidak ditemukan

def delete_service(db: Session, service_id: int):
    db_service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if db_service:
        db.delete(db_service)
        db.commit()
        return db_service
    return None

# ==================================
# === CRUD Functions for Doctor ===
# ==================================

def get_doctor(db: Session, doctor_id: int):
    return db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()

def get_doctors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Doctor).offset(skip).limit(limit).all()

def create_doctor(db: Session, doctor: schemas.DoctorBase):
    db_doctor = models.Doctor(**doctor.model_dump())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

def assign_service_to_doctor(db: Session, doctor_id: int, service_id: int):
    """Menghubungkan seorang dokter dengan layanan yang bisa ia tangani."""
    db_doctor = get_doctor(db, doctor_id)
    db_service = get_service(db, service_id)
    if db_doctor and db_service:
        db_doctor.services.append(db_service)
        db.commit()
        db.refresh(db_doctor)
        return db_doctor
    return None

def delete_doctor(db: Session, doctor_id: int):
    db_doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if db_doctor:
        db.delete(db_doctor)
        db.commit()
        return db_doctor
    return None

# ==================================
# === "Read" Functions for Queue ===
# ==================================

def get_todays_queues_by_service(db: Session, service_id: int):
    """Mendapatkan daftar antrean hari ini untuk sebuah layanan spesifik."""
    today = date.today()
    return db.query(models.Queue).filter(
        models.Queue.service_id == service_id,
        func.date(models.Queue.registration_time) == today
    ).order_by(models.Queue.queue_number).all()

def get_patient_history(db: Session, patient_id: int):
    """Mendapatkan seluruh riwayat kunjungan seorang pasien."""
    return db.query(models.Queue).filter(models.Queue.patient_id == patient_id).all()