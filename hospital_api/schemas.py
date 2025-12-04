from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional
from datetime import date, datetime, time

# --- VALIDATOR HELPER ---
def validate_not_empty(v: str, field_name: str):
    if not v or not v.strip():
        raise ValueError(f"{field_name} tidak boleh kosong.")
    return v.strip()

# ==========================================
# 1. INPUT SCHEMAS (DATA YANG DIKIRIM)
# ==========================================

class PoliCreate(BaseModel):
    poli: str = Field(..., min_length=3)
    prefix: str = Field(..., min_length=1, max_length=4)

    @field_validator('poli')
    def check_poli_name(cls, v): return validate_not_empty(v, "Nama Poli")

    @field_validator('prefix')
    def check_prefix(cls, v):
        v = validate_not_empty(v, "Prefix")
        if not v.isalpha(): raise ValueError('Prefix hanya boleh huruf (A-Z).')
        return v.upper()

    # CONTOH UNTUK SWAGGER
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "poli": "Poli Mata",
                "prefix": "MATA"
            }
        }
    )

class DoctorCreate(BaseModel):
    dokter: str = Field(..., min_length=3)
    poli: str = Field(...)
    practice_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Format HH:MM")
    practice_end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Format HH:MM")
    max_patients: int = Field(default=20, ge=1)
    doctor_id: Optional[int] = Field(default=None)

    @field_validator('dokter')
    def check_dokter_name(cls, v): return validate_not_empty(v, "Nama Dokter")

    @model_validator(mode='after')
    def check_times(self):
        try:
            t1 = datetime.strptime(self.practice_start_time, "%H:%M").time()
            t2 = datetime.strptime(self.practice_end_time, "%H:%M").time()
            if t2 <= t1: raise ValueError('Jam Selesai harus lebih akhir.')
        except ValueError as e:
            if "does not match format" in str(e): raise ValueError("Format jam salah (Gunakan HH:MM)")
            raise e
        return self

    # CONTOH UNTUK SWAGGER
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dokter": "Dr. Strange",
                "poli": "Poli Mata",
                "practice_start_time": "08:00",
                "practice_end_time": "16:00",
                "max_patients": 20,
                "doctor_id": 0
            }
        }
    )

class DoctorUpdate(BaseModel):
    dokter: Optional[str] = None
    poli: Optional[str] = None
    max_patients: Optional[int] = Field(default=None, ge=1)
    practice_start_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    practice_end_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")

    # CONTOH UNTUK SWAGGER (PUT)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dokter": "Dr. Strange Edited",
                "poli": "Poli Mata",
                "max_patients": 25,
                "practice_start_time": "09:00",
                "practice_end_time": "17:00"
            }
        }
    )

class RegistrationFinal(BaseModel):
    nama_pasien: str = Field(..., min_length=3)
    poli: str = Field(...)
    doctor_id: int = Field(...)
    visit_date: date = Field(...)

    @field_validator('nama_pasien')
    def check_pasien(cls, v): return validate_not_empty(v, "Nama Pasien")

    @field_validator('visit_date')
    def check_date(cls, v):
        if v < date.today(): raise ValueError('Tanggal tidak boleh masa lalu.')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nama_pasien": "Budi Santoso",
                "poli": "Poli Mata",
                "doctor_id": 1,
                "visit_date": "2025-12-01"
            }
        }
    )

class ScanRequest(BaseModel):
    # Hapus validasi integer/ID, fokus ke String
    barcode_data: str = Field(..., description="Nomor Antrean (Contoh: GIGI-001-001)")
    location: str = Field(..., pattern="^(arrival|clinic|finish)$")

    # KONFIGURASI SWAGGER UI (FIXED)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "barcode_data": "GIGI-001-001", # Contoh String (Bukan ID lagi)
                "location": "arrival"
            }
        }
    )

class UpdateQueueStatus(BaseModel):
    action: str = Field(...)

# ==========================================
# 2. OUTPUT SCHEMAS (DATA YANG DITERIMA DARI SERVER)
# ==========================================

class PoliSchema(BaseModel):
    poli: str
    prefix: str
    model_config = ConfigDict(from_attributes=True)

class DoctorSchema(BaseModel):
    # Ini yang akan muncul di RESPONSE BODY (Lengkap)
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
    doctor_schedule: Optional[str] = None 
    model_config = ConfigDict(from_attributes=True)

class ClinicStats(BaseModel):
    poli_name: str
    total_doctors: int
    total_patients_today: int
    patients_waiting: int
    patients_being_served: int
    patients_finished: int
    model_config = ConfigDict(from_attributes=True)