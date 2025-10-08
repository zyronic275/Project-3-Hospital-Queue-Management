'''
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Basis Data In-Memory ---
db: Dict[str, List[Dict[str, Any]]] = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "A"},
        {"id": 2, "name": "Poli Gigi", "prefix": "B"},
        {"id": 3, "name": "Poli Anak", "prefix": "C"},
        {"id": 4, "name": "Laboratorium", "prefix": "D"},
    ],
    "doctors": [
        {"id": 1, "doctor_code": "1", "name": "dr. Elan", "services": [1]},
        {"id": 5, "doctor_code": "2", "name": "dr. Budi", "services": [1]},
        {"id": 2, "doctor_code": "1", "name": "drg. Aura", "services": [2]},
        {"id": 6, "doctor_code": "2", "name": "drg. Tiffany", "services": [2]},
        {"id": 3, "doctor_code": "1", "name": "dr. Candra", "services": [3]},
        {"id": 7, "doctor_code": "2", "name": "dr. Putri", "services": [3]},
        {"id": 4, "doctor_code": "1", "name": "dr. Dita", "services": [4]},
        {"id": 8, "doctor_code": "2", "name": "dr. Eka", "services": [4]},
    ],
    "patients": [],
    "queues": []
}

# --- Model Pydantic ---
class Service(BaseModel):
    id: int
    name: str

class Doctor(BaseModel):
    id: int
    doctor_code: str
    name: str
    services: List[int]

class Patient(BaseModel):
    id: int
    name: str

class Ticket(BaseModel):
    service: Service
    doctor: Doctor
    queue_number: str

class RegistrationRequest(BaseModel):
    patient_name: str
    service_ids: List[int]
    doctor_id: Optional[int] = None

class RegistrationResponse(BaseModel):
    patient: Patient
    tickets: List[Ticket]

# --- Aplikasi FastAPI ---
app = FastAPI()

@app.get("/admin/services/", response_model=List[Service])
async def get_services():
    return db["services"]

@app.get("/admin/doctors/", response_model=List[Doctor])
async def get_doctors():
    return db["doctors"]


@app.post("/register", response_model=RegistrationResponse)
async def register_patient(request: RegistrationRequest):
    patient_name = request.patient_name.strip()
    patient = next((p for p in db["patients"] if p["name"].lower() == patient_name.lower()), None)

    if not patient:
        new_id = len(db["patients"]) + 1
        patient = {"id": new_id, "name": patient_name}
        db["patients"].append(patient)

    response_tickets = []
    for service_id in request.service_ids:
        service = next((s for s in db["services"] if s["id"] == service_id), None)
        if not service:
            raise HTTPException(status_code=404, detail=f"Layanan dengan ID {service_id} tidak ditemukan.")

        doctor = None
        if request.doctor_id:
            doctor = next((d for d in db["doctors"] if d["id"] == request.doctor_id), None)
            if not doctor or service_id not in doctor["services"]:
                 raise HTTPException(status_code=400, detail="Dokter yang dipilih tidak sesuai dengan layanan.")
        else:
            available_doctors = [d for d in db["doctors"] if service_id in d["services"]]
            if not available_doctors:
                raise HTTPException(status_code=404, detail=f"Tidak ada dokter yang tersedia untuk layanan {service['name']}.")
            
            doctor_queue_counts = []
            for d in available_doctors:
                count = len([q for q in db["queues"] if q["service_id"] == service_id and q["doctor_id"] == d["id"]])
                doctor_queue_counts.append({'doctor': d, 'count': count})
            
            least_busy_doctor_info = min(doctor_queue_counts, key=lambda x: x['count'])
            doctor = least_busy_doctor_info['doctor']

        current_queues_for_service = [q for q in db["queues"] if q["service_id"] == service_id and q["doctor_id"] == doctor["id"]]
        queue_number_int = len(current_queues_for_service) + 1

        new_queue_id = len(db["queues"]) + 1
        db["queues"].append({
            "id": new_queue_id,
            "patient_id": patient["id"],
            "service_id": service_id,
            "doctor_id": doctor["id"],
            "queue_number": queue_number_int, # Simpan sebagai angka saja
        })

        # Format nomor antrean baru: [Prefix]-[DoctorCode]-[NomorUrut]
        formatted_queue_number = f"{service['prefix']}-{doctor['doctor_code']}-{queue_number_int:03}"

        response_tickets.append({
            "service": service,
            "doctor": doctor,
            "queue_number": formatted_queue_number, # Kirim nomor yang sudah diformat
        })

    return {"patient": patient, "tickets": response_tickets}

# Middleware CORS (Tidak ada perubahan)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
'''
'''
# hospital_api/main.py

from datetime import datetime, date, time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import copy

# --- Pydantic Schemas (Struktur Data) ---

class ServiceSchema(BaseModel):
    id: int
    name: str
    prefix: str = Field(..., max_length=1)

# PERUBAHAN: Menambahkan 'doctor_code' dan menyesuaikan 'services'
class DoctorSchema(BaseModel):
    id: int
    doctor_code: str
    name: str
    services: List[int] # ID layanan yang ditangani dokter

class PatientSchema(BaseModel):
    id: int
    name: str

class QueueSchema(BaseModel):
    id: int
    queue_id_display: str
    queue_number: int
    registration_time: datetime
    status: str = "waiting" # waiting, serving, done
    visit_notes: Optional[str] = None
    patient_id: int
    service_id: int
    doctor_id: int

# Skema untuk request dan response
class ServiceCreate(BaseModel):
    name: str
    prefix: str = Field(..., max_length=1)

# PERUBAHAN: Menyesuaikan dengan model DoctorSchema
class DoctorCreate(BaseModel):
    doctor_code: str
    name: str
    services: List[int]

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


# --- In-Memory Database dengan Data Baru ---
# PERUBAHAN: Menggunakan data yang Anda berikan
db_data: Dict[str, List[Dict[str, Any]]] = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "A"},
        {"id": 2, "name": "Poli Gigi", "prefix": "B"},
        {"id": 3, "name": "Poli Anak", "prefix": "C"},
        {"id": 4, "name": "Laboratorium", "prefix": "D"},
    ],
    "doctors": [
        {"id": 1, "doctor_code": "1", "name": "dr. Elan", "services": [1]},
        {"id": 5, "doctor_code": "2", "name": "dr. Budi", "services": [1]},
        {"id": 2, "doctor_code": "1", "name": "drg. Aura", "services": [2]},
        {"id": 6, "doctor_code": "2", "name": "drg. Tiffany", "services": [2]},
        {"id": 3, "doctor_code": "1", "name": "dr. Candra", "services": [3]},
        {"id": 7, "doctor_code": "2", "name": "dr. Putri", "services": [3]},
        {"id": 4, "doctor_code": "1", "name": "dr. Dita", "services": [4]},
        {"id": 8, "doctor_code": "2", "name": "dr. Eka", "services": [4]},
    ],
    "patients": [],
    "queues": []
}

# Mengonversi data mentah menjadi objek Pydantic untuk konsistensi
db = {
    "services": [ServiceSchema(**s) for s in db_data["services"]],
    "doctors": [DoctorSchema(**d) for d in db_data["doctors"]],
    "patients": [PatientSchema(**p) for p in db_data["patients"]],
    "queues": [QueueSchema(**q) for q in db_data["queues"]],
}


# --- Counter untuk ID ---
def get_max_id(data_list: List[Dict[str, Any]]) -> int:
    if not data_list:
        return 0
    return max(item.get("id", 0) for item in data_list)

id_counters = {
    "services": get_max_id(db_data["services"]),
    "doctors": get_max_id(db_data["doctors"]),
    "patients": get_max_id(db_data["patients"]),
    "queues": get_max_id(db_data["queues"]),
}

# --- Inisialisasi Aplikasi FastAPI ---
app = FastAPI(title="Hospital Queue Management API (Updated In-Memory)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Endpoints ---

@app.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_patient(request: RegistrationRequest):
    patient = next((p for p in db["patients"] if p.name == request.patient_name), None)
    if not patient:
        id_counters["patients"] += 1
        patient = PatientSchema(id=id_counters["patients"], name=request.patient_name)
        db["patients"].append(patient)

    tickets = []
    today = date.today()

    for service_id in request.service_ids:
        service = next((s for s in db["services"] if s.id == service_id), None)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service with id {service_id} not found")

        doctor = None
        if request.doctor_id:
            doctor = next((d for d in db["doctors"] if d.id == request.doctor_id), None)
            # PERUBAHAN: Cek di list 'services' milik dokter
            if service_id not in doctor.services:
                raise HTTPException(status_code=400, detail=f"Doctor {doctor.name} does not provide service {service.name}")
        else:
            # PERUBAHAN: Cek di list 'services' milik dokter
            available_doctors = [d for d in db["doctors"] if service_id in d.services]
            if not available_doctors:
                raise HTTPException(status_code=404, detail=f"No doctors available for service {service.name}")
            doctor = available_doctors[0]
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        queues_today = [
            q for q in db["queues"] 
            if q.service_id == service_id and q.registration_time.date() == today
        ]
        new_queue_number = len(queues_today) + 1
        queue_id_display = f"{service.prefix}-{new_queue_number:03d}"

        id_counters["queues"] += 1
        new_queue = QueueSchema(
            id=id_counters["queues"],
            queue_id_display=queue_id_display,
            queue_number=new_queue_number,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor.id,
            registration_time=datetime.now()
        )
        db["queues"].append(new_queue)
        
        tickets.append(Ticket(
            service=service, 
            queue_number=new_queue.queue_id_display, 
            doctor=doctor
        ))
        
    return RegistrationResponse(patient=patient, tickets=tickets)


# Endpoint untuk Admin
@app.get("/admin/services/", response_model=List[ServiceSchema])
def get_services():
    return db["services"]

@app.post("/admin/services/", response_model=ServiceSchema, status_code=status.HTTP_201_CREATED)
def create_service(service: ServiceCreate):
    id_counters["services"] += 1
    new_service = ServiceSchema(id=id_counters["services"], **service.dict())
    db["services"].append(new_service)
    return new_service

@app.get("/admin/doctors/", response_model=List[DoctorSchema])
def get_doctors():
    return db["doctors"]

@app.post("/admin/doctors/", response_model=DoctorSchema, status_code=status.HTTP_201_CREATED)
def create_doctor(doctor_req: DoctorCreate):
    id_counters["doctors"] += 1
    # PERUBAHAN: Menyesuaikan dengan model DoctorSchema
    new_doctor = DoctorSchema(id=id_counters["doctors"], **doctor_req.dict())
    
    for sid in new_doctor.services:
        if not any(s.id == sid for s in db["services"]):
            raise HTTPException(status_code=404, detail=f"Service with id {sid} not found")
    
    db["doctors"].append(new_doctor)
    return new_doctor


# Endpoint untuk Staf Medis/Dokter
@app.get("/queues/{service_id}", response_model=List[QueueSchema])
def get_queue_for_service(service_id: int, status: Optional[str] = "waiting"):
    today = date.today()
    queues = [
        q for q in db["queues"] 
        if q.service_id == service_id and q.status == status and q.registration_time.date() == today
    ]
    queues.sort(key=lambda q: q.queue_number)
    return queues

@app.put("/queues/{queue_id}/status", response_model=QueueSchema)
def update_queue_status(queue_id: int, new_status: str):
    queue = next((q for q in db["queues"] if q.id == queue_id), None)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    
    allowed_statuses = ["waiting", "serving", "done"]
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {allowed_statuses}")

    queue.status = new_status
    return queue

@app.put("/queues/{queue_id}/notes", response_model=QueueSchema)
def update_visit_notes(queue_id: int, notes: str):
    queue = next((q for q in db["queues"] if q.id == queue_id), None)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    
    queue.visit_notes = notes # Menyimpan catatan kunjungan
    return queue
'''
# hospital_api/main.py

