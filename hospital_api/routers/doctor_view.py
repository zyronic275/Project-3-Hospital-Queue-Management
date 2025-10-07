# hospital_api/routers/doctor_view.py

from fastapi import APIRouter, HTTPException
from typing import List
import datetime

# Import modul yang relevan dari aplikasi Anda
from .. import crud, schemas

router = APIRouter(
    prefix="/doctor",
    tags=["Doctor View"],
)

@router.get("/queues/{service_id}", response_model=List[schemas.QueueTicket])
def get_todays_queue_for_doctor(service_id: int):
    """Endpoint untuk dokter melihat daftar antrean hari ini di polinya."""
    # Logika untuk filter antrean berdasarkan service_id dan tanggal hari ini
    # sekarang bisa dilakukan langsung di sini atau di dalam fungsi crud baru.
    # Untuk kesederhanaan, kita bisa membuatnya di sini.
    all_queues = crud.get_all_queues() # Asumsi ada fungsi ini di crud.py
    today = datetime.date.today()
    
    todays_queue = [
        q for q in all_queues
        if q["service"]["id"] == service_id and
           q["registration_time"].date() == today
    ]
    
    # Urutkan berdasarkan nomor antrean
    return sorted(todays_queue, key=lambda q: q["queue_number"])


@router.patch("/queues/{queue_id}", response_model=schemas.QueueTicket)
def update_queue_status(queue_id: int, update_data: schemas.QueueUpdate):
    """Endpoint untuk dokter mengubah status pasien dan menambahkan catatan."""
    updated_queue = crud.update_queue(queue_id=queue_id, update_data=update_data)
    if not updated_queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan")
    return updated_queue