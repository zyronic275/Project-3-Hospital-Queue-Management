import pytest
from fastapi.testclient import TestClient
from datetime import time, date, datetime
import copy
from freezegun import freeze_time

# Menggunakan path impor absolut untuk kompatibilitas dengan pytest
from hospital_api.main import app
from hospital_api import storage, schemas

# Klien untuk melakukan request ke API
client = TestClient(app)

# Menyimpan state awal dari database untuk di-reset
initial_db_data = copy.deepcopy(storage.db_data)
initial_id_counters = copy.deepcopy(storage.id_counters)

@pytest.fixture(autouse=True)
def reset_database():
    """Fixture yang berjalan sebelum setiap tes untuk memastikan state yang bersih."""
    global initial_db_data, initial_id_counters
    
    # Reset data mentah dan counter ID ke kondisi awal
    storage.db_data = copy.deepcopy(initial_db_data)
    storage.id_counters = copy.deepcopy(initial_id_counters)

    # Inisialisasi ulang objek Pydantic dari data mentah
    storage.db = {
        "services": [schemas.ServiceSchema(**s) for s in storage.db_data["services"]],
        "doctors": [schemas.DoctorSchema(**d) for d in storage.db_data["doctors"]],
        "patients": [schemas.PatientSchema(**p) for p in storage.db_data["patients"]],
        "queues": [], # Antrean selalu dimulai dari kosong
    }
    yield # Tes akan berjalan di sini


# --- Tes untuk Pendaftaran Pasien ---

