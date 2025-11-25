import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from datetime import time
import sys
import os 
from pydantic import ConfigDict 

# --- PERBAIKAN IMPORT PATH: Menambahkan folder root ke sys.path ---
# Ini memungkinkan Python menemukan main.py dan database.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

# --- IMPORTS MODUL APLIKASI ---
from main import app 
from database import get_db, Base 
from modules.master.models import Service, Doctor, GenderRestriction
from modules.queue.models import Visit, VisitStatus
from modules.queue.schemas import InsuranceType 

# Database pengujian in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 1. SETUP FIXTURES ---

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    service_umum = Service(id=1, name="Poli Umum", prefix="U", min_age=0, max_age=100, gender_restriction=GenderRestriction.NONE, is_active=True)
    service_kandungan = Service(id=2, name="Poli Kandungan", prefix="K", min_age=15, max_age=55, gender_restriction=GenderRestriction.FEMALE, is_active=True)

    doctor_ali = Doctor(id=101, doctor_name="dr. Ali", doctor_code=1, max_patients=3, service_id=1, practice_start_time=time(8, 0), practice_end_time=time(17, 0), is_active=True)
    doctor_budi = Doctor(id=102, doctor_name="dr. Budi", doctor_code=2, max_patients=5, service_id=2, practice_start_time=time(8, 0), practice_end_time=time(17, 0), is_active=True)
    
    db.add_all([service_umum, service_kandungan, doctor_ali, doctor_budi])
    db.commit()
    
    yield db 
    
    Base.metadata.drop_all(bind=engine)

# --- 2. FUNGSI PENGUJIAN ---

# ... (test_read_services, test_available_services_filtering, test_available_doctors_by_time tidak diubah) ...

def test_register_patient_validation(setup_database):
    """Memastikan validasi usia dan gender diterapkan saat registrasi (Logika Bisnis -> 400)."""
    
    data_fail_gender = {
        "patient_name": "Mr. Uji Gagal",
        "gender": "MALE",
        "age": 30, 
        "insurance_type": InsuranceType.PRIBADI.value,
        "doctor_id": 102, 
        "consultation_time": "10:00"
    }
    response = client.post("/api/v1/queue/register", json=data_fail_gender)
    assert response.status_code == 400
    
    data_fail_age = {
        "patient_name": "Ms. Uji Gagal",
        "gender": "FEMALE",
        "age": 10, 
        "insurance_type": InsuranceType.PRIBADI.value,
        "doctor_id": 102, 
        "consultation_time": "10:00"
    }
    response = client.post("/api/v1/queue/register", json=data_fail_age)
    assert response.status_code == 400

def test_successful_registration_and_numbering(setup_database):
    """Memastikan pendaftaran berhasil dan nomor antrean komposit benar."""
    
    data_success = {
        "patient_name": "Mr. Uji Sukses",
        "gender": "MALE",
        "age": 40, 
        "insurance_type": InsuranceType.BPJS.value,
        "doctor_id": 101, 
        "consultation_time": "09:00"
    }
    
    response1 = client.post("/api/v1/queue/register", json=data_success)
    assert response1.status_code == 201
    
    data1 = response1.json()
    assert data1['queue_sequence'] == 1
    assert data1['queue_number'] == "U-1-001" 
    assert data1['status'] == VisitStatus.IN_QUEUE.value 
    
    response2 = client.post("/api/v1/queue/register", json=data_success)
    assert response2.status_code == 201
    
    data2 = response2.json()
    assert data2['queue_sequence'] == 2
    assert data2['queue_number'] == "U-1-002"
    assert data2['status'] == VisitStatus.IN_QUEUE.value

def test_quota_limit(setup_database):
    """Memastikan pendaftaran gagal jika kuota dokter sudah terpenuhi (Max Quota Dokter Ali = 3)."""
    
    data_quota = {
        "patient_name": "Quota Test",
        "gender": "MALE", "age": 40, "insurance_type": InsuranceType.PRIBADI.value, 
        "doctor_id": 101, "consultation_time": "09:00"
    }
    
    # Registrasi ke-3 (Mengisi slot terakhir, Seharusnya OK -> 201)
    client.post("/api/v1/queue/register", json=data_quota)
    
    # Registrasi ke-4 (Seharusnya GAGAL -> 400)
    response_fail = client.post("/api/v1/queue/register", json=data_quota)
    assert response_fail.status_code == 400
    assert "Doctor quota reached for today" in response_fail.json()['detail']

def test_update_status(setup_database):
    """Memastikan status antrean dapat diubah (memperbaiki error 404/400)."""
    
    data_success = {
        "patient_name": "Status Update Test",
        "gender": "FEMALE", "age": 30, "insurance_type": InsuranceType.BPJS.value,
        "doctor_id": 102, "consultation_time": "11:00"
    }
    
    response_reg = client.post("/api/v1/queue/register", json=data_success)
    assert response_reg.status_code == 201
    visit_id = response_reg.json()['id']
    
    # Ubah status dari IN_QUEUE ke CALLED (Harus sukses -> 200)
    response_called = client.put(f"/api/v1/queue/{visit_id}/status", json={"status": VisitStatus.CALLED.value})
    assert response_called.status_code == 200
    
    # Ubah status dari CALLED ke FINISHED (Harus sukses -> 200)
    response_finished = client.put(f"/api/v1/queue/{visit_id}/status", json={"status": VisitStatus.FINISHED.value})
    assert response_finished.status_code == 200