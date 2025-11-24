from pydantic import BaseModel, Field
from typing import Optional
from datetime import time
from enum import Enum

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

# Gender Restriction Enum
class GenderRestriction(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    NONE = "NONE"

# --- Service Schemas (DIUBAH) ---
class ServiceCreate(BaseModel):
    name: str = Field(..., max_length=100)
    prefix: str = Field(..., max_length=4)
    min_age: int = Field(0, ge=0)
    max_age: int = Field(100, ge=0)
    gender_restriction: GenderRestriction = GenderRestriction.NONE

class ServiceResponse(BaseModel):
    id: int
    name: str
    prefix: str
    min_age: int
    max_age: int
    gender_restriction: GenderRestriction
    is_active: bool
    
    class Config:
        from_attributes = True

# --- Doctor Schemas (DIUBAH) ---
class DoctorBase(BaseModel):
    doctor_name: str = Field(..., max_length=100)
    service_id: int 
    doctor_code: int = Field(..., gt=0) 
    max_patients: int = Field(50, gt=0)
    
    practice_start_time: time
    practice_end_time: time
    
    is_active: Optional[bool] = True

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int
    service_name: str
    
    class Config:
        from_attributes = True

class DoctorAvailableResponse(BaseModel):
    id: int
    doctor_name: str
    remaining_quota: int
    
    class Config:
        from_attributes = True