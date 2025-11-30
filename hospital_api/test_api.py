import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

# Import aplikasi dan database dari main.py
from main import app, get_db
import storage

# --- KONFIGURASI TEST DATABASE (SQLite) ---
TEST_DATABASE_URL = "sqlite:///./test.db"

# connect_args check_same_thread=False diperlukan untuk SQLite di FastAPI
engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override Dependency Database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# --- FIXTURE: Setup & Teardown ---
@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # 1. Buat Tabel Baru
    storage.Base.metadata.create_all(bind=engine)
    yield
    # 2. CLEANUP (Perbaikan WinError 32)
    storage.Base.metadata.drop_all(bind=engine)
    
    # PENTING: Tutup koneksi engine sebelum hapus file
    engine.dispose() 
    
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except PermissionError:
            pass # Abaikan jika Windows masih menahan file sebentar

# =================================================================
# 1. TEST ADMIN: MANAJEMEN POLI
# =================================================================
def test_create_poli():
    """Menguji pembuatan Poli baru dan validasi prefix unik"""
    # Case 1: Sukses
    payload = {"poli": "Poli Gigi Test", "prefix": "GIGI"}
    response = client.post("/admin/polis", json=payload)
    assert response.status_code == 200
    assert response.json()["poli"] == "Poli Gigi Test"
    assert response.json()["prefix"] == "GIGI"

    # Case 2: Gagal (Nama Sama)
    response = client.post("/admin/polis", json=payload)
    assert response.status_code == 400
    
    # Case 3: Gagal (Prefix Sama, Nama Beda)
    payload_fail = {"poli": "Poli Lain", "prefix": "GIGI"}
    response = client.post("/admin/polis", json=payload_fail)
    assert response.status_code == 400

# =================================================================
# 2. TEST ADMIN: MANAJEMEN DOKTER
# =================================================================
def test_create_doctor():
    """Menguji pembuatan Dokter dan Auto-Code Generation"""
    # Case 1: Sukses
    payload = {
        "dokter": "Dr. Strange",
        "poli": "Poli Gigi Test", 
        "practice_start_time": "08:00",
        "practice_end_time": "16:00",
        "max_patients": 10
    }
    response = client.post("/admin/doctors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["dokter"] == "Dr. Strange"
    # Cek Auto Code: Prefix (GIGI) + 001
    assert data["doctor_code"] == "GIGI-001"

    # Case 2: Tambah dokter kedua di poli sama (Code harus increment)
    payload["dokter"] = "Dr. Fate"
    response = client.post("/admin/doctors", json=payload)
    assert response.status_code == 200
    assert response.json()["doctor_code"] == "GIGI-002"

    # Case 3: Gagal (Format Waktu Salah)
    # PERBAIKAN: Expect 422 (Validation Error Pydantic), bukan 400
    payload["practice_start_time"] = "Jam 8"
    response = client.post("/admin/doctors", json=payload)
    assert response.status_code == 422 

# =================================================================
# 3. TEST PUBLIC: PENDAFTARAN PASIEN
# =================================================================
def test_registration_flow():
    """Menguji pendaftaran pasien dan format nomor antrean"""
    # 1. Cari Dokter dulu
    res_doc = client.get("/public/available-doctors", params={"poli_name": "Poli Gigi Test", "visit_date": "2025-12-01"})
    doctor_id = res_doc.json()[0]['doctor_id']

    # 2. Daftar Pasien
    payload = {
        "nama_pasien": "Budi Test",
        "poli": "Poli Gigi Test",
        "doctor_id": doctor_id,
        "visit_date": "2025-12-01"
    }
    response = client.post("/public/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Assertions
    assert data["nama_pasien"] == "Budi Test"
    assert data["status_pelayanan"] == "Terdaftar" 
    assert data["checkin_time"] is None 
    # Cek Format Antrean: GIGI-001-001 (Prefix-DocCode-Seq)
    assert data["queue_number"].startswith("GIGI-001")
    assert data["queue_sequence"] == 1

# =================================================================
# 4. TEST OPERASIONAL: ALUR SCAN BARCODE (LENGKAP)
# =================================================================
def test_full_scan_lifecycle():
    """Menguji siklus hidup pasien dari Datang -> Masuk -> Selesai"""
    # 1. Setup: Daftar Pasien Baru
    doc_id = 1 
    reg_payload = {"nama_pasien": "Ani Scan", "poli": "Poli Gigi Test", "doctor_id": doc_id, "visit_date": "2025-12-01"}
    reg_res = client.post("/public/submit", json=reg_payload)
    ticket_id = reg_res.json()["id"]
    
    # 2. SCAN 1: KEDATANGAN (Arrival) -> Status: Menunggu
    scan_payload = {"barcode_data": str(ticket_id), "location": "arrival"}
    res = client.post("/ops/scan-barcode", json=scan_payload)
    assert res.status_code == 200
    assert res.json()["current_status"] == "Menunggu"

    # 3. SCAN 2: MASUK POLI (Clinic) -> Status: Melayani
    scan_payload["location"] = "clinic"
    res = client.post("/ops/scan-barcode", json=scan_payload)
    assert res.status_code == 200
    assert res.json()["current_status"] == "Melayani"

    # 4. SCAN 3: SELESAI (Finish) -> Status: Selesai
    scan_payload["location"] = "finish"
    res = client.post("/ops/scan-barcode", json=scan_payload)
    assert res.status_code == 200
    assert res.json()["current_status"] == "Selesai"

    # 5. TEST SCAN ERROR (Loncati Langkah)
    reg_res_2 = client.post("/public/submit", json={"nama_pasien": "Skip", "poli": "Poli Gigi Test", "doctor_id": doc_id, "visit_date": "2025-12-01"})
    ticket_id_2 = reg_res_2.json()["id"]
    
    # Langsung scan finish (padahal belum checkin)
    res_fail = client.post("/ops/scan-barcode", json={"barcode_data": str(ticket_id_2), "location": "finish"})
    assert res_fail.status_code == 400 

# =================================================================
# 5. TEST PUBLIC: CARI TIKET
# =================================================================
def test_find_ticket():
    """Menguji pencarian tiket berdasarkan nama dan tanggal"""
    # Cari nama 'Ani' yang sudah didaftarkan di step sebelumnya
    response = client.get("/public/find-ticket", params={"nama": "Ani", "target_date": "2025-12-01"})
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["nama_pasien"] == "Ani Scan"

    # Cari nama ngawur
    response = client.get("/public/find-ticket", params={"nama": "Hantu", "target_date": "2025-12-01"})
    assert response.status_code == 404

# =================================================================
# 6. TEST MONITORING
# =================================================================
def test_dashboard():
    """Menguji apakah dashboard mengembalikan data statistik"""
    response = client.get("/monitor/dashboard", params={"target_date": "2025-12-01"})
    assert response.status_code == 200
    stats = response.json()
    assert isinstance(stats, list)
    # Harus ada Poli Gigi Test
    found = False
    for s in stats:
        if s["poli_name"] == "Poli Gigi Test":
            found = True
            break
    assert found