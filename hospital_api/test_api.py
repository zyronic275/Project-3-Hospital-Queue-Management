import pytest
from fastapi.testclient import TestClient
import copy

# Impor app dan objek dari file lokal Anda
from hospital_api.main import app
from hospital_api import storage, schemas

# Buat client untuk melakukan request ke API
client = TestClient(app)

# Simpan state awal dari database untuk di-reset
initial_db_state = copy.deepcopy(storage.db)
initial_id_counters_state = copy.deepcopy(storage.id_counters)

@pytest.fixture(autouse=True)
def reset_database():
    """
    Fixture ini berjalan sebelum setiap fungsi tes untuk memastikan state yang bersih,
    mengembalikan database ke kondisi awal seperti saat aplikasi pertama kali dimuat.
    """
    storage.db = copy.deepcopy(initial_db_state)
    storage.id_counters = copy.deepcopy(initial_id_counters_state)
    # Pastikan data dinamis (pasien & antrean) benar-benar kosong
    storage.db["patients"].clear()
    storage.db["queues"].clear()
    storage.id_counters["patients"] = 0
    storage.id_counters["queues"] = 0
    yield # Tes akan berjalan di sini

# --- Tes untuk Admin: Services ---

def test_get_initial_services():
    """Tes untuk mendapatkan daftar layanan awal."""
    response = client.get("/admin/services/")
    assert response.status_code == 200
    assert len(response.json()) == 4 # Sesuai data awal di storage.py

def test_create_service():
    """Tes berhasil membuat layanan baru."""
    response = client.post("/admin/services/", json={"name": "Klinik Fisioterapi", "prefix": "E"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Klinik Fisioterapi"
    assert data["prefix"] == "E"

# --- Tes untuk Admin: Doctors ---

def test_create_doctor_success():
    """Tes membuat dokter baru dengan menyertakan jam layanan dan kuota maksimal."""
    new_doctor_data = {
        "doctor_code": "3",
        "name": "dr. Zaky",
        "services": [1],
        "service_hours": "13:00-16:00",
        "max_patients": 15
    }
    response = client.post("/admin/doctors/", json=new_doctor_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "dr. Zaky"
    assert data["max_patients"] == 15
    assert data["service_hours"] == "13:00-16:00"

# --- Tes untuk Logika Registrasi dan Kuota Pasien ---

def test_register_patient_success():
    """Tes registrasi pasien berhasil ketika kuota masih tersedia."""
    response = client.post("/register", json={"patient_name": "Rina", "service_ids": [1]})
    assert response.status_code == 201
    data = response.json()
    assert data["patient"]["name"] == "Rina"
    assert len(data["tickets"]) == 1
    assert data["tickets"][0]["service"]["name"] == "Poli Umum"

def test_registration_fails_when_quota_is_full():
    """
    Tes paling penting: memastikan pendaftaran GAGAL jika kuota dokter sudah penuh.
    """
    # Langkah 1: Ubah kuota dokter menjadi sangat kecil (1) untuk kemudahan tes.
    # Kita akan update data dr. Elan (id: 1) yang kuotanya 20 menjadi 1.
    client.put("/admin/doctors/1", json={"max_patients": 1})

    # Langkah 2: Daftarkan pasien pertama, ini seharusnya berhasil.
    response1 = client.post("/register", json={"patient_name": "Pasien Pertama", "service_ids": [1], "doctor_id": 1})
    assert response1.status_code == 201, "Pendaftaran pasien pertama seharusnya berhasil"

    # Langkah 3: Coba daftarkan pasien kedua ke dokter yang sama. Ini harus GAGAL.
    response2 = client.post("/register", json={"patient_name": "Pasien Kedua", "service_ids": [1], "doctor_id": 1})
    
    # Langkah 4: Verifikasi hasilnya.
    assert response2.status_code == 400, "Pendaftaran kedua seharusnya gagal dengan status 400"
    error_data = response2.json()
    assert "kuota" in error_data["detail"].lower()
    assert "penuh" in error_data["detail"].lower()
    assert "dr. Elan" in error_data["detail"]

# --- Tes untuk Dasbor Monitoring ---

def test_dashboard_returns_correct_initial_data():
    """Tes dasbor saat tidak ada antrean. Semua statistik harus nol."""
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    # Cek data untuk Poli Umum
    poli_umum_status = next(item for item in data if item["service_name"] == "Poli Umum")
    assert poli_umum_status["patients_waiting"] == 0
    assert poli_umum_status["patients_serving"] == 0
    assert poli_umum_status["total_patients_today"] == 0
    assert poli_umum_status["density_percentage"] == 0.0

def test_dashboard_updates_after_registration_and_status_change():
    """Tes dasbor memberikan data yang akurat setelah ada pendaftaran dan perubahan status."""
    # Langkah 1: Daftarkan 2 pasien ke Poli Umum (dilayani oleh dr. Elan dan dr. Budi)
    client.post("/register", json={"patient_name": "Pasien A", "service_ids": [1], "doctor_id": 1})
    client.post("/register", json={"patient_name": "Pasien B", "service_ids": [1], "doctor_id": 5})

    # Cek dasbor setelah registrasi
    response1 = client.get("/admin/dashboard")
    assert response1.status_code == 200
    poli_umum_status1 = next(item for item in response1.json() if item["service_name"] == "Poli Umum")
    
    assert poli_umum_status1["total_patients_today"] == 2
    assert poli_umum_status1["patients_waiting"] == 2
    assert poli_umum_status1["patients_serving"] == 0
    # Kuota total Poli Umum = kuota dr. Elan (20) + kuota dr. Budi (25) = 45
    # Kepadatan = (2 / 45) * 100 = 4.44
    assert poli_umum_status1["max_patients_total"] == 45
    assert poli_umum_status1["density_percentage"] == 4.44

    # Langkah 2: Ubah status antrean pertama (ID 1) menjadi 'serving'
    client.put("/queues/1/status", params={"new_status": "serving"})

    # Cek dasbor lagi setelah status diubah
    response2 = client.get("/admin/dashboard")
    assert response2.status_code == 200
    poli_umum_status2 = next(item for item in response2.json() if item["service_name"] == "Poli Umum")

    assert poli_umum_status2["total_patients_today"] == 2
    assert poli_umum_status2["patients_waiting"] == 1  # Berkurang satu
    assert poli_umum_status2["patients_serving"] == 1  # Bertambah satu
    assert poli_umum_status2["density_percentage"] == 4.44 # Persentase tetap sama

