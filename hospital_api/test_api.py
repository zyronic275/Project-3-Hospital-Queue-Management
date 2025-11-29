import pytest
from fastapi.testclient import TestClient
from main import app
from datetime import date

client = TestClient(app)

# Helper untuk data unik agar test bisa diulang-ulang tanpa reset DB
import random
RANDOM_CODE = random.randint(1000, 9999)
TEST_POLI = f"Poli Test {RANDOM_CODE}"
TEST_PREFIX = f"TES{RANDOM_CODE}"
TEST_DOKTER = f"Dr. Test {RANDOM_CODE}"

def test_root_dashboard():
    """Test apakah dashboard bisa diakses"""
    response = client.get("/monitor/dashboard")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_poli():
    """Test membuat poli baru & validasi duplikat"""
    payload = {"poli": TEST_POLI, "prefix": TEST_PREFIX}
    response = client.post("/admin/polis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["poli"] == TEST_POLI
    assert data["prefix"] == TEST_PREFIX
    
    # Test Duplikat Poli
    res_fail = client.post("/admin/polis", json=payload)
    assert res_fail.status_code == 400 # Harus error karena sudah ada

def test_create_doctor():
    """Test membuat dokter dengan format waktu yang benar"""
    payload = {
        "dokter": TEST_DOKTER,
        "poli": TEST_POLI,
        "practice_start_time": "08:00", # Format benar
        "practice_end_time": "16:00",
        "max_patients": 10
    }
    response = client.post("/admin/doctors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["dokter"] == TEST_DOKTER
    # Cek format kode dokter (harus mengandung prefix poli)
    assert TEST_PREFIX in data["doctor_code"]

def test_create_doctor_invalid_time():
    """Test validasi format waktu salah"""
    payload = {
        "dokter": "Dr. Fail",
        "poli": TEST_POLI,
        "practice_start_time": "Jam 8", # Salah
        "practice_end_time": "16:00",
        "max_patients": 10
    }
    response = client.post("/admin/doctors", json=payload)
    assert response.status_code == 400 # Expect error

def test_registration_flow():
    """Test pendaftaran pasien & format nomor antrean"""
    # 1. Cari ID Dokter dulu
    res_doc = client.get("/public/available-doctors", params={"poli_name": TEST_POLI, "visit_date": str(date.today())})
    doctor_id = res_doc.json()[0]['doctor_id']
    
    # 2. Register
    payload = {
        "nama_pasien": "Pasien Test",
        "poli": TEST_POLI,
        "doctor_id": doctor_id,
        "visit_date": str(date.today())
    }
    response = client.post("/public/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Assert Queue Number Format (String)
    # Format harus: PREFIX-XXX-YYY
    assert data["queue_number"].startswith(TEST_PREFIX)
    # Assert Sequence (Int)
    assert isinstance(data["queue_sequence"], int)
    assert data["queue_sequence"] >= 1

def test_import_random():
    """Test endpoint import data"""
    response = client.get("/admin/import-random-data", params={"count": 2})
    assert response.status_code == 200
    assert "Sukses import" in response.json()["message"]