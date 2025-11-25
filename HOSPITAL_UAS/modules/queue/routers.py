import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract
from ..queue import models as queue_models
from ..queue import schemas as queue_schemas
from ..master import models as master_models
from ..master import schemas as master_schemas
from ..master.models import Service, GenderRestriction 
from ..master import schemas as master_schemas # Import schema master
from sqlalchemy.orm import joinedload, aliased 
from ..database import get_db  # <--- HANYA INI YANG BENAR
from ..queue import models as queue_models

router = APIRouter()

import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from ..queue import models as queue_models
from ..queue import schemas as queue_schemas
from ..master import models as master_models
from ..master import schemas as master_schemas 
from ..master.models import Service, GenderRestriction 
from sqlalchemy.orm import joinedload, aliased 

router = APIRouter()

# --- ENDPOINT 1: REGISTRASI PASIEN BARU ---
@router.post("/register", response_model=queue_schemas.VisitResponse, status_code=status.HTTP_201_CREATED)
def register_patient(visit: queue_schemas.VisitCreate, db: Session = Depends(get_db)):
    
    doctor = db.query(master_models.Doctor).options(joinedload(master_models.Doctor.service)).get(visit.doctor_id)
    if not doctor or not doctor.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or inactive.")

    service = doctor.service
    
    # 1. VALIDASI BATAS USIA
    if not (service.min_age <= visit.age <= service.max_age):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Usia pasien harus antara {service.min_age} dan {service.max_age} tahun untuk Layanan '{service.name}'."
        )
        
    # 2. VALIDASI BATAS JENIS KELAMIN
    restriction = service.gender_restriction
    if restriction != GenderRestriction.NONE and restriction.value != visit.gender:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Layanan '{service.name}' hanya diperuntukkan bagi pasien berjenis kelamin {restriction.value}."
        )

    # 3. VALIDASI JAM PRAKTIK DOKTER
    if not (doctor.practice_start_time <= visit.consultation_time <= doctor.practice_end_time):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Dokter tidak tersedia pada waktu konsultasi yang diminta ({visit.consultation_time.strftime('%H:%M')})."
        )
    
    # 4. Cek Kuota & Tentukan Nomor Urut Antrean
    today = datetime.datetime.utcnow().date()
    visits_today_count = db.query(queue_models.Visit).filter(
        queue_models.Visit.doctor_id == doctor.id,
        queue_models.Visit.t_register >= today,
        queue_models.Visit.t_register < today + datetime.timedelta(days=1),
        queue_models.Visit.status.notin_([queue_models.VisitStatus.FINISHED, queue_models.VisitStatus.CANCELED])
    ).count()

    if visits_today_count >= doctor.max_patients:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor quota reached for today.")
    
    max_sequence = db.query(func.max(queue_models.Visit.queue_sequence)).filter(
        queue_models.Visit.doctor_id == doctor.id,
        queue_models.Visit.t_register >= today,
        queue_models.Visit.t_register < today + datetime.timedelta(days=1)
    ).scalar() or 0
    
    new_sequence = max_sequence + 1
    
    # 5. Buat objek Visit
    visit_data = visit.model_dump()
    visit_data.pop('consultation_time') 
    
    db_visit = queue_models.Visit(
        **visit_data,
        queue_sequence=new_sequence,
        t_register=datetime.datetime.utcnow(),
        status=queue_models.VisitStatus.IN_QUEUE
    )
    
    db.add(db_visit)
    db.commit()
    db.refresh(db_visit)
    
    db_visit = db.query(queue_models.Visit).options(joinedload(queue_models.Visit.doctor).joinedload(master_models.Doctor.service)).get(db_visit.id)
    
    return db_visit

# --- ENDPOINT 2: UPDATE STATUS PASIEN (PUT /{visit_id}/status) ---
@router.put("/{visit_id}/status", response_model=queue_schemas.VisitResponse) # PERBAIKAN PATH
def update_visit_status(visit_id: int, update_data: queue_schemas.VisitUpdateStatus, db: Session = Depends(get_db)):
    db_visit = db.query(queue_models.Visit).get(visit_id)
    if not db_visit:
        # Error 404 pada PUT menunjukkan ID Visit tidak ditemukan
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antrean tidak ditemukan.")

    db_visit.status = update_data.status
    
    now = datetime.datetime.now(datetime.timezone.utc) # Ganti utcnow() yang deprecated
    if update_data.status == queue_models.VisitStatus.CALLED:
        db_visit.t_called = now
    elif update_data.status == queue_models.VisitStatus.IN_SERVICE:
        db_visit.t_in_service = now
    elif update_data.status == queue_models.VisitStatus.FINISHED:
        db_visit.t_finished = now
    
    db.commit()
    db.refresh(db_visit)
    
    db_visit = db.query(queue_models.Visit).options(joinedload(queue_models.Visit.doctor).joinedload(master_models.Doctor.service)).get(db_visit.id)
    
    return db_visit
