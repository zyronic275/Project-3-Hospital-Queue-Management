from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, datetime, time

# ==========================================
# 1. INPUT SCHEMAS (Data Masuk dari User)
# ==========================================

class PoliCreate(BaseModel):
    poli: str = Field(..., examples=["Poli Mata"])
    prefix: str = Field(..., examples=["MATA"], description="Prefix kode antrean, harus unik")

class DoctorCreate(BaseModel):
    dokter: str = Field(..., examples=["Dr. Strange"])
    poli: str = Field(..., examples=["Poli Mata"], description="Nama Poli tempat dokter bekerja")
    
    # Format waktu string "HH:MM"
    practice_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", examples=["08:00"], description="Format Jam:Menit")
    practice_end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", examples=["16:00"], description="Format Jam:Menit")
    
    max_patients: int = Field(default=20, examples=[20])
    doctor_id: Optional[int] = Field(default=None, examples=[0], description="Kosongkan untuk Auto ID")

class DoctorUpdate(BaseModel):
    dokter: Optional[str] = None
    poli: Optional[str] = None
    max_patients: Optional[int] = None
    practice_start_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$", examples=["09:00"])
    practice_end_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$", examples=["17:00"])

class RegistrationFinal(BaseModel):
    nama_pasien: str = Field(..., examples=["Budi Santoso"])
    poli: str = Field(..., examples=["Poli Mata"], description="Nama Poli yang dituju")
    doctor_id: int = Field(..., examples=[1], description="ID Dokter yang dipilih")
    visit_date: date = Field(..., examples=["2025-11-29"])

class UpdateQueueStatus(BaseModel):
    action: str = Field(..., examples=["call_patient"], description="Isi dengan 'call_patient' atau 'finish'")

# ==========================================
# 2. OUTPUT SCHEMAS (Data Keluar ke API)
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
    
    # Menampilkan dua format nomor antrean
    queue_number: str      # String: GIGI-001-005
    queue_sequence: int    # Integer: 5
    
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