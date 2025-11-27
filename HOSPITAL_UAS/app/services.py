import pandas as pd
import random
import os
from datetime import datetime, date
from dotenv import load_dotenv
from fastapi import HTTPException

# Load Env
load_dotenv()

# Setup Path File CSV (Agar aman dibaca dari folder manapun)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE_NAME = os.getenv("CSV_FILENAME", "data_set_final_merged.csv")
CSV_PATH = os.path.join(BASE_DIR, CSV_FILE_NAME)

# --- DATABASE SEMENTARA (IN-MEMORY) ---
# Data akan reset jika server dimatikan.
active_queues = [] 
queue_counters = {} # Contoh: {"Poli Umum": 10, "Poli Gigi": 2}

# --- LOGIKA 1: CSV LAZY LOADING ---
def get_historical_samples(limit: int):
    """
    Hanya membaca file CSV saat fungsi ini dipanggil.
    Tidak membebani memori saat startup.
    """
    if not os.path.exists(CSV_PATH):
        raise HTTPException(status_code=404, detail=f"File {CSV_FILE_NAME} tidak ditemukan.")
    
    try:
        # Baca CSV
        df = pd.read_csv(CSV_PATH)
        
        # Logic Limit
        if limit > len(df):
            limit = len(df)
        
        # Sampling Acak
        return df.sample(n=limit).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- LOGIKA 2: SISTEM ANTREAN BERURUT ---
def register_patient_logic(data):
    """Mendaftarkan pasien & generate nomor antrean (PO-YYYYMMDD-001)"""
    global active_queues, queue_counters
    
    clinic_name = data.clinic_name
    today_str = date.today().strftime("%Y%m%d")
    
    # Ambil inisial klinik (Poli Umum -> PO)
    prefix = clinic_name[:2].upper()
    
    # Cek nomor urut terakhir
    if clinic_name not in queue_counters:
        queue_counters[clinic_name] = 0
    
    # Tambah nomor urut
    queue_counters[clinic_name] += 1
    current_no = queue_counters[clinic_name]
    
    # Format: PO-20231127-001
    queue_code = f"{prefix}-{today_str}-{current_no:03d}"
    
    new_entry = {
        "queue_number": queue_code,
        "patient_name": data.patient_name,
        "clinic": clinic_name,
        "doctor": data.doctor_name,
        "status": "MENUNGGU",
        "registration_time": datetime.now(),
        "diagnosis": None
    }
    
    active_queues.append(new_entry)
    return new_entry

def get_doctor_queue_logic(doctor_name: str):
    """Filter antrean berdasarkan nama dokter"""
    return [q for q in active_queues if q['doctor'] == doctor_name]

def update_status_logic(queue_number: str, status: str, diagnosis: str = None):
    """Update status pasien"""
    for patient in active_queues:
        if patient['queue_number'] == queue_number:
            patient['status'] = status
            if diagnosis:
                patient['diagnosis'] = diagnosis
            return patient
    
    raise HTTPException(status_code=404, detail="Nomor antrean tidak ditemukan")

def get_all_queues():
    """Untuk admin monitoring"""
    return active_queues