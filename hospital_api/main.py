from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
from sqlalchemy import func

# Local imports
import storage
import schemas
from migrate import seed_data # Import fungsi seed baru kita

# Inisialisasi Database Tables
storage.init_db()

app = FastAPI(
    title="Hospital Queue API (Random Import)",
    version="2.2.0"
)

router_public = APIRouter(tags=["Public Info & Registration"])
router_admin_services = APIRouter(prefix="/admin/services", tags=["Admin: Services"])
router_admin_doctors = APIRouter(prefix="/admin/doctors", tags=["Admin: Doctors"])
router_monitoring = APIRouter(prefix="/admin", tags=["Admin: Monitoring"])
router_data = APIRouter(prefix="/admin/data", tags=["Admin: Data Import"]) # Router baru

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = storage.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================================================================
# NEW ENDPOINT FOR RANDOM DATA IMPORT (POIN 2)
# =================================================================

@router_data.get("/seed-random", summary="Import Random Data from CSV")
def import_random_data_endpoint(
    count: int = Query(..., description="Jumlah baris data yang ingin digenerate secara random dari CSV", ge=1),
    db: Session = Depends(get_db)
):
    """
    Endpoint ini memenuhi Poin 2:
    Mengambil data dari file CSV secara acak sejumlah `count` dan memasukkannya ke database via ORM.
    """
    try:
        result = seed_data(db, count)
        return {
            "status": "success",
            "message": "Data imported successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# PUBLIC ENDPOINTS
# =================================================================

def time_to_seconds(t: datetime.time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second

@router_public.get("/services/{service_id}/available-doctors", response_model=List[schemas.DoctorSchema])
def get_available_doctors(service_id: int, db: Session = Depends(get_db)):
    service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service.doctors

@router_public.get("/services", response_model=List[schemas.ServiceSchema])
def get_services(db: Session = Depends(get_db)):
    return db.query(storage.Service).all()

@router_public.post("/register", response_model=schemas.RegistrationResponse)
def register_patient(payload: schemas.RegistrationRequest, db: Session = Depends(get_db)):
    # 1. Create/Get Patient
    patient = db.query(storage.Patient).filter(storage.Patient.name == payload.patient_name).first()
    if not patient:
        patient = storage.Patient(
            name=payload.patient_name,
            date_of_birth=payload.date_of_birth
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    
    tickets = []
    
    # 2. Process each service
    for s_id in payload.service_ids:
        service = db.query(storage.Service).filter(storage.Service.id == s_id).first()
        if not service:
            continue
            
        # Select Doctor (specific or random/first available)
        doctor = None
        if payload.doctor_id:
             doctor = db.query(storage.Doctor).filter(storage.Doctor.id == payload.doctor_id).first()
        
        if not doctor:
            # Auto-assign logic: pick first doctor in service
            if service.doctors:
                doctor = service.doctors[0]
            else:
                continue # No doctor available for this service

        # Generate Queue Number
        today = datetime.date.today()
        count_today = db.query(storage.Queue).filter(
            storage.Queue.doctor_id == doctor.id,
            func.date(storage.Queue.registration_time) == today
        ).count()
        
        queue_num = count_today + 1
        q_display = f"{service.prefix}-{doctor.doctor_code}-{queue_num:04d}"
        
        new_queue = storage.Queue(
            queue_id_display=q_display,
            queue_number=queue_num,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor.id,
            status="menunggu"
        )
        db.add(new_queue)
        db.commit()
        db.refresh(new_queue)
        
        tickets.append(schemas.Ticket(
            service=service,
            queue_number=q_display,
            doctor=doctor
        ))
        
    return schemas.RegistrationResponse(patient=patient, tickets=tickets)

# =================================================================
# ADMIN ENDPOINTS (SERVICES & DOCTORS)
# =================================================================

@router_admin_services.post("/", response_model=schemas.ServiceSchema)
def create_service(service: schemas.ServiceCreate, db: Session = Depends(get_db)):
    db_service = storage.Service(name=service.name, prefix=service.prefix)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router_admin_doctors.post("/", response_model=schemas.DoctorSchema)
def create_doctor(doctor: schemas.DoctorCreate, db: Session = Depends(get_db)):
    db_doctor = storage.Doctor(
        doctor_code=doctor.doctor_code,
        name=doctor.name,
        practice_start_time=doctor.practice_start_time,
        practice_end_time=doctor.practice_end_time,
        max_patients=doctor.max_patients
    )
    
    # Associate services
    if doctor.services:
        services = db.query(storage.Service).filter(storage.Service.id.in_(doctor.services)).all()
        db_doctor.services = services
        
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

# =================================================================
# MONITORING DASHBOARD
# =================================================================

@router_monitoring.get("/dashboard", response_model=List[schemas.ClinicStatus])
def get_dashboard(db: Session = Depends(get_db)):
    data = []
    today = datetime.date.today()
    services = db.query(storage.Service).all()
    
    for s in services:
        doctors = s.doctors
        waiting = 0
        serving = 0
        total_today = 0
        max_p = 0
        
        for d in doctors:
            max_p += d.max_patients
            q_today = db.query(storage.Queue).filter(
                storage.Queue.doctor_id == d.id,
                func.date(storage.Queue.registration_time) == today
            ).all()
            
            waiting += sum(1 for q in q_today if q.status == "menunggu")
            serving += sum(1 for q in q_today if q.status == "sedang dilayani")
            total_today += len(q_today)
            
        active = waiting + serving
        density = (active / max_p * 100) if max_p > 0 else 0
        
        data.append(schemas.ClinicStatus(
            service_id=s.id,
            service_name=s.name,
            doctors_count=len(doctors),
            max_patients_total=max_p,
            patients_waiting=waiting,
            patients_serving=serving,
            total_patients_today=total_today,
            current_density_percentage=round(density, 2)
        ))
        
    return data

@router_monitoring.get("/queues", response_model=List[schemas.QueueSchema])
def get_all_queues(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    queues = db.query(storage.Queue).offset(skip).limit(limit).all()
    return queues

# Register routers
app.include_router(router_public)
app.include_router(router_admin_services)
app.include_router(router_admin_doctors)
app.include_router(router_monitoring)
app.include_router(router_data)