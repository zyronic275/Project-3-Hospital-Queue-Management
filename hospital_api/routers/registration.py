# Di dalam file router baru, misal: routers/registration.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db
from datetime import date, datetime
from sqlalchemy import func, and_

router = APIRouter(
    tags=["Patient Registration"],
)

@router.post("/register", response_model=schemas.QueueRegistrationResponse)
def register_patient_for_services(request: schemas.QueueRegistrationRequest, db: Session = Depends(get_db)):
    # ... (kode untuk get/create patient tetap sama) ...
    patient = db.query(models.Patient).filter(models.Patient.name == request.patient_name).first()
    if not patient:
        patient = models.Patient(name=request.patient_name)
        db.add(patient)
        db.commit()
        db.refresh(patient)

    response_tickets = []
    today = date.today()
    now_time = datetime.now().time()

    for service_id in request.service_ids:
        service = db.query(models.Service).filter(models.Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Service with ID {service_id} not found")
        
        # ... (kode pengecekan jam kerja dokter tetap sama) ...
        available_doctors_query = db.query(models.Doctor).join(models.Doctor.services).filter(
            models.Service.id == service_id,
            models.Doctor.start_time <= now_time,
            models.Doctor.end_time >= now_time
        )
        
        # ▼▼▼ TAMBAHKAN PENGURUTAN DI SINI ▼▼▼
        # Urutkan dokter berdasarkan ID untuk memastikan urutan yang konsisten
        available_doctors = available_doctors_query.order_by(models.Doctor.id).all()

        if not available_doctors:
            raise HTTPException(status_code=400, detail=f"Tidak ada dokter yang tersedia untuk layanan '{service.name}' saat ini.")

        assigned_doctor = None
        
        # Cari dokter yang kuotanya belum penuh (logika ini tetap sama)
        for doctor in available_doctors:
            patients_today = db.query(models.Queue).filter(
                models.Queue.doctor_id == doctor.id,
                func.date(models.Queue.registration_time) == today
            ).count()
            
            if patients_today < doctor.max_patients:
                assigned_doctor = doctor
                break

        if not assigned_doctor:
            raise HTTPException(status_code=400, detail=f"Semua dokter untuk layanan '{service.name}' sudah mencapai kuota maksimum.")

        # --- LOGIKA ROUND-ROBIN YANG DISESUAIKAN ---
        # Untuk memilih dokter, kita gunakan daftar 'available_doctors' yang sudah terurut
        todays_queue_count = db.query(models.Queue).filter(
            models.Queue.service_id == service.id,
            func.date(models.Queue.registration_time) == today
        ).count()
        
        num_doctors = len(available_doctors)
        doctor_index = todays_queue_count % num_doctors
        assigned_doctor = available_doctors[doctor_index]

        # ... (sisa kode pembuatan antrean tetap sama) ...
        # Dapatkan nomor antrean baru untuk layanan ini
        max_queue = db.query(func.max(models.Queue.queue_number)).filter(
            models.Queue.service_id == service_id,
            func.date(models.Queue.registration_time) == today
        ).scalar()
        new_queue_number = (max_queue or 0) + 1
        
        display_id = f"{service.prefix}{new_queue_number}"

        new_queue_entry = models.Queue(
            queue_id_display=display_id,
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