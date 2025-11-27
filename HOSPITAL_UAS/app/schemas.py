from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Schema untuk CSV History ---
class CsvDataResponse(BaseModel):
    status: str
    count: int
    data: List[Dict[str, Any]]

# --- Schema untuk Operasional Antrean ---
class PatientRegistration(BaseModel):
    patient_name: str
    clinic_name: str  # Contoh: "Poli Umum", "Poli Gigi"
    doctor_name: str

class StatusUpdate(BaseModel):
    status: str  # "MENUNGGU", "SEDANG DILAYANI", "SELESAI"
    diagnosis: Optional[str] = None

class QueueItem(BaseModel):
    queue_number: str
    patient_name: str
    clinic: str
    doctor: str
    status: str
    registration_time: datetime
    diagnosis: Optional[str] = None