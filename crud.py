from datetime import datetime
from . import schemas

# ===== Data Penyimpanan di Memori =====
clinics = []
doctors = []
queues = []

# ===== Clinic CRUD =====
def create_clinic(clinic: schemas.ClinicCreate):
    clinic_id = len(clinics) + 1
    new_clinic = {"id": clinic_id, "name": clinic.name}
    clinics.append(new_clinic)
    return new_clinic


def get_clinics():
    return clinics


def delete_clinic(clinic_id: int):
    global clinics
    for clinic in clinics:
        if clinic["id"] == clinic_id:
            clinics.remove(clinic)
            return clinic
    return None

# ===== Doctor CRUD =====
def create_doctor(doctor: schemas.DoctorCreate):
    doctor_id = len(doctors) + 1
    new_doctor = {"id": doctor_id, "name": doctor.name, "clinic_id": doctor.clinic_id}
    doctors.append(new_doctor)
    return new_doctor


def get_doctors():
    return doctors


def delete_doctor(doctor_id: int):
    global doctors
    for doctor in doctors:
        if doctor["id"] == doctor_id:
            doctors.remove(doctor)
            return doctor
    return None

# ===== Queue CRUD =====
def get_next_queue_number(clinic_id: int):
    today = datetime.now().date()
    today_queues = [q for q in queues if q["clinic_id"] == clinic_id and q["date"] == today]
    return len(today_queues) + 1


def create_queue(queue: schemas.QueueCreate):
    queue_id = len(queues) + 1
    queue_number = get_next_queue_number(queue.clinic_id)
    new_queue = {
        "id": queue_id,
        "patient_name": queue.patient_name,
        "clinic_id": queue.clinic_id,
        "doctor_id": queue.doctor_id,
        "queue_number": queue_number,
        "status": schemas.QueueStatus.MENUNGGU,
        "date": datetime.now().date(),
    }
    queues.append(new_queue)
    return new_queue


def update_queue_status(queue_id: int, status: schemas.QueueStatus):
    for q in queues:
        if q["id"] == queue_id:
            q["status"] = status
            return q
    return None


def get_queues_by_clinic(clinic_id: int):
    today = datetime.now().date()
    return [q for q in queues if q["clinic_id"] == clinic_id and q["date"] == today]


def get_visit_history(patient_name: str):
    return [q for q in queues if q["patient_name"] == patient_name]