# --- ENDPOINT 2: MENCARI LAYANAN BERDASARKAN FILTER PASIEN (Usia, Gender) ---
@router.post("/available-services", response_model=list[master_schemas.ServiceResponse])
def get_available_services(patient_data: dict, db: Session = Depends(get_db)):
    
    age = patient_data.get('age')
    gender = patient_data.get('gender')
    
    if age is None or gender is None:
        raise HTTPException(status_code=400, detail="Usia dan jenis kelamin pasien wajib diisi.")
    
    # 1. Validasi Usia
    query = db.query(Service).filter(
        Service.is_active == True,
        Service.min_age <= age,
        Service.max_age >= age
    )
    
    # 2. Validasi Jenis Kelamin
    if gender in [GenderRestriction.MALE.value, GenderRestriction.FEMALE.value]:
        query = query.filter(
            (Service.gender_restriction == gender) | (Service.gender_restriction == GenderRestriction.NONE)
        )
        
    return query.all()

# --- ENDPOINT 3: DASHBOARD METRIK ---
@router.get("/admin/dashboard", response_model=list[master_schemas.DashboardServiceMetric])
def get_dashboard_data(db: Session = Depends(get_db)):
    today = datetime.datetime.utcnow().date()
    
    VisitAlias = aliased(queue_models.Visit)

    # Kueri kompleks untuk menghitung metrik per Service
    query = db.query(
        master_models.Service.id,
        master_models.Service.name.label('service_name'),
        func.count(master_models.Doctor.id).label('doctors_count'),
        func.sum(master_models.Doctor.max_patients).label('max_patients_total'),
        
        func.sum(case((VisitAlias.status.in_([queue_models.VisitStatus.IN_QUEUE.value, queue_models.VisitStatus.CALLED.value]), 1), else_=0)).label('patients_waiting'),
        func.sum(case((VisitAlias.status == queue_models.VisitStatus.IN_SERVICE.value, 1), else_=0)).label('patients_serving'),
        func.count(VisitAlias.id).label('total_patients_today'),
        
    ).join(
        master_models.Doctor, master_models.Service.id == master_models.Doctor.service_id
    ).outerjoin(
        VisitAlias, 
        (master_models.Doctor.id == VisitAlias.doctor_id) & 
        (VisitAlias.t_register >= today) & 
        (VisitAlias.t_register < today + datetime.timedelta(days=1)) &
        (VisitAlias.status.notin_([queue_models.VisitStatus.FINISHED.value, queue_models.VisitStatus.CANCELED.value]))
    ).group_by(
        master_models.Service.id, master_models.Service.name
    ).all()

    results = []
    for row in query:
        total_active_patients = row.patients_waiting + row.patients_serving
        max_capacity = row.max_patients_total
        
        density_percentage = (total_active_patients / max_capacity) * 100 if max_capacity > 0 else 0
        total_today = total_active_patients 
        
        results.append(master_schemas.DashboardServiceMetric(
            id=row.id,
            service_name=row.service_name,
            doctors_count=row.doctors_count,
            density_percentage=round(density_percentage, 2),
            total_patients_today=total_today,
            max_patients_total=max_capacity,
            patients_waiting=row.patients_waiting,
            patients_serving=row.patients_serving
        ))
        
    return results


# --- 4. ENDPOINT TAMPILAN ANTREAN PUBLIK ---
@router.get("/queues/{service_id}", response_model=list[queue_schemas.VisitResponse])
def get_public_queue_display(service_id: int, db: Session = Depends(get_db)):
    today = datetime.datetime.utcnow().date()
    
    # Ambil semua kunjungan hari ini untuk service_id tertentu
    queues = db.query(queue_models.Visit).options(
        joinedload(queue_models.Visit.doctor).joinedload(master_models.Doctor.service)
    ).join(
        master_models.Doctor, queue_models.Visit.doctor_id == master_models.Doctor.id
    ).filter(
        master_models.Doctor.service_id == service_id,
        queue_models.Visit.t_register >= today,
        queue_models.Visit.t_register < today + datetime.timedelta(days=1)
    ).order_by(
        queue_models.Visit.queue_sequence # Urutkan berdasarkan urutan antrean
    ).all()
    
    return queues


@router.get("/")
def queue_root():
    return {"module": "Queue", "status": "Ready"}