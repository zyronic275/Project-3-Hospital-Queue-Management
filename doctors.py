# hospital_api/routers/doctors.py

from fastapi import APIRouter, HTTPException
from .. import schemas, storage

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors (Admin)"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Doctor)
def create_doctor(doctor: schemas.DoctorCreate):
    if doctor.clinic_id not in storage.CLINICS:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    new_doctor = storage.create_doctor(doctor_create=doctor)
    if not new_doctor:
        raise HTTPException(status_code=400, detail="Clinic already has an assigned doctor")
    return new_doctor
    
@router.delete("/{doctor_id}", response_model=schemas.Doctor)
def delete_doctor(doctor_id: int):
    db_doctor = storage.delete_doctor(doctor_id=doctor_id)
    if db_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor
