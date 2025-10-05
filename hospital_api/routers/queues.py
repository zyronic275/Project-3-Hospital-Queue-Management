# hospital_api/routers/queues.py

from fastapi import APIRouter, HTTPException
from typing import List
from .. import schemas, storage

router = APIRouter(
    tags=["Queue Management"],
)

@router.post("/register-patient/", response_model=schemas.Queue)
def register_patient_for_queue(queue: schemas.QueueCreate):
    if queue.clinic_id not in storage.CLINICS:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    new_queue = storage.create_queue(queue_create=queue)
    if not new_queue:
        raise HTTPException(status_code=404, detail="No doctor assigned to this clinic")
    return new_queue

@router.get("/queues/{clinic_id}", response_model=List[schemas.Queue])
def get_today_queue_for_clinic(clinic_id: int):
    if clinic_id not in storage.CLINICS:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return storage.get_queues_by_clinic(clinic_id=clinic_id)

@router.patch("/queues/{queue_id}/status", response_model=schemas.Queue)
def update_patient_status(queue_id: int, status_update: schemas.QueueUpdateStatus):
    updated_queue = storage.update_queue_status(queue_id=queue_id, new_status=status_update.status)
    if updated_queue is None:
        raise HTTPException(status_code=404, detail="Queue not found")
    return updated_queue