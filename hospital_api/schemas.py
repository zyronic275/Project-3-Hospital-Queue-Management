# hospital_api/schemas.py

from pydantic import BaseModel
from datetime import datetime
import enum

class QueueStatus(str, enum.Enum):
    MENUNGGU = "menunggu"
    DILAYANI = "sedang dilayani"
    SELESAI = "selesai"

# --- Clinic Schemas ---
class ClinicBase(BaseModel):
    name: str

class ClinicCreate(ClinicBase):
    pass

class ClinicUpdate(ClinicBase):
    pass

class Clinic(ClinicBase):
    id: int

# --- Doctor Schemas ---
class DoctorBase(BaseModel):
    name: str
    specialization: str

class DoctorCreate(DoctorBase):
    clinic_id: int

class DoctorUpdate(DoctorBase):
    clinic_id: int
    
class Doctor(DoctorBase):
    id: int
    clinic_id: int
        
# --- Queue Schemas ---
class QueueBase(BaseModel):
    patient_name: str

class QueueCreate(QueueBase):
    clinic_id: int
    
class QueueUpdateStatus(BaseModel):
    status: QueueStatus

class Queue(QueueBase):
    id: int
    queue_number: int
    status: QueueStatus
    registration_time: datetime
    clinic_id: int
    doctor_id: int