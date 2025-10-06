from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import datetime # <-- PASTIKAN IMPORT INI ADA

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/doctor",
    tags=["Doctor View"],
)

@router.get("/queues/{service_id}", response_model=List[schemas.QueueTicket])
def get_todays_queue_for_doctor(service_id: int, db: Session = Depends(get_db)):
    """Endpoint untuk dokter melihat daftar antrean hari ini di polinya."""
    today = datetime.date.today()
    return db.query(models.Queue).filter(
        models.Queue.service_id == service_id,
        func.date(models.Queue.registration_time) == today
    ).order_by(models.Queue.queue_number).all()

@router.patch("/queues/{queue_id}", response_model=schemas.QueueTicket)
def update_queue_status(queue_id: int, update_data: schemas.QueueUpdate, db: Session = Depends(get_db)):
    """Endpoint untuk dokter mengubah status pasien dan menambahkan catatan."""
    updated_queue = crud.update_queue(db=db, queue_id=queue_id, update_data=update_data)
    if not updated_queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan")
    return updated_queue