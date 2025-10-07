# hospital_api/in_memory_db.py
import datetime

DB = { "services": {}, "doctors": {}, "queues": [], "patients": {} }
COUNTERS = { "service_id": 0, "doctor_id": 0, "queue_id": 0, "patient_id": 0 }

def get_next_id(name):
    COUNTERS[name] += 1
    return COUNTERS[name]

def reset_database():
    """Mengosongkan semua data di memori."""
    global DB, COUNTERS
    DB = { "services": {}, "doctors": {}, "queues": [], "patients": {} }
    COUNTERS = { "service_id": 0, "doctor_id": 0, "queue_id": 0, "patient_id": 0 }