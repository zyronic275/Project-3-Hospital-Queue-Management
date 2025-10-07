# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

# -----------------------------------------------------
# 1. INISIALISASI APLIKASI
# -----------------------------------------------------
app = FastAPI(
    title="Sistem Antrean Rumah Sakit",
    description="API untuk mengelola antrean pasien berdasarkan klinik dan dokter.",
    version="1.0.0"
)

# -----------------------------------------------------
# 2. "IN-MEMORY DATABASE" (DATA DISIMPAN DI VARIABEL)
# -----------------------------------------------------
# Data ini akan reset setiap kali aplikasi direstart.

# Data Master Klinik
CLINICS_DATA = [
    {"id": 1, "name": "Klinik Gizi", "code": "A"},
    {"id": 2, "name": "Klinik Gigi", "code": "B"},
    {"id": 3, "name": "Klinik Umum", "code": "C"},
]

# Data Master Dokter (2 dokter per klinik)
DOCTORS_DATA = [
    # Dokter untuk Klinik Gizi (clinic_id: 1)
    {"id": 101, "name": "Dr. Amanda Puspita, Sp.GK", "clinic_id": 1},
    {"id": 102, "name": "Dr. Bayu Wijaya, Sp.GK", "clinic_id": 1},
    
    # Dokter untuk Klinik Gigi (clinic_id: 2)
    {"id": 201, "name": "Dr. Citra Lestari, Sp.KGA", "clinic_id": 2},
    {"id": 202, "name": "Dr. Dian Permana, Sp.Ort", "clinic_id": 2},

    # Dokter untuk Klinik Umum (clinic_id: 3)
    {"id": 301, "name": "Dr. Eko Prasetyo", "clinic_id": 3},
    {"id": 302, "name": "Dr. Fina Rahmawati", "clinic_id": 3},
]

# Penyimpan nomor antrean terakhir untuk setiap klinik
# Key adalah clinic_id, Value adalah nomor urut terakhir
QUEUE_COUNTERS = {clinic["id"]: 0 for clinic in CLINICS_DATA}

# Penyimpan data antrean yang sudah diambil
PATIENT_QUEUES = []

# -----------------------------------------------------
# 3. MODEL DATA (PYDANTIC)
# -----------------------------------------------------
# Model untuk request pengambilan nomor antrean
class QueueRequest(BaseModel):
    patient_name: str
    clinic_id: int
    doctor_id: int

# Model untuk response data dokter, klinik, dan antrean
class Clinic(BaseModel):
    id: int
    name: str
    code: str

class Doctor(BaseModel):
    id: int
    name: str
    clinic_id: int

class QueueTicket(BaseModel):
    queue_number: str
    patient_name: str
    clinic: Clinic
    doctor: Doctor

# -----------------------------------------------------
# 4. ENDPOINTS API
# -----------------------------------------------------

@app.get("/", tags=["Home"])
async def read_root():
    """Endpoint utama untuk mengecek apakah API berjalan."""
    return {"message": "Selamat datang di API Sistem Antrean Rumah Sakit"}

# --- Endpoint untuk Flow Pengambilan Antrean ---

@app.get("/clinics", response_model=List[Clinic], tags=["Antrean"])
async def get_all_clinics():
    """
    Langkah 1: Mendapatkan daftar semua klinik yang tersedia.
    """
    return CLINICS_DATA

@app.get("/clinics/{clinic_id}/doctors", response_model=List[Doctor], tags=["Antrean"])
async def get_doctors_by_clinic(clinic_id: int):
    """
    Langkah 2: Mendapatkan daftar dokter untuk klinik yang dipilih.
    """
    # Cek apakah klinik ada
    if not any(c["id"] == clinic_id for c in CLINICS_DATA):
        raise HTTPException(status_code=404, detail="Klinik tidak ditemukan.")
    
    # Filter dokter berdasarkan clinic_id
    available_doctors = [doc for doc in DOCTORS_DATA if doc["clinic_id"] == clinic_id]
    return available_doctors

@app.post("/queues/take", response_model=QueueTicket, tags=["Antrean"])
async def take_queue_number(request: QueueRequest):
    """
    Langkah 3: Mengambil nomor antrean setelah memilih klinik dan dokter.
    """
    # Validasi input
    clinic = next((c for c in CLINICS_DATA if c["id"] == request.clinic_id), None)
    doctor = next((d for d in DOCTORS_DATA if d["id"] == request.doctor_id), None)

    if not clinic:
        raise HTTPException(status_code=404, detail="Klinik dengan ID tersebut tidak ditemukan.")
    if not doctor:
        raise HTTPException(status_code=404, detail="Dokter dengan ID tersebut tidak ditemukan.")
    if doctor["clinic_id"] != clinic["id"]:
        raise HTTPException(status_code=400, detail="Dokter yang dipilih tidak bertugas di klinik tersebut.")

    # Buat nomor antrean baru
    # 1. Ambil nomor urut terakhir dan tambahkan 1
    QUEUE_COUNTERS[clinic["id"]] += 1
    new_queue_seq = QUEUE_COUNTERS[clinic["id"]]

    # 2. Format nomor antrean dengan kode klinik (contoh: A001, B012)
    queue_number_str = f"{clinic['code']}{new_queue_seq:03d}"

    # Buat "tiket" antrean
    ticket = {
        "queue_number": queue_number_str,
        "patient_name": request.patient_name,
        "clinic": clinic,
        "doctor": doctor
    }

    # Simpan tiket ke daftar antrean (simulasi database)
    PATIENT_QUEUES.append(ticket)

    return ticket