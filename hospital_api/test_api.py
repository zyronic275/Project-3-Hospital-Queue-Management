import pytest
from fastapi.testclient import TestClient
from datetime import time, date, datetime
import copy
from freezegun import freeze_time
import sys
import os

# Menambahkan path proyek ke sys.path agar impor modul bekerja
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hospital_api.main import app
from hospital_api import storage, schemas

# Klien untuk melakukan request ke API
client = TestClient(app)

# Menyimpan state awal dari database untuk di-reset
initial_db_data = copy.deepcopy(storage.db_data)
initial_id_counters = copy.deepcopy(storage.id_counters)

@pytest.fixture(autouse=True)
def reset_database():
    """
    Fixture yang berjalan sebelum setiap tes untuk memastikan state yang bersih.
    Ini me-reset data dan memuat ulang model Pydantic secara manual.
    """
    global initial_db_data, initial_id_counters
    
    # Reset data mentah dan counter ID ke kondisi awal
    storage.db_data = copy.deepcopy(initial_db_data)
    storage.id_counters = copy.deepcopy(initial_id_counters)

    # Inisialisasi ulang objek Pydantic dari data mentah secara manual
    storage.db["services"] = [schemas.ServiceSchema(**s) for s in storage.db_data["services"]]
    storage.db["doctors"] = [schemas.DoctorSchema(**d) for d in storage.db_data["doctors"]]
    storage.db["patients"] = [schemas.PatientSchema(**p) for p in storage.db_data["patients"]]
    storage.db["queues"] = []

    yield # Tes akan berjalan di sini


# --- Tes untuk Pendaftaran Pasien ---

