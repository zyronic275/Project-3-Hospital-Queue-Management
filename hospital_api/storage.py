# hospital_api/storage.py

from gc import get_stats
from . import schemas
from datetime import date, datetime
from typing import Optional

# --- In-Memory Data Storage ---
# We use dictionaries to simulate database tables.
# The key is the ID (integer), and the value is the Pydantic model.
CLINICS: dict[int, schemas.Clinic] = {}
DOCTORS: dict[int, schemas.Doctor] = {}
QUEUES: dict[int, schemas.Queue] = {}

# --- ID Counters for auto-incrementing ---
next_clinic_id = 1
next_doctor_id = 1
next_queue_id = 1

# === Clinic Functions ===

def get_clinics() -> list[schemas.Clinic]:
    return list(CLINICS.values())

def get_clinic_by_name(name: str) -> Optional[schemas.Clinic]:
    for clinic in CLINICS.values():
        if clinic.name == name:
            return clinic
    return None

def create_clinic(clinic_create: schemas.ClinicCreate) -> schemas.Clinic:
    global next_clinic_id
    new_clinic = schemas.Clinic(id=next_clinic_id, name=clinic_create.name)
    CLINICS[next_clinic_id] = new_clinic
    next_clinic_id += 1
    return new_clinic

def delete_clinic(clinic_id: int) -> Optional[schemas.Clinic]:
    if clinic_id in CLINICS:
        return CLINICS.pop(clinic_id)
    return None

# === Doctor Functions ===

def get_doctor_by_clinic(clinic_id: int) -> Optional[schemas.Doctor]:
    for doctor in DOCTORS.values():
        if doctor.clinic_id == clinic_id:
            return doctor
    return None

def create_doctor(doctor_create: schemas.DoctorCreate) -> Optional[schemas.Doctor]:
    # Enforce the "one doctor per clinic" rule
    if get_doctor_by_clinic(doctor_create.clinic_id):
        return None  # Clinic already has a doctor
    
    global next_doctor_id
    new_doctor = schemas.Doctor(
        id=next_doctor_id, 
        name=doctor_create.name, 
        specialization=doctor_create.specialization,
        clinic_id=doctor_create.clinic_id
    )
    DOCTORS[next_doctor_id] = new_doctor
    next_doctor_id += 1
    return new_doctor
    
def delete_doctor(doctor_id: int) -> Optional[schemas.Doctor]:
    if doctor_id in DOCTORS:
        return DOCTORS.pop(doctor_id)
    return None

# === Queue Functions ===

def get_next_queue_number(clinic_id: int) -> int:
    today = date.today()
    max_queue = 0
    for queue in QUEUES.values():
        if queue.clinic_id == clinic_id and queue.registration_time.date() == today:
            if queue.queue_number > max_queue:
                max_queue = queue.queue_number
    return max_queue + 1

def create_queue(queue_create: schemas.QueueCreate) -> Optional[schemas.Queue]:
    doctor = get_doctor_by_clinic(queue_create.clinic_id)
    if not doctor:
        return None # No doctor in this clinic

    queue_number = get_next_queue_number(queue_create.clinic_id)
    
    global next_queue_id
    new_queue = schemas.Queue(
        id=next_queue_id,
        patient_name=queue_create.patient_name,
        clinic_id=queue_create.clinic_id,
        doctor_id=doctor.id,
        queue_number=queue_number,
        status=schemas.QueueStatus.MENUNGGU,
        registration_time=datetime.utcnow()
    )
    QUEUES[next_queue_id] = new_queue
    next_queue_id += 1
    return new_queue
    
def get_queues_by_clinic(clinic_id: int) -> list[schemas.Queue]:
    today = date.today()
    today_queues = []
    for queue in QUEUES.values():
        if queue.clinic_id == clinic_id and queue.registration_time.date() == today:
            today_queues.append(queue)
    # Sort by queue number
    return sorted(today_queues, key=lambda q: q.queue_number)

def update_queue_status(queue_id: int, status: str) -> Optional[schemas.Queue]:
    if queue_id in QUEUES:
        QUEUES[queue_id].status = get_stats
        return QUEUES[queue_id]
    return None