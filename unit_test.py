# unit_test.py (versi perbaikan)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import dari aplikasi utama Anda
# Pastikan semua model diimport agar Base.metadata tahu semua tabel
from hospital_api.main import app
from hospital_api.database import get_db
from hospital_api.models import Base, Service, Doctor, Patient, Queue, QueueStatus
from unittest.mock import patch
import datetime


# --- Konfigurasi Database Khusus untuk Testing ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Override Dependency get_db ---
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# --- Fixture untuk Setup dan Teardown Database ---
# Ini adalah bagian yang diperbaiki.
# scope="function" berarti ini akan dijalankan untuk setiap fungsi tes
@pytest.fixture(scope="function")
def db_session():
    # Buat semua tabel dari models.py DI DALAM database memori
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Hapus semua tabel setelah tes selesai, agar tes berikutnya mulai dari nol lagi
        Base.metadata.drop_all(bind=engine)

# Membuat client untuk melakukan request ke API
# Kita lewatkan db_session sebagai argumen ke setiap tes yang membutuhkannya
client = TestClient(app)

# ===============================================
# === Mulai Skenario Pengujian (Unit Tests) ===
# ===============================================

def test_create_service(db_session):
    """Tes 1: Admin - Memastikan bisa membuat layanan baru."""
    response = client.post("/admin/services/", json={"name": "Poli Umum", "prefix": "A"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Poli Umum"
    assert data["prefix"] == "A"
    assert "id" in data

def test_create_doctor(db_session):
    """Tes 2: Admin - Memastikan bisa membuat dokter baru."""
    response = client.post("/admin/doctors/", json={"name": "Dr. Warkop"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Dr. Warkop"
    assert "id" in data

def test_assign_doctor_to_service(db_session):
    """Tes 3: Admin - Memastikan bisa menugaskan dokter ke layanan."""
    service_res = client.post("/admin/services/", json={"name": "Poli Komedi", "prefix": "K"})
    doctor_res = client.post("/admin/doctors/", json={"name": "Dr. Indro"})
    service_id = service_res.json()["id"]
    doctor_id = doctor_res.json()["id"]

    response = client.post(f"/admin/doctors/{doctor_id}/assign-service/?service_id={service_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["name"] == "Dr. Indro"
    assert len(data["services"]) == 1
    assert data["services"][0]["name"] == "Poli Komedi"

@patch('hospital_api.routers.registration.datetime')
def test_patient_registration_and_queue_id(mock_dt, db_session):
    """Tes 4: Pendaftaran - Memastikan pasien mendapat ID antrean yang benar."""
    mock_dt.now.return_value.time.return_value = datetime.time(10, 0) # Anggap sekarang jam 10:00

    client.post("/admin/services/", json={"name": "Poli Jantung", "prefix": "J"})
    client.post("/admin/doctors/", json={"name": "Dr. Dono"})
    client.post("/admin/doctors/1/assign-service/?service_id=1")

    response = client.post("/register", json={"patient_name": "Pasien Satu", "service_ids": [1]})
    assert response.status_code == 200, response.text
    # ... sisa tes tetap sama ...
    data = response.json()
    assert data["tickets"][0]["queue_id_display"] == "J1"

@patch('hospital_api.routers.registration.datetime')
def test_doctor_round_robin_logic(mock_dt, db_session):
    """Tes 5: Pendaftaran - Memastikan logika Round-Robin berjalan."""
    mock_dt.now.return_value.time.return_value = datetime.time(11, 0) # Anggap sekarang jam 11:00

    client.post("/admin/services/", json={"name": "Poli Mata", "prefix": "M"})
    client.post("/admin/doctors/", json={"name": "Dr. Kasino"}) # ID Dokter = 1
    client.post("/admin/doctors/", json={"name": "Dr. Nanu"})   # ID Dokter = 2

    # ▼▼▼ TAMBAHKAN DUA BARIS YANG HILANG INI ▼▼▼
    client.post("/admin/doctors/1/assign-service/?service_id=1") # Tugaskan Dr. Kasino ke Poli Mata
    client.post("/admin/doctors/2/assign-service/?service_id=1") # Tugaskan Dr. Nanu ke Poli Mata

    res1 = client.post("/register", json={"patient_name": "Pasien A", "service_ids": [1]})
    assert res1.status_code == 200, res1.text
    res2 = client.post("/register", json={"patient_name": "Pasien B", "service_ids": [1]})
    assert res2.status_code == 200, res2.text

    doctor1 = res1.json()["tickets"][0]["doctor"]["name"]
    doctor2 = res2.json()["tickets"][0]["doctor"]["name"]

    assert doctor1 != doctor2
    assert {doctor1, doctor2} == {"Dr. Kasino", "Dr. Nanu"}


@patch('hospital_api.routers.registration.datetime')
def test_queue_management_by_doctor(mock_dt, db_session):
    """Tes 6: Dokter - Memastikan bisa melihat antrean dan mengubah status."""
    mock_dt.now.return_value.time.return_value = datetime.time(10, 30)

    service_res = client.post("/admin/services/", json={"name": "Poli THT", "prefix": "T"})
    service_id = service_res.json()["id"]
    doc_res = client.post("/admin/doctors/", json={"name": "Dr. Eva"})
    doctor_id = doc_res.json()["id"]
    client.post(f"/admin/doctors/{doctor_id}/assign-service/?service_id={service_id}")
    reg_res = client.post("/register", json={"patient_name": "Pasien THT", "service_ids": [service_id]})
    
    # Ambil queue_id yang benar dari respons registrasi
    queue_id = reg_res.json()["tickets"][0]["id"]

    # 1. Dokter melihat antrean hari ini
    queue_list_res = client.get(f"/queues/today/{service_id}")
    assert queue_list_res.status_code == 200, queue_list_res.text
    assert len(queue_list_res.json()) == 1
    assert queue_list_res.json()[0]["patient"]["name"] == "Pasien THT"
    
    # 2. Dokter mengubah status dan menambah catatan
    update_res = client.patch(f"/queues/{queue_id}", json={
        "status": "Selesai",
        "visit_notes": "Telinga sudah dibersihkan."
    })
    assert update_res.status_code == 200, update_res.text
    data = update_res.json()
    assert data["status"] == "Selesai"
    assert data["visit_notes"] == "Telinga sudah dibersihkan."