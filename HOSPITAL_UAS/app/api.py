from fastapi import APIRouter, Query
from typing import List

# Import modules dari dalam folder app
from app.schemas import CsvDataResponse, PatientRegistration, QueueItem, StatusUpdate
from app.services import (
    get_historical_samples, 
    register_patient_logic, 
    get_doctor_queue_logic, 
    update_status_logic,
    get_all_queues
)

router = APIRouter()

# --- A. FITUR HISTORY (LAZY LOAD) ---
@router.get("/history/sample", response_model=CsvDataResponse, tags=["History Data"])
def get_history_random(limit: int = Query(10, description="Jumlah data acak")):
    """Memicu pembacaan CSV secara acak (Lazy Load)"""
    data = get_historical_samples(limit)
    return {
        "status": "success",
        "count": len(data),
        "data": data
    }

# --- B. FITUR OPERASIONAL HARIAN ---
@router.post("/queue/register", response_model=QueueItem, tags=["Operasional"])
def register_patient(data: PatientRegistration):
    """Pendaftaran pasien baru (Nomor Antrean Berurut)"""
    return register_patient_logic(data)

@router.get("/doctor/queue", response_model=List[QueueItem], tags=["Dokter"])
def doctor_view_queue(doctor_name: str):
    """Dokter melihat pasien antreannya"""
    return get_doctor_queue_logic(doctor_name)

@router.put("/doctor/update/{queue_number}", response_model=QueueItem, tags=["Dokter"])
def doctor_update_status(queue_number: str, data: StatusUpdate):
    """Update status pasien (MENUNGGU -> DILAYANI -> SELESAI)"""
    return update_status_logic(queue_number, data.status, data.diagnosis)

@router.get("/admin/monitor", tags=["Admin"])
def admin_monitor():
    """Monitoring seluruh antrean aktif"""
    return {"total_active": len(get_all_queues()), "data": get_all_queues()}