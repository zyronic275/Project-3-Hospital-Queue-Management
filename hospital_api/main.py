from fastapi import FastAPI, Depends, HTTPException, APIRouter, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np
import re
import random
from faker import Faker
import security
from fastapi.security import OAuth2PasswordRequestForm
import security

import storage
import schemas
import csv_utils

app = FastAPI(title="Sistem RS: Analytics Pro Max")



storage.init_db()

# Setup Router
router_admin = APIRouter(prefix="/admin", tags=["Admin: Manajemen Data"])
router_public = APIRouter(prefix="/public", tags=["Public: Pendaftaran"])
router_ops = APIRouter(prefix="/ops", tags=["Medical Staff: Operasional"])
router_monitor = APIRouter(prefix="/monitor", tags=["Admin: Monitoring"])
router_analytics = APIRouter(prefix="/analytics", tags=["Data Science & Insights"])

def get_db():
    db = storage.SessionLocal()
    try: yield db
    finally: db.close()

# --- HELPER ---
def parse_datetime_smart(date_val, time_val=None):
    if pd.isna(date_val) or str(date_val).strip() == "": return None
    try:
        d_obj = pd.to_datetime(str(date_val)).date()
        if pd.isna(time_val) or str(time_val).strip() == "": return datetime.combine(d_obj, time(0,0))
        t_obj = pd.to_datetime(str(time_val).strip()).time()
        return datetime.combine(d_obj, t_obj)
    except: return None

def get_random_time_window():
    base_h = random.randint(8, 13)
    base_m = random.randint(0, 59)
    t_chk = datetime.combine(date.today(), time(base_h, base_m))
    t_ent = t_chk + timedelta(minutes=random.randint(5, 90)) 
    t_fin = t_ent + timedelta(minutes=random.randint(5, 30)) 
    return t_chk, t_ent, t_fin

# =================================================================
# 1. IMPORT DATA (HYBRID)
# =================================================================
def clean_simple_name(full_name: str) -> str:
    """
    Membersihkan gelar dan mengambil satu kata nama utama.
    Contoh: 
    - "Drs. Moh. Hatta" -> "Hatta"
    - "Gibran, S.Pd" -> "Gibran"
    """
    if not full_name: return "TanpaNama"
    
    # 1. Buang gelar belakang (setelah koma)
    # "Gibran, S.Pd" -> "Gibran"
    name_no_suffix = full_name.split(',')[0]
    
    # 2. Buang gelar depan umum (Case Insensitive)
    # Regex membuang Dr. Drs. Ir. Prof. H. Hj. Ns.
    name_clean = re.sub(r'^(dr\.|drs\.|dra\.|ir\.|prof\.|h\.|hj\.|ns\.|mr\.|mrs\.)\s*', '', name_no_suffix, flags=re.IGNORECASE)
    
    # 3. Bersihkan spasi berlebih & titik
    parts = name_clean.replace('.', ' ').split()
    
    # 4. Ambil kata TERAKHIR (Sesuai contoh "Moh. Hatta" -> "Hatta")
    if parts:
        return parts[-1].title() # Capitalize
    else:
        return "User"

@router_admin.get("/import-random-data")
def import_random_data(count: int = 10, db: Session = Depends(get_db)):
    try:
        fake = Faker('id_ID')
        df_doc_m, df_pas_m = csv_utils.get_merged_random_data(count)
        
        # Daftar diagnosa untuk WordCloud
        contoh_catatan = [
            "Demam tinggi dan menggigil.", "Sakit kepala sebelah (migrain) akut.", 
            "Batuk berdahak sudah 3 hari.", "Tekanan darah tinggi (Hipertensi).", 
            "Gatal-gatal alergi seafood.", "Nyeri punggung bawah (Low Back Pain).",
            "Mata merah iritasi debu.", "Sakit gigi geraham bungsu.", 
            "Asam lambung naik (GERD).", "Kelelahan kronis butuh vitamin.",
            "Cek kolesterol dan asam urat.", "Flu berat dan hidung tersumbat."
        ]
        
        imported_count = 0
        
        for _ in range(count):
            
            # --- 1. SETUP DOKTER ---
            r_poli = "Poli Umum"; r_dokter_db = "dr. Umum"; r_prefix = "UMUM"
            t_start = time(8,0); t_end = time(16,0); doc_code = "UM-001"; max_p = 20

            if not df_doc_m.empty:
                row = df_doc_m.sample(n=1).iloc[0]
                r_poli = str(row['poli']).strip()
                r_dokter_db = f"dr. {clean_simple_name(str(row['dokter']))}"
                r_prefix = str(row.get('prefix', r_poli[:4].upper())).strip()
                try:
                    t_start = datetime.strptime(str(row['practice_start_time']), "%H:%M:%S").time()
                    t_end = datetime.strptime(str(row['practice_end_time']), "%H:%M:%S").time()
                except: pass
                doc_code = row['doctor_code']; max_p = int(row['max_patients'])

            # Simpan Poli & Dokter
            if not db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == r_poli).first():
                db.add(storage.TabelPoli(poli=r_poli, prefix=r_prefix)); db.commit()
            
            doc_obj = db.query(storage.TabelDokter).filter(storage.TabelDokter.dokter == r_dokter_db).first()
            if not doc_obj:
                max_id = db.query(func.max(storage.TabelDokter.doctor_id)).scalar() or 0
                doc_obj = storage.TabelDokter(doctor_id=max_id+1, dokter=r_dokter_db, poli=r_poli, 
                                              practice_start_time=t_start, practice_end_time=t_end, 
                                              doctor_code=doc_code, max_patients=max_p)
                db.add(doc_obj); db.commit()

            # --- 2. SETUP PASIEN ---
            r_nama_pasien = clean_simple_name(fake.name())
            username_pasien = r_nama_pasien.lower().replace(" ", "") + str(random.randint(1,999))
            
            if not db.query(storage.TabelUser).filter(storage.TabelUser.username == username_pasien).first():
                db.add(storage.TabelUser(username=username_pasien, password=security.get_password_hash("123"), 
                                         role="pasien", nama_lengkap=r_nama_pasien)); db.commit()

            # --- 3. RANDOM TANGGAL & WAKTU (BAGIAN BARU) ---
            
            # A. Tentukan Tanggal Kunjungan (Acak dalam 30 hari terakhir)
            # start_date='-30d' artinya 30 hari ke belakang
            r_date = fake.date_between(start_date='-30d', end_date='today')
            
            # B. Generate Jam Acak (Antara jam 08:00 s.d 14:00)
            # Kita buat manual datetime-nya agar sinkron dengan r_date
            jam_acak_dt = random.randint(8, 14)
            menit_acak_dt = random.randint(0, 59)
            
            # Waktu Check-in (Datang)
            # Gabungkan Tanggal Acak (r_date) + Jam Acak
            t_chk = datetime.combine(r_date, time(jam_acak_dt, menit_acak_dt))
            
            # Waktu Masuk Poli (Misal 10-60 menit setelah checkin)
            t_ent = t_chk + timedelta(minutes=random.randint(10, 60))
            
            # Waktu Selesai (Misal 10-30 menit setelah masuk)
            t_fin = t_ent + timedelta(minutes=random.randint(10, 30))

            # --- 4. STATUS & CATATAN ---
            # Jika tanggalnya masa lalu (< hari ini), statusnya harus 'Selesai' biar logis
            if r_date < date.today():
                r_status = "Selesai"
                f_chk, f_ent, f_fin = t_chk, t_ent, t_fin
            else:
                # Jika hari ini, status bisa random
                r_status = random.choices(["Menunggu", "Sedang Dilayani", "Selesai"], weights=[20, 20, 60])[0]
                f_chk = t_chk
                f_ent = t_ent if r_status in ["Sedang Dilayani", "Selesai"] else None
                f_fin = t_fin if r_status == "Selesai" else None

            # Catatan Medis (PASTI ADA)
            r_catatan = random.choice(contoh_catatan)

            # --- 5. GENERATE NOMOR ANTREAN (SESUAI TANGGAL RANDOM) ---
            # Penting: Hitung nomor antrean berdasarkan TANGGAL RANDOM tsb, bukan hari ini.
            last_cnt = db.query(storage.TabelPelayanan).filter(
                storage.TabelPelayanan.doctor_id_ref == doc_obj.doctor_id, 
                storage.TabelPelayanan.visit_date == r_date  # <--- Filter by Tanggal Random
            ).count()
            
            seq = last_cnt + 1
            try: d_suf = doc_obj.doctor_code.split('-')[-1]
            except: d_suf = "001"
            q_str = f"{r_prefix}-{d_suf}-{seq:03d}"
            
            # Status Member
            is_lama = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.username == username_pasien).count() > 0
            stat_mem = "Pasien Lama" if is_lama else "Pasien Baru"

            # --- 6. SIMPAN KE DB ---
            pel = storage.TabelPelayanan(
                username=username_pasien, status_member=stat_mem, nama_pasien=r_nama_pasien, 
                poli=r_poli, dokter=doc_obj.dokter, doctor_id_ref=doc_obj.doctor_id, 
                
                visit_date=r_date, # <--- Tanggal Random
                checkin_time=f_chk, # <--- Waktu Random Sinkron
                clinic_entry_time=f_ent, 
                completion_time=f_fin, 
                
                status_pelayanan=r_status, queue_number=q_str, queue_sequence=seq, 
                catatan_medis=r_catatan
            )
            db.add(pel)
            
            gab = storage.TabelGabungan(
                username=username_pasien, status_member=stat_mem, nama_pasien=r_nama_pasien, 
                poli=r_poli, prefix_poli=r_prefix, dokter=doc_obj.dokter, doctor_code=doc_obj.doctor_code, doctor_id=doc_obj.doctor_id, 
                visit_date=r_date, checkin_time=f_chk, clinic_entry_time=f_ent, completion_time=f_fin, 
                status_pelayanan=r_status, queue_number=q_str, queue_sequence=seq, 
                catatan_medis=r_catatan
            )
            db.add(gab)
            
            db.commit()
            imported_count += 1
            
        return {"message": f"Sukses import {imported_count} data (Tanggal Bervariasi)."}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, detail=str(e))

