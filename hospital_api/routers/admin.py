from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .. import crud, models, schemas

router = APIRouter(
    prefix="/admin",
    tags=["Admin Panel"])

# --- Endpoints for Services ---
@router.post("/services/", response_model=schemas.Service)
def create_new_service(service: schemas.ServiceCreate):
    return crud.create_service(service=service)

@router.get("/services/", response_model=List[schemas.Service])
def read_all_services():
    return crud.get_services()

# --- Endpoints for Doctors ---
@router.post("/doctors/", response_model=schemas.Doctor)
def create_new_doctor(doctor: schemas.DoctorBase):
    return crud.create_doctor(doctor=doctor)

@router.get("/doctors/", response_model=List[schemas.Doctor])
def read_all_doctors():
    return crud.get_doctors()
    
@router.put("/doctors/{doctor_id}", response_model=schemas.Doctor)
def update_existing_doctor(doctor_id: int, doctor: schemas.DoctorBase):
    # Pastikan fungsi crud.update_doctor ada di crud.py
    updated_doctor = crud.update_doctor(doctor_id=doctor_id, doctor=doctor)
    if not updated_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return updated_doctor

@router.delete("/services/{service_id}", response_model=schemas.Service)
def delete_existing_service(service_id: int):
    deleted_service = crud.delete_service(service_id=service_id)
    if not deleted_service:
        raise HTTPException(status_code=404, detail="Service not found")
    return deleted_service

@router.delete("/doctors/{doctor_id}", response_model=schemas.Doctor)
def delete_existing_doctor(doctor_id: int):
    deleted_doctor = crud.delete_doctor(doctor_id=doctor_id)
    if not deleted_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return deleted_doctor

# --- Endpoint untuk Menghubungkan Dokter dan Layanan ---
@router.post("/doctors/{doctor_id}/assign-service/", response_model=schemas.Doctor)
def assign_service_to_doctor_endpoint(doctor_id: int, service_id: int):
    doctor = crud.assign_service_to_doctor(doctor_id=doctor_id, service_id=service_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor or Service not found")
    return doctor