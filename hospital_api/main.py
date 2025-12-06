from fastapi import FastAPI, Depends, HTTPException, APIRouter, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np
import re
import random
from faker import Faker 

import storage
import schemas
import csv_utils

storage.init_db()

app = FastAPI(title="Sistem RS: Analytics Pro Max")

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
@router_admin.get("/import-random-data")
def import_random_data(count: int = 10, db: Session = Depends(get_db)):
    try:
        fake = Faker('id_ID')
        df_doc_m, df_pas_m = csv_utils.get_merged_random_data(count)

        # --- [BARU] DAFTAR CONTOH CATATAN MEDIS (BAHASA INDONESIA) ---
        contoh_catatan = [
            "Pasien mengeluh demam tinggi dan pusing sejak 2 hari lalu.",
            "Tekanan darah 140/90, pasien disarankan istirahat total.",
            "Batuk berdahak dan pilek, diberikan obat sirup dan vitamin.",
            "Sakit gigi pada geraham bawah, dilakukan pembersihan karang gigi.",
            "Pemeriksaan rutin kehamilan, kondisi janin sehat dan aktif.",
            "Luka lecet pada lutut akibat jatuh, sudah dibersihkan dan diperban.",
            "Gejala maag kambuh, nyeri ulu hati dan mual.",
            "Alergi kulit kemerahan gatal-gatal, diberikan salep hidrokortison.",
            "Sakit kepala sebelah (migrain), diberikan pereda nyeri.",
            "Pemeriksaan mata, visus normal, tidak perlu kacamata.",
            "Nyeri otot punggung akibat salah posisi tidur.",
            "Kolesterol sedikit tinggi, disarankan diet rendah lemak."
        ]
        # -------------------------------------------------------------

        imported_count = 0
        attempts = 0
        max_attempts = count * 5 

        while imported_count < count and attempts < max_attempts:
            attempts += 1
            if not df_doc_m.empty:
                row_doc = df_doc_m.sample(n=1).iloc[0]
                r_poli = str(row_doc['poli']).strip()
                
                # --- UPDATE LOGIKA NAMA DOKTER RANDOM ---
                raw_name = str(row_doc['dokter']).strip()
                # Pastikan formatnya dr. Xxx (pakai helper function kalau mau, atau manual di sini)
                clean_name = raw_name.lower().replace("dr.", "").replace("dr ", "").strip().title()
                r_dokter = f"dr. {clean_name}"
                # ----------------------------------------
                
                r_prefix = str(row_doc.get('prefix', r_poli[:4].upper())).strip()
            else:
                r_poli = "Poli Umum"; r_dokter = "dr. Contoh"; r_prefix="UMUM"

            r_nama_pasien = fake.name()
            r_date = date.today()
            
            dup = db.query(storage.TabelGabungan).filter(storage.TabelGabungan.nama_pasien == r_nama_pasien, storage.TabelGabungan.dokter == r_dokter, storage.TabelGabungan.visit_date == r_date).first()
            if dup: continue 

            poli_obj = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == r_poli).first()
            if not poli_obj:
                poli_obj = storage.TabelPoli(poli=r_poli, prefix=r_prefix)
                db.add(poli_obj); db.commit()

            doc_obj = db.query(storage.TabelDokter).filter(storage.TabelDokter.dokter == r_dokter).first()
            if not doc_obj:
                final_doc_id = (db.query(storage.TabelDokter).count() + 1)
                formatted_doc_code = f"{poli_obj.prefix}-{final_doc_id:03d}"
                doc_obj = storage.TabelDokter(doctor_id=final_doc_id, dokter=r_dokter, poli=r_poli, practice_start_time=time(8,0), practice_end_time=time(16,0), doctor_code=formatted_doc_code, max_patients=20)
                db.add(doc_obj); db.commit()

            r_status = random.choices(["Menunggu", "Sedang Dilayani", "Selesai"], weights=[10, 10, 80])[0]
            t_chk, t_ent, t_fin = get_random_time_window()
            f_chk = t_chk
            f_ent = t_ent if r_status in ["Sedang Dilayani", "Selesai"] else None
            f_fin = t_fin if r_status == "Selesai" else None
            
            # [LOGIKA BARU] Pilih Catatan Acak Bahasa Indonesia
            if r_status == "Selesai":
                r_catatan = random.choice(contoh_catatan)
            else:
                r_catatan = None

            last_cnt = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == doc_obj.doctor_id, storage.TabelPelayanan.visit_date == r_date).count()
            seq = last_cnt + 1
            d_suf = doc_obj.doctor_code.split('-')[-1]
            q_str = f"{poli_obj.prefix}-{d_suf}-{seq:03d}"

            pel = storage.TabelPelayanan(nama_pasien=r_nama_pasien, poli=r_poli, dokter=doc_obj.dokter, doctor_id_ref=doc_obj.doctor_id, visit_date=r_date, checkin_time=f_chk, clinic_entry_time=f_ent, completion_time=f_fin, status_pelayanan=r_status, queue_number=q_str, queue_sequence=seq, catatan_medis=r_catatan)
            db.add(pel)
            gab = storage.TabelGabungan(nama_pasien=r_nama_pasien, poli=r_poli, prefix_poli=poli_obj.prefix, dokter=doc_obj.dokter, doctor_code=doc_obj.doctor_code, doctor_id=doc_obj.doctor_id, visit_date=r_date, checkin_time=f_chk, clinic_entry_time=f_ent, completion_time=f_fin, status_pelayanan=r_status, queue_number=q_str, queue_sequence=seq, catatan_medis=r_catatan)
            db.add(gab)
            imported_count += 1
            
        db.commit()
        return {"message": f"Sukses import {imported_count} data dengan catatan medis Indonesia."}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, detail=str(e))