# =================================================================
# 2. ANALYTICS
# =================================================================
@router_analytics.get("/comprehensive-report")
def get_analytics_report(
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    # 1. Query Dasar
    query = db.query(storage.TabelPelayanan)

    # 2. Filter Tanggal (Jika ada parameter)
    if start_date:
        query = query.filter(storage.TabelPelayanan.visit_date >= start_date)
    if end_date:
        query = query.filter(storage.TabelPelayanan.visit_date <= end_date)
    
    results = query.all()
    
    if not results: 
        return {"status": "No Data"}

    # 3. Konversi ke DataFrame
    data = [{
        "poli": q.poli,
        "dokter": q.dokter,
        "checkin_time": q.checkin_time,
        "entry_time": q.clinic_entry_time,
        "completion_time": q.completion_time,
        "status": q.status_pelayanan,
        "catatan": q.catatan_medis
    } for q in results]
    
    df = pd.DataFrame(data)

    # 4. Preprocessing Waktu
    for col in ['checkin_time', 'entry_time', 'completion_time']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    df['wait_minutes'] = (df['entry_time'] - df['checkin_time']).dt.total_seconds() / 60
    df['service_minutes'] = (df['completion_time'] - df['entry_time']).dt.total_seconds() / 60
    
    df_valid_wait = df[df['wait_minutes'] >= 0].copy()
    df_valid_svc = df[df['service_minutes'] >= 0].copy()

    # --- ANALISIS TOTAL (Tanpa membedakan pasien lama/baru) ---
    
    # A. Volume per Poli
    poli_vol = df['poli'].value_counts().to_dict()

    # B. Efisiensi Waktu
    eff_wait = df_valid_wait.groupby('poli')['wait_minutes'].mean().fillna(0)
    eff_svc = df_valid_svc.groupby('poli')['service_minutes'].mean().fillna(0)
    
    poli_efficiency = {}
    all_polis = set(eff_wait.index).union(set(eff_svc.index))
    for p in all_polis:
        poli_efficiency[p] = {
            'wait_minutes': round(eff_wait.get(p, 0), 1),
            'service_minutes': round(eff_svc.get(p, 0), 1)
        }

    # C. Jam Sibuk
    peak_hours = {}
    if not df['checkin_time'].isna().all():
        peak_hours = df['checkin_time'].dropna().dt.hour.value_counts().sort_index().to_dict()

    # D. Produktivitas Dokter
    doc_perf = df_valid_svc.groupby('dokter')['service_minutes'].mean()
    doc_throughput = {}
    for doc, minutes in doc_perf.items():
        if minutes > 0: doc_throughput[doc] = round(60 / minutes, 1)
        else: doc_throughput[doc] = 0

    # E. Ghosting Rate
    total_p = len(df)
    ghosts = df[df['checkin_time'].isna()]
    ghost_rate = round((len(ghosts) / total_p) * 100, 1) if total_p > 0 else 0

    # F. Korelasi Crowd vs Speed (Hourly)
    correlation = 0
    if not df_valid_svc.empty and not df['checkin_time'].isna().all():
        df_valid_svc['hour_col'] = df_valid_svc['checkin_time'].dt.hour
        hourly_stats = df_valid_svc.groupby('hour_col').agg(crowd_count=('status', 'count'), avg_speed=('service_minutes', 'mean'))
        if len(hourly_stats) > 1:
            correlation = round(hourly_stats['crowd_count'].corr(hourly_stats['avg_speed']), 2)
            if pd.isna(correlation): correlation = 0

    # G. Text Mining
    all_notes = " ".join([str(x) for x in df['catatan'].dropna().tolist()])
    
    return {
        "status": "Success",
        "poli_volume": poli_vol,
        "poli_efficiency": poli_efficiency,
        "peak_hours": peak_hours,
        "doctor_throughput": doc_throughput,
        "ghost_rate": ghost_rate,
        "correlation": correlation,
        "text_mining": all_notes,
        "total_patients": total_p
    }
# =================================================================
# 3. CRUD & OPS
# =================================================================

# ... [ADMIN CRUD TETAP SAMA SEPERTI SEBELUMNYA] ... 
# (Silakan copy paste bagian router_admin dan router_public dari kode sebelumnya)
# Saya singkat di sini agar muat, tapi pastikan Anda tidak menghapusnya.

@router_admin.post("/polis", response_model=schemas.PoliSchema)
def create_poli(p: schemas.PoliCreate, db: Session = Depends(get_db)):
    # 1. Cek Nama Poli (Sudah ada)
    if db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == p.poli).first(): 
        raise HTTPException(400, f"Poli '{p.poli}' sudah ada.")
    
    # 2. [BARU] Cek Prefix Unik
    # Kita cek apakah ada poli LAIN yang sudah pakai prefix ini?
    if db.query(storage.TabelPoli).filter(storage.TabelPoli.prefix == p.prefix.upper()).first(): 
        raise HTTPException(400, f"Prefix '{p.prefix.upper()}' sudah digunakan poli lain! Ganti prefix lain.")

    # 3. Simpan
    new = storage.TabelPoli(poli=p.poli, prefix=p.prefix.upper())
    db.add(new); db.commit(); db.refresh(new)
    return new
