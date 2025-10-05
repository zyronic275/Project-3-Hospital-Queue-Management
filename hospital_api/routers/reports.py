from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas
from ..database import get_db

router = APIRouter(
    prefix="/reports",
    tags=["Reports & History"],
)

@router.get("/history/patient/{patient_id}", response_model=List[schemas.QueueTicket])
def get_patient_visit_history(patient_id: int, db: Session = Depends(get_db)):
    """Melihat seluruh riwayat kunjungan seorang pasien."""
    return crud.get_patient_history(db=db, patient_id=patient_id)

# Endpoint untuk memantau kepadatan antrean (outputnya perlu schema khusus jika ingin lebih rapi)
@router.get("/density/today")
def get_todays_queue_density(db: Session = Depends(get_db)):
    """Melihat jumlah pasien dan statusnya di setiap poli hari ini."""
    return crud.get_queue_density_today(db=db)