import requests
import pytest
import time  # [BARU] Import time untuk jeda
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000"

# ==========================================
# 🧹 FIXTURE: SETUP & TEARDOWN
# ==========================================
@pytest.fixture
def clean_setup():
    """
    Membersihkan data Poli Realistis sebelum dan sesudah tes.
    """
    polies_to_clean = [
        "Poli Umum", "Poli Gigi", "Poli Anak", "Poli THT", 
        "Poli Mata", "Poli Jantung", "Poli Kulit", 
        "Poli Syaraf", "Poli Kandungan", "Poli Diagnosa" # Tambahan Diagnosa
    ]
    
    def run_cleanup():
        print("\n[CLEANUP] Membersihkan data RS...")
        for p in polies_to_clean:
            try:
                requests.delete(f"{BASE_URL}/admin/polis/{p}")
            except: pass
        # [PENTING] Beri napas database 0.5 detik
        time.sleep(0.5)

    run_cleanup()
    yield 
    run_cleanup()

# ==========================================
# 1. HAPPY PATH (Skenario Pasien Umum)
# ==========================================

def test_full_flow_success(clean_setup):
    """Skenario: Pasien datang ke Poli Umum (Input Singkat)."""
    # 1. Buat Poli
    r_poli = requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Umum", "prefix": "UMU"})
    assert r_poli.status_code == 200, f"Gagal buat poli: {r_poli.text}"
    assert r_poli.json()['poli'] == "Poli Umum"

    # 2. Buat Dokter
    doc_data = {
        "dokter": "Andi Santoso", "poli": "Umum",
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 20
    }
    r = requests.post(f"{BASE_URL}/admin/doctors", json=doc_data)
    assert r.status_code == 200, f"Gagal buat dokter: {r.text}"
    doc_id = r.json()['doctor_id']

    # 3. Daftar Pasien
    besok = str(date.today() + timedelta(days=1))
    pasien_data = {
        "nama_pasien": "Bapak Budi", "poli": "Poli Umum",
        "doctor_id": doc_id, "visit_date": besok
    }
    r = requests.post(f"{BASE_URL}/public/submit", json=pasien_data)
    assert r.status_code == 200
    ticket_code = r.json()['queue_number']

    # 4. Operasional: Scan Barcode (Arrival)
    scan_data = {"barcode_data": ticket_code, "location": "arrival"}
    r = requests.post(f"{BASE_URL}/ops/scan-barcode", json=scan_data)
    assert r.status_code == 200
    assert r.json()['current_status'] == "Menunggu"

# ==========================================
# 2. NEGATIVE CASES (Validasi Input)
# ==========================================

def test_create_poli_empty_string():
    r = requests.post(f"{BASE_URL}/admin/polis", json={"poli": "", "prefix": ""})
    assert r.status_code == 422

def test_create_poli_invalid_prefix():
    r = requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Ngawur", "prefix": "123"})
    assert r.status_code == 422

def test_duplicate_poli(clean_setup):
    payload = {"poli": "Poli Gigi", "prefix": "GIG"}
    # Request 1 (Sukses)
    requests.post(f"{BASE_URL}/admin/polis", json=payload)
    # Request 2 (Gagal)
    r = requests.post(f"{BASE_URL}/admin/polis", json=payload)
    assert r.status_code == 400

def test_doctor_time_logic(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Gigi", "prefix": "GIG"})
    payload = {
        "dokter": "Dr. Ratna Sari", "poli": "Poli Gigi",
        "practice_start_time": "15:00", "practice_end_time": "07:00", 
        "max_patients": 5
    }
    r = requests.post(f"{BASE_URL}/admin/doctors", json=payload)
    assert r.status_code == 422

def test_register_past_date(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Gigi", "prefix": "GIG"})
    res_doc = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Ratna Sari", "poli": "Poli Gigi", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 10
    }).json()
    
    kemarin = str(date.today() - timedelta(days=1))
    payload = {
        "nama_pasien": "Pasien Telat", "poli": "Poli Gigi",
        "doctor_id": res_doc['doctor_id'], "visit_date": kemarin
    }
    r = requests.post(f"{BASE_URL}/public/submit", json=payload)
    assert r.status_code == 422

# ==========================================
# 3. ADVANCED FEATURES
# ==========================================

def test_update_doctor_info(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Anak", "prefix": "ANA"})
    r_create = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Typo", "poli": "Poli Anak", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 15
    })
    doc_id = r_create.json()['doctor_id']

    new_data = {"dokter": "Dr. Setiawan"}
    r_update = requests.put(f"{BASE_URL}/admin/doctors/{doc_id}", json=new_data)
    assert r_update.status_code == 200
    assert r_update.json()['dokter'] == "dr. Setiawan" # Cek auto-format

def test_cascade_delete_poli(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli THT", "prefix": "THT"})
    r_doc = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Herman", "poli": "Poli THT",
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 10
    })
    doc_id = r_doc.json()['doctor_id']

    r_del = requests.delete(f"{BASE_URL}/admin/polis/Poli THT")
    assert r_del.status_code == 200

    r_check = requests.get(f"{BASE_URL}/admin/doctors/{doc_id}")
    assert r_check.status_code == 404

def test_search_ticket_by_name(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Mata", "prefix": "MAT"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Citra Lestari", "poli": "Poli Mata", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 10
    }).json()
    
    nama_unik = "Ibu Siti Aminah"
    requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": nama_unik, "poli": "Poli Mata", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today() + timedelta(days=1))
    })

    r_search = requests.get(f"{BASE_URL}/public/find-ticket", params={"nama": "Siti"})
    assert r_search.status_code == 200
    assert len(r_search.json()) > 0

# ==========================================
# 4. OPERATIONAL LOGIC
# ==========================================

def test_ops_strict_flow_sequence(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Jantung", "prefix": "JAN"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Hartono", "poli": "Poli Jantung", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 10
    }).json()
    p_res = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien Jantung A", "poli": "Poli Jantung", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today()) 
    }).json()
    ticket = p_res['queue_number']

    r = requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "finish"})
    assert r.status_code == 400 # Gagal loncat

    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "clinic"})
    r_fin = requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "finish"})
    
    assert r_fin.status_code == 200
    assert r_fin.json()['current_status'] == "Selesai"

def test_ops_double_scan(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Kulit", "prefix": "KUL"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Indah", "poli": "Poli Kulit", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 10
    }).json()
    p_res = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien Kulit B", "poli": "Poli Kulit", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today()) 
    }).json()
    ticket = p_res['queue_number']

    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    r2 = requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    assert r2.status_code == 200
    assert "Already checkin" in r2.json()['message']

# ==========================================
# 5. DATA ANALYTICS & MEDICAL NOTES
# ==========================================

def test_dashboard_statistics_accuracy(clean_setup):
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Syaraf", "prefix": "SYA"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Bambang", "poli": "Poli Syaraf", 
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 20
    }).json()
    doc_id = d_res['doctor_id']
    today = str(date.today())
    
    r_a = requests.post(f"{BASE_URL}/public/submit", json={"nama_pasien": "Pasien A", "poli": "Poli Syaraf", "doctor_id": doc_id, "visit_date": today})
    r_b = requests.post(f"{BASE_URL}/public/submit", json={"nama_pasien": "Pasien B", "poli": "Poli Syaraf", "doctor_id": doc_id, "visit_date": today})
    
    ticket_a = r_a.json()['queue_number']
    ticket_b = r_b.json()['queue_number']

    # Pasien A (Menunggu)
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_a, "location": "arrival"})
    
    # Pasien B (Selesai)
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_b, "location": "arrival"})
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_b, "location": "clinic"})
    
    # [FIX] Tambahkan sleep di sini juga agar Dr. Bambang punya durasi layanan valid
    time.sleep(1.1) 
    
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_b, "location": "finish"})

    r_dash = requests.get(f"{BASE_URL}/monitor/dashboard", params={"target_date": today})
    stats = r_dash.json()
    stat_poli = next((item for item in stats if item["poli_name"] == "Poli Syaraf"), None)
    
    assert stat_poli['patients_waiting'] == 1
    assert stat_poli['patients_finished'] == 1
def test_analytics_report_generation(clean_setup):
    """Skenario Poli Kandungan untuk Laporan Analitik"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Kandungan", "prefix": "KAN"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Farah", "poli": "Poli Kandungan", 
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 20
    }).json()
    
    r_p = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Ibu Hamil C", "poli": "Poli Kandungan", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today())
    })
    ticket = r_p.json()['queue_number']
    
    # PROSES SCAN (DENGAN JEDA WAKTU AGAR DURASI TIDAK 0)
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "clinic"})
    
    # [FIX] Tunggu 1 detik biar seolah-olah diperiksa (Mencegah ZeroDivisionError)
    time.sleep(1.1) 
    
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "finish"})

    # Cek Report
    r_rep = requests.get(f"{BASE_URL}/analytics/comprehensive-report")
    
    # Assert
    assert r_rep.status_code == 200, f"Analytics Error: {r_rep.text}"
    data = r_rep.json()
    assert "Poli Kandungan" in data['poli_volume']

def test_medical_notes_flow(clean_setup):
    """Skenario: Dokter mengisi catatan medis pasien."""
    # 1. Setup
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Diagnosa", "prefix": "DIA"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. House", "poli": "Poli Diagnosa", 
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 10
    }).json()
    
    # 2. Daftar
    r_p = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien Rumit", "poli": "Poli Diagnosa", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today())
    })
    ticket = r_p.json()['queue_number']
    
    # 3. Isi Catatan
    catatan = "Pasien menderita flu berat."
    r_note = requests.put(f"{BASE_URL}/ops/medical-notes/{ticket}", json={"catatan": catatan})
    
    assert r_note.status_code == 200
    assert r_note.json()['message'] == "Catatan medis tersimpan"