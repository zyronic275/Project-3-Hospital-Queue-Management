# schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date, time

# --- Base Schemas ---\
class ServiceBase(BaseModel):
    name: str
    prefix: str = Field(max_length=5)
    class Config:
        from_attributes = True

class DoctorBase(BaseModel):
    doctor_code: str = Field(max_length=10)
    name: str
    practice_start_time: time
    practice_end_time: time
    max_patients: int
    class Config:
        from_attributes = True

class PatientBase(BaseModel):
    name: str
    date_of_birth: date
    class Config:
        from_attributes = True

# --- ADMIN CRUD Schemas ---\
class ServiceCreate(ServiceBase): pass
class ServiceUpdate(ServiceBase):
    name: Optional[str] = None
    prefix: Optional[str] = None
class ServiceSchema(ServiceBase):
    id: int

class DoctorSchema(DoctorBase):
    id: int
    services: List[ServiceSchema] = []
    
class DoctorCreate(DoctorBase):
    services: List[int] # List ID Service

class DoctorUpdate(DoctorBase):
    doctor_code: Optional[str] = None
    name: Optional[str] = None
    practice_start_time: Optional[time] = None
    practice_end_time: Optional[time] = None
    max_patients: Optional[int] = None
    services: Optional[List[int]] = None

# --- PUBLIC/QUEUE SCHEMAS ---\
class PatientSchema(PatientBase):
    id: int

class DoctorAvailableSchema(DoctorSchema):
    remaining_quota: int = 0
    class Config:
        from_attributes = True

class Ticket(BaseModel):
    service: ServiceSchema
    queue_number: str
    doctor: DoctorSchema
    qr_code_base64: str # <--- FIELD BARU UNTUK QR CODE
    class Config:
        from_attributes = True

class RegistrationRequest(BaseModel):
    patient_name: str
    date_of_birth: date
    service_ids: List[int]
    doctor_id: Optional[int] = None

class RegistrationResponse(BaseModel): # <--- CLASS BARU UNTUK RESPON QR
    patient: PatientSchema
    tickets: List[Ticket]

class ClinicStatus(BaseModel):
    service_id: int
    service_name: str
    doctors_count: int
    max_patients_total: int
    patients_waiting: int
    patients_serving: int
    total_patients_today: int
    density_percentage: float

class QueueSchema(BaseModel):
    id: int
    queue_id_display: str
    queue_number: int
    status: str
    registration_time: datetime
    patient_id: int
    service_id: int
    doctor_id: int
    class Config:
        from_attributes = True

class QueueStatusUpdate(BaseModel):
    status: str # menunggu, sedang dilayani, selesai, tidak hadir