@router_admin.put("/polis/{original_name}")
def update_poli(original_name: str, p: schemas.PoliUpdate, db: Session = Depends(get_db)):
    # 1. Cari Poli Lama
    poli = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == original_name).first()
    if not poli: raise HTTPException(404, "Poli tidak ditemukan")
    
    # 2. Update Prefix
    if p.new_prefix:
        # Cek unik
        cek = db.query(storage.TabelPoli).filter(storage.TabelPoli.prefix == p.new_prefix).first()
        if cek and cek.poli != original_name:
            raise HTTPException(400, f"Prefix {p.new_prefix} sudah dipakai poli lain.")
        poli.prefix = p.new_prefix.upper()

    # 3. Update Nama Poli (Hati-hati, ini Primary Key di desain lama)
    # Jika nama berubah, kita harus update semua dokter yang ada di poli ini juga
    if p.new_name and p.new_name != original_name:
        # Cek nama baru
        if db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == p.new_name).first():
            raise HTTPException(400, f"Poli {p.new_name} sudah ada.")
        
        # Update Relasi Dokter (Manual Cascade karena SQLite/MySQL kadang strict)
        docs = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == original_name).all()
        for doc in docs:
            doc.poli = p.new_name
            
        poli.poli = p.new_name

    db.commit()
    return {"message": "Poli berhasil diupdate"}

@router_admin.delete("/polis/{poli_name}")
def delete_poli(poli_name: str, db: Session = Depends(get_db)):
    p = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == poli_name).first()
    if not p: raise HTTPException(404, "Not Found")
    docs = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()
    for d in docs:
        db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == d.doctor_id).delete()
        db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == d.doctor_id).delete()
        db.delete(d)
    db.delete(p); db.commit()
    return {"msg": "Deleted"}

@router_admin.get("/doctors", response_model=List[schemas.DoctorSchema])
def get_all_doctors(db: Session = Depends(get_db)): return db.query(storage.TabelDokter).all()

@router_admin.get("/doctors/{id}", response_model=schemas.DoctorSchema)
def get_doc(id: int, db: Session = Depends(get_db)):
    doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == id).first()
    if not doc: raise HTTPException(404, "Dokter tidak ditemukan")
    return doc

