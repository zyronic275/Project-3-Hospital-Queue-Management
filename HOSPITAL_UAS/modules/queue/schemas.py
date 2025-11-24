from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time
from enum import Enum
from .models import VisitStatus 

# Enum untuk Pilihan Asuransi
class InsuranceType(str, Enum):
    PRIBADI = "Pribadi"
    ASURANSI = "Asuransi"
    BPJS = "BPJS"

# --- 1. Skema Input untuk Pendaftaran (VisitCreate) ---
class VisitCreate(BaseModel):
    patient_name: str = Field(..., max_length=100)
    patient_mr_number: Optional[str] = Field(None, max_length=20)
    gender: str = Field(..., max_length=20) # MALE atau FEMALE
    age: int = Field(..., gt=0) 
    
    insurance_type: InsuranceType 
    
    doctor_id: int = Field(..., gt=0) 

    # Field yang digunakan untuk filtering, akan dihapus dari data Visit
    consultation_time: time 

# --- 2. Skema Input untuk Update Status (VisitUpdateStatus) ---
class VisitUpdateStatus(BaseModel):
    status: VisitStatus 

# --- 3. Skema Output/Response (VisitResponse) ---
class VisitResponse(BaseModel):
    id: int
    queue_number: str
    queue_sequence: int 
    
    patient_name: str
    patient_mr_number: Optional[str] = None
    doctor_id: int
    status: VisitStatus
    
    t_register: datetime
    t_in_queue: Optional[datetime] = None
    t_called: Optional[datetime] = None
    t_in_service: Optional[datetime] = None
    t_service_finish: Optional[datetime] = None
    t_finished: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Skema Metrik Dashboard ---
class DashboardServiceMetric(BaseModel):
    id: int
    service_name: str
    doctors_count: int
    density_percentage: float
    total_patients_today: int
    max_patients_total: int
    patients_waiting: int 
    patients_serving: int 
    
    class Config:
        from_attributes = True