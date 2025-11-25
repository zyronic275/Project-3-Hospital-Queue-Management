import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from ..database import get_db
from ..master import models as master_models
from ..master import schemas as master_schemas
from ..queue import models as queue_models 

router = APIRouter()

# --- HELPER ---
def get_doctor_response_with_service(db: Session, doctor: master_models.Doctor):
    service = db.query(master_models.Service).get(doctor.service_id)
    if not service:
        raise HTTPException(status_code=500, detail="Service not found for doctor.")
    
    return master_schemas.DoctorResponse.model_validate(doctor, update={'service_name': service.name})


# --- ENDPOINTS SERVICE (KLINIK) ---
@router.post("/services/", response_model=master_schemas.ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(service: master_schemas.ServiceCreate, db: Session = Depends(get_db)):
    db_service = master_models.Service(**service.model_dump())
    try:
        db.add(db_service)
        db.commit()
        db.refresh(db_service)
        return db_service
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service name or prefix already exists.")

@router.get("/services/", response_model=list[master_schemas.ServiceResponse])
def read_services(db: Session = Depends(get_db)):
    return db.query(master_models.Service).filter(master_models.Service.is_active == True).all()


# --- ENDPOINTS DOCTOR ---
@router.post("/doctors/", response_model=master_schemas.DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(doctor: master_schemas.DoctorCreate, db: Session = Depends(get_db)):
    db_doctor = master_models.Doctor(**doctor.model_dump())
    try:
        db.add(db_doctor)
        db.commit()
        db.refresh(db_doctor)
        return get_doctor_response_with_service(db, db_doctor)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor code already exists or service_id is invalid.")

@router.get("/doctors/", response_model=list[master_schemas.DoctorResponse])
def read_doctors(db: Session = Depends(get_db)):
    doctors = db.query(master_models.Doctor).all()
    return [get_doctor_response_with_service(db, d) for d in doctors]


# --- ENDPOINT KETERSEDIAAN DOKTER ---
@router.get("/services/{service_id}/available-doctors-by-time", response_model=list[master_schemas.DoctorAvailableResponse])
def get_available_doctors_by_time(service_id: int, consultation_time: str, db: Session = Depends(get_db)):
    
    try:
        # Konversi string HH:MM menjadi objek datetime.time
        time_obj = datetime.datetime.strptime(consultation_time, '%H:%M').time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format waktu konsultasi harus HH:MM.")

    today = datetime.datetime.utcnow().date()
    
    # 1. Filter berdasarkan Jam Praktik dan Service ID
    available_doctors = db.query(master_models.Doctor).filter(
        master_models.Doctor.service_id == service_id,
        master_models.Doctor.is_active == True,
        master_models.Doctor.practice_start_time <= time_obj,
        master_models.Doctor.practice_end_time >= time_obj
    ).all()

    results = []
    
    for doctor in available_doctors:
        visits_today = db.query(queue_models.Visit).filter(
            queue_models.Visit.doctor_id == doctor.id,
            queue_models.Visit.t_register >= today,
            queue_models.Visit.t_register < today + datetime.timedelta(days=1),
            queue_models.Visit.status.notin_([queue_models.VisitStatus.FINISHED, queue_models.VisitStatus.CANCELED])
        ).count()
        
        remaining = doctor.max_patients - visits_today
        
        if remaining > 0:
            results.append(master_schemas.DoctorAvailableResponse(
                id=doctor.id,
                doctor_name=doctor.doctor_name,
                remaining_quota=remaining
            ))
            
    return results