from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, datetime, time

class PoliCreate(BaseModel):
    poli: str = Field(..., examples=["Poli Mata"])
    prefix: str = Field(..., examples=["MATA"])

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
    practice_start_time: Optional[str] = None
    practice_end_time: Optional[str] = None

class RegistrationFinal(BaseModel):
    nama_pasien: str = Field(..., examples=["Budi"])
    poli: str = Field(..., examples=["Poli Mata"])
    doctor_id: int = Field(..., examples=[1])
    visit_date: date = Field(..., examples=["2025-11-29"])

# UPDATED: Support input string (untuk nomor antrean)
class ScanRequest(BaseModel):
    barcode_data: str = Field(..., description="ID (123) atau No Antrean (GIGI-001-005)")
    location: str = Field(..., description="'arrival', 'clinic', atau 'finish'")

class UpdateQueueStatus(BaseModel):
    action: str = Field(..., examples=["call_patient"])

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