@router_admin.post("/doctors", response_model=schemas.DoctorSchema)
def add_doctor(p: schemas.DoctorCreate, db: Session = Depends(get_db)):
    # Validasi Poli
    pol = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == p.poli).first()
    if not pol: raise HTTPException(404, "Poli not found")
    
    # Bersihkan Nama Input (misal: "budi" -> "dr. Budi")
    clean_input_name = clean_simple_name(p.dokter)
    final_doc_name = f"dr. {clean_input_name}"

    # Validasi Nama Kembar
    if db.query(storage.TabelDokter).filter(storage.TabelDokter.dokter == final_doc_name).first(): 
        raise HTTPException(400, "Nama dokter sudah ada.")
    
    # --- PERBAIKAN LOGIKA ID (AUTO INCREMENT MANUAL YANG AMAN) ---
    # Cari ID terbesar yang ada di database saat ini
    max_id = db.query(func.max(storage.TabelDokter.doctor_id)).scalar()
    # Jika tabel kosong (None), mulai dari 1. Jika ada, max + 1.
    next_id = 1 if max_id is None else max_id + 1
    
    # Gunakan ID dari input user jika ada, kalau tidak pakai next_id
    fid = p.doctor_id if p.doctor_id else next_id
    
    # Cek double protect (jika user maksa input ID yang sudah ada)
    if db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == fid).first():
        # Jika ID tabrakan, cari lagi next available ID yang benar-benar kosong
        while db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == next_id).first():
            next_id += 1
        fid = next_id
    # -------------------------------------------------------------

    # Generate Kode Dokter (Contoh: GIG-005)
    last = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == p.poli).order_by(storage.TabelDokter.doctor_id.desc()).first()
    try:
        nxt_num = int(last.doctor_code.split('-')[-1]) + 1 if last else 1
    except:
        nxt_num = 1 # Fallback jika format kode lama rusak
    code = f"{pol.prefix}-{nxt_num:03d}"
    
    # Parse Waktu
    ts = datetime.strptime(p.practice_start_time, "%H:%M").time()
    te = datetime.strptime(p.practice_end_time, "%H:%M").time()
    
    new = storage.TabelDokter(
        doctor_id=fid, 
        dokter=final_doc_name, 
        poli=p.poli, 
        practice_start_time=ts, 
        practice_end_time=te, 
        doctor_code=code, 
        max_patients=p.max_patients
    )
    db.add(new)
    
    # [HAPUS BAGIAN "AUTO CREATE USER LOGIN" DI SINI] - SUDAH BERSIH
    
    db.commit()
    db.refresh(new)
    return new

@router_admin.put("/doctors/{id}", response_model=schemas.DoctorSchema)
def update_doc(id: int, p: schemas.DoctorUpdate, db: Session = Depends(get_db)):
    d = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == id).first()
    if not d: raise HTTPException(404, "Dokter tidak ditemukan")
    
    old_name = d.dokter # Simpan nama lama
    
    # Update Field
    if p.dokter: 
        clean_new = clean_simple_name(p.dokter)
        d.dokter = f"dr. {clean_new}"
        
    if p.poli: 
        if not db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == p.poli).first():
            raise HTTPException(400, "Poli tidak ditemukan")
        d.poli = p.poli

    if p.max_patients: d.max_patients = p.max_patients
    if p.practice_start_time: d.practice_start_time = datetime.strptime(p.practice_start_time, "%H:%M").time()
    if p.practice_end_time: d.practice_end_time = datetime.strptime(p.practice_end_time, "%H:%M").time()

    # --- CASCADE UPDATE (Update juga Tabel Transaksi) ---
    # Jika nama dokter berubah, kita harus update semua riwayat transaksi yang pakai nama lama
    if p.dokter and old_name != d.dokter:
        print(f"🔄 Mengupdate nama dokter di riwayat: {old_name} -> {d.dokter}")
        
        # 1. Update Tabel Pelayanan
        db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == id).update(
            {storage.TabelPelayanan.dokter: d.dokter}, synchronize_session=False
        )
        
        # 2. Update Tabel Gabungan
        db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == id).update(
            {storage.TabelGabungan.dokter: d.dokter}, synchronize_session=False
        )
    # ----------------------------------------------------

    db.commit()
    db.refresh(d)
    return d

@router_admin.delete("/doctors/{id}")
def del_doc(id: int, db: Session = Depends(get_db)):
    d = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == id).first()
    if not d: raise HTTPException(404, "Dokter tidak ditemukan")
    
    nama_dokter = d.dokter
    
    # --- CASCADE DELETE ---
    # Hapus semua transaksi terkait dokter ini agar data bersih
    db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == id).delete()
    db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == id).delete()
    
    db.delete(d)
    db.commit()
    return {"message": f"Dokter {nama_dokter} dan seluruh riwayatnya telah dihapus."}

@router_admin.get("/generate-doctor-accounts")
def generate_doctor_accounts(db: Session = Depends(get_db)):
    # Ambil semua data dokter yang ada di tabel dokter
    doctors = db.query(storage.TabelDokter).all()
    created = 0
    
    for doc in doctors:
        # Generate username dari nama dokter
        # Contoh: "dr. Ryan Reynolds" -> "dr_ryan_reynolds"
        clean_name = doc.dokter.lower().replace(" ", "_").replace(".", "")
        
        # Cek apakah akun sudah ada
        if not db.query(storage.TabelUser).filter(storage.TabelUser.username == clean_name).first():
            new_user = storage.TabelUser(
                username=clean_name,
                password=security.get_password_hash("123"), # Default password
                role="dokter",
                nama_lengkap=doc.dokter # Nama harus SAMA PERSIS dengan di TabelDokter
            )
            db.add(new_user)
            created += 1
    
    db.commit()
    return {"message": f"Berhasil membuat {created} akun login untuk dokter. Password default: 123"}
