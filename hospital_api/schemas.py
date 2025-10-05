# hospital_api/schemas.py

from pydantic import BaseModel
from typing import List, Optional
import datetime
from .models import QueueStatus # Import the enum from models

# --- Clinic Schemas ---
class ClinicBase(BaseModel):
    name: str

class ClinicCreate(ClinicBase):
    pass

class Clinic(ClinicBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Doctor Schemas ---
class DoctorBase(BaseModel):
    name: str
    specialization: str

class DoctorCreate(DoctorBase):
    clinic_id: int

class Doctor(DoctorBase):
    id: int
    clinic_id: int
    
    class Config:
        from_attributes = True
        
# --- Queue (Patient Registration & Visit History) Schemas ---
class QueueBase(BaseModel):
    patient_name: str

class QueueCreate(QueueBase):
    clinic_id: int
    doctor_id: int
    
class QueueUpdateStatus(BaseModel):
    status: QueueStatus

class Queue(QueueBase):
    id: int
    queue_number: int
    status: QueueStatus
    registration_time: datetime.datetime
    clinic_id: int
    doctor_id: int
    
    class Config:
        from_attributes = True