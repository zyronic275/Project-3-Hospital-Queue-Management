from pydantic import BaseModel, Field
from datetime import datetime, time
from typing import List, Optional

# --- Skema Dasar ---

class ServiceBase(BaseModel):
    name: str
    prefix: str = Field(..., max_length=1)

class DoctorBase(BaseModel):
    doctor_code: str
    name: str
    practice_start_time: time # DITAMBAHKAN
    practice_end_time: time
    max_patients: int
    services: List[int]

class PatientSchema(BaseModel):
    id: int
    name: str

class QueueBase(BaseModel):
    patient_id: int
    service_id: int
    doctor_id: int

# --- Skema untuk Response (Keluaran dari API) ---

class ServiceSchema(ServiceBase):
    id: int

class DoctorSchema(DoctorBase):
    id: int

class QueueSchema(QueueBase):
    id: int
    queue_id_display: str
    queue_number: int
    registration_time: datetime = Field(default_factory=datetime.now)
    status: str = "waiting"

class Ticket(BaseModel):
    service: ServiceSchema
    queue_number: str
    doctor: DoctorSchema

class RegistrationResponse(BaseModel):
    patient: PatientSchema
    tickets: List[Ticket]

# --- Skema untuk Request (Masukan ke API) ---

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    prefix: Optional[str] = Field(None, max_length=1)

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(BaseModel):
    doctor_code: Optional[str] = None
    name: Optional[str] = None
    practice_start_time: Optional[time] = None # DITAMBAHKAN
    practice_end_time: Optional[time] = None
    max_patients: Optional[int] = None
    services: Optional[List[int]] = None

class RegistrationRequest(BaseModel):
    patient_name: str
    service_ids: List[int]

class QueueStatusUpdate(BaseModel):
    status: str

# --- Skema untuk Monitoring ---
class ClinicStatus(BaseModel):
    service_id: int
    service_name: str
    doctors_count: int
    max_patients_total: int
    patients_waiting: int
    patients_serving: int
    total_patients_today: int
    density_percentage: float

