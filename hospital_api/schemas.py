from pydantic import BaseModel, Field
from datetime import datetime, time, date
from typing import List, Optional
from enum import Enum

# --- PERUBAHAN 1: Enum Status dalam Bahasa Indonesia ---
# Validasi sekarang akan memaksa penggunaan salah satu dari nilai ini.
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
    services: List[int]

class PatientBase(BaseModel):
    name: str

class QueueBase(BaseModel):
    # Menggunakan Enum Bahasa Indonesia dengan nilai default 'menunggu'
    status: QueueStatus = QueueStatus.menunggu

# --- Skema untuk Membuat Data (Create) ---

class ServiceCreate(ServiceBase):
    pass

class DoctorCreate(DoctorBase):
    pass

# --- Skema untuk Memperbarui Data (Update) ---

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
    # Menggunakan Enum Bahasa Indonesia untuk validasi input
    status: QueueStatus

# --- Skema Respons API (Model Lengkap dengan ID) ---

class ServiceSchema(ServiceBase):
    id: int
    class Config:
        from_attributes = True

class DoctorSchema(DoctorBase):
    id: int
    class Config:
        from_attributes = True

class PatientSchema(PatientBase):
    id: int
    class Config:
        from_attributes = True

class QueueSchema(QueueBase):
    id: int
    queue_id_display: str
    queue_number: int
    registration_time: datetime = Field(default_factory=datetime.now)
    patient_id: int
    service_id: int
    doctor_id: int
    class Config:
        from_attributes = True

# --- Skema untuk Registrasi & Tiket ---

class RegistrationRequest(BaseModel):
    patient_name: str
    service_ids: List[int]
    doctor_id: Optional[int] = None

class Ticket(BaseModel):
    service: ServiceSchema
    queue_number: str
    doctor: DoctorSchema

class RegistrationResponse(BaseModel):
    patient: PatientSchema
    tickets: List[Ticket]

# --- Skema Baru untuk Ketersediaan Dokter ---
class DoctorAvailableSchema(DoctorSchema):
    remaining_quota: int

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

