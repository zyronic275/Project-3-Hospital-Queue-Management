# hospital_api/routers/doctors.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors (Admin)"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Doctor)
def create_doctor(doctor: schemas.DoctorCreate, db: Session = Depends(get_db)):
    # Check if clinic exists
    db_clinic = crud.get_clinic(db, clinic_id=doctor.clinic_id)
    if not db_clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return crud.create_doctor(db=db, doctor=doctor)

@router.get("/", response_model=List[schemas.Doctor])
def read_doctors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    doctors = crud.get_doctors(db, skip=skip, limit=limit)
    return doctors
    
@router.delete("/{doctor_id}", response_model=schemas.Doctor)
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    db_doctor = crud.delete_doctor(db, doctor_id=doctor_id)
    if db_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor