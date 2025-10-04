# hospital_api/schemas.py

from pydantic import BaseModel
from typing import List, Optional
import datetime

# --- Service Schemas ---
# Harus didefinisikan sebelum Doctor agar bisa digunakan di dalam Doctor
class ServiceBase(BaseModel):
    name: str

class ServiceCreate(ServiceBase):
    pass

class Service(ServiceBase):
    id: int
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

class QueueTicket(BaseModel):
    queue_number: int
    service: Service
    doctor: Doctor # Skema Doctor yang digunakan di sini sekarang sudah lengkap

class QueueRegistrationResponse(BaseModel):
    patient: Patient
    tickets: List[QueueTicket]