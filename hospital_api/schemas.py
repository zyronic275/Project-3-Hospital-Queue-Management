from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional
from datetime import date, datetime, time

<<<<<<< HEAD
def validate_not_empty(v: str, field_name: str):
    if not v or not v.strip():
        raise ValueError(f"{field_name} tidak boleh kosong.")
    return v.strip()

class PoliCreate(BaseModel):
    poli: str = Field(..., min_length=3, examples=["Poli Mata"])
    prefix: str = Field(..., min_length=2, max_length=5, examples=["MATA"])

    @field_validator('poli')
    def check_poli_name(cls, v): return validate_not_empty(v, "Nama Poli")

    @field_validator('prefix')
    def check_prefix(cls, v):
        v = validate_not_empty(v, "Prefix")
        if not v.isalpha(): raise ValueError('Prefix hanya huruf (A-Z).')
        return v.upper()

class DoctorCreate(BaseModel):
    dokter: str = Field(..., min_length=3, examples=["Dr. Strange"])
    poli: str = Field(...)
    practice_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    practice_end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    max_patients: int = Field(default=20, ge=1)
    doctor_id: Optional[int] = None

    @field_validator('dokter')
    def check_dokter_name(cls, v): return validate_not_empty(v, "Nama Dokter")

    @model_validator(mode='after')
    def check_times(self):
        try:
            t1 = datetime.strptime(self.practice_start_time, "%H:%M").time()
            t2 = datetime.strptime(self.practice_end_time, "%H:%M").time()
            if t2 <= t1: raise ValueError('Jam Selesai harus lebih akhir.')
        except ValueError as e:
            if "does not match format" in str(e): raise ValueError("Format jam salah")
            raise e
        return self

class DoctorUpdate(BaseModel):
    dokter: Optional[str] = None
    poli: Optional[str] = None
    max_patients: Optional[int] = Field(default=None, ge=1)
    practice_start_time: Optional[str] = None
    practice_end_time: Optional[str] = None

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

class ScanRequest(BaseModel):
    barcode_data: str = Field(..., min_length=1)
    location: str = Field(..., pattern="^(arrival|clinic|finish)$")

class UpdateQueueStatus(BaseModel):
    action: str = Field(...)

class PoliSchema(BaseModel):
    poli: str; prefix: str
    model_config = ConfigDict(from_attributes=True)

class DoctorSchema(BaseModel):
    doctor_id: int; dokter: str; poli: str; doctor_code: str
    practice_start_time: time; practice_end_time: time; max_patients: int
    model_config = ConfigDict(from_attributes=True)

class PelayananSchema(BaseModel):
    id: int; nama_pasien: str; dokter: str; poli: str; visit_date: date; status_pelayanan: str
    queue_number: str; queue_sequence: int
=======
# --- VALIDATOR HELPER ---
def validate_not_empty(v: str, field_name: str):
    if not v or not v.strip():
        raise ValueError(f"{field_name} tidak boleh kosong atau hanya spasi.")
    return v.strip()

# ==========================================
# 1. INPUT SCHEMAS
# ==========================================

class PoliCreate(BaseModel):
    poli: str = Field(..., min_length=3, examples=["Poli Mata"])
    prefix: str = Field(..., min_length=2, max_length=5, examples=["MATA"])

    @field_validator('poli')
    def check_poli_name(cls, v):
        return validate_not_empty(v, "Nama Poli")

    @field_validator('prefix')
    def check_prefix(cls, v):
        v = validate_not_empty(v, "Prefix")
        if not v.isalpha():
            raise ValueError('Prefix hanya boleh huruf (A-Z).')
        return v.upper()

class DoctorCreate(BaseModel):
    dokter: str = Field(..., min_length=3, examples=["Dr. Strange"])
    poli: str = Field(...)
    practice_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    practice_end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    max_patients: int = Field(default=20, ge=1)
    doctor_id: Optional[int] = None

    @field_validator('dokter')
    def check_dokter_name(cls, v):
        return validate_not_empty(v, "Nama Dokter")

    @model_validator(mode='after')
    def check_times(self):
        try:
            t1 = datetime.strptime(self.practice_start_time, "%H:%M").time()
            t2 = datetime.strptime(self.practice_end_time, "%H:%M").time()
            if t2 <= t1: raise ValueError('Jam Selesai harus lebih akhir dari Jam Mulai.')
        except ValueError as e:
            if "does not match format" in str(e): raise ValueError("Format jam salah")
            raise e
        return self

class DoctorUpdate(BaseModel):
    dokter: Optional[str] = None
    poli: Optional[str] = None
    max_patients: Optional[int] = Field(default=None, ge=1)
    practice_start_time: Optional[str] = None
    practice_end_time: Optional[str] = None

    @field_validator('dokter')
    def check_name(cls, v):
        if v is not None:
            return validate_not_empty(v, "Nama Dokter")
        return v

class RegistrationFinal(BaseModel):
    nama_pasien: str = Field(..., min_length=3)
    poli: str = Field(...)
    doctor_id: int = Field(...)
    visit_date: date = Field(...)

    @field_validator('nama_pasien')
    def check_pasien(cls, v):
        return validate_not_empty(v, "Nama Pasien")

    @field_validator('visit_date')
    def check_date(cls, v):
        if v < date.today(): raise ValueError('Tanggal tidak boleh masa lalu.')
        return v

class ScanRequest(BaseModel):
    barcode_data: str = Field(..., min_length=1)
    location: str = Field(..., pattern="^(arrival|clinic|finish)$")

class UpdateQueueStatus(BaseModel):
    action: str = Field(...)

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
>>>>>>> 57f37a25aae074be8b66a8d26db930948df27bd6
    checkin_time: Optional[datetime] = None
    clinic_entry_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ClinicStats(BaseModel):
<<<<<<< HEAD
    poli_name: str; total_doctors: int; total_patients_today: int
    patients_waiting: int; patients_being_served: int; patients_finished: int
=======
    poli_name: str
    total_doctors: int
    total_patients_today: int
    patients_waiting: int
    patients_being_served: int
    patients_finished: int
>>>>>>> 57f37a25aae074be8b66a8d26db930948df27bd6
    model_config = ConfigDict(from_attributes=True)