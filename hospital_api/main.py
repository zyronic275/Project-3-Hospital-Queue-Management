import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Basis Data In-Memory ---
# Jumlah dokter sekarang ditambahkan menjadi dua per poli.

db: Dict[str, List[Dict[str, Any]]] = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "A"},
        {"id": 2, "name": "Poli Gigi", "prefix": "B"},
        {"id": 3, "name": "Poli Anak", "prefix": "C"},
        {"id": 4, "name": "Laboratorium", "prefix": "D"},
    ],
    "doctors": [
        # Dua dokter untuk Poli Umum (ID Layanan: 1)
        {"id": 1, "name": "Dr. Budi Santoso", "services": [1]},
        {"id": 5, "name": "Dr. Elara Vance", "services": [1]},

        # Dua dokter untuk Poli Gigi (ID Layanan: 2)
        {"id": 2, "name": "Drg. Aura Salsabila", "services": [2]},
        {"id": 6, "name": "Drg. Finnian Gale", "services": [2]},
        
        # Dua dokter untuk Poli Anak (ID Layanan: 3)
        {"id": 3, "name": "Dr. Candra Wijaya", "services": [3]},
        {"id": 7, "name": "Dr. Lyra Solstice", "services": [3]},

        # Dua dokter untuk Laboratorium (ID Layanan: 4)
        {"id": 4, "name": "Dr. Dita Amelia", "services": [4]},
        {"id": 8, "name": "Dr. Ronan Petrova", "services": [4]},
    ],
    "patients": [],
    "queues": []
}

# --- Model Pydantic (Tidak ada perubahan) ---
class Service(BaseModel):
    id: int
    name: str

class Doctor(BaseModel):
    id: int
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
            # --- LOGIKA BARU: Penugasan Dokter Otomatis yang Lebih Baik ---
            # 1. Cari semua dokter yang bisa menangani layanan ini
            available_doctors = [d for d in db["doctors"] if service_id in d["services"]]
            if not available_doctors:
                raise HTTPException(status_code=404, detail=f"Tidak ada dokter yang tersedia untuk layanan {service['name']}.")
            
            # 2. Hitung jumlah antrean untuk setiap dokter yang tersedia
            doctor_queue_counts = []
            for d in available_doctors:
                count = len([q for q in db["queues"] if q["service_id"] == service_id and q["doctor_id"] == d["id"]])
                doctor_queue_counts.append({'doctor': d, 'count': count})
            
            # 3. Pilih dokter dengan jumlah antrean paling sedikit
            least_busy_doctor_info = min(doctor_queue_counts, key=lambda x: x['count'])
            doctor = least_busy_doctor_info['doctor']

        # --- Proses Pembuatan Antrean (Tidak ada perubahan) ---
        current_queues_for_service = [q for q in db["queues"] if q["service_id"] == service_id and q["doctor_id"] == doctor["id"]]
        queue_number = len(current_queues_for_service) + 1

        new_queue_id = len(db["queues"]) + 1
        db["queues"].append({
            "id": new_queue_id,
            "patient_id": patient["id"],
            "service_id": service_id,
            "doctor_id": doctor["id"],
            "queue_number": queue_number,
        })

        response_tickets.append({
            "service": service,
            "doctor": doctor,
            "queue_number": f"{service['prefix']}{queue_number:03}",
        })

    return {"patient": patient, "tickets": response_tickets}

# Middleware CORS (Tidak ada perubahan)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)