@freeze_time("2025-10-09 10:00:00") # Mensimulasikan pendaftaran pada jam 10 pagi
def test_register_with_doctor_selection():
    """Tes berhasil mendaftar dengan memilih dokter spesifik dan format antrean baru."""
    response = client.post(
        "/register",
        json={"patient_name": "Budi", "service_ids": [1], "doctor_id": 1} # Pilih dr. Elan (kode 1)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["patient"]["name"] == "Budi"
    assert len(data["tickets"]) == 1
    # Format baru: A (Prefix) - 1 (Kode Dokter) - 001 (Nomor Urut)
    assert data["tickets"][0]["queue_number"] == "A-1-001"
    assert data["tickets"][0]["doctor"]["name"] == "dr. Elan"

@freeze_time("2025-10-09 09:00:00") # Jam 9 pagi, hanya dr. Candra (Poli Anak) yang praktik
def test_register_auto_doctor_assignment():
    """Tes berhasil mendaftar tanpa memilih dokter (penugasan otomatis) ketika hanya ada satu pilihan."""
    response = client.post(
        "/register",
        json={"patient_name": "Siti", "service_ids": [3]} # Poli Anak
    )
    assert response.status_code == 201
    data = response.json()
    # Seharusnya otomatis memilih dr. Candra karena hanya dia yang tersedia
    assert data["tickets"][0]["doctor"]["name"] == "dr. Candra"
    assert data["tickets"][0]["queue_number"] == "C-1-001"

@freeze_time("2025-10-09 11:00:00") # Jam 11 pagi
def test_auto_assigns_first_doctor_when_multiple_available():
    """
    Tes memverifikasi bahwa API menugaskan dokter pertama secara otomatis
    ketika ada beberapa yang tersedia dan tidak ada yang dipilih oleh pasien.
    """
    # MODIFIKASI: Ubah jam praktik drg. Aura agar tumpang tindih dengan drg. Tiffany
    # Ini untuk memastikan skenario "beberapa dokter tersedia" benar-benar terjadi.
    dr_aura = next((d for d in storage.db["doctors"] if d.id == 2), None)
    dr_aura.practice_start_time = time(10, 0) # Sekarang drg. Aura praktik dari jam 10:00 - 18:00

    response = client.post(
        "/register",
        json={"patient_name": "Rina", "service_ids": [2]} # Poli Gigi
    )
    # VERIFIKASI: Pastikan pendaftaran berhasil (bukan gagal)
    assert response.status_code == 201
    data = response.json()
    # VERIFIKASI: Pastikan dokter pertama yang tersedia (drg. Aura) yang ditugaskan
    assert data["tickets"][0]["doctor"]["name"] == "drg. Aura"

@freeze_time("2025-10-09 09:30:00") # Mensimulasikan pendaftaran pada jam 9:30 pagi
def test_fail_register_if_quota_full():
    """Tes gagal mendaftar jika kuota dokter yang dituju sudah penuh."""
    # Set kuota dr. Candra (id 3) menjadi 1 untuk tes ini
    dr_candra = next(d for d in storage.db["doctors"] if d.id == 3)
    dr_candra.max_patients = 1
    
    # Pasien pertama berhasil
    client.post("/register", json={"patient_name": "Pasien 1", "service_ids": [3], "doctor_id": 3})
    
    # Pasien kedua gagal
    response = client.post("/register", json={"patient_name": "Pasien 2", "service_ids": [3], "doctor_id": 3})
    assert response.status_code == 400
    assert "Kuota untuk dokter dr. Candra sudah penuh" in response.json()["detail"]

# --- Tes untuk Admin & Monitoring ---

def test_create_and_delete_service():
    """Tes siklus hidup: membuat layanan baru lalu menghapusnya."""
    # Membuat layanan baru
    create_response = client.post(
        "/admin/services/",
        json={"name": "Klinik Fisioterapi", "prefix": "F"}
    )
    assert create_response.status_code == 201
    new_service = create_response.json()
    assert new_service["name"] == "Klinik Fisioterapi"
    
    # Memastikan layanan ada di daftar
    get_response = client.get("/admin/services/")
    assert any(s["id"] == new_service["id"] for s in get_response.json())

    # Menghapus layanan
    delete_response = client.delete(f"/admin/services/{new_service['id']}")
    assert delete_response.status_code == 204
    
    # Memastikan layanan sudah terhapus
    get_response_after_delete = client.get("/admin/services/")
    assert not any(s["id"] == new_service["id"] for s in get_response_after_delete.json())

def test_update_doctor():
    """Tes berhasil memperbarui data dokter."""
    update_data = {
        "name": "dr. Elan Subekti",
        "max_patients": 25,
        "practice_start_time": "09:00:00"
    }
    response = client.put("/admin/doctors/1", json=update_data)
    assert response.status_code == 200
    updated_doctor = response.json()
    assert updated_doctor["name"] == "dr. Elan Subekti"
    assert updated_doctor["max_patients"] == 25
    assert updated_doctor["practice_start_time"] == "09:00:00"

@freeze_time("2025-10-09 13:00:00") # Mensimulasikan pendaftaran pada jam 1 siang
def test_dashboard_updates_correctly():
    """Tes dasbor memberikan data yang akurat setelah pendaftaran."""
    # Awalnya kosong
    response_empty = client.get("/admin/dashboard")
    poli_umum_status_empty = next(item for item in response_empty.json() if item["service_name"] == "Poli Umum")
    assert poli_umum_status_empty["total_patients_today"] == 0

    # Daftarkan 2 pasien ke Poli Umum
    client.post("/register", json={"patient_name": "Pasien A", "service_ids": [1], "doctor_id": 1})
    client.post("/register", json={"patient_name": "Pasien B", "service_ids": [1], "doctor_id": 5})

    # Cek dasbor setelah registrasi
    response_after = client.get("/admin/dashboard")
    poli_umum_status_after = next(item for item in response_after.json() if item["service_name"] == "Poli Umum")
    
    assert poli_umum_status_after["total_patients_today"] == 2
    assert poli_umum_status_after["patients_waiting"] == 2
    assert poli_umum_status_after["patients_serving"] == 0
    # Kuota total Poli Umum = kuota dr. Elan (20) + kuota dr. Budi (25) = 45
    assert poli_umum_status_after["max_patients_total"] == 45
    # Kepadatan = (2 / 45) * 100 = 4.44
    assert poli_umum_status_after["density_percentage"] == 4.44

# --- Tes untuk Layar Antrean Publik ---

@freeze_time("2025-10-09 14:00:00") # Mensimulasikan pendaftaran pada jam 2 siang
def test_public_queue_display():
    """Tes layar antrean publik menampilkan data dengan benar."""
    # Daftarkan pasien
    client.post("/register", json={"patient_name": "Dewi", "service_ids": [4]}) # Lab
    # Ambil ID antrean terakhir yang dibuat langsung dari storage
    queue_id = storage.db["queues"][-1].id
    
    # Cek antrean saat status "waiting"
    queue_response1 = client.get("/queues/4")
    assert queue_response1.status_code == 200
    data1 = queue_response1.json()
    assert len(data1) == 1
    assert data1[0]["queue_id_display"] == "D-1-001"
    assert data1[0]["status"] == "waiting"

    # Ubah status menjadi "serving"
    client.put(f"/queues/{queue_id}/status", json={"status": "serving"})

    # Cek lagi antrean "waiting" (seharusnya kosong)
    queue_response2 = client.get("/queues/4?status=waiting")
    assert len(queue_response2.json()) == 0

    # Cek antrean "serving" (seharusnya ada isinya)
    queue_response3 = client.get("/queues/4?status=serving")
    assert len(queue_response3.json()) == 1
    assert queue_response3.json()[0]["status"] == "serving"

