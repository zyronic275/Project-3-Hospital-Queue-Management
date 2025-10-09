# hospital_api/routers/doctors.py

from fastapi import APIRouter, HTTPException
from typing import List
from .. import schemas, storage

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors (Admin)"],
    responses={404: {"description": "Not found"}},
)

@router.get("/read", response_model=List[schemas.Doctor])
def get_doctors():
    return storage.get_doctors()

@router.post("/create", response_model=schemas.Doctor)
def create_doctor(doctor: schemas.DoctorCreate):
    if doctor.clinic_id not in storage.CLINICS:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    new_doctor = storage.create_doctor(doctor_create=doctor)
    if not new_doctor:
        raise HTTPException(status_code=400, detail="Clinic already has an assigned doctor")
    return new_doctor

@router.get("/read{doctor_id}", response_model=schemas.Doctor)
def get_doctor(doctor_id: int):
    db_doctor = storage.get_doctor(doctor_id=doctor_id)
    if db_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor

@router.put("/update{doctor_id}", response_model=schemas.Doctor)
def update_doctor(doctor_id: int, doctor: schemas.DoctorUpdate):
    # Check if doctor exists
    existing_doctor = storage.get_doctor(doctor_id=doctor_id)
    if existing_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Check if clinic exists
    if doctor.clinic_id not in storage.CLINICS:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    updated_doctor = storage.update_doctor(doctor_id=doctor_id, doctor_update=doctor)
    if not updated_doctor:
        raise HTTPException(status_code=400, detail="Cannot update doctor: clinic already has another assigned doctor")
    
    return updated_doctor
    
@router.delete("/delete{doctor_id}", response_model=schemas.Doctor)
def delete_doctor(doctor_id: int):
    db_doctor = storage.delete_doctor(doctor_id=doctor_id)
    if db_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor

