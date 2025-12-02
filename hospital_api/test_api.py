import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from datetime import date

# Import aplikasi
from main import app, get_db
import storage

# --- SETUP DATABASE TEST (SQLite Memory) ---
TEST_DATABASE_URL = "sqlite:///./test_hardcore_fixed.db"

engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    storage.Base.metadata.create_all(bind=engine)
    yield
    storage.Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_hardcore_fixed.db"):
        try: os.remove("./test_hardcore_fixed.db")
        except: pass

# =================================================================
# 1. TEST VALIDASI DATA (ADMIN)
# =================================================================

def test_create_poli_invalid_prefix():
    """Menguji sistem menolak Prefix yang mengandung angka/simbol"""
    res = client.post("/admin/polis", json={"poli": "Poli Angka", "prefix": "123"})
    assert res.status_code == 422 
    
    res = client.post("/admin/polis", json={"poli": "Poli Simbol", "prefix": "A$AP"})
    assert res.status_code == 422

def test_create_poli_duplicate():
    """Menguji sistem menolak Nama atau Prefix yang kembar"""
    # Buat Poli Valid dulu
    client.post("/admin/polis", json={"poli": "Poli Umum", "prefix": "UMUM"})
    
    # Coba buat lagi (Nama Sama)
    res1 = client.post("/admin/polis", json={"poli": "Poli Umum", "prefix": "XXX"})
    assert res1.status_code == 400
    
    # Coba buat lagi (Prefix Sama)
    res2 = client.post("/admin/polis", json={"poli": "Poli Lain", "prefix": "UMUM"})
    assert res2.status_code == 400

def test_create_doctor_invalid_time():
    """Menguji validasi format jam"""
    payload = {
        "dokter": "Dr. Salah Jam",
        "poli": "Poli Umum",
        "practice_start_time": "Jam 8 Pagi", 
        "practice_end_time": "16:00",
        "max_patients": 10
    }
    res = client.post("/admin/doctors", json=payload)
    assert res.status_code == 422

# =================================================================
# 2. TEST LOGIKA BISNIS (CORE)
# =================================================================

def test_auto_code_generation():
    """Menguji apakah kode dokter bertambah otomatis"""
    # Buat Dokter 1
    d1 = client.post("/admin/doctors", json={
        "dokter": "Dr. Satu", "poli": "Poli Umum", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 10
    })
    assert d1.status_code == 200
    assert d1.json()["doctor_code"] == "UMUM-001"
    
    # Buat Dokter 2
    d2 = client.post("/admin/doctors", json={
        "dokter": "Dr. Dua", "poli": "Poli Umum", 
        "practice_start_time": "13:00", "practice_end_time": "17:00", "max_patients": 10
    })
    assert d2.status_code == 200
    assert d2.json()["doctor_code"] == "UMUM-002"

def test_cross_poli_validation():
    """MENCEGAH pasien daftar ke Poli A tapi pilih Dokter dari Poli B"""
    # Setup: Buat Poli Gigi dan Dokter Gigi
    client.post("/admin/polis", json={"poli": "Poli Gigi", "prefix": "GIGI"})
    doc_gigi = client.post("/admin/doctors", json={
        "dokter": "Drg. Budi", "poli": "Poli Gigi",
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 10
    }).json()
    
    # TEST: Daftar ke "Poli Umum" tapi pilih "Drg. Budi" (Poli Gigi)
    payload = {
        "nama_pasien": "Pasien Bingung",
        "poli": "Poli Umum", # Salah Poli
        "doctor_id": doc_gigi["doctor_id"],
        "visit_date": str(date.today())
    }
    res = client.post("/public/submit", json=payload)
    assert res.status_code == 400

def test_queue_sequence_increment():
    """Menguji nomor antrean bertambah (1, 2, 3)"""
    # Ambil ID Dr. Satu (UMUM-001)
    res_docs = client.get("/public/available-doctors", params={"poli_name": "Poli Umum", "visit_date": str(date.today())})
    doc_id = res_docs.json()[0]["doctor_id"]
    
    # --- PERBAIKAN: GANTI NAMA "P1" MENJADI "Pasien Satu" (Min 3 Huruf) ---
    p1 = client.post("/public/submit", json={"nama_pasien": "Pasien Satu", "poli": "Poli Umum", "doctor_id": doc_id, "visit_date": str(date.today())})
    assert p1.status_code == 200
    assert p1.json()["queue_sequence"] == 1
    assert "001" in p1.json()["queue_number"]
    
    # Pasien 2
    p2 = client.post("/public/submit", json={"nama_pasien": "Pasien Dua", "poli": "Poli Umum", "doctor_id": doc_id, "visit_date": str(date.today())})
    assert p2.status_code == 200
    assert p2.json()["queue_sequence"] == 2
    assert "002" in p2.json()["queue_number"]

# =================================================================
# 3. TEST UPDATE & DELETE (INTEGRITAS DATA)
# =================================================================

def test_update_doctor():
    """Menguji fitur edit dokter"""
    docs = client.get("/public/available-doctors", params={"poli_name": "Poli Umum", "visit_date": str(date.today())}).json()
    d_id = docs[0]['doctor_id']
    
    update_payload = {
        "dokter": "Dr. Satu Edited",
        "practice_end_time": "20:00"
    }
    res = client.put(f"/admin/doctors/{d_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json()["dokter"] == "Dr. Satu Edited"

def test_cascading_delete():
    """HARDCORE: Jika Dokter dihapus, apakah data antrean Pasien ikut terhapus?"""
    # 1. Setup: Pastikan ada pasien terdaftar ("Pasien Satu" dari tes sebelumnya)
    docs = client.get("/public/available-doctors", params={"poli_name": "Poli Umum", "visit_date": str(date.today())}).json()
    target_doc = docs[0]
    doc_id = target_doc['doctor_id']
    
    # Cek tiket masih ada (Gunakan nama baru "Pasien Satu")
    check = client.get("/public/find-ticket", params={"nama": "Pasien Satu"})
    assert check.status_code == 200
    
    # 2. DELETE DOKTER
    del_res = client.delete(f"/admin/doctors/{doc_id}")
    assert del_res.status_code == 200
    
    # 3. VERIFIKASI (Tiket Pasien harusnya HILANG)
    check_again = client.get("/public/find-ticket", params={"nama": "Pasien Satu"})
    assert check_again.status_code == 404 

# =================================================================
# 4. TEST ALUR OPERASIONAL (SCANNER)
# =================================================================

def test_scan_flow_strict():
    """Menguji alur scan harus berurutan"""
    # Setup data baru
    res_docs = client.get("/public/available-doctors", params={"poli_name": "Poli Gigi", "visit_date": str(date.today())})
    doc_gigi_id = res_docs.json()[0]['doctor_id']
    
    reg = client.post("/public/submit", json={"nama_pasien": "Ani Scan", "poli": "Poli Gigi", "doctor_id": doc_gigi_id, "visit_date": str(date.today())})
    ticket_id = str(reg.json()["id"])
    
    # 1. Coba Scan 'Finish' duluan (HARUS GAGAL)
    fail_res = client.post("/ops/scan-barcode", json={"barcode_data": ticket_id, "location": "finish"})
    assert fail_res.status_code == 400
    
    # 2. Scan Arrival (SUKSES)
    ok_res = client.post("/ops/scan-barcode", json={"barcode_data": ticket_id, "location": "arrival"})
    assert ok_res.status_code == 200
    assert ok_res.json()["current_status"] == "Menunggu"