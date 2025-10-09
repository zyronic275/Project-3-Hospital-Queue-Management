from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import date, datetime

# Impor dari file lokal
from . import storage
from . import schemas

# =================================================================
# BAGIAN 1: INISIALISASI APLIKASI UTAMA DAN ROUTER
# =================================================================

# Aplikasi utama FastAPI
app = FastAPI(
    title="Hospital Queue Management API (Router Version)",
    description="API yang diorganisir menggunakan APIRouter untuk skalabilitas.",
    version="1.3.0"
)

# Router untuk setiap grup fungsionalitas
router_patient = APIRouter(tags=["Patient Registration"])
router_admin_services = APIRouter(prefix="/admin/services", tags=["Admin: Services"])
router_admin_doctors = APIRouter(prefix="/admin/doctors", tags=["Admin: Doctors"])
router_monitoring = APIRouter(prefix="/admin", tags=["Admin: Monitoring"])

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================================================================
# BAGIAN 2: ENDPOINT UNTUK PASIEN (REGISTRASI & ANTRIAN)
# =================================================================

@router_patient.post("/register", response_model=schemas.RegistrationResponse, status_code=201)
def register_patient(request: schemas.RegistrationRequest):
    """Mendaftarkan pasien ke satu atau lebih layanan (klinik)."""
    patient = next((p for p in storage.db["patients"] if p.name.lower() == request.patient_name.lower()), None)
    if not patient:
        storage.id_counters["patients"] += 1
        patient = schemas.PatientSchema(id=storage.id_counters["patients"], name=request.patient_name)
        storage.db["patients"].append(patient)

    tickets = []
    today = date.today()

    for service_id in request.service_ids:
        service = next((s for s in storage.db["services"] if s.id == service_id), None)
        if not service:
            raise HTTPException(status_code=404, detail=f"Layanan dengan id {service_id} tidak ditemukan")

        available_doctors = [d for d in storage.db["doctors"] if service_id in d.services]
        if not available_doctors:
            raise HTTPException(status_code=404, detail=f"Tidak ada dokter untuk layanan {service.name}")

        doctor = available_doctors[0]

        # --- LOGIKA BARU: Cek Jam Praktik ---
        current_time = datetime.now().time()
        if not (doctor.practice_start_time <= current_time <= doctor.practice_end_time):
            raise HTTPException(
                status_code=400, 
                detail=f"Dokter {doctor.name} tidak sedang praktik. Jam praktik: {doctor.practice_start_time.strftime('%H:%M')} - {doctor.practice_end_time.strftime('%H:%M')}"
            )
        # --- AKHIR LOGIKA BARU ---

        queues_today_for_doctor = [
            q for q in storage.db["queues"]
            if q.doctor_id == doctor.id and q.registration_time.date() == today
        ]
        if len(queues_today_for_doctor) >= doctor.max_patients:
            raise HTTPException(status_code=400, detail=f"Kuota untuk dokter {doctor.name} sudah penuh.")

        new_queue_number = len(queues_today_for_doctor) + 1
        queue_id_display = f"{service.prefix}-{doctor.doctor_code}-{new_queue_number:03d}"
        
        storage.id_counters["queues"] += 1
        new_queue = schemas.QueueSchema(
            id=storage.id_counters["queues"],
            queue_id_display=queue_id_display,
            queue_number=new_queue_number,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor.id,
        )
        storage.db["queues"].append(new_queue)
        
        tickets.append(schemas.Ticket(
            service=service, 
            queue_number=new_queue.queue_id_display, 
            doctor=doctor
        ))
            
    return schemas.RegistrationResponse(patient=patient, tickets=tickets)

@router_patient.get("/queues/{service_id}", response_model=List[schemas.QueueSchema])
def get_queue_for_service(service_id: int, status: str = "waiting"):
    """Mendapatkan daftar antrean untuk layanan tertentu berdasarkan status."""
    today = date.today()
    queues = [
        q for q in storage.db["queues"] 
        if q.service_id == service_id and q.status == status and q.registration_time.date() == today
    ]
    queues.sort(key=lambda q: q.queue_number)
    return queues

@router_patient.put("/queues/{queue_id}/status", response_model=schemas.QueueSchema)
def update_queue_status(queue_id: int, request_body: schemas.QueueStatusUpdate):
    """Memperbarui status antrean (misal dari 'waiting' ke 'serving')."""
    queue = next((q for q in storage.db["queues"] if q.id == queue_id), None)
    if not queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan")
    
    queue.status = request_body.status
    return queue

# =================================================================
# BAGIAN 3: ENDPOINT UNTUK ADMIN (MANAJEMEN LAYANAN)
# =================================================================

