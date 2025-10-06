# unit_test.py (Versi Final dengan Pendekatan Fixture yang Benar)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import datetime
from unittest.mock import patch

from hospital_api.main import app
from hospital_api.models import Base
from hospital_api.database import get_db

# --- Konfigurasi Database (Tidak Berubah) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# --- Fixtures ---

@pytest.fixture(scope="function")
def db_session():
    """Fixture dasar: membuat tabel sebelum tes, menghapusnya setelah tes."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def populated_db(db_session):
    """Fixture baru: bergantung pada db_session, lalu mengisi data awal."""
    client.post("/admin/services/", json={"name": "Poli Jantung", "prefix": "A"})
    client.post("/admin/doctors/", json={"name": "Dr. Jantung Pagi", "start_time": "08:00:00", "end_time": "12:00:00", "max_patients": 1})
    client.post("/admin/doctors/", json={"name": "Dr. Jantung Siang", "start_time": "13:00:00", "end_time": "17:00:00","max_patients":0})
    client.post("/admin/doctors/1/assign-service/?service_id=1")
    client.post("/admin/doctors/2/assign-service/?service_id=1")
    yield

# =========================================================
# === KELAS TES UNTUK FITUR-FITUR ADMIN ===
# =========================================================
@pytest.mark.usefixtures("db_session")
class TestAdminFeatures:
    # ... (Isi kelas ini tidak perlu diubah, sudah benar)
    def test_create_service(self):
        response = client.post("/admin/services/", json={"name": "Poli Gigi", "prefix": "G"})
        assert response.status_code == 200
        assert response.json()["name"] == "Poli Gigi"

    def test_create_doctor(self):
        response = client.post("/admin/doctors/", json={"name": "Dr. Gigi"})
        assert response.status_code == 200
        assert response.json()["name"] == "Dr. Gigi"

# =========================================================
# === KELAS TES UNTUK ALUR KERJA APLIKASI ===
# =========================================================
# Tidak perlu lagi @pytest.mark.usefixtures karena setiap tes akan memanggil populated_db
class TestAppWorkflow:

    @patch('hospital_api.routers.registration.datetime')
    def test_registration_success_in_working_hours(self, mock_dt, populated_db):
        """Memastikan pasien bisa mendaftar di jam kerja dokter."""
        mock_dt.datetime.now.return_value = datetime.datetime(2025, 1, 1, 10, 0, 0)
        mock_dt.date.today.return_value = datetime.date(2025, 1, 1)

        response = client.post("/register", json={"patient_name": "Pasien Pagi", "service_ids": [1]})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["tickets"][0]["doctor"]["name"] == "Dr. Jantung Pagi"
        assert data["tickets"][0]["queue_id_display"] == "A1"

    @patch('hospital_api.routers.registration.datetime')
    def test_registration_fail_out_of_hours(self, mock_dt, populated_db):
        """Memastikan pasien ditolak jika mendaftar di luar jam kerja."""
        mock_dt.datetime.now.return_value = datetime.datetime(2025, 1, 1, 12, 30, 0)
        mock_dt.date.today.return_value = datetime.date(2025, 1, 1)

        response = client.post("/register", json={"patient_name": "Pasien Istirahat", "service_ids": [1]})
        assert response.status_code == 400
        assert "Tidak ada dokter yang praktek" in response.json()["detail"]

    @patch('hospital_api.routers.registration.datetime')
    def test_registration_fail_when_full(self, mock_dt, populated_db):
        """Tes: Pendaftaran gagal jika semua dokter di satu poli sudah penuh."""
        mock_dt.datetime.now.return_value = datetime.datetime(2025, 1, 1, 10, 0, 0)
        mock_dt.date.today.return_value = datetime.date(2025, 1, 1)

        # Kuota Dr. Jantung Pagi adalah 1. Kita daftarkan 1 pasien.
        client.post("/register", json={"patient_name": "Pasien 1", "service_ids": [1]})
        
        # Aksi: Coba daftarkan pasien ke-2 di jam yang sama
        response = client.post("/register", json={"patient_name": "Pasien 2", "service_ids": [1]})

        # Verifikasi: Seharusnya gagal karena Dr. Jantung Pagi sudah penuh
        assert response.status_code == 400
        assert "sudah penuh" in response.json()["detail"]