from datetime import datetime, date, time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import copy

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
    visit_notes: Optional[str] = None
    patient_id: int
    service_id: int
    doctor_id: int

# Skema untuk request dan response
class ServiceCreate(BaseModel):
    name: str
    prefix: str = Field(..., max_length=1)

class DoctorCreate(BaseModel):
    doctor_code: str
    name: str
    services: List[int]

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


# --- In-Memory Database dengan Data Baru ---
db_data: Dict[str, List[Dict[str, Any]]] = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "A"},
        {"id": 2, "name": "Poli Gigi", "prefix": "B"},
        {"id": 3, "name": "Poli Anak", "prefix": "C"},
        {"id": 4, "name": "Laboratorium", "prefix": "D"},
    ],
    "doctors": [
        {"id": 1, "doctor_code": "1", "name": "dr. Elan", "services": [1]},
        {"id": 5, "doctor_code": "2", "name": "dr. Budi", "services": [1]},
        {"id": 2, "doctor_code": "1", "name": "drg. Aura", "services": [2]},
        {"id": 6, "doctor_code": "2", "name": "drg. Tiffany", "services": [2]},
        {"id": 3, "doctor_code": "1", "name": "dr. Candra", "services": [3]},
        {"id": 7, "doctor_code": "2", "name": "dr. Putri", "services": [3]},
        {"id": 4, "doctor_code": "1", "name": "dr. Dita", "services": [4]},
        {"id": 8, "doctor_code": "2", "name": "dr. Eka", "services": [4]},
    ],
    "patients": [],
    "queues": []
}

