# hospital_api/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from datetime import date
import datetime
from typing import List, Dict, Any

# ==========================================================
# PENGGANTI DATABASE: Semua data disimpan di sini
# ==========================================================
CLINICS_DATA: List[Dict[str, Any]] = [
    {"id": 1, "name": "Klinik Umum"},
    {"id": 2, "name": "Klinik Gigi"},
]
DOCTORS_DATA: List[Dict[str, Any]] = [
    {"id": 101, "name": "Dr. Budi", "clinic_id": 1},
    {"id": 102, "name": "Dr. Ani", "clinic_id": 1},
    {"id": 201, "name": "Dr. Citra", "clinic_id": 2},
]
QUEUES_DATA: List[Dict[str, Any]] = []

# Counter untuk ID, agar setiap data baru punya ID unik
next_clinic_id = 3
next_doctor_id = 202
next_queue_id = 1

# ==========================================================
# Fungsi CRUD untuk Klinik (Tanpa Database)
# ==========================================================

def get_clinic(clinic_id: int):
    """Mencari klinik berdasarkan ID dari list."""
    return next((clinic for clinic in CLINICS_DATA if clinic["id"] == clinic_id), None)

def get_clinic_by_name(name: str):
    """Mencari klinik berdasarkan nama dari list."""
    return next((clinic for clinic in CLINICS_DATA if clinic["name"] == name), None)

def get_clinics(skip: int = 0, limit: int = 100):
    """Mengambil semua data klinik dengan paginasi sederhana."""
    return CLINICS_DATA[skip : skip + limit]

def create_clinic(clinic_name: str):
    """Menambahkan klinik baru ke dalam list."""
    global next_clinic_id
    new_clinic = {"id": next_clinic_id, "name": clinic_name}
    CLINICS_DATA.append(new_clinic)
    next_clinic_id += 1
    return new_clinic

def delete_clinic(clinic_id: int):
    """Menghapus klinik dari list berdasarkan ID."""
    clinic_to_delete = get_clinic(clinic_id)
    if clinic_to_delete:
        CLINICS_DATA.remove(clinic_to_delete)
        return clinic_to_delete
    return None

# ==========================================================
# Fungsi CRUD untuk Dokter (Tanpa Database)
# ==========================================================

def get_doctor(doctor_id: int):
    """Mencari dokter berdasarkan ID dari list."""
    return next((doc for doc in DOCTORS_DATA if doc["id"] == doctor_id), None)

def get_doctors(skip: int = 0, limit: int = 100):
    """Mengambil semua data dokter."""
    return DOCTORS_DATA[skip : skip + limit]

def create_doctor(name: str, clinic_id: int):
    """Menambahkan dokter baru ke dalam list."""
    global next_doctor_id
    new_doctor = {"id": next_doctor_id, "name": name, "clinic_id": clinic_id}
    DOCTORS_DATA.append(new_doctor)
    next_doctor_id += 1
    return new_doctor
    
def delete_doctor(doctor_id: int):
    """Menghapus dokter dari list."""
    doctor_to_delete = get_doctor(doctor_id)
    if doctor_to_delete:
        DOCTORS_DATA.remove(doctor_to_delete)
        return doctor_to_delete
    return None

# ==========================================================
# Fungsi CRUD untuk Antrean (Tanpa Database)
# ==========================================================

def get_next_queue_number(clinic_id: int):
    """Mendapatkan nomor antrean berikutnya untuk klinik tertentu pada hari ini."""
    today = datetime.date.today()
    
    # Filter antrean untuk klinik dan hari yang sama
    queues_today = [
        q for q in QUEUES_DATA 
        if q["clinic_id"] == clinic_id and q["registration_time"].date() == today
    ]
    
    # Cari nomor antrean tertinggi
    max_queue