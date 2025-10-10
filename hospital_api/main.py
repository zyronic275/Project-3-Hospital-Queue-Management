from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# --- Pydantic Schemas (Struktur Data) ---

class ServiceSchema(BaseModel):
    id: int
    name: str
    prefix: str = Field(..., max_length=1)

class DoctorSchema(BaseModel):
    id: int
    doctor_code: str
    name: str
    services: List[int]

class PatientSchema(BaseModel):
    id: int
    name: str

class QueueSchema(BaseModel):
    id: int
    queue_id_display: str
    queue_number: int
    registration_time: datetime
    status: str = "waiting"
    patient_id: int
    service_id: int
    doctor_id: int

# --- Skema untuk Request Body (Create/Update) ---

class ServiceCreate(BaseModel):
    name: str
    prefix: str = Field(..., max_length=1)

class DoctorCreate(BaseModel):
    doctor_code: str
    name: str
    services: List[int]

class QueueStatusUpdate(BaseModel):
    status: str

# --- Skema untuk Response ---

class RegistrationRequest(BaseModel):
    patient_name: str
    service_ids: List[int]
    doctor_id: Optional[int] = None

class Ticket(BaseModel):
    service: ServiceSchema
    queue_number: str
    doctor: DoctorSchema

class RegistrationResponse(BaseModel):
    patient: PatientSchema
    tickets: List[Ticket]

# --- In-Memory Database dengan Data Awal ---

db_data: Dict[str, List[Dict[str, Any]]] = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "A"},
        {"id": 2, "name": "Poli Gigi", "prefix": "B"},
        {"id": 3, "name": "Poli Anak", "prefix": "C"},
        {"id": 4, "name": "Laboratorium", "prefix": "D"},
    ],
    "doctors": [
        {"id": 1, "doctor_code": "1", "name": "dr. Budi Santoso", "services": [1]},
        {"id": 5, "doctor_code": "2", "name": "dr. Elara Vance", "services": [1]},
        {"id": 2, "doctor_code": "1", "name": "drg. Anisa Lestari", "services": [2]},
        {"id": 6, "doctor_code": "2", "name": "drg. Finnian Gale", "services": [2]},
        {"id": 3, "doctor_code": "1", "name": "dr. Candra Wijaya", "services": [3]},
        {"id": 7, "doctor_code": "2", "name": "dr. Lyra Solstice", "services": [3]},
        {"id": 4, "doctor_code": "1", "name": "dr. Dita Amelia", "services": [4]},
        {"id": 8, "doctor_code": "2", "name": "dr. Ronan Petrova", "services": [4]},
    ],
    "patients": [],
    "queues": []
}

db = {
    "services": [ServiceSchema(**s) for s in db_data["services"]],
    "doctors": [DoctorSchema(**d) for d in db_data["doctors"]],
    "patients": [PatientSchema(**p) for p in db_data["patients"]],
    "queues": [], # Akan diisi dengan QueueSchema saat registrasi
}

def get_max_id(data_list: List[Any]) -> int:
    if not data_list:
        return 0
    return max(item.id for item in data_list)

id_counters = {
    "services": get_max_id(db["services"]),
    "doctors": get_max_id(db["doctors"]),
    "patients": get_max_id(db["patients"]),
    "queues": get_max_id(db["queues"]),
}

