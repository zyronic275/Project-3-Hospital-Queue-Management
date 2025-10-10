from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import datetime

# Impor dari file lokal
from . import storage
from . import schemas

# =================================================================
# BAGIAN 1: INISIALISASI APLIKASI UTAMA DAN ROUTER
# =================================================================

app = FastAPI(
    title="Hospital Queue Management API (Router Version)",
    description="API yang diorganisir menggunakan APIRouter untuk skalabilitas.",
    version="1.5.0"
)

router_public = APIRouter(tags=["Public Info & Registration"])
router_admin_services = APIRouter(prefix="/admin/services", tags=["Admin: Services"])
router_admin_doctors = APIRouter(prefix="/admin/doctors", tags=["Admin: Doctors"])
router_monitoring = APIRouter(prefix="/admin", tags=["Admin: Monitoring"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def load_initial_data():
    """Memuat dan mengonversi data awal ke model Pydantic saat aplikasi dimulai."""
    storage.db["services"] = [schemas.ServiceSchema(**s) for s in storage.db_data["services"]]
    storage.db["doctors"] = [schemas.DoctorSchema(**d) for d in storage.db_data["doctors"]]
    storage.db["patients"] = [schemas.PatientSchema(**p) for p in storage.db_data["patients"]]
    storage.db["queues"] = []


# =================================================================
# BAGIAN 2: ENDPOINT PUBLIK (INFO, REGISTRASI & ANTRIAN)
# =================================================================

def time_to_seconds(t: datetime.time) -> int:
    """Fungsi bantuan untuk mengubah objek waktu menjadi detik sejak tengah malam."""
    return t.hour * 3600 + t.minute * 60 + t.second

@router_public.get("/services/{service_id}/available-doctors", response_model=List[schemas.DoctorAvailableSchema])
def get_available_doctors_for_service(service_id: int):
    service = next((s for s in storage.db["services"] if s.id == service_id), None)
    if not service:
        raise HTTPException(status_code=404, detail=f"Layanan dengan id {service_id} tidak ditemukan")

    now_in_seconds = time_to_seconds(datetime.datetime.now().time())
    today = datetime.date.today()

    practicing_doctors = [
        d for d in storage.db["doctors"]
        if service_id in d.services and \
           time_to_seconds(d.practice_start_time) <= now_in_seconds and \
           time_to_seconds(d.practice_end_time) >= now_in_seconds
    ]
    
    if not practicing_doctors:
          raise HTTPException(status_code=404, detail=f"Tidak ada dokter yang sedang praktik untuk layanan {service.name} saat ini.")

    available_doctors_with_quota = []
    for doctor in practicing_doctors:
        current_queue_count = len([
            q for q in storage.db["queues"]
            if q.doctor_id == doctor.id and q.registration_time.date() == today
        ])
        remaining_quota = doctor.max_patients - current_queue_count
        if remaining_quota > 0:
            doctor_data = doctor.model_dump()
            doctor_data["remaining_quota"] = remaining_quota
            available_doctors_with_quota.append(doctor_data)

    if not available_doctors_with_quota:
        raise HTTPException(status_code=404, detail=f"Semua dokter untuk layanan {service.name} sudah penuh.")

    return available_doctors_with_quota


@router_public.post("/register", response_model=schemas.RegistrationResponse, status_code=201)
def register_patient(request: schemas.RegistrationRequest):
    patient = next((p for p in storage.db["patients"] if p.name.lower() == request.patient_name.lower()), None)
    if not patient:
        storage.id_counters["patients"] += 1
        patient = schemas.PatientSchema(id=storage.id_counters["patients"], name=request.patient_name)
        storage.db["patients"].append(patient)

    tickets = []
    today = datetime.date.today()
    now_in_seconds = time_to_seconds(datetime.datetime.now().time())

    for service_id in request.service_ids:
        service = next((s for s in storage.db["services"] if s.id == service_id), None)
        if not service:
            raise HTTPException(status_code=404, detail=f"Layanan dengan id {service_id} tidak ditemukan")

        available_doctors = [
            d for d in storage.db["doctors"]
            if service_id in d.services and \
               time_to_seconds(d.practice_start_time) <= now_in_seconds and \
               time_to_seconds(d.practice_end_time) >= now_in_seconds
        ]
        
        if not available_doctors:
            raise HTTPException(status_code=404, detail=f"Tidak ada dokter yang praktik untuk layanan {service.name} saat ini.")

        doctor_to_assign = None
        if request.doctor_id:
            chosen_doctor = next((d for d in available_doctors if d.id == request.doctor_id), None)
            if not chosen_doctor:
                raise HTTPException(status_code=400, detail="Dokter yang dipilih tidak tersedia atau tidak melayani layanan ini saat ini.")
            doctor_to_assign = chosen_doctor
        elif len(available_doctors) > 1:
             raise HTTPException(status_code=400, detail=f"Terdapat lebih dari satu dokter yang tersedia untuk {service.name}. Harap pilih salah satu.")
        else:
            doctor_to_assign = available_doctors[0]
        
        queues_today_for_doctor = [
            q for q in storage.db["queues"]
            if q.doctor_id == doctor_to_assign.id and q.registration_time.date() == today
        ]
        if len(queues_today_for_doctor) >= doctor_to_assign.max_patients:
            raise HTTPException(status_code=400, detail=f"Kuota untuk dokter {doctor_to_assign.name} sudah penuh.")

        new_queue_number = len(queues_today_for_doctor) + 1
        queue_id_display = f"{service.prefix}-{doctor_to_assign.doctor_code}-{new_queue_number:03d}"
        
        storage.id_counters["queues"] += 1
        new_queue = schemas.QueueSchema(
            id=storage.id_counters["queues"],
            queue_id_display=queue_id_display,
            queue_number=new_queue_number,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor_to_assign.id,
            registration_time=datetime.datetime.now()
        )
        storage.db["queues"].append(new_queue)
        
        tickets.append(schemas.Ticket(
            service=service, 
            queue_number=new_queue.queue_id_display, 
            doctor=doctor_to_assign
        ))
            
    return schemas.RegistrationResponse(patient=patient, tickets=tickets)

@router_public.get("/queues/{service_id}", response_model=List[schemas.QueueSchema])
def get_queue_for_service(service_id: int, status: str = "waiting"):
    today = datetime.date.today()
    queues = [
        q for q in storage.db["queues"] 
        if q.service_id == service_id and q.status == status and q.registration_time.date() == today
    ]
    queues.sort(key=lambda q: q.queue_number)
    return queues

@router_public.put("/queues/{queue_id}/status", response_model=schemas.QueueSchema)
def update_queue_status(queue_id: int, request_body: schemas.QueueStatusUpdate):
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
    if any(s.prefix.lower() == service.prefix.lower() for s in storage.db["services"]):
        raise HTTPException(status_code=400, detail=f"Prefix '{service.prefix}' sudah digunakan oleh layanan lain.")
    
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

    if "prefix" in update_data:
        if any(s.prefix.lower() == update_data["prefix"].lower() and s.id != service_id for s in storage.db["services"]):
            raise HTTPException(status_code=400, detail=f"Prefix '{update_data['prefix']}' sudah digunakan oleh layanan lain.")

    for key, value in update_data.items():
        setattr(service, key, value)
    return service

@router_admin_services.delete("/{service_id}", status_code=204)
def delete_service(service_id: int):
    service_index = next((i for i, s in enumerate(storage.db["services"]) if s.id == service_id), -1)
    if service_index == -1:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan")
    
    doctors_to_remove = []
    for doctor in storage.db["doctors"]:
        if service_id in doctor.services:
            if len(doctor.services) == 1:
                doctors_to_remove.append(doctor.id)
            else:
                doctor.services.remove(service_id)

    if doctors_to_remove:
        storage.db["doctors"] = [d for d in storage.db["doctors"] if d.id not in doctors_to_remove]

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
    # PERUBAHAN BARU: Validasi keunikan `doctor_code` per layanan
    for service_id in doctor_req.services:
        for existing_doctor in storage.db["doctors"]:
            if service_id in existing_doctor.services and existing_doctor.doctor_code == doctor_req.doctor_code:
                service = next((s for s in storage.db["services"] if s.id == service_id), None)
                raise HTTPException(
                    status_code=400,
                    detail=f"Kode dokter '{doctor_req.doctor_code}' sudah digunakan di {service.name} oleh {existing_doctor.name}."
                )

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
    
    # PERUBAHAN BARU: Validasi keunikan `doctor_code` saat update
    check_code = update_data.get("doctor_code", doctor.doctor_code)
    check_services = update_data.get("services", doctor.services)

    for service_id in check_services:
        for existing_doctor in storage.db["doctors"]:
            if existing_doctor.id != doctor_id and service_id in existing_doctor.services and existing_doctor.doctor_code == check_code:
                service = next((s for s in storage.db["services"] if s.id == service_id), None)
                raise HTTPException(
                    status_code=400,
                    detail=f"Kode dokter '{check_code}' sudah digunakan di {service.name} oleh {existing_doctor.name}."
                )

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
    today = datetime.date.today()
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

app.include_router(router_public)
app.include_router(router_admin_services)
app.include_router(router_admin_doctors)
app.include_router(router_monitoring)

