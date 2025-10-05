# hospital_api/routers/queues.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(
    tags=["Queue Management"],
)

@router.post("/register-patient/", response_model=schemas.Queue)
def register_patient_for_queue(queue: schemas.QueueCreate, db: Session = Depends(get_db)):
    """
    Patient registration to get a queue number.
    """
    # Check if clinic and doctor exist
    db_clinic = crud.get_clinic(db, clinic_id=queue.clinic_id)
    if not db_clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    db_doctor = crud.get_doctor(db, doctor_id=queue.doctor_id)
    if not db_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    return crud.create_queue(db=db, queue=queue)

@router.get("/queues/{clinic_id}", response_model=List[schemas.Queue])
def get_today_queue_for_clinic(clinic_id: int, db: Session = Depends(get_db)):
    """
    Get the list of today's queue for a specific clinic.
    """
    return crud.get_queues_by_clinic(db=db, clinic_id=clinic_id)

@router.patch("/queues/{queue_id}/status", response_model=schemas.Queue)
def update_patient_status(queue_id: int, status_update: schemas.QueueUpdateStatus, db: Session = Depends(get_db)):
    """
    Doctor/medical staff action to update patient status 
    (e.g., call patient, finish consultation).
    """
    updated_queue = crud.update_queue_status(db=db, queue_id=queue_id, status=status_update.status)
    if updated_queue is None:
        raise HTTPException(status_code=404, detail="Queue not found")
    return updated_queue

@router.get("/history/{patient_name}", response_model=List[schemas.Queue])
def get_patient_visit_history(patient_name: str, db: Session = Depends(get_db)):
    """
    Get the complete visit history for a specific patient by name.
    """
    return crud.get_visit_history(db=db, patient_name=patient_name)