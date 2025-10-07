# unit_test.py (Final In-Memory Version)

import pytest
from fastapi.testclient import TestClient
import datetime
from unittest.mock import patch

# Import dari aplikasi utama dan database memori Anda
from hospital_api.main import app
from hospital_api.in_memory_db import reset_database

client = TestClient(app)

# Fixture ini akan dijalankan secara otomatis sebelum SETIAP fungsi tes
@pytest.fixture(autouse=True)
def setup_and_teardown_database():
    """Mereset database memori sebelum setiap tes dijalankan."""
    reset_database()
    yield # Ini adalah titik di mana tes dijalankan

# =========================================================
# === KELAS TES UNTUK FITUR-FITUR ADMIN ===
# =========================================================
class TestAdminFeatures:
    def test_create_essentials(self):
        """Tes: Admin bisa membuat Service dan Doctor."""
        service_res = client.post("/admin/services/", json={"name": "Poli Gigi", "prefix": "G"})
        assert service_res.status_code == 200
        assert service_res.json()["name"] == "Poli Gigi"

        doctor_res = client.post("/admin/doctors/", json={"name": "Dr. Gigi"})
        assert doctor_res.status_code == 200
        assert doctor_res.json()["name"] == "Dr. Gigi"

    def test_assign_doctor_to_service(self):
        """Tes: Admin bisa menghubungkan Dokter ke Layanan."""
        client.post("/admin/services/", json={"name": "Poli Gigi", "prefix": "G"})
        client.post("/admin/doctors/", json={"name": "Dr. Gigi"})
        
        assign_res = client.post(f"/admin/doctors/1/assign-service/?service_id=1")
        assert assign_res.status_code == 200
        data = assign_res.json()
        assert len(data["services"]) == 1
        assert data["services"][0]["name"] == "Poli Gigi"
        
        service_data = client.get(f"/admin/services/").json()
        assert len(service_data[0]["doctors"]) == 1

# =========================================================
# === KELAS TES UNTUK ALUR KERJA APLIKASI ===
# =========================================================
class TestAppWorkflow:
    @pytest.fixture(autouse=True)
    def setup_workflow_data(self):
        """Menyiapkan data dasar untuk setiap tes di kelas ini."""
        client.post("/admin/services/", json={"name": "Poli Jantung", "prefix": "A"})
        client.post("/admin/doctors/", json={"name": "Dr. Pagi", "start_time": "08:00:00", "end_time": "12:00:00", "max_patients": 1})
        client.post("/admin/doctors/", json={"name": "Dr. Siang", "start_time": "13:00:00", "end_time": "17:00:00"})
        client.post("/admin/doctors/1/assign-service/?service_id=1")
        client.post("/admin/doctors/2/assign-service/?service_id=1")

    @patch('hospital_api.routers.registration.datetime')
    def test_registration_success(self, mock_datetime):
        """Tes: Pasien berhasil mendaftar di jam kerja."""
        mock_datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1, 10, 0, 0)
        
        response = client.post("/register", json={"patient_name": "Pasien Pagi", "service_ids": [1]})
        assert response.status_code == 200
        data = response.json()
        assert data["tickets"][0]["doctor"]["name"] == "Dr. Pagi"
        assert data["tickets"][0]["queue_id_display"] == "A1"

    @patch('hospital_api.routers.registration.datetime')
    def test_registration_fail_out_of_hours(self, mock_datetime):
        """Tes: Pasien ditolak jika mendaftar di luar jam kerja."""
        mock_datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1, 12, 30, 0)

        response = client.post("/register", json={"patient_name": "Pasien Istirahat", "service_ids": [1]})
        assert response.status_code == 400
        assert "Tidak ada dokter yang praktek" in response.json()["detail"]

    @patch('hospital_api.routers.registration.datetime')
    def test_registration_fail_when_full(self, mock_datetime):
        """Tes: Pendaftaran gagal jika dokter yang praktek sudah penuh."""
        mock_datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1, 10, 0, 0)
        
        # Penuhi kuota Dr. Pagi (kuota 1)
        res1 = client.post("/register", json={"patient_name": "Pasien 1", "service_ids": [1]})
        assert res1.status_code == 200

        # Coba daftarkan pasien kedua di jam yang sama
        response = client.post("/register", json={"patient_name": "Pasien 2", "service_ids": [1]})
        
        # Seharusnya gagal karena satu-satunya dokter yang praktek (Dr. Pagi) sudah penuh
        assert response.status_code == 400
        assert "sudah penuh" in response.json()["detail"]