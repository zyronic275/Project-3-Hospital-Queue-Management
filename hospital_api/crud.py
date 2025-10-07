# hospital_api/crud.py (Final In-Memory Version)
from . import schemas
from .in_memory_db import DB, get_next_id
import datetime

# --- Service CRUD ---
def create_service(service: schemas.ServiceCreate):
    service_id = get_next_id("service_id")
    new_service = {"id": service_id, "name": service.name, "prefix": service.prefix, "doctors": []}
    DB["services"][service_id] = new_service
    return new_service

def get_service(service_id: int):
    return DB["services"].get(service_id)

def get_services():
    return list(DB["services"].values())

# --- Doctor CRUD ---
def create_doctor(doctor: schemas.DoctorBase):
    doctor_id = get_next_id("doctor_id")
    new_doctor = {
        "id": doctor_id, "name": doctor.name,
        "start_time": doctor.start_time or datetime.time(9, 0),
        "end_time": doctor.end_time or datetime.time(17, 0),
        "max_patients": doctor.max_patients or 10, "services": []
    }
    DB["doctors"][doctor_id] = new_doctor
    return new_doctor

def get_doctor(doctor_id: int):
    return DB["doctors"].get(doctor_id)
    
def get_doctors():
    return list(DB["doctors"].values())

def assign_service_to_doctor(doctor_id: int, service_id: int):
    doctor = DB["doctors"].get(doctor_id)
    service = DB["services"].get(service_id)
    if doctor and service:
        if not any(s['id'] == service_id for s in doctor['services']):
            doctor['services'].append(service)
        if not any(d['id'] == doctor_id for d in service['doctors']):
            service['doctors'].append(doctor)
        return doctor
    return None

def update_doctor(doctor_id: int, doctor: schemas.DoctorBase):
    db_doctor = DB["doctors"].get(doctor_id)
    if not db_doctor:
        return None
    update_data = doctor.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        db_doctor[key] = value
    return db_doctor
    
# --- Patient & Queue Functions ---
def get_or_create_patient(patient_name: str):
    for patient in DB["patients"].values():
        if patient['name'] == patient_name:
            return patient
    patient_id = get_next_id("patient_id")
    new_patient = {"id": patient_id, "name": patient_name}
    DB["patients"][patient_id] = new_patient
    return new_patient

def create_queue(patient: dict, service: dict, doctor: dict):
    queue_id = get_next_id("queue_id")
    today = datetime.date.today()
    queue_number = 1 + len([q for q in DB["queues"] if q["doctor"]["id"] == doctor["id"] and q["service"]["id"] == service["id"] and q["registration_time"].date() == today])
    display_id = f"{service['prefix']}{queue_number}"
    new_queue = {
        "id": queue_id, "queue_id_display": display_id, "queue_number": queue_number,
        "registration_time": datetime.datetime.now(), "status": "Menunggu", "visit_notes": None,
        "patient": patient, "service": service, "doctor": doctor
    }
    DB["queues"].append(new_queue)
    return new_queue

def get_queues_for_doctor_today(doctor_id: int, today: datetime.date):
    return [q for q in DB["queues"] if q["doctor"]["id"] == doctor_id and q["registration_time"].date() == today]