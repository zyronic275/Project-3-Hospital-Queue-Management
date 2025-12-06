import requests
import pytest
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000"

# ==========================================
# 🧹 FIXTURE: PERSIAPAN & PEMBERSIHAN DATA
# ==========================================
@pytest.fixture
def clean_setup():
    """
    Membersihkan data tes SEBELUM tes dimulai.
    """
    # Daftar semua nama Poli yang dipakai di script ini
    polies_to_clean = [
        "Poli Tes Flow", 
        "Poli Validasi", 
        "Poli Edit", 
        "Poli Hapus", 
        "Poli Cari", 
        "Poli Ops", 
        "Poli Double",

        "Poli Stat",  
        "Poli Data" 
    ]
    
    print("\n[CLEANUP] Menghapus data sisa...")
    for p in polies_to_clean:
        try:
            requests.delete(f"{BASE_URL}/admin/polis/{p}")
        except:
            pass 
    return True

# ==========================================
# 1. HAPPY PATH (Alur Sukses Utama)
# ==========================================

def test_full_flow_success(clean_setup):
    """
    Skenario: Pasien datang ke Poli Umum (Input Singkat).
    """
    print("\n[TEST] Memulai Happy Path (Auto Format)...")

    # 1. Buat Poli (INPUT CUMA 'Umum')
    # Harapan: Tersimpan sebagai 'Poli Umum'
    r_poli = requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Umum", "prefix": "UMU"})
    assert r_poli.status_code == 200
    assert r_poli.json()['poli'] == "Poli Umum"  # <--- BUKTI FITUR BERJALAN

    # 2. Buat Dokter (Input Cuma 'Andi')
    doc_data = {
        "dokter": "Andi Santoso", 
        "poli": "Umum",  # <--- Input singkat juga di sini
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 20
    }
    r = requests.post(f"{BASE_URL}/admin/doctors", json=doc_data)
    assert r.status_code == 200
    assert r.json()['dokter'] == "dr. Andi Santoso"
    doc_id = r.json()['doctor_id']

    # 3. Daftar Pasien (Besok)
    besok = str(date.today() + timedelta(days=1))
    pasien_data = {
        "nama_pasien": "Budi Santoso", "poli": "Poli Tes Flow",
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
# 2. NEGATIVE CASES (Validasi Error)
# ==========================================

def test_create_poli_empty_string():
    """Coba input nama poli kosong -> Harapannya Error 422"""
    r = requests.post(f"{BASE_URL}/admin/polis", json={"poli": "", "prefix": ""})
    assert r.status_code == 422

def test_create_poli_invalid_prefix():
    """Coba prefix angka -> Harapannya Error 422"""
    r = requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Ngawur", "prefix": "123"})
    assert r.status_code == 422

def test_duplicate_poli(clean_setup):
    """Coba buat poli kembar -> Harapannya Error 400"""
    payload = {"poli": "Poli Validasi", "prefix": "VAL"}
    # Request 1 (Sukses)
    requests.post(f"{BASE_URL}/admin/polis", json=payload)
    # Request 2 (Gagal)
    r = requests.post(f"{BASE_URL}/admin/polis", json=payload)
    assert r.status_code == 400

def test_doctor_time_logic(clean_setup):
    """Jam Selesai < Jam Mulai -> Harapannya Error 422"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Validasi", "prefix": "VAL"})
    payload = {
        "dokter": "Dr. Aneh", "poli": "Poli Validasi",
        "practice_start_time": "15:00", "practice_end_time": "07:00", # Terbalik
        "max_patients": 5
    }
    r = requests.post(f"{BASE_URL}/admin/doctors", json=payload)
    assert r.status_code == 422

def test_register_past_date(clean_setup):
    """Daftar tanggal lampau -> Harapannya Error 422"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Validasi", "prefix": "VAL"})
    res_doc = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Time", "poli": "Poli Validasi", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 5
    }).json()
    
    kemarin = str(date.today() - timedelta(days=1))
    payload = {
        "nama_pasien": "Pasien Telat", "poli": "Poli Validasi",
        "doctor_id": res_doc['doctor_id'], "visit_date": kemarin
    }
    r = requests.post(f"{BASE_URL}/public/submit", json=payload)
    assert r.status_code == 422

# ==========================================
# 3. ADVANCED FEATURES (Update, Delete, Search)
# ==========================================

def test_update_doctor_info(clean_setup):
    """Admin salah ketik nama dokter -> Update -> Nama berubah"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Edit", "prefix": "EDT"})
    r_create = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Typo", "poli": "Poli Edit",
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 5
    })
    doc_id = r_create.json()['doctor_id']

 # Update jadi Setiawan (Input tanpa gelar)
    new_data = {"dokter": "Setiawan"} 
    r_update = requests.put(f"{BASE_URL}/admin/doctors/{doc_id}", json=new_data)
    
    assert r_update.status_code == 200
    # Pastikan outputnya ada gelarnya
    assert r_update.json()['dokter'] == "dr. Setiawan"

def test_cascade_delete_poli(clean_setup):
    """Poli dihapus -> Dokternya harus ikut terhapus"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Hapus", "prefix": "DEL"})
    r_doc = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Korban", "poli": "Poli Hapus",
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 5
    })
    doc_id = r_doc.json()['doctor_id']

    # Hapus Poli
    r_del = requests.delete(f"{BASE_URL}/admin/polis/Poli Hapus")
    assert r_del.status_code == 200

    # Cek Dokter (Harusnya 404 Not Found)
    r_check = requests.get(f"{BASE_URL}/admin/doctors/{doc_id}")
    # Karena kita sudah fix main.py untuk raise 404, ini harusnya 404
    assert r_check.status_code == 404

def test_search_ticket_by_name(clean_setup):
    """Cari tiket pakai sebagian nama"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Cari", "prefix": "SRC"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Watson", "poli": "Poli Cari", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 5
    }).json()
    
    nama_unik = "Sherlock Holmes"
    requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": nama_unik, "poli": "Poli Cari", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today() + timedelta(days=1))
    })

    # Test Cari (Partial Name "Sherlock")
    r_search = requests.get(f"{BASE_URL}/public/find-ticket", params={"nama": "Sherlock"})
    assert r_search.status_code == 200
    assert len(r_search.json()) > 0

# ==========================================
# 4. OPERATIONAL LOGIC (Strict Flow)
# ==========================================

def test_ops_strict_flow_sequence(clean_setup):
    """Coba scan 'Finish' tanpa 'Clinic' -> Harusnya Gagal"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Ops", "prefix": "OPS"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Ops", "poli": "Poli Ops", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 5
    }).json()
    p_res = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Agent Ops", "poli": "Poli Ops", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today()) 
    }).json()
    
    ticket = p_res['queue_number']

    # Coba Scan Finish langsung (ERROR)
    r = requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "finish"})
    assert r.status_code == 400

    # Alur Benar: Arrival -> Clinic -> Finish
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "clinic"})
    r_fin = requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "finish"})
    
    assert r_fin.status_code == 200
    assert r_fin.json()['current_status'] == "Selesai"

def test_ops_double_scan(clean_setup):
    """Scan 2x di lokasi sama -> Tidak error, tapi beri info"""
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Double", "prefix": "DBL"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Double", "poli": "Poli Double", 
        "practice_start_time": "08:00", "practice_end_time": "12:00", "max_patients": 5
    }).json()
    p_res = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien Gugup", "poli": "Poli Double", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today()) 
    }).json()
    ticket = p_res['queue_number']

    # Scan Pertama
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    
    # Scan Kedua
    r2 = requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    assert r2.status_code == 200
    assert "Already checkin" in r2.json()['message']

# ==========================================
# 5. DATA ANALYTICS & DASHBOARD ACCURACY
# ==========================================

def test_dashboard_statistics_accuracy(clean_setup):
    """
    Skenario: Buat 2 pasien.
    - Pasien A: Check-in (Status: Menunggu)
    - Pasien B: Check-in -> Masuk Poli -> Selesai (Status: Selesai)
    
    Harapan: Dashboard melaporkan:
    - Total Pasien: 2
    - Waiting: 1
    - Finished: 1
    """
    # 1. Setup Poli & Dokter
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Stat", "prefix": "STAT"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Math", "poli": "Poli Stat", 
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 10
    }).json()
    doc_id = d_res['doctor_id']

    # 2. Daftar Pasien A & B (Hari Ini)
    today = str(date.today())
    
    # Pasien A
    r_a = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien A", "poli": "Poli Stat", "doctor_id": doc_id, "visit_date": today
    })
    ticket_a = r_a.json()['queue_number']

    # Pasien B
    r_b = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien B", "poli": "Poli Stat", "doctor_id": doc_id, "visit_date": today
    })
    ticket_b = r_b.json()['queue_number']

    # 3. Gerakkan Pasien (Simulasi Status)
    
    # Pasien A -> Cuma sampai Arrival (Menunggu)
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_a, "location": "arrival"})
    
    # Pasien B -> Sampai Finish (Selesai)
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_b, "location": "arrival"})
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_b, "location": "clinic"})
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket_b, "location": "finish"})

    # 4. CEK DASHBOARD
    r_dash = requests.get(f"{BASE_URL}/monitor/dashboard", params={"target_date": today})
    assert r_dash.status_code == 200
    
    stats = r_dash.json()
    # Cari statistik untuk Poli Stat
    stat_poli = next((item for item in stats if item["poli_name"] == "Poli Stat"), None)
    
    assert stat_poli is not None, "Statistik Poli Stat tidak ditemukan"
    assert stat_poli['total_patients_today'] == 2, f"Total salah: {stat_poli['total_patients_today']}"
    assert stat_poli['patients_waiting'] == 1, f"Jml Menunggu salah: {stat_poli['patients_waiting']}"
    assert stat_poli['patients_finished'] == 1, f"Jml Selesai salah: {stat_poli['patients_finished']}"


def test_analytics_report_generation(clean_setup):
    """
    Skenario: Memastikan endpoint laporan komprehensif (Wait Time, Service Time) 
    berjalan dan menghasilkan data valid setelah ada aktivitas.
    """
    # Kita gunakan data dari tes sebelumnya (atau buat baru simple)
    # Setup cepat:
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Data", "prefix": "DAT"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. Data", "poli": "Poli Data", 
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 10
    }).json()
    
    # Buat 1 pasien full flow (Selesai) agar ada data durasi
    r_p = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien Data", "poli": "Poli Data", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today())
    })
    ticket = r_p.json()['queue_number']
    
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "arrival"})
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "clinic"})
    requests.post(f"{BASE_URL}/ops/scan-barcode", json={"barcode_data": ticket, "location": "finish"})

    # TEST ENDPOINT ANALYTICS
    r_rep = requests.get(f"{BASE_URL}/analytics/comprehensive-report")
    assert r_rep.status_code == 200
    
    data = r_rep.json()
    
    # Validasi Dasar Struktur Data
    assert "poli_volume" in data
    assert "poli_speed" in data
    assert "poli_wait" in data
    
    # Pastikan Poli Data masuk hitungan
    assert "Poli Data" in data['poli_volume']
    assert data['poli_volume']['Poli Data'] >= 1

def test_medical_notes_flow(clean_setup):
    """
    Skenario: Dokter mengisi catatan medis pasien.
    """
    # 1. Setup Data
    requests.post(f"{BASE_URL}/admin/polis", json={"poli": "Poli Diagnosa", "prefix": "DIA"})
    d_res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "dokter": "Dr. House", "poli": "Poli Diagnosa", 
        "practice_start_time": "08:00", "practice_end_time": "16:00", "max_patients": 10
    }).json()
    
    # 2. Daftar Pasien
    r_p = requests.post(f"{BASE_URL}/public/submit", json={
        "nama_pasien": "Pasien Rumit", "poli": "Poli Diagnosa", 
        "doctor_id": d_res['doctor_id'], "visit_date": str(date.today())
    })
    ticket = r_p.json()['queue_number']
    
    # 3. Masukkan Catatan Medis
    catatan_dokter = "Pasien menderita flu berat, resep diberikan."
    r_note = requests.put(f"{BASE_URL}/ops/medical-notes/{ticket}", json={"catatan": catatan_dokter})
    
    assert r_note.status_code == 200
    assert r_note.json()['message'] == "Catatan medis tersimpan"