# =================================================================
# 2. ANALYTICS
# =================================================================
@router_analytics.get("/comprehensive-report")
def get_comprehensive_analytics(db: Session = Depends(get_db)):
    query = db.query(storage.TabelPelayanan).all()
    all_doctors = db.query(storage.TabelDokter).all()
    
    if not query: return {"status": "No Data"}
    
    data = []
    for q in query:
        data.append({
            "poli": q.poli, "dokter": q.dokter, "doctor_id": q.doctor_id_ref,
            "checkin_time": pd.to_datetime(q.checkin_time) if q.checkin_time else None,
            "entry_time": pd.to_datetime(q.clinic_entry_time) if q.clinic_entry_time else None,
            "completion_time": pd.to_datetime(q.completion_time) if q.completion_time else None,
            "status": q.status_pelayanan
        })
    df = pd.DataFrame(data)
    
    df['wait_minutes'] = (df['entry_time'] - df['checkin_time']).dt.total_seconds() / 60
    df['service_minutes'] = (df['completion_time'] - df['entry_time']).dt.total_seconds() / 60
    df_valid_svc = df.dropna(subset=['service_minutes'])
    df_valid_wait = df.dropna(subset=['wait_minutes'])

    poli_volume = df['poli'].value_counts(ascending=True).to_dict()
    avg_svc_poli = df_valid_svc.groupby('poli')['service_minutes'].mean().round(1).sort_values(ascending=True).to_dict()
    avg_wait_poli = df_valid_wait.groupby('poli')['wait_minutes'].mean().round(1).sort_values(ascending=True).to_dict()
    
    peak_hours = {}
    if 'checkin_time' in df and not df['checkin_time'].isna().all():
        peak_hours = df['checkin_time'].dt.hour.value_counts().sort_index().to_dict()

    avg_svc_doc = df_valid_svc.groupby('dokter')['service_minutes'].mean()
    staff_eff = {}
    if not avg_svc_doc.empty:
        avg_svc_doc = avg_svc_doc[avg_svc_doc > 0]
        staff_eff = (60 / avg_svc_doc).round(1).sort_values(ascending=True).to_dict()

    summary = df.groupby('poli').agg(count=('status','count'), speed=('service_minutes','mean')).dropna()
    corr_coef = round(summary['count'].corr(summary['speed']), 2) if len(summary) > 1 else 0

    active_ids = df['doctor_id'].unique().tolist()
    idle_docs = [f"{d.dokter} (ID:{d.doctor_id})" for d in all_doctors if d.doctor_id not in active_ids]
    # Gabungkan semua catatan medis yang tidak kosong
    all_notes_text = " ".join([str(q.catatan_medis) for q in query if q.catatan_medis])
    return {
        "poli_volume": poli_volume, "poli_speed": avg_svc_poli, "poli_wait": avg_wait_poli,
        "peak_hours": peak_hours, "staff_effectiveness": staff_eff,
        "correlation": {"coef": corr_coef},
        "ghost_rate": round((len(df[df['status']=='Terdaftar'])/len(df)*100), 1),
        "idle_doctors": idle_docs,
        "medical_notes_text": all_notes_text,
        "total_active_doctors": len(active_ids),
        "total_doctors_registered": len(all_doctors)
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
    pol = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == p.poli).first()
    if not pol: raise HTTPException(404, "Poli not found")
    if db.query(storage.TabelDokter).filter(storage.TabelDokter.dokter == p.dokter).first(): raise HTTPException(400, "Name exists")
    
    fid = p.doctor_id or ((db.query(storage.TabelDokter).count() + 1))
    last = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == p.poli).order_by(storage.TabelDokter.doctor_id.desc()).first()
    nxt = int(last.doctor_code.split('-')[-1]) + 1 if last else 1
    code = f"{pol.prefix}-{nxt:03d}"
    
    ts = datetime.strptime(p.practice_start_time, "%H:%M").time()
    te = datetime.strptime(p.practice_end_time, "%H:%M").time()
    
    new = storage.TabelDokter(doctor_id=fid, dokter=p.dokter, poli=p.poli, practice_start_time=ts, practice_end_time=te, doctor_code=code, max_patients=p.max_patients)
    db.add(new); db.commit(); db.refresh(new)
    return new

@router_admin.put("/doctors/{id}", response_model=schemas.DoctorSchema)
def update_doc(id: int, p: schemas.DoctorUpdate, db: Session = Depends(get_db)):
    d = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == id).first()
    if not d: raise HTTPException(404, "Not found")
    if p.dokter: d.dokter = p.dokter
    if p.max_patients: d.max_patients = p.max_patients
    db.commit(); db.refresh(d); return d

@router_admin.delete("/doctors/{id}")
def del_doc(id: int, db: Session = Depends(get_db)):
    d = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == id).first()
    if not d: raise HTTPException(404, "Not found")
    db.delete(d); db.commit(); return {"msg": "Deleted"}

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
def register(p: schemas.RegistrationFinal, db: Session = Depends(get_db)):
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
    
    # 5. Simpan ke Database
    new = storage.TabelPelayanan(
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
    s = None
    val = p.barcode_data.strip()
    if val.isdigit(): s = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.id == int(val)).first()
    if not s: s = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.queue_number == val).first()
    if not s: raise HTTPException(404, "Not found")
    
    msg = ""
    if p.location == "arrival":
        if s.checkin_time: return {"status":"Info", "message":"Already checkin", "current_status":s.status_pelayanan}
        s.checkin_time = datetime.now(); s.status_pelayanan = "Menunggu"; msg="Checkin OK"
    elif p.location == "clinic":
        if not s.checkin_time: raise HTTPException(400, "Belum Checkin")
        s.clinic_entry_time = datetime.now(); s.status_pelayanan = "Sedang Dilayani"; msg="Masuk Poli"
    elif p.location == "finish":
        if not s.clinic_entry_time: raise HTTPException(400, "Belum Masuk Poli")
        s.completion_time = datetime.now(); s.status_pelayanan = "Selesai"; msg="Selesai"
    
    gab = db.query(storage.TabelGabungan).filter(storage.TabelGabungan.id == s.id).first()
    if gab: 
        gab.checkin_time=s.checkin_time; gab.clinic_entry_time=s.clinic_entry_time; gab.completion_time=s.completion_time; gab.status_pelayanan=s.status_pelayanan
    db.commit()
    return {"status": "Success", "message": msg, "current_status": s.status_pelayanan}

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

app.include_router(router_admin)
app.include_router(router_public)
app.include_router(router_ops)
app.include_router(router_monitor)
app.include_router(router_analytics)