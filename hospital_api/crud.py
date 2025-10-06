# hospital_api/crud.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from datetime import date

# === Clinic CRUD Functions ===

def get_clinic(db: Session, clinic_id: int):
    return db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()

def get_clinic_by_name(db: Session, name: str):
    return db.query(models.Clinic).filter(models.Clinic.name == name).first()

def get_clinics(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Clinic).offset(skip).limit(limit).all()

def create_clinic(db: Session, clinic: schemas.ClinicCreate):
    db_clinic = models.Clinic(name=clinic.name)
    db.add(db_clinic)
    db.commit()
    db.refresh(db_clinic)
    return db_clinic

def delete_clinic(db: Session, clinic_id: int):
    db_clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if db_clinic:
        db.delete(db_clinic)
        db.commit()
        return db_clinic
    return None

# === Doctor CRUD Functions ===

def get_doctor(db: Session, doctor_id: int):
    return db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()

def get_doctors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Doctor).offset(skip).limit(limit).all()

def create_doctor(db: Session, doctor: schemas.DoctorCreate):
    db_doctor = models.Doctor(**doctor.model_dump())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor
    
def delete_doctor(db: Session, doctor_id: int):
    db_doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if db_doctor:
        db.delete(db_doctor)
        db.commit()
        return db_doctor
    return None

# === Queue CRUD Functions ===

def get_next_queue_number(db: Session, clinic_id: int):
    today = date.today()
    # Find the maximum queue number for today in the specific clinic
    max_queue = db.query(func.max(models.Queue.queue_number)).filter(
        models.Queue.clinic_id == clinic_id,
        func.date(models.Queue.registration_time) == today
    ).scalar()
    
    return (max_queue or 0) + 1

def create_queue(db: Session, queue: schemas.QueueCreate):
    queue_number = get_next_queue_number(db, queue.clinic_id)
    
    db_queue = models.Queue(
        patient_name=queue.patient_name,
        clinic_id=queue.clinic_id,
        doctor_id=queue.doctor_id,
        queue_number=queue_number,
        status=models.QueueStatus.MENUNGGU # Default status
    )
    db.add(db_queue)
    db.commit()
    db.refresh(db_queue)
    return db_queue

def get_queues_by_clinic(db: Session, clinic_id: int):
    today = date.today()
    return db.query(models.Queue).filter(
        models.Queue.clinic_id == clinic_id,
        func.date(models.Queue.registration_time) == today
    ).order_by(models.Queue.queue_number).all()

def update_queue_status(db: Session, queue_id: int, status: schemas.QueueStatus):
    db_queue = db.query(models.Queue).filter(models.Queue.id == queue_id).first()
    if db_queue:
        db_queue.status = status
        db.commit()
        db.refresh(db_queue)
    return db_queue
    
def get_visit_history(db: Session, patient_name: str):
    return db.query(models.Queue).filter(models.Queue.patient_name == patient_name).all()