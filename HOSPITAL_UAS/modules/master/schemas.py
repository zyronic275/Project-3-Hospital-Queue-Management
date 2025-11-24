from pydantic import BaseModel, Field
from typing import Optional, List

# --- Service Schemas ---
class ServiceCreate(BaseModel):
    name: str = Field(..., max_length=100)
    prefix: str = Field(..., max_length=4)

class ServiceResponse(BaseModel):
    id: int
    name: str
    prefix: str
    is_active: bool
    
    class Config:
        from_attributes = True

# --- Doctor Schemas (DIUBAH) ---
class DoctorCreate(BaseModel):
    doctor_name: str = Field(..., max_length=100)
    
    # DIUBAH: Kunci asing
    service_id: int 
    
    is_active: Optional[bool] = True

class DoctorResponse(BaseModel):
    id: int
    doctor_name: str
    service_id: int
    
    # Tambahan: Untuk respons yang lebih informatif di frontend
    service_name: str 
    
    is_active: bool
    
    class Config:
        from_attributes = True

# Catatan: Skema DoctorCreate menggunakan service_id.
# Skema DoctorResponse menggunakan service_id dan service_name (harus diambil oleh routers).