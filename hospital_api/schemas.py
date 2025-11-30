from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import date, datetime, time

# ==========================================
# 1. INPUT SCHEMAS
# ==========================================

class PoliCreate(BaseModel):
    poli: str = Field(..., examples=["Poli Mata"])
    prefix: str = Field(..., examples=["MATA"], description="Hanya huruf (A-Z), max 3-4 karakter")

    # VALIDASI BARU: PREFIX HARUS HURUF
    @field_validator('prefix')
    @classmethod
    def validate_prefix_alpha(cls, v: str):
        if not v.isalpha():
            raise ValueError('Prefix harus berupa HURUF saja (tidak boleh angka/simbol).')
        return v.upper()

class DoctorCreate(BaseModel):
    dokter: str = Field(..., examples=["Dr. Strange"])
    poli: str = Field(..., examples=["Poli Mata"])
    practice_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", examples=["08:00"])
    practice_end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", examples=["16:00"])
    max_patients: int = Field(default=20, examples=[20])
    doctor_id: Optional[int] = Field(default=None, examples=[0])

class DoctorUpdate(BaseModel):
    dokter: Optional[str] = None
    poli: Optional[str] = None
    max_patients: Optional[int] = None
    practice_start_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    practice_end_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")

class RegistrationFinal(BaseModel):
    nama_pasien: str = Field(..., examples=["Budi Santoso"])
    poli: str = Field(..., examples=["Poli Mata"])
    doctor_id: int = Field(..., examples=[1])
    visit_date: date = Field(..., examples=["2025-11-29"])

class ScanRequest(BaseModel):
    barcode_data: str = Field(..., description="ID atau No Antrean")
    location: str = Field(..., description="'arrival', 'clinic', 'finish'")

class UpdateQueueStatus(BaseModel):
    action: str = Field(..., examples=["call_patient"])

# ==========================================
# 2. OUTPUT SCHEMAS
# ==========================================

class PoliSchema(BaseModel):
    poli: str
    prefix: str
    model_config = ConfigDict(from_attributes=True)

class DoctorSchema(BaseModel):
    doctor_id: int
    dokter: str
    poli: str
    doctor_code: str
    practice_start_time: time
    practice_end_time: time
    max_patients: int
    model_config = ConfigDict(from_attributes=True)

class PelayananSchema(BaseModel):
    id: int
    nama_pasien: str
    dokter: str
    poli: str
    visit_date: date
    status_pelayanan: str
    queue_number: str      
    queue_sequence: int    
    checkin_time: Optional[datetime] = None
    clinic_entry_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ClinicStats(BaseModel):
    poli_name: str
    total_doctors: int
    total_patients_today: int
    patients_waiting: int
    patients_being_served: int
    patients_finished: int
    model_config = ConfigDict(from_attributes=True)