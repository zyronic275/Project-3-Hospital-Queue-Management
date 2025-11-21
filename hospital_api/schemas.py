from pydantic import BaseModel, Field, field_validator
from datetime import datetime, time
from typing import List, Optional, Any
from enum import Enum

class QueueStatus(str, Enum):
    menunggu = "menunggu"
    sedang_dilayani = "sedang dilayani"
    selesai = "selesai"

# --- Skema Dasar ---

class ServiceBase(BaseModel):
    name: str
    prefix: str = Field(..., max_length=4)

class DoctorBase(BaseModel):
    doctor_code: str
    name: str
    practice_start_time: time
    practice_end_time: time
    max_patients: int
    # Input expects IDs
    services: List[int] 

class PatientBase(BaseModel):
    name: str

class QueueBase(BaseModel):
    status: QueueStatus = QueueStatus.menunggu

# --- Create/Update Schemas ---

class ServiceCreate(ServiceBase):
    pass

class DoctorCreate(DoctorBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    prefix: Optional[str] = Field(None, max_length=4)

class DoctorUpdate(BaseModel):
    doctor_code: Optional[str] = None
    name: Optional[str] = None
    practice_start_time: Optional[time] = None
    practice_end_time: Optional[time] = None
    max_patients: Optional[int] = None
    services: Optional[List[int]] = None

class QueueStatusUpdate(BaseModel):
    status: QueueStatus

# --- Response Schemas (The Important Fix) ---

class ServiceSchema(ServiceBase):
    id: int
    class Config:
        from_attributes = True

class DoctorSchema(DoctorBase):
    id: int
    
    class Config:
        from_attributes = True

    # FIX: This converts the SQL "List of Service Objects" into "List of Ints"
    @field_validator('services', mode='before')
    def parse_services(cls, v: Any):
        # If v is a list of objects (SQLAlchemy models), extract IDs
        if v and isinstance(v, list) and hasattr(v[0], 'id'):
            return [item.id for item in v]
        return v

class PatientSchema(PatientBase):
    id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    class Config:
        from_attributes = True

class QueueSchema(QueueBase):
    id: int
    queue_id_display: str
    queue_number: int
    registration_time: datetime
    patient_id: int
    service_id: int
    doctor_id: int
    class Config:
        from_attributes = True

# --- Registration & Ticket ---

class Ticket(BaseModel):
    service: ServiceSchema
    queue_number: str
    doctor: DoctorSchema

class RegistrationRequest(BaseModel):
    patient_name: str
    service_ids: List[int]
    doctor_id: Optional[int] = None

class RegistrationResponse(BaseModel):
    patient: PatientSchema
    tickets: List[Ticket]

class DoctorAvailableSchema(DoctorSchema):
    remaining_quota: int

class ClinicStatus(BaseModel):
    service_id: int
    service_name: str
    doctors_count: int
    max_patients_total: int
    patients_waiting: int
    patients_serving: int
    total_patients_today: int
    density_percentage: float