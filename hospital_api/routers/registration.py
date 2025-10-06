# hospital_api/routers/registration.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from .. import models, schemas
from ..database import get_db
import datetime

router = APIRouter(tags=["Patient Registration"])

@router.post("/register", response_model=schemas.RegistrationResponse)
def register_patient_for_services(request: schemas.RegistrationRequest, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.name == request.patient_name).first()
    if not patient:
        patient = models.Patient(name=request.patient_name)
        db.add(patient)
        db.commit()
        db.refresh(patient)

    response_tickets = []
    today = datetime.date.today()
    now_time = datetime.datetime.now().time()

    for service_id in request.service_ids:
        service = db.query(models.Service).filter(models.Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Layanan dengan ID {service_id} tidak ditemukan.")

        # Langkah 1: Saring dokter yang sedang praktek SAAT INI
        practicing_doctors = [
            doc for doc in service.doctors 
            if doc.start_time <= now_time and now_time < doc.end_time
        ]
        
        if not practicing_doctors:
            raise HTTPException(status_code=400, detail=f"Tidak ada dokter yang praktek untuk layanan '{service.name}' saat ini.")

        # Langkah 2: Dari yang praktek, saring yang kuotanya BELUM PENUH
        available_doctors = []
        for doc in practicing_doctors:
            patients_today = db.query(models.Queue).filter(
                models.Queue.doctor_id == doc.id,
                func.date(models.Queue.registration_time) == today
            ).count()
            if patients_today < doc.max_patients:
                available_doctors.append(doc)
            
        
        if not available_doctors:
            raise HTTPException(status_code=400, detail=f"Semua dokter untuk layanan '{service.name}' sudah penuh.")

        # Langkah 3: Terapkan Round-Robin pada dokter yang benar-benar tersedia
        todays_queue_count_for_service = db.query(models.Queue).filter(
            models.Queue.service_id == service_id,
            func.date(models.Queue.registration_time) == today
        ).count()
        
        doctor_index = todays_queue_count_for_service % len(available_doctors)
        assigned_doctor = sorted(available_doctors, key=lambda d: d.id)[doctor_index]
        
        # Langkah 4: Buat nomor antrean
        queue_number = db.query(models.Queue).filter(
            models.Queue.doctor_id == assigned_doctor.id,
            models.Queue.service_id == service.id,
            func.date(models.Queue.registration_time) == today
        ).count() + 1
        
        display_id = f"{service.prefix}{queue_number}"

        new_queue_entry = models.Queue(
            queue_id_display=display_id, queue_number=queue_number,
            patient_id=patient.id, service_id=service.id,
            doctor_id=assigned_doctor.id
        )
        db.add(new_queue_entry); db.commit(); db.refresh(new_queue_entry)
        response_tickets.append(new_queue_entry)
    
    return {"patient": patient, "tickets": response_tickets}