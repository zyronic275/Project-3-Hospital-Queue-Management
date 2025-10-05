from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas
from ..database import get_db

router = APIRouter(
    prefix="/queues",
    tags=["Queue Management (for Doctors)"],
)

@router.get("/today/{service_id}", response_model=List[schemas.QueueTicket])
def get_todays_queue(service_id: int, db: Session = Depends(get_db)):
    """Melihat daftar antrean hari ini untuk sebuah poli/layanan."""
    return crud.get_todays_queues_by_service(db=db, service_id=service_id)

@router.patch("/{queue_id}", response_model=schemas.QueueTicket)
def update_queue_status_and_notes(queue_id: int, update_data: schemas.QueueUpdate, db: Session = Depends(get_db)):
    """Mengubah status pasien dan menambahkan catatan kunjungan."""
    updated_queue = crud.update_queue(db=db, queue_id=queue_id, update_data=update_data)
    if not updated_queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    return updated_queue