@freeze_time("2025-10-09 10:00:00")
def test_register_with_doctor_selection():
    """Tes berhasil mendaftar dengan memilih dokter spesifik."""
    response = client.post(
        "/register",
        json={"patient_name": "Budi", "service_ids": [1], "doctor_id": 1}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tickets"][0]["queue_number"] == "UMUM-1-001"
    assert data["tickets"][0]["doctor"]["name"] == "dr. Elan"

@freeze_time("2025-10-09 09:00:00")
def test_register_auto_doctor_assignment_when_only_one_available():
    """Tes berhasil mendaftar dengan penugasan otomatis ketika hanya ada satu dokter."""
    response = client.post("/register", json={"patient_name": "Siti", "service_ids": [3]})
    assert response.status_code == 201
    data = response.json()
    assert data["tickets"][0]["doctor"]["name"] == "dr. Candra"

@freeze_time("2025-10-09 14:30:00")
def test_fail_register_when_multiple_doctors_available_without_choice():
    """Tes gagal mendaftar jika ada beberapa dokter tapi tidak ada yang dipilih."""
    response = client.post("/register", json={"patient_name": "Rina", "service_ids": [3]})
    assert response.status_code == 400
    assert "Terdapat lebih dari satu dokter yang tersedia" in response.json()["detail"]

@freeze_time("2025-10-09 09:30:00")
def test_fail_register_if_quota_full():
    """Tes gagal mendaftar jika kuota dokter yang dituju sudah penuh."""
    dr_candra = next(d for d in storage.db["doctors"] if d.id == 3)
    dr_candra.max_patients = 1
    
    client.post("/register", json={"patient_name": "Pasien 1", "service_ids": [3], "doctor_id": 3})
    
    response1 = client.post("/register", json={"patient_name": "Pasien 2", "service_ids": [3], "doctor_id": 3})
    
    assert response1.status_code == 400
    assert "Kuota untuk dokter dr. Candra sudah penuh" in response1.json()["detail"]

# --- Tes untuk Info Publik & Kuota ---

@freeze_time("2025-10-09 14:30:00")
def test_get_available_doctors_shows_remaining_quota():
    """Tes endpoint ketersediaan dokter menampilkan sisa kuota dengan benar."""
    client.post("/register", json={"patient_name": "Pasien Gigi 1", "service_ids": [2], "doctor_id": 2})
    
    response = client.get("/services/2/available-doctors") # Poli Gigi
    assert response.status_code == 200
    doctors = response.json()
    
    dr_aura = next(d for d in doctors if d["name"] == "drg. Aura")

    assert dr_aura["remaining_quota"] == dr_aura["max_patients"]-1

@freeze_time("2025-10-09 14:30:00")
def test_get_available_doctors_hides_full_doctor():
    """Tes dokter yang kuotanya habis tidak muncul di daftar tersedia."""
    dr_tiffany = next(d for d in storage.db["doctors"] if d.id == 6)
    dr_tiffany.max_patients = 1
    client.post("/register", json={"patient_name": "Pasien Gigi X", "service_ids": [2], "doctor_id": 6})

    response = client.get("/services/2/available-doctors")
    assert response.status_code == 200
    doctors = response.json()
    
    assert len(doctors) == 1
    assert doctors[0]["name"] == "drg. Aura"

# --- Tes untuk Admin (CRUD & Logika Terkait) ---

def test_fail_create_service_with_duplicate_prefix():
    """Tes untuk memastikan API menolak pembuatan layanan dengan prefix yang sudah ada."""
    response = client.post("/admin/services/", json={"name": "Poli Umum Darurat", "prefix": "UMUM"})
    assert response.status_code == 400
    assert "Prefix 'UMUM' sudah digunakan" in response.json()["detail"]

def test_fail_create_doctor_with_duplicate_code_in_same_service():
    """Tes gagal membuat dokter jika 'doctor_code' sudah ada di poli yang sama."""
    # dr. Elan (ID 1) sudah ada di Poli Umum (ID 1) dengan kode "1"
    response = client.post("/admin/doctors/", json={
        "name": "dr. Fajar",
        "doctor_code": "1", # Kode duplikat
        "services": [1], # Poli yang sama
        "practice_start_time": "09:00:00",
        "practice_end_time": "17:00:00",
        "max_patients": 10
    })
    assert response.status_code == 400
    assert "Kode dokter '1' sudah digunakan di Poli Umum oleh dr. Elan." in response.json()["detail"]

def test_delete_service_also_deletes_doctor():
    """Tes menghapus layanan juga menghapus dokter yang hanya bertugas di sana."""
    service_resp = client.post("/admin/services/", json={"name": "Urologi", "prefix": "URO"})
    new_service_id = service_resp.json()["id"]

    doctor_resp = client.post("/admin/doctors/", json={
        "name": "dr. Ujang", "doctor_code": "9", "services": [new_service_id],
        "practice_start_time": "08:00:00", "practice_end_time": "12:00:00", "max_patients": 5
    })
    new_doctor_id = doctor_resp.json()["id"]

    doctors_before = client.get("/admin/doctors/").json()
    assert any(d["id"] == new_doctor_id for d in doctors_before)
    
    client.delete(f"/admin/services/{new_service_id}")

    doctors_after = client.get("/admin/doctors/").json()
    assert not any(d["id"] == new_doctor_id for d in doctors_after)

def test_delete_service_updates_doctor_services():
    """Tes menghapus layanan akan memperbarui daftar layanan dokter, bukan menghapusnya."""
    dr_elan = next(d for d in storage.db["doctors"] if d.id == 1)
    dr_elan.services = [1, 4]

    client.delete("/admin/services/4")

    response = client.get("/admin/doctors/")
    updated_dr_elan = next(d for d in response.json() if d["id"] == 1)
    
    assert updated_dr_elan is not None
    assert updated_dr_elan["services"] == [1]

@freeze_time("2025-10-09 13:00:00")
def test_dashboard_updates_correctly():
    """Tes dasbor memberikan data yang akurat setelah pendaftaran."""
    client.post("/register", json={"patient_name": "Pasien A", "service_ids": [1], "doctor_id": 1})
    client.post("/register", json={"patient_name": "Pasien B", "service_ids": [1], "doctor_id": 5})

    response_after = client.get("/admin/dashboard")
    poli_umum_status_after = next(item for item in response_after.json() if item["service_name"] == "Poli Umum")
    
    assert poli_umum_status_after["total_patients_today"] == 2
    assert poli_umum_status_after["patients_waiting"] == 2
    assert poli_umum_status_after["max_patients_total"] == 45
    assert poli_umum_status_after["density_percentage"] == 4.44

@freeze_time("2025-10-09 14:00:00")
def test_public_queue_display():
    """Tes layar antrean publik menampilkan data dengan benar."""
    client.post("/register", json={"patient_name": "Dewi", "service_ids": [4]}) # Lab
    queue_id = storage.db["queues"][-1].id
    
    queue_response1 = client.get("/queues/4")
    assert len(queue_response1.json()) == 1
    assert queue_response1.json()[0]["status"] == "waiting"

    client.put(f"/queues/{queue_id}/status", json={"status": "serving"})

    assert len(client.get("/queues/4?status=waiting").json()) == 0
    assert len(client.get("/queues/4?status=serving").json()) == 1