@router_admin_services.get("/", response_model=List[schemas.ServiceSchema])
def get_services():
    return storage.db["services"]

@router_admin_services.post("/", response_model=schemas.ServiceSchema, status_code=201)
def create_service(service: schemas.ServiceCreate):
    storage.id_counters["services"] += 1
    new_service = schemas.ServiceSchema(id=storage.id_counters["services"], **service.model_dump())
    storage.db["services"].append(new_service)
    return new_service

@router_admin_services.put("/{service_id}", response_model=schemas.ServiceSchema)
def update_service(service_id: int, service_update: schemas.ServiceUpdate):
    service = next((s for s in storage.db["services"] if s.id == service_id), None)
    if not service:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan")
    update_data = service_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)
    return service

@router_admin_services.delete("/{service_id}", status_code=204)
def delete_service(service_id: int):
    service_index = next((i for i, s in enumerate(storage.db["services"]) if s.id == service_id), -1)
    if service_index == -1:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan")
    storage.db["services"].pop(service_index)
    return

# =================================================================
# BAGIAN 4: ENDPOINT UNTUK ADMIN (MANAJEMEN DOKTER)
# =================================================================

@router_admin_doctors.get("/", response_model=List[schemas.DoctorSchema])
def get_doctors():
    return storage.db["doctors"]

@router_admin_doctors.post("/", response_model=schemas.DoctorSchema, status_code=201)
def create_doctor(doctor_req: schemas.DoctorCreate):
    for sid in doctor_req.services:
        if not any(s.id == sid for s in storage.db["services"]):
            raise HTTPException(status_code=404, detail=f"Layanan dengan id {sid} tidak ditemukan")
    storage.id_counters["doctors"] += 1
    new_doctor = schemas.DoctorSchema(id=storage.id_counters["doctors"], **doctor_req.model_dump())
    storage.db["doctors"].append(new_doctor)
    return new_doctor

@router_admin_doctors.put("/{doctor_id}", response_model=schemas.DoctorSchema)
def update_doctor(doctor_id: int, doctor_update: schemas.DoctorUpdate):
    doctor = next((d for d in storage.db["doctors"] if d.id == doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="Dokter tidak ditemukan")
    update_data = doctor_update.model_dump(exclude_unset=True)
    if "services" in update_data:
        for sid in update_data["services"]:
            if not any(s.id == sid for s in storage.db["services"]):
                raise HTTPException(status_code=404, detail=f"Layanan dengan id {sid} tidak ditemukan")
    for key, value in update_data.items():
        setattr(doctor, key, value)
    return doctor

@router_admin_doctors.delete("/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: int):
    doctor_index = next((i for i, d in enumerate(storage.db["doctors"]) if d.id == doctor_id), -1)
    if doctor_index == -1:
        raise HTTPException(status_code=404, detail="Dokter tidak ditemukan")
    storage.db["doctors"].pop(doctor_index)
    return

# =================================================================
# BAGIAN 5: ENDPOINT UNTUK MONITORING
# =================================================================

@router_monitoring.get("/dashboard", response_model=List[schemas.ClinicStatus])
def get_monitoring_dashboard():
    dashboard_data = []
    today = date.today()
    for service in storage.db["services"]:
        doctors_in_service = [d for d in storage.db["doctors"] if service.id in d.services]
        total_patients_waiting = 0
        total_patients_serving = 0
        total_patients_today = 0
        total_max_patients = 0
        for doctor in doctors_in_service:
            queues_today_for_doctor = [q for q in storage.db["queues"] if q.doctor_id == doctor.id and q.registration_time.date() == today]
            total_patients_waiting += len([q for q in queues_today_for_doctor if q.status == 'waiting'])
            total_patients_serving += len([q for q in queues_today_for_doctor if q.status == 'serving'])
            total_patients_today += len(queues_today_for_doctor)
            total_max_patients += doctor.max_patients
        density_percentage = (total_patients_today / total_max_patients * 100) if total_max_patients > 0 else 0
        status_entry = schemas.ClinicStatus(
            service_id=service.id,
            service_name=service.name,
            doctors_count=len(doctors_in_service),
            max_patients_total=total_max_patients,
            patients_waiting=total_patients_waiting,
            patients_serving=total_patients_serving,
            total_patients_today=total_patients_today,
            density_percentage=round(density_percentage, 2)
        )
        dashboard_data.append(status_entry)
    return dashboard_data

# =================================================================
# BAGIAN 6: MENGGABUNGKAN SEMUA ROUTER KE APLIKASI UTAMA
# =================================================================

app.include_router(router_patient)
app.include_router(router_admin_services)
app.include_router(router_admin_doctors)
app.include_router(router_monitoring)

