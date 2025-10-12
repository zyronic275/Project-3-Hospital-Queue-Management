from datetime import time

# --- Database In-Memory ---

# PERUBAHAN: Menggunakan prefix yang lebih deskriptif
db_data = {
    "services": [
        {"id": 1, "name": "Poli Umum", "prefix": "UMUM"},
        {"id": 2, "name": "Poli Gigi", "prefix": "GIGI"},
        {"id": 3, "name": "Poli Anak", "prefix": "ANAK"},
        {"id": 4, "name": "Laboratorium", "prefix": "LAB"},
    ],
    "doctors": [
        {"id": 1, "doctor_code": "1", "name": "dr. Elan", "services": [1], "practice_start_time": time(8, 0), "practice_end_time": time(16, 0), "max_patients": 20},
        {"id": 5, "doctor_code": "2", "name": "dr. Budi", "services": [1], "practice_start_time": time(13, 0), "practice_end_time": time(17, 0), "max_patients": 25},
        {"id": 2, "doctor_code": "1", "name": "drg. Aura", "services": [2], "practice_start_time": time(14, 0), "practice_end_time": time(18, 0), "max_patients": 15},
        {"id": 6, "doctor_code": "2", "name": "drg. Tiffany", "services": [2], "practice_start_time": time(10, 0), "practice_end_time": time(14, 0), "max_patients": 15},
        {"id": 3, "doctor_code": "1", "name": "dr. Candra", "services": [3], "practice_start_time": time(8, 0), "practice_end_time": time(15, 0), "max_patients": 1},
        {"id": 7, "doctor_code": "2", "name": "dr. Putri", "services": [3], "practice_start_time": time(12, 0), "practice_end_time": time(18, 0), "max_patients": 20},
        {"id": 4, "doctor_code": "1", "name": "dr. Dita", "services": [4], "practice_start_time": time(9, 0), "practice_end_time": time(13, 0), "max_patients": 50},
        {"id": 8, "doctor_code": "2", "name": "dr. Eka", "services": [4], "practice_start_time": time(13, 0), "practice_end_time": time(17, 0), "max_patients": 40},
    ],
    "patients": [],
    "queues": []
}

# Inisialisasi counter ID
def get_max_id(data_list):
    if not data_list: return 0
    return max(item.get("id", 0) for item in data_list)

id_counters = {
    "services": get_max_id(db_data["services"]),
    "doctors": get_max_id(db_data["doctors"]),
    "patients": get_max_id(db_data["patients"]),
    "queues": get_max_id(db_data["queues"]),
}

# Inisialisasi database Pydantic (akan diisi saat startup)
db = {
    "services": [],
    "doctors": [],
    "patients": [],
    "queues": [],
}
