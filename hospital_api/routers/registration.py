# Di dalam file router baru, misal: routers/registration.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db
from datetime import date
from sqlalchemy import func

router = APIRouter(
    tags=["Patient Registration"],
)

@router.post("/register", response_model=schemas.QueueRegistrationResponse)
def register_patient_for_services(request: schemas.QueueRegistrationRequest, db: Session = Depends(get_db)):
    # 1. Pasien memasukkan nama, sistem mencari atau membuat pasien baru
    patient = db.query(models.Patient).filter(models.Patient.name == request.patient_name).first()
    if not patient:
        patient = models.Patient(name=request.patient_name)
        db.add(patient)
        db.commit()
        db.refresh(patient)

    response_tickets = []
    today = date.today()

    # 2. Loop sebanyak penyakit/layanan yang dipilih
    for service_id in request.service_ids:
        service = db.query(models.Service).filter(models.Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Service with ID {service_id} not found")
        
        # Pastikan ada dokter yang tersedia untuk layanan ini
        if not service.doctors:
            raise HTTPException(status_code=400, detail=f"No doctors available for service '{service.name}'")

        # --- LOGIKA BARU DIMULAI DI SINI ---

        # 3. Hitung berapa pasien yang sudah ada di antrean layanan ini HARI INI
        todays_queue_count = db.query(models.Queue).filter(
            models.Queue.service_id == service.id,
            func.date(models.Queue.registration_time) == today
        ).count()

        # 4. Gunakan sisa bagi (modulo) untuk memilih dokter secara bergiliran
        num_doctors = len(service.doctors)
        doctor_index = todays_queue_count % num_doctors
        assigned_doctor = service.doctors[doctor_index]

        # --- LOGIKA BARU SELESAI DI SINI ---

        # Dapatkan nomor antrean baru untuk layanan ini
        max_queue = db.query(func.max(models.Queue.queue_number)).filter(
            models.Queue.service_id == service_id,
            func.date(models.Queue.registration_time) == today
        ).scalar()
        new_queue_number = (max_queue or 0) + 1

        # Buat entri antrean baru
        new_queue_entry = models.Queue(
            queue_number=new_queue_number,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=assigned_doctor.id
        )
        db.add(new_queue_entry)
        db.commit()
        db.refresh(new_queue_entry)

        response_tickets.append(new_queue_entry)
    
    return {"patient": patient, "tickets": response_tickets}