# --- Aplikasi FastAPI ---
app = FastAPI(title="Hospital Queue Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === PENAMBAHAN ENDPOINT ROOT UNTUK FIX 404 ===
@app.get("/", tags=["Root"])
def read_root():
    """Endpoint utama untuk mengecek apakah API berjalan."""
    return {"message": "Welcome to the Hospital Queue Management API"}
# ===============================================

# === ENDPOINTS: Patient Registration & Queue Management ===

@app.post("/register", response_model=RegistrationResponse, tags=["Patient Registration"], status_code=status.HTTP_201_CREATED)
def register_patient(request: RegistrationRequest):
    # (Kode fungsi ini tidak berubah, sudah benar)
    patient = next((p for p in db["patients"] if p.name.lower() == request.patient_name.strip().lower()), None)
    if not patient:
        id_counters["patients"] += 1
        patient = PatientSchema(id=id_counters["patients"], name=request.patient_name.strip())
        db["patients"].append(patient)

    tickets = []
    today = date.today()

    for service_id in request.service_ids:
        service = next((s for s in db["services"] if s.id == service_id), None)
        if not service: raise HTTPException(status_code=404, detail=f"Layanan ID {service_id} tidak ditemukan.")

        doctor = None
        available_doctors = [d for d in db["doctors"] if service_id in d.services]
        if not available_doctors: raise HTTPException(status_code=404, detail=f"Tidak ada dokter untuk layanan {service.name}.")
        
        if request.doctor_id:
            doctor = next((d for d in available_doctors if d.id == request.doctor_id), None)
            if not doctor: raise HTTPException(status_code=400, detail="Dokter tidak sesuai dengan layanan.")
        else:
            doctor_queues = {d.id: len([q for q in db["queues"] if q.doctor_id == d.id and q.registration_time.date() == today]) for d in available_doctors}
            least_busy_doctor_id = min(doctor_queues, key=doctor_queues.get)
            doctor = next((d for d in available_doctors if d.id == least_busy_doctor_id), None)

        if not doctor: raise HTTPException(status_code=404, detail="Gagal menemukan dokter.")

        queues_for_doctor_today = [q for q in db["queues"] if q.doctor_id == doctor.id and q.registration_time.date() == today]
        new_queue_number = len(queues_for_doctor_today) + 1
        queue_id_display = f"{service.prefix}-{doctor.doctor_code}-{new_queue_number:03d}"
        
        id_counters["queues"] += 1
        new_queue = QueueSchema(
            id=id_counters["queues"], queue_id_display=queue_id_display, queue_number=new_queue_number,
            patient_id=patient.id, service_id=service.id, doctor_id=doctor.id, registration_time=datetime.now()
        )
        db["queues"].append(new_queue)
        
        tickets.append(Ticket(service=service, queue_number=queue_id_display, doctor=doctor))
        
    return RegistrationResponse(patient=patient, tickets=tickets)

@app.get("/queues/{service_id}", response_model=List[QueueSchema], tags=["Patient Registration"])
def get_queue_for_service(service_id: int, status: Optional[str] = None):
    today = date.today()
    queues = [q for q in db["queues"] if q.service_id == service_id and q.registration_time.date() == today]
    if status:
        queues = [q for q in queues if q.status == status]
    return sorted(queues, key=lambda q: q.queue_number)

@app.put("/queues/{queue_id}/status", response_model=QueueSchema, tags=["Patient Registration"])
def update_queue_status(queue_id: int, request: QueueStatusUpdate):
    queue = next((q for q in db["queues"] if q.id == queue_id), None)
    if not queue:
        raise HTTPException(status_code=404, detail="Antrian tidak ditemukan.")
    
    allowed_statuses = ["waiting", "serving", "done", "skipped"]
    if request.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Status tidak valid. Pilih dari: {allowed_statuses}")
    
    queue.status = request.status
    return queue

# === ENDPOINTS: Admin - Services ===

@app.get("/admin/services/", response_model=List[ServiceSchema], tags=["Admin: Services"])
def get_services():
    return db["services"]

@app.post("/admin/services/", response_model=ServiceSchema, tags=["Admin: Services"], status_code=status.HTTP_201_CREATED)
def create_service(service: ServiceCreate):
    id_counters["services"] += 1
    new_service = ServiceSchema(id=id_counters["services"], **service.dict())
    db["services"].append(new_service)
    return new_service

@app.put("/admin/services/{service_id}", response_model=ServiceSchema, tags=["Admin: Services"])
def update_service(service_id: int, service_update: ServiceCreate):
    service = next((s for s in db["services"] if s.id == service_id), None)
    if not service:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan.")
    service.name = service_update.name
    service.prefix = service_update.prefix
    return service

@app.delete("/admin/services/{service_id}", response_model=ServiceSchema, tags=["Admin: Services"])
def delete_service(service_id: int):
    service_idx = next((i for i, s in enumerate(db["services"]) if s.id == service_id), None)
    if service_idx is None:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan.")
    return db["services"].pop(service_idx)

# === ENDPOINTS: Admin - Doctors ===

@app.get("/admin/doctors/", response_model=List[DoctorSchema], tags=["Admin: Doctors"])
def get_doctors():
    return db["doctors"]

@app.post("/admin/doctors/", response_model=DoctorSchema, tags=["Admin: Doctors"], status_code=status.HTTP_201_CREATED)
def create_doctor(doctor: DoctorCreate):
    for sid in doctor.services:
        if not any(s.id == sid for s in db["services"]):
            raise HTTPException(status_code=400, detail=f"Layanan dengan ID {sid} tidak ditemukan.")
    
    id_counters["doctors"] += 1
    new_doctor = DoctorSchema(id=id_counters["doctors"], **doctor.dict())
    db["doctors"].append(new_doctor)
    return new_doctor

@app.put("/admin/doctors/{doctor_id}", response_model=DoctorSchema, tags=["Admin: Doctors"])
def update_doctor(doctor_id: int, doctor_update: DoctorCreate):
    doctor = next((d for d in db["doctors"] if d.id == doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="Dokter tidak ditemukan.")
    
    for sid in doctor_update.services:
        if not any(s.id == sid for s in db["services"]):
            raise HTTPException(status_code=400, detail=f"Layanan dengan ID {sid} tidak ditemukan.")
            
    doctor.name = doctor_update.name
    doctor.doctor_code = doctor_update.doctor_code
    doctor.services = doctor_update.services
    return doctor

@app.delete("/admin/doctors/{doctor_id}", response_model=DoctorSchema, tags=["Admin: Doctors"])
def delete_doctor(doctor_id: int):
    doctor_idx = next((i for i, d in enumerate(db["doctors"]) if d.id == doctor_id), None)
    if doctor_idx is None:
        raise HTTPException(status_code=404, detail="Dokter tidak ditemukan.")
    return db["doctors"].pop(doctor_idx)

# === ENDPOINTS: Admin - Monitoring ===

@app.get("/admin/dashboard", tags=["Admin: Monitoring"], status_code=status.HTTP_200_OK)
def get_dashboard_stats():
    # (Kode fungsi ini tidak berubah, sudah benar)
    today = date.today()
    queues_today = [q for q in db["queues"] if q.registration_time.date() == today]
    patients_waiting = [q for q in queues_today if q.status == "waiting"]
    return {
        "total_queues_today": len(queues_today), "patients_waiting": len(patients_waiting),
        "total_doctors": len(db["doctors"]), "total_services": len(db["services"])
    }

@app.delete("/admin/queues/reset", tags=["Admin: Monitoring"], status_code=status.HTTP_200_OK)
def reset_all_queues():
    # (Kode fungsi ini tidak berubah, sudah benar)
    if id_counters["queues"] < 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Reset gagal. Total antrian {id_counters['queues']}, harus minimal 1000.")
    
    queues_deleted_count = len(db["queues"])
    db["queues"].clear()
    id_counters["queues"] = 0
    return {"message": "Data antrian berhasil direset.", "active_queues_deleted": queues_deleted_count, "next_queue_id": 1}