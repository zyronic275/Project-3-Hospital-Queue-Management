import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Basis Data In-Memory (Tidak ada perubahan) ---
db: Dict[str, List[Dict[str, Any]]] = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "A"},
        {"id": 2, "name": "Poli Gigi", "prefix": "B"},
        {"id": 3, "name": "Poli Anak", "prefix": "C"},
        {"id": 4, "name": "Laboratorium", "prefix": "D"},
    ],
    "doctors": [
        {"id": 1, "doctor_code": "1", "name": "Dr. Budi Santoso", "services": [1]},
        {"id": 5, "doctor_code": "2", "name": "Dr. Elara Vance", "services": [1]},
        {"id": 2, "doctor_code": "1", "name": "Dr. Anisa Lestari", "services": [2]},
        {"id": 6, "doctor_code": "2", "name": "Dr. Finnian Gale", "services": [2]},
        {"id": 3, "doctor_code": "1", "name": "Dr. Candra Wijaya", "services": [3]},
        {"id": 7, "doctor_code": "2", "name": "Dr. Lyra Solstice", "services": [3]},
        {"id": 4, "doctor_code": "1", "name": "Dr. Dita Amelia", "services": [4]},
        {"id": 8, "doctor_code": "2", "name": "Dr. Ronan Petrova", "services": [4]},
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
    # Bagian ini tidak ada perubahan
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

        # --- INI SATU-SATUNYA BARIS YANG BERUBAH ---
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