db = {
    "services": [ServiceSchema(**s) for s in db_data["services"]],
    "doctors": [DoctorSchema(**d) for d in db_data["doctors"]],
    "patients": [PatientSchema(**p) for p in db_data["patients"]],
    "queues": [QueueSchema(**q) for q in db_data["queues"]],
}

def get_max_id(data_list: List[Dict[str, Any]]) -> int:
    if not data_list:
        return 0
    return max(item.get("id", 0) for item in data_list)

id_counters = {
    "services": get_max_id(db_data["services"]),
    "doctors": get_max_id(db_data["doctors"]),
    "patients": get_max_id(db_data["patients"]),
    "queues": get_max_id(db_data["queues"]),
}

app = FastAPI(title="Hospital Queue Management API (Updated In-Memory)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_patient(request: RegistrationRequest):
    patient = next((p for p in db["patients"] if p.name == request.patient_name), None)
    if not patient:
        id_counters["patients"] += 1
        patient = PatientSchema(id=id_counters["patients"], name=request.patient_name)
        db["patients"].append(patient)

    tickets = []
    today = date.today()

    for service_id in request.service_ids:
        service = next((s for s in db["services"] if s.id == service_id), None)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service with id {service_id} not found")

        doctor = None
        if request.doctor_id:
            doctor = next((d for d in db["doctors"] if d.id == request.doctor_id), None)
            if service_id not in doctor.services:
                raise HTTPException(status_code=400, detail=f"Doctor {doctor.name} does not provide service {service.name}")
        else:
            available_doctors = [d for d in db["doctors"] if service_id in d.services]
            if not available_doctors:
                raise HTTPException(status_code=404, detail=f"No doctors available for service {service.name}")
            doctor = available_doctors[0]
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        queues_today = [
            q for q in db["queues"] 
            if q.service_id == service_id and q.registration_time.date() == today
        ]
        new_queue_number = len(queues_today) + 1
        
        # ================================================================= #
        # === PERUBAHAN UTAMA ADA DI BARIS INI === #
        queue_id_display = f"{service.prefix}-{doctor.doctor_code}-{new_queue_number:03d}"
        # ================================================================= #
        
        id_counters["queues"] += 1
        new_queue = QueueSchema(
            id=id_counters["queues"],
            queue_id_display=queue_id_display,
            queue_number=new_queue_number,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor.id,
            registration_time=datetime.now()
        )
        db["queues"].append(new_queue)
        
        tickets.append(Ticket(
            service=service, 
            queue_number=new_queue.queue_id_display, 
            doctor=doctor
        ))
        
    return RegistrationResponse(patient=patient, tickets=tickets)


@app.get("/admin/services/", response_model=List[ServiceSchema])
def get_services():
    return db["services"]

@app.post("/admin/services/", response_model=ServiceSchema, status_code=status.HTTP_201_CREATED)
def create_service(service: ServiceCreate):
    id_counters["services"] += 1
    new_service = ServiceSchema(id=id_counters["services"], **service.dict())
    db["services"].append(new_service)
    return new_service

@app.get("/admin/doctors/", response_model=List[DoctorSchema])
def get_doctors():
    return db["doctors"]

@app.post("/admin/doctors/", response_model=DoctorSchema, status_code=status.HTTP_201_CREATED)
def create_doctor(doctor_req: DoctorCreate):
    id_counters["doctors"] += 1
    new_doctor = DoctorSchema(id=id_counters["doctors"], **doctor_req.dict())
    
    for sid in new_doctor.services:
        if not any(s.id == sid for s in db["services"]):
            raise HTTPException(status_code=404, detail=f"Service with id {sid} not found")
    
    db["doctors"].append(new_doctor)
    return new_doctor

@app.get("/queues/{service_id}", response_model=List[QueueSchema])
def get_queue_for_service(service_id: int, status: Optional[str] = "waiting"):
    today = date.today()
    queues = [
        q for q in db["queues"] 
        if q.service_id == service_id and q.status == status and q.registration_time.date() == today
    ]
    queues.sort(key=lambda q: q.queue_number)
    return queues

@app.put("/queues/{queue_id}/status", response_model=QueueSchema)
def update_queue_status(queue_id: int, new_status: str):
    queue = next((q for q in db["queues"] if q.id == queue_id), None)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    
    allowed_statuses = ["waiting", "serving", "done"]
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {allowed_statuses}")

    queue.status = new_status
    return queue

@app.put("/queues/{queue_id}/notes", response_model=QueueSchema)
def update_visit_notes(queue_id: int, notes: str):
    queue = next((q for q in db["queues"] if q.id == queue_id), None)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    
    queue.visit_notes = notes
    return queue