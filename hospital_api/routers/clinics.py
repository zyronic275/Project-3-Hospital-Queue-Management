# hospital_api/routers/clinics.py

from fastapi import APIRouter, HTTPException
from typing import List
from .. import schemas, storage

router = APIRouter(
    prefix="/clinics",
    tags=["Clinics (Admin)"],
    responses={404: {"description": "Not found"}},
)

<<<<<<< HEAD
@router.post("/", response_model=schemas.Clinic)
=======
@router.post("/create", response_model=schemas.Clinic)
>>>>>>> main
def create_clinic(clinic: schemas.ClinicCreate):
    db_clinic = storage.get_clinic_by_name(clinic.name)
    if db_clinic:
        raise HTTPException(status_code=400, detail="Clinic with this name already exists")
    return storage.create_clinic(clinic_create=clinic)

<<<<<<< HEAD
@router.get("/", response_model=List[schemas.Clinic])
def read_clinics():
    return storage.get_clinics()

@router.delete("/{clinic_id}", response_model=schemas.Clinic)
=======
@router.get("/read", response_model=List[schemas.Clinic])
def read_clinics():
    return storage.get_clinics()


@router.get("/read{clinic_id}", response_model=schemas.Clinic)
def read_clinic(clinic_id: int):
    db_clinic = storage.get_clinic(clinic_id=clinic_id)
    if db_clinic is None:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return db_clinic


@router.put("/update{clinic_id}", response_model=schemas.Clinic)
def update_clinic(clinic_id: int, clinic: schemas.ClinicUpdate):
    # Check if clinic exists
    existing_clinic = storage.get_clinic(clinic_id=clinic_id)
    if existing_clinic is None:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    # Check if new name already exists (if it's different from current name)
    if existing_clinic.name != clinic.name:
        db_clinic_with_name = storage.get_clinic_by_name(clinic.name)
        if db_clinic_with_name:
            raise HTTPException(status_code=400, detail="Clinic with this name already exists")
    
    updated_clinic = storage.update_clinic(clinic_id=clinic_id, clinic_update=clinic)
    return updated_clinic


@router.delete("/delete{clinic_id}", response_model=schemas.Clinic)
>>>>>>> main
def delete_clinic(clinic_id: int):
    db_clinic = storage.delete_clinic(clinic_id=clinic_id)
    if db_clinic is None:
        raise HTTPException(status_code=404, detail="Clinic not found")
<<<<<<< HEAD
    return db_clinic
=======
    return db_clinic
>>>>>>> main
