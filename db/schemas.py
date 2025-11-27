from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from enum import Enum

# enums
class VisitStatus(str, Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

# clinic
class ClinicBase(BaseModel):
    name: str
    location: Optional[str] = None

class ClinicCreate(ClinicBase):
    pass

class ClinicResponse(ClinicBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# doctor
class DoctorBase(BaseModel):
    name: str
    specialization: Optional[str] = None
    clinic_id: Optional[int] = None
    is_active: bool = True

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int
    clinic: Optional[ClinicResponse] = None
    class Config:
        from_attributes = True

# patient
class PatientBase(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    nik: str
    phone: Optional[str] = None
    dob: Optional[date] = None

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# visit
class VisitBase(BaseModel):
    patient_id: int
    doctor_id: int
    date_visit: date

class VisitCreate(VisitBase):
    pass 

class VisitUpdateStatus(BaseModel):
    status: VisitStatus
    medical_notes: Optional[str] = None

class VisitResponse(VisitBase):
    id: int
    queue_number: int
    status: VisitStatus
    medical_notes: Optional[str] = None
    created_at: datetime
    patient: Optional[PatientResponse] = None
    doctor: Optional[DoctorResponse] = None
    class Config:
        from_attributes = True