# --- PUBLIC ---
@router_public.get("/polis", response_model=List[schemas.PoliSchema])
def get_polis(db: Session = Depends(get_db)): return db.query(storage.TabelPoli).all()

@router_public.get("/available-doctors", response_model=List[schemas.DoctorSchema])
def get_avail_docs(poli_name: str, db: Session = Depends(get_db)): return db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()

@router_public.get("/find-ticket", response_model=List[schemas.PelayananSchema])
def find_ticket(nama: str, target_date: Optional[date] = None, db: Session = Depends(get_db)):
    q = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.nama_pasien.ilike(f"%{nama}%"))
    if target_date: q = q.filter(storage.TabelPelayanan.visit_date == target_date)
    res = q.order_by(storage.TabelPelayanan.visit_date.desc()).all()
    if not res: raise HTTPException(404, "Not Found")
    out = []
    for r in res:
        rd = r.__dict__
        rd['doctor_schedule'] = "-"
        out.append(rd)
    return out

@router_public.post("/submit", response_model=schemas.PelayananSchema)
def register(p: schemas.RegistrationFinal, db: Session = Depends(get_db),current_user: dict = Depends(security.get_current_user_token)):
    # 1. Validasi Tanggal
    if p.visit_date < date.today(): raise HTTPException(400, "Tanggal tidak boleh masa lalu")
    
    # 2. Ambil Data Dokter
    doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == p.doctor_id).first()
    if not doc: raise HTTPException(404, "Dokter tidak ditemukan")
    
    # 3. Cek Kesesuaian Poli (Validasi Nama Poli yang sudah diformat otomatis)
    # Gunakan lower() untuk membandingkan biar aman (misal "Poli Gigi" vs "Poli gigi")
    if doc.poli.lower() != p.poli.lower(): 
        raise HTTPException(400, f"Dokter ini bukan dari {p.poli}")

    # 4. Hitung Nomor Antrean
    cnt = db.query(storage.TabelPelayanan).filter(
        storage.TabelPelayanan.doctor_id_ref == p.doctor_id, 
        storage.TabelPelayanan.visit_date == p.visit_date
    ).count()
    seq = cnt + 1
    
    # Format Nomor: PREFIX-001-001 (Poli-Dokter-Urutan)
    try: suf = doc.doctor_code.split('-')[-1]
    except: suf = "000"
    qstr = f"{doc.poli_rel.prefix}-{suf}-{seq:03d}"
    
    # --- [LOGIKA BARU] CEK STATUS MEMBER ---
    # Hitung berapa kali dia sudah 'Selesai' berobat sebelumnya
    riwayat_count = db.query(storage.TabelPelayanan).filter(
        storage.TabelPelayanan.username == current_user['username'],
        storage.TabelPelayanan.status_pelayanan == "Selesai"
    ).count()

    status_member_now = "Pasien Lama" if riwayat_count > 0 else "Pasien Baru"
    # ---------------------------------------

    # 5. Simpan ke Database
    new = storage.TabelPelayanan(
        username=current_user['username'],
        status_member=status_member_now,
        nama_pasien=p.nama_pasien, 
        poli=doc.poli, 
        dokter=doc.dokter, 
        doctor_id_ref=doc.doctor_id, 
        visit_date=p.visit_date, 
        status_pelayanan="Terdaftar", 
        queue_number=qstr, 
        queue_sequence=seq
    )
    db.add(new)
    
    gab = storage.TabelGabungan(
        username=current_user['username'],
        status_member=status_member_now,
        nama_pasien=p.nama_pasien, 
        poli=doc.poli, 
        prefix_poli=doc.poli_rel.prefix, 
        dokter=doc.dokter, 
        doctor_code=doc.doctor_code, 
        doctor_id=doc.doctor_id, 
        visit_date=p.visit_date, 
        status_pelayanan="Terdaftar", 
        queue_number=qstr, 
        queue_sequence=seq
    )
    db.add(gab)
    
    db.commit(); db.refresh(new)
    
    # --- [FIX UTAMA] MANUAL INJECT JADWAL DOKTER ---
    # Kita ubah objek SQLAlchemy menjadi Dictionary agar bisa ditambah field manual
    response_data = new.__dict__
    
    # Ambil jam praktik dari objek 'doc' yang sudah kita query di atas
    jam_mulai = doc.practice_start_time.strftime('%H:%M')
    jam_selesai = doc.practice_end_time.strftime('%H:%M')
    
    # Masukkan ke field 'doctor_schedule' agar muncul di Frontend
    response_data['doctor_schedule'] = f"{jam_mulai} - {jam_selesai}"
    
    return response_data

# --- OPS ---
@router_ops.post("/scan-barcode")
def scan(p: schemas.ScanRequest, db: Session = Depends(get_db)):
    # 1. Cari Data Pasien
    s = None
    val = p.barcode_data.strip()
    
    # Cek by ID atau Queue Number
    if val.isdigit(): 
        s = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.id == int(val)).first()
    if not s: 
        s = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.queue_number == val).first()
    
    if not s: 
        raise HTTPException(404, "Data tiket tidak ditemukan")

    # 2. DEFINISI LEVEL STATUS (State Machine)
    # Urutan logis alur pasien
    STATE_LEVEL = {
        "Terdaftar": 0,
        "Menunggu": 1,
        "Sedang Dilayani": 2,
        "Selesai": 3
    }
    
    # Mapping Lokasi Scan ke Target Status
    LOCATION_TARGET = {
        "arrival": ("Menunggu", 1),
        "clinic": ("Sedang Dilayani", 2),
        "finish": ("Selesai", 3)
    }

    # Ambil status saat ini & target
    current_status = s.status_pelayanan
    current_lvl = STATE_LEVEL.get(current_status, 0)
    
    target_status, target_lvl = LOCATION_TARGET.get(p.location)

    # 3. VALIDASI ALUR (VALIDATION LOGIC)

    # KASUS A: SUDAH DILAKUKAN (Level Sama)
    if current_lvl == target_lvl:
        return {
            "status": "Warning", 
            "message": f"Pasien ini SUDAH berstatus '{current_status}'. Tidak perlu scan ulang.",
            "current_status": current_status
        }

    # KASUS B: MUNDUR (Level Target < Level Sekarang)
    # Contoh: Mau scan 'Arrival' (1) padahal status sudah 'Selesai' (3)
    if target_lvl < current_lvl:
        return {
            "status": "Error",
            "message": f"TIDAK BISA MUNDUR! Pasien sudah '{current_status}', tidak bisa diubah kembali ke '{target_status}'.",
            "current_status": current_status
        }

    # KASUS C: LONCAT (Opsional - misal dari Terdaftar langsung Finish)
    # Jika Anda ingin memaksa urutan ketat, aktifkan ini. 
    # Tapi kalau boleh loncat (misal lupa scan arrival), biarkan saja.
    # if target_lvl > current_lvl + 1:
    #     return {"status": "Error", "message": "Harap scan berurutan!"}

    # 4. EKSEKUSI PERUBAHAN (Hanya jika lolos validasi)
    msg = ""
    waktu_skrg = datetime.now()

    if p.location == "arrival":
        s.checkin_time = waktu_skrg
        msg = "Check-in Berhasil"
    elif p.location == "clinic":
        s.clinic_entry_time = waktu_skrg
        msg = "Pasien Masuk Poli"
    elif p.location == "finish":
        s.completion_time = waktu_skrg
        msg = "Pelayanan Selesai"
    
    # Update Status
    s.status_pelayanan = target_status
    
    # Sinkronisasi ke Tabel Gabungan
    gab = db.query(storage.TabelGabungan).filter(storage.TabelGabungan.queue_number == s.queue_number).first()
    if gab:
        gab.checkin_time = s.checkin_time
        gab.clinic_entry_time = s.clinic_entry_time
        gab.completion_time = s.completion_time
        gab.status_pelayanan = s.status_pelayanan

    db.commit()
    
    return {
        "status": "Success", 
        "message": msg, 
        "current_status": s.status_pelayanan
    }

# [BARU] Endpoint untuk Mengisi Catatan Medis
@router_ops.put("/medical-notes/{queue_number}")
def update_medical_notes(queue_number: str, note: schemas.MedicalNoteUpdate, db: Session = Depends(get_db)):
    # Cari pasien
    pel = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.queue_number == queue_number).first()
    if not pel: raise HTTPException(404, "Pasien tidak ditemukan")
    
    # Update catatan
    pel.catatan_medis = note.catatan
    
    # Update di Tabel Gabungan juga
    gab = db.query(storage.TabelGabungan).filter(storage.TabelGabungan.queue_number == queue_number).first()
    if gab: gab.catatan_medis = note.catatan
    
    db.commit()
    return {"status": "Success", "message": "Catatan medis tersimpan"}

@router_monitor.get("/dashboard", response_model=List[schemas.ClinicStats])
def dash(db: Session = Depends(get_db), target_date: date = None):
    td = target_date if target_date else datetime.now().date()
    st = []
    for p in db.query(storage.TabelPoli).all():
        svcs = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.poli == p.poli, storage.TabelPelayanan.visit_date == td).all()
        st.append({"poli_name": p.poli, "total_doctors": 0, "total_patients_today": len(svcs), 
                   "patients_waiting": sum(1 for x in svcs if x.status_pelayanan=="Menunggu"),
                   "patients_being_served": sum(1 for x in svcs if x.status_pelayanan=="Sedang Dilayani"),
                   "patients_finished": sum(1 for x in svcs if x.status_pelayanan=="Selesai")})
    return st

