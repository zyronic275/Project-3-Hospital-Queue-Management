# hospital_api/routers/clinics.py

from fastapi import APIRouter, HTTPException
from typing import List
from .. import schemas, storage

router = APIRouter(
    prefix="/clinics",
    tags=["Clinics (Admin)"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Clinic)
def create_clinic(clinic: schemas.ClinicCreate):
    db_clinic = storage.get_clinic_by_name(clinic.name)
    if db_clinic:
        raise HTTPException(status_code=400, detail="Clinic with this name already exists")
    return storage.create_clinic(clinic_create=clinic)

@router.get("/", response_model=List[schemas.Clinic])
def read_clinics():
    return storage.get_clinics()

@router.delete("/{clinic_id}", response_model=schemas.Clinic)
def delete_clinic(clinic_id: int):
    db_clinic = storage.delete_clinic(clinic_id=clinic_id)
    if db_clinic is None:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return db_clinic

