from typing import List, Dict, Any
from datetime import time
from . import schemas

# Data awal untuk aplikasi
db_data: Dict[str, List[Dict[str, Any]]] = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "A"},
        {"id": 2, "name": "Poli Gigi", "prefix": "B"},
        {"id": 3, "name": "Poli Anak", "prefix": "C"},
        {"id": 4, "name": "Laboratorium", "prefix": "D"},
    ],
    "doctors": [
        {"id": 1, "doctor_code": "1", "name": "dr. Elan", "services": [1], "practice_start_time": time(9, 0), "practice_end_time": time(17, 0), "max_patients": 20},
        {"id": 5, "doctor_code": "2", "name": "dr. Budi", "services": [1], "practice_start_time": time(10, 0), "practice_end_time": time(16, 30), "max_patients": 25},
        {"id": 2, "doctor_code": "1", "name": "drg. Aura", "services": [2], "practice_start_time": time(14, 0), "practice_end_time": time(18, 0), "max_patients": 15},
        {"id": 6, "doctor_code": "2", "name": "drg. Tiffany", "services": [2], "practice_start_time": time(15, 0), "practice_end_time": time(19, 0), "max_patients": 15},
        {"id": 3, "doctor_code": "1", "name": "dr. Candra", "services": [3], "practice_start_time": time(8, 0), "practice_end_time": time(15, 0), "max_patients": 30},
        {"id": 7, "doctor_code": "2", "name": "dr. Putri", "services": [3], "practice_start_time": time(8, 30), "practice_end_time": time(14, 0), "max_patients": 20},
        {"id": 4, "doctor_code": "1", "name": "dr. Dita", "services": [4], "practice_start_time": time(7, 0), "practice_end_time": time(20, 0), "max_patients": 50},
        {"id": 8, "doctor_code": "2", "name": "dr. Eka", "services": [4], "practice_start_time": time(7, 0), "practice_end_time": time(20, 0), "max_patients": 50},
    ],
    "patients": [],
    "queues": []
}

# Inisialisasi database dalam memori menggunakan Pydantic schemas
db = {
    "services": [schemas.ServiceSchema(**s) for s in db_data["services"]],
    "doctors": [schemas.DoctorSchema(**d) for d in db_data["doctors"]],
    "patients": [schemas.PatientSchema(**p) for p in db_data["patients"]],
    "queues": [schemas.QueueSchema(**q) for q in db_data["queues"]],
}

def get_max_id(data_list: List[Dict[str, Any]]) -> int:
    if not data_list:
        return 0
    return max(item.get("id", 0) for item in data_list)

# Penghitung ID untuk memastikan ID baru selalu unik
id_counters = {
    "services": get_max_id(db_data["services"]),
    "doctors": get_max_id(db_data["doctors"]),
    "patients": get_max_id(db_data["patients"]),
    "queues": get_max_id(db_data["queues"]),
}