@router_monitor.get("/queue-board", response_model=List[schemas.PelayananSchema])
def board(db: Session = Depends(get_db)):
    return db.query(storage.TabelPelayanan).filter(
        storage.TabelPelayanan.visit_date == datetime.now().date(), 
        storage.TabelPelayanan.status_pelayanan.in_(["Menunggu", "Sedang Dilayani"])
    ).all()

# =================================================================
# 4. AUTHENTICATION & USERS (NEW)
# =================================================================
router_auth = APIRouter(prefix="/auth", tags=["Authentication"])

@router_auth.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(storage.TabelUser).filter(storage.TabelUser.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    # --- LOGIKA BARU: DEFINISI PASIEN LAMA VS BARU ---
    status_pasien = "Staff/Dokter" # Default jika bukan pasien
    if user.role == "pasien":
        # Cek apakah pernah punya transaksi dengan status 'Selesai'
        # Kita cek berdasarkan username agar akurat
        count_selesai = db.query(storage.TabelPelayanan).filter(
            storage.TabelPelayanan.username == user.username,
            storage.TabelPelayanan.status_pelayanan == "Selesai"
        ).count()
        
        if count_selesai > 0:
            status_pasien = "Pasien Lama"
        else:
            status_pasien = "Pasien Baru"
    # ------------------------------------------------
    
    token = security.create_access_token(data={"sub": user.username, "role": user.role})
    
    # Masukkan status_pasien ke response (Kita perlu update schema Token sedikit nanti, 
    # tapi untuk sekarang kita selipkan di field 'nama' atau buat field baru di schema)
    # Agar cepat, kita kirim status ini gabung dengan nama dulu, atau Anda update schema.
    # Disini saya update schema di Langkah 2.
    
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "role": user.role, 
        "nama": user.nama_lengkap,
        "status_member": status_pasien # <--- Field Baru
    }

@router_auth.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(storage.TabelUser).filter(storage.TabelUser.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    token = security.create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role, "nama": user.nama_lengkap}

# --- SEEDING USER ADMIN DEFAULT ---
# Agar kamu bisa login pertama kali
@app.on_event("startup")
def create_default_admin():
    db = storage.SessionLocal()
    if not db.query(storage.TabelUser).filter(storage.TabelUser.username == "admin").first():
        print("Creating default admin...")
        admin = storage.TabelUser(
            username="admin", 
            password=security.get_password_hash("admin123"), 
            role="admin", 
            nama_lengkap="Administrator RS"
        )
        db.add(admin)
        db.commit()
    db.close()

# --- ENDPOINT BARU: RIWAYAT SAYA ---
# main.py

@router_public.get("/my-history", response_model=List[schemas.PelayananSchema])
def get_my_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(security.get_current_user_token), 
    db: Session = Depends(get_db)
):
    # 1. Query Data Transaksi
    query = db.query(storage.TabelPelayanan).filter(
        storage.TabelPelayanan.username == current_user['username']
    )

    if start_date:
        query = query.filter(storage.TabelPelayanan.visit_date >= start_date)
    if end_date:
        query = query.filter(storage.TabelPelayanan.visit_date <= end_date)
    
    # Eager loading untuk mengambil relasi dokter (agar data jam praktik terbawa)
    # Pastikan di storage.py relasi 'dokter_rel' sudah didefinisikan dengan benar
    results = query.order_by(storage.TabelPelayanan.visit_date.desc()).all()
    
    # 2. Inject Jam Praktik secara Manual ke Response
    # Kita ubah objek SQLAlchemy menjadi Dictionary agar bisa dimodifikasi
    final_results = []
    for r in results:
        item = r.__dict__ # Konversi ke dict
        
        # Ambil jam dari relasi dokter_rel (jika ada)
        if r.dokter_rel:
            jam_mulai = r.dokter_rel.practice_start_time.strftime("%H:%M")
            jam_selesai = r.dokter_rel.practice_end_time.strftime("%H:%M")
            item['doctor_schedule'] = f"{jam_mulai} - {jam_selesai}"
        else:
            item['doctor_schedule'] = "Jadwal Tidak Tersedia"
            
        final_results.append(item)
    
    return final_results

# Jangan lupa daftarkan router auth
app.include_router(router_auth)

app.include_router(router_admin)
app.include_router(router_public)
app.include_router(router_ops)
app.include_router(router_monitor)
app.include_router(router_analytics)