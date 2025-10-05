# hospital_api/schemas.py

from .models import QueueStatus
from pydantic import BaseModel
from typing import List, Optional
import datetime

# --- Service Schemas ---
# Harus didefinisikan sebelum Doctor agar bisa digunakan di dalam Doctor
class ServiceBase(BaseModel):
    name: str

class ServiceCreate(ServiceBase):
    prefix: str

class Service(ServiceBase):
    id: int
    prefix: str # <-- TAMBAHKAN BARIS INI
    
    class Config:
        from_attributes = True

# --- Doctor Schemas ---
class DoctorBase(BaseModel):
    name: str

# ▼▼▼ BAGIAN YANG DIPERBAIKI ADA DI SINI ▼▼▼
class Doctor(DoctorBase):
    id: int
    services: List[Service] = [] # Menambahkan kolom untuk daftar layanan

    class Config:
        from_attributes = True

# --- Patient Schemas ---
class PatientBase(BaseModel):
    name: str

class Patient(PatientBase):
    id: int
    class Config:
        from_attributes = True

# --- Queue & Registration Schemas ---
class QueueRegistrationRequest(BaseModel):
    patient_name: str
    service_ids: List[int]

class Queue(BaseModel):
    id: int
    queue_id_display: str
    queue_number: int
    status: QueueStatus
    visit_notes: Optional[str] = None
    patient: Patient
    service: Service
    doctor: Doctor

    class Config:
        from_attributes = True

class QueueTicket(BaseModel):
    id: int # Tambahkan ID agar bisa di-query nanti
    queue_id_display: str
    queue_number: int
    status: QueueStatus
    service: Service
    doctor: Doctor
    patient: Patient # Tambahkan data pasien agar lebih informatif
    visit_notes: Optional[str] = None

    class Config:
        from_attributes = True

class QueueRegistrationResponse(BaseModel):
    patient: Patient
    tickets: List[QueueTicket]

class QueueUpdate(BaseModel):
    status: QueueStatus
    visit_notes: Optional[str] = None