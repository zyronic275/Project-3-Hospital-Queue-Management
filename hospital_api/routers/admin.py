from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/admin",
    tags=["Admin Panel"])

# --- Endpoints for Services ---
@router.post("/services/", response_model=schemas.Service)
def create_new_service(service: schemas.ServiceCreate, db: Session = Depends(get_db)):
    return crud.create_service(db=db, service=service)

@router.get("/services/", response_model=List[schemas.Service])
def read_all_services(db: Session = Depends(get_db)):
    return crud.get_services(db=db)

# --- Endpoints for Doctors ---
@router.post("/doctors/", response_model=schemas.Doctor)
def create_new_doctor(doctor: schemas.DoctorBase, db: Session = Depends(get_db)):
    return crud.create_doctor(db=db, doctor=doctor)

@router.get("/doctors/", response_model=List[schemas.Doctor])
def read_all_doctors(db: Session = Depends(get_db)):
    return crud.get_doctors(db=db)
    
@router.put("/doctors/{doctor_id}", response_model=schemas.Doctor)
def update_existing_doctor(doctor_id: int, doctor: schemas.DoctorBase, db: Session = Depends(get_db)):
    # Pastikan fungsi crud.update_doctor ada di crud.py
    updated_doctor = crud.update_doctor(db=db, doctor_id=doctor_id, doctor=doctor)
    if not updated_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return updated_doctor

@router.delete("/services/{service_id}", response_model=schemas.Service)
def delete_existing_service(service_id: int, db: Session = Depends(get_db)):
    deleted_service = crud.delete_service(db, service_id=service_id)
    if not deleted_service:
        raise HTTPException(status_code=404, detail="Service not found")
    return deleted_service

@router.delete("/doctors/{doctor_id}", response_model=schemas.Doctor)
def delete_existing_doctor(doctor_id: int, db: Session = Depends(get_db)):
    deleted_doctor = crud.delete_doctor(db, doctor_id=doctor_id)
    if not deleted_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return deleted_doctor

# --- Endpoint untuk Menghubungkan Dokter dan Layanan ---
@router.post("/doctors/{doctor_id}/assign-service/", response_model=schemas.Doctor)
def assign_service_to_doctor_endpoint(doctor_id: int, service_id: int, db: Session = Depends(get_db)):
    doctor = crud.assign_service_to_doctor(db=db, doctor_id=doctor_id, service_id=service_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor or Service not found")
    return doctor