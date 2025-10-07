# hospital_api/routers/registration.py (Final In-Memory Version)
from fastapi import APIRouter, HTTPException
from typing import List
from .. import crud, schemas
import datetime

router = APIRouter(tags=["Patient Registration"])

def time_to_seconds(t: datetime.time) -> int:
    """Helper function to convert time object to total seconds from midnight."""
    return t.hour * 3600 + t.minute * 60 + t.second

@router.post("/register", response_model=schemas.RegistrationResponse)
def register_patient_for_services(request: schemas.RegistrationRequest):
    patient = crud.get_or_create_patient(request.patient_name)
    response_tickets = []
    
    today = datetime.date.today()
    # --- PERUBAHAN LOGIKA WAKTU DIMULAI DI SINI ---
    now_in_seconds = time_to_seconds(datetime.datetime.now().time())
    # --- AKHIR PERUBAHAN ---

    for service_id in request.service_ids:
        service = crud.get_service(service_id)
        if not service:
            raise HTTPException(status_code=404, detail=f"Layanan dengan ID {service_id} tidak ditemukan.")

        # 2. Cari dokter yang sedang praktek untuk layanan ini
        practicing_doctors = []
        for doc in service["doctors"]:
            start_seconds = time_to_seconds(doc["start_time"])
            end_seconds = time_to_seconds(doc["end_time"])

            # Bandingkan angka detik, bukan objek waktu
            if start_seconds <= now_in_seconds < end_seconds:
                practicing_doctors.append(doc)
        
        if not practicing_doctors:
            raise HTTPException(status_code=400, detail=f"Tidak ada dokter yang praktek untuk layanan '{service['name']}' saat ini.")

        # 3. Cari dokter yang tersedia (kuota belum penuh) dan paling sedikit pasiennya
        best_doctor = None
        min_patients = -1

        for doc in sorted(practicing_doctors, key=lambda d: d['id']):
            patients_today = len(crud.get_queues_for_doctor_today(doc["id"], today))
            
            if patients_today < doc["max_patients"]:
                if best_doctor is None or patients_today < min_patients:
                    min_patients = patients_today
                    best_doctor = doc
        
        if best_doctor is None:
            raise HTTPException(status_code=400, detail=f"Semua dokter untuk layanan '{service['name']}' sudah penuh.")

        assigned_doctor = best_doctor
        
        # 4. Buat antrean baru
        new_queue_entry = crud.create_queue(
            patient=patient, 
            service=service, 
            doctor=assigned_doctor
        )
        response_tickets.append(new_queue_entry)
    
    return {"patient": patient, "tickets": response_tickets}