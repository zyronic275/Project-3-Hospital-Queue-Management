from pydantic import BaseModel
from typing import List, Optional
import datetime
from .models import QueueStatus

class ServiceBase(BaseModel):
    name: str
class ServiceCreate(ServiceBase):
    prefix: str
class Service(ServiceBase):
    id: int
    prefix: str
    class Config:
        from_attributes = True

class DoctorBase(BaseModel):
    name: str
    start_time: Optional[datetime.time] = None
    end_time: Optional[datetime.time] = None
    max_patients: Optional[int] = None
class Doctor(DoctorBase):
    id: int
    services: List[Service] = []
    class Config:
        from_attributes = True

class PatientBase(BaseModel):
    name: str
class Patient(PatientBase):
    id: int
    class Config:
        from_attributes = True

class QueueUpdate(BaseModel):
    status: QueueStatus
    visit_notes: Optional[str] = None
    
class QueueTicket(BaseModel):
    id: int
    queue_id_display: str
    status: QueueStatus
    service: Service
    doctor: Doctor
    patient: Patient
    class Config:
        from_attributes = True

class QueueUpdate(BaseModel):
    status: QueueStatus
    visit_notes: Optional[str] = None
        
class RegistrationRequest(BaseModel):
    patient_name: str
    service_ids: List[int]

class RegistrationResponse(BaseModel):
    patient: Patient
    tickets: List[QueueTicket]

class ServiceDensity(BaseModel):
    service_name: str
    total_patients_today: int
    waiting: int
    in_service: int
    finished: int

class DensityReport(BaseModel):
    report_date: datetime.date
    hospital_total_patients_today: int
    density_per_service: List[ServiceDensity]