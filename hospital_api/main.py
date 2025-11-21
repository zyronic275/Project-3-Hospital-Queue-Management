from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
from sqlalchemy import func

# Local imports
import storage
import schemas

app = FastAPI(
    title="Hospital Queue API (Updated Dataset)",
    version="2.1.0"
)

router_public = APIRouter(tags=["Public Info & Registration"])
router_admin_services = APIRouter(prefix="/admin/services", tags=["Admin: Services"])
router_admin_doctors = APIRouter(prefix="/admin/doctors", tags=["Admin: Doctors"])
router_monitoring = APIRouter(prefix="/admin", tags=["Admin: Monitoring"])

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
# PUBLIC ENDPOINTS
# =================================================================

def time_to_seconds(t: datetime.time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second

@router_public.get("/services/{service_id}/available-doctors", response_model=List[schemas.DoctorAvailableSchema])
def get_available_doctors_for_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Layanan {service_id} tidak ditemukan")

    now_seconds = time_to_seconds(datetime.datetime.now().time())
    today = datetime.date.today()

    all_doctors = db.query(storage.Doctor).all()
    practicing_doctors = []
    
    for doc in all_doctors:
        if any(s.id == service_id for s in doc.services):
            start = time_to_seconds(doc.practice_start_time)
            end = time_to_seconds(doc.practice_end_time)
            # Simple check: is current time within practice hours?
            # You might want to disable this check for testing if outside hours
            if start <= now_seconds <= end: 
                practicing_doctors.append(doc)

    # Fallback: If no one is practicing RIGHT NOW, maybe just return all doctors for that service 
    # (so you can test the UI). Uncomment below to relax rules:
    # if not practicing_doctors:
    #     practicing_doctors = [d for d in all_doctors if any(s.id == service_id for s in d.services)]

    if not practicing_doctors:
        raise HTTPException(status_code=404, detail="Tidak ada dokter praktik saat ini.")

    available = []
    for doctor in practicing_doctors:
        active_count = db.query(storage.Queue).filter(
            storage.Queue.doctor_id == doctor.id,
            func.date(storage.Queue.registration_time) == today,
            storage.Queue.status != "selesai"
        ).count()

        remaining = doctor.max_patients - active_count
        if remaining > 0:
            doc_schema = schemas.DoctorAvailableSchema.model_validate(doctor)
            doc_schema.remaining_quota = remaining
            available.append(doc_schema)

    return available

@router_public.post("/register", response_model=schemas.RegistrationResponse, status_code=201)
def register_patient(request: schemas.RegistrationRequest, db: Session = Depends(get_db)):
    # 1. Find or Create Patient
    patient = db.query(storage.Patient).filter(storage.Patient.name == request.patient_name).first()
    if not patient:
        patient = storage.Patient(
            name=request.patient_name,
            date_of_birth=request.date_of_birth # Save DOB if provided
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    tickets = []
    today = datetime.date.today()
    
    # For registration, we usually check "Now"
    now_seconds = time_to_seconds(datetime.datetime.now().time())

    for service_id in request.service_ids:
        service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
        if not service:
            raise HTTPException(404, f"Service {service_id} not found")

        # Find doctor logic
        candidates = []
        all_docs = db.query(storage.Doctor).all()
        for d in all_docs:
            if any(s.id == service_id for s in d.services):
                 # Strict time check
                if time_to_seconds(d.practice_start_time) <= now_seconds <= time_to_seconds(d.practice_end_time):
                    candidates.append(d)
        
        # Relaxed check for testing if empty
        if not candidates:
             candidates = [d for d in all_docs if any(s.id == service_id for s in d.services)]

        doctor_to_assign = None
        if request.doctor_id:
            doctor_to_assign = next((d for d in candidates if d.id == request.doctor_id), None)
            if not doctor_to_assign:
                raise HTTPException(400, "Selected doctor not available")
        elif len(candidates) > 1:
            raise HTTPException(400, f"Multiple doctors available for {service.name}, please choose one.")
        elif len(candidates) == 1:
            doctor_to_assign = candidates[0]
        else:
             raise HTTPException(404, f"No doctors found for {service.name}")

        # Check Quota
        queue_today_count = db.query(storage.Queue).filter(
            storage.Queue.doctor_id == doctor_to_assign.id,
            func.date(storage.Queue.registration_time) == today,
            storage.Queue.status != "selesai"
        ).count()

        if queue_today_count >= doctor_to_assign.max_patients:
            raise HTTPException(400, f"Doctor {doctor_to_assign.name} is full.")

        # Create Queue
        total_today = db.query(storage.Queue).filter(
            storage.Queue.doctor_id == doctor_to_assign.id,
            func.date(storage.Queue.registration_time) == today
        ).count()
        
        new_num = total_today + 1
        display_id = f"{service.prefix}-{doctor_to_assign.doctor_code}-{new_num:03d}"

        new_queue = storage.Queue(
            queue_id_display=display_id,
            queue_number=new_num,
            status="menunggu",
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor_to_assign.id,
            registration_time=datetime.datetime.now()
        )
        db.add(new_queue)
        db.commit()
        db.refresh(new_queue)

        tickets.append(schemas.Ticket(
            service=service,
            queue_number=display_id,
            doctor=doctor_to_assign
        ))

    return schemas.RegistrationResponse(patient=patient, tickets=tickets)

@router_public.get("/queues/{service_id}", response_model=List[schemas.QueueSchema])
def get_queue_for_service(service_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    today = datetime.date.today()
    query = db.query(storage.Queue).filter(
        storage.Queue.service_id == service_id,
        func.date(storage.Queue.registration_time) == today
    )
    if status:
        query = query.filter(storage.Queue.status == status)
    
    return query.order_by(storage.Queue.queue_number).all()

@router_public.put("/queues/{queue_id}/status", response_model=schemas.QueueSchema)
def update_queue_status(queue_id: int, req: schemas.QueueStatusUpdate, db: Session = Depends(get_db)):
    queue = db.query(storage.Queue).filter(storage.Queue.id == queue_id).first()
    if not queue:
        raise HTTPException(404, "Queue not found")
    
    queue.status = req.status
    db.commit()
    db.refresh(queue)
    return queue

# =================================================================
# ADMIN ENDPOINTS
# =================================================================

@router_admin_services.get("/", response_model=List[schemas.ServiceSchema])
def get_services(db: Session = Depends(get_db)):
    return db.query(storage.Service).all()

@router_admin_services.post("/", response_model=schemas.ServiceSchema)
def create_service(s: schemas.ServiceCreate, db: Session = Depends(get_db)):
    if db.query(storage.Service).filter(storage.Service.prefix == s.prefix).first():
        raise HTTPException(400, "Prefix exists")
    new_s = storage.Service(**s.model_dump())
    db.add(new_s)
    db.commit()
    db.refresh(new_s)
    return new_s

@router_admin_services.put("/{service_id}", response_model=schemas.ServiceSchema)
def update_service(service_id: int, s_update: schemas.ServiceUpdate, db: Session = Depends(get_db)):
    service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
    if not service:
        raise HTTPException(404, "Service not found")
    
    for key, value in s_update.model_dump(exclude_unset=True).items():
        setattr(service, key, value)
    
    db.commit()
    db.refresh(service)
    return service

@router_admin_services.delete("/{service_id}", status_code=204)
def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
    if not service:
        raise HTTPException(404, "Service not found")
    db.delete(service)
    db.commit()
    return

@router_admin_doctors.get("/", response_model=List[schemas.DoctorSchema])
def get_doctors(db: Session = Depends(get_db)):
    return db.query(storage.Doctor).all()

@router_admin_doctors.post("/", response_model=schemas.DoctorSchema)
def create_doctor(d: schemas.DoctorCreate, db: Session = Depends(get_db)):
    services = db.query(storage.Service).filter(storage.Service.id.in_(d.services)).all()
    if len(services) != len(d.services):
        raise HTTPException(404, "Some services not found")
    
    new_doc = storage.Doctor(
        doctor_code=d.doctor_code,
        name=d.name,
        practice_start_time=d.practice_start_time,
        practice_end_time=d.practice_end_time,
        max_patients=d.max_patients
    )
    new_doc.services = services
    
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc

@router_admin_doctors.put("/{doctor_id}", response_model=schemas.DoctorSchema)
def update_doctor(doctor_id: int, d_update: schemas.DoctorUpdate, db: Session = Depends(get_db)):
    doctor = db.query(storage.Doctor).filter(storage.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    
    data = d_update.model_dump(exclude_unset=True)
    if "services" in data:
        services = db.query(storage.Service).filter(storage.Service.id.in_(data["services"])).all()
        doctor.services = services
        del data["services"]
        
    for key, value in data.items():
        setattr(doctor, key, value)
        
    db.commit()
    db.refresh(doctor)
    return doctor

@router_admin_doctors.delete("/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(storage.Doctor).filter(storage.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    db.delete(doctor)
    db.commit()
    return

# =================================================================
# MONITORING
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
            density_percentage=round(density, 2)
        ))
    return data

app.include_router(router_public)
app.include_router(router_admin_services)
app.include_router(router_admin_doctors)
app.include_router(router_monitoring)