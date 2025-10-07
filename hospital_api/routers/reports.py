# hospital_api/routers/reports.py

from fastapi import APIRouter
from typing import List
from .. import crud, schemas

router = APIRouter(
    prefix="/reports",
    tags=["Reports & History"],
)

@router.get("/history/patient/{patient_id}", response_model=List[schemas.QueueTicket])
def get_patient_visit_history(patient_id: int):
    """Melihat seluruh riwayat kunjungan seorang pasien."""
    return crud.get_patient_history(patient_id=patient_id)

@router.get("/density/today", response_model=schemas.DensityReport)
def get_todays_queue_density():
    """Melihat jumlah pasien dan statusnya di setiap poli hari ini."""
    return crud.get_queue_density_today()