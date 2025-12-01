from fastapi import FastAPI, Depends, HTTPException, APIRouter, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time
import pandas as pd
import numpy as np
import re

# Pastikan file storage.py, schemas.py, csv_utils.py ada di folder yang sama
import storage
import schemas
import csv_utils

# Inisialisasi Database
storage.init_db()

app = FastAPI(title="Sistem RS: Barcode, Queue & Analytics")

# Setup Router
router_admin = APIRouter(prefix="/admin", tags=["Admin: Manajemen Data"])
router_public = APIRouter(prefix="/public", tags=["Public: Pendaftaran"])
router_ops = APIRouter(prefix="/ops", tags=["Medical Staff: Operasional"])
router_monitor = APIRouter(prefix="/monitor", tags=["Admin: Monitoring"])
router_analytics = APIRouter(prefix="/analytics", tags=["Data Science & Insights"])

# Dependency Database
def get_db():
    db = storage.SessionLocal()
    try: yield db
    finally: db.close()

# --- HELPER: Parsing Waktu Pintar (Untuk Import CSV) ---
def parse_datetime_smart(date_val, time_val=None):
    if pd.isna(date_val) or str(date_val).strip() == "": return None
    try:
        d_obj = pd.to_datetime(str(date_val)).date()
        # Jika jam kosong, set ke 00:00
        if pd.isna(time_val) or str(time_val).strip() == "": 
            return datetime.combine(d_obj, time(0,0))
        # Parse jam
        t_obj = pd.to_datetime(str(time_val).strip()).time()
        return datetime.combine(d_obj, t_obj)
    except: return None

# =================================================================
# 1. ADMIN: IMPORT DATA (CSV) - DENGAN REGEX FIX
# =================================================================
@router_admin.get("/import-random-data")
def import_random_data(count: int = 10, db: Session = Depends(get_db)):
    try:
        df = csv_utils.get_merged_random_data(count)
        imported = 0
        
        for _, row in df.iterrows():
            # A. Poli
            poli_clean = str(row['poli']).strip()
            if not poli_clean: continue
            
            poli_obj = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == poli_clean).first()
            if not poli_obj:
                # Ambil prefix dari CSV atau generate dari nama
                raw_p = row.get('prefix', 'POL')
                clean_p = ''.join(filter(str.isalpha, str(raw_p))).upper()[:5]
                poli_obj = storage.TabelPoli(poli=poli_clean, prefix=clean_p)
                db.add(poli_obj); db.commit()
            
            # B. Dokter
            try: csv_doc_id = int(float(row['doctor_id']))
            except: csv_doc_id = 0
            
            doc_obj = None
            if csv_doc_id > 0: 
                doc_obj = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == csv_doc_id).first()
            
            if not doc_obj:
                final_doc_id = csv_doc_id if csv_doc_id > 0 else (db.query(storage.TabelDokter).count() + 1)
                
                # --- FIX KODE DOKTER (REGEX) ---
                # Mengambil angka dari string CSV (misal "A-1" -> 1)
                raw_code_str = str(row['doctor_code'])
                found_numbers = re.findall(r'\d+', raw_code_str)
                code_number = int(found_numbers[-1]) if found_numbers else final_doc_id
                
                # Format ulang: PREFIX-00X
                formatted_doc_code = f"{poli_obj.prefix}-{code_number:03d}"

                try:
                    t_start = pd.to_datetime(str(row['practice_start_time'])).time()
                    t_end = pd.to_datetime(str(row['practice_end_time'])).time()
                except: 
                    t_start, t_end = time(8,0), time(16,0)

                doc_obj = storage.TabelDokter(
                    doctor_id=final_doc_id, dokter=row['dokter'], poli=poli_clean,
                    practice_start_time=t_start, practice_end_time=t_end,
                    doctor_code=formatted_doc_code, max_patients=20
                )
                db.add(doc_obj); db.commit()

            # C. Pelayanan
            real_checkin = parse_datetime_smart(row['visit_date'], row['checkin_time'])
            real_entry = parse_datetime_smart(row['visit_date'], row['clinic_entry_time'])
            real_completion = parse_datetime_smart(row['visit_date'], row['completion_time'])
            real_visit_date = real_checkin.date() if real_checkin else datetime.now().date()
            
            # Tentukan Status
            real_status = row['status_pelayanan']
            if not real_status:
                if real_completion: real_status = "Selesai"
                elif real_entry: real_status = "Melayani"
                elif real_checkin: real_status = "Menunggu"
                else: real_status = "Terdaftar"

            # Tentukan Nomor Antrean (String & Int)
            csv_queue_str = str(row['queue_number']) if row['queue_number'] else ""
            try: real_seq = int(float(row['queue_sequence']))
            except: real_seq = 999
            if real_seq > 999: real_seq = 999 # Batas 3 digit
            
            if not csv_queue_str or csv_queue_str == "nan":
                 doc_suffix = doc_obj.doctor_code.split('-')[-1]
                 csv_queue_str = f"{poli_obj.prefix}-{doc_suffix}-{real_seq:03d}"

            # Simpan
            pelayanan = storage.TabelPelayanan(
                nama_pasien=row['nama_pasien'] or "Pasien", poli=poli_clean, dokter=doc_obj.dokter,
                doctor_id_ref=doc_obj.doctor_id, visit_date=real_visit_date,
                checkin_time=real_checkin, clinic_entry_time=real_entry, completion_time=real_completion,
                status_pelayanan=real_status, queue_number=csv_queue_str, queue_sequence=real_seq     
            )
            db.add(pelayanan)
            
            gabungan = storage.TabelGabungan(
                nama_pasien=row['nama_pasien'] or "Pasien", poli=poli_clean, prefix_poli=poli_obj.prefix,
                dokter=doc_obj.dokter, doctor_code=doc_obj.doctor_code, doctor_id=doc_obj.doctor_id,
                visit_date=real_visit_date, checkin_time=real_checkin, clinic_entry_time=real_entry,
                completion_time=real_completion, status_pelayanan=real_status,
                queue_number=csv_queue_str, queue_sequence=real_seq     
            )
            db.add(gabungan)
            imported += 1
            
        db.commit()
        return {"message": f"Sukses import {imported} data."}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, detail=str(e))

# =================================================================
# 2. ADMIN: MANAJEMEN POLI (CRUD)
# =================================================================
@router_admin.post("/polis", response_model=schemas.PoliSchema)
def create_poli(payload: schemas.PoliCreate, db: Session = Depends(get_db)):
    clean_poli = payload.poli.strip()
    clean_prefix = payload.prefix.strip().upper()
    
    if db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == clean_poli).first():
        raise HTTPException(400, f"Nama Poli '{clean_poli}' sudah ada.")
    
    existing_prefix = db.query(storage.TabelPoli).filter(storage.TabelPoli.prefix == clean_prefix).first()
    if existing_prefix:
        raise HTTPException(400, f"Prefix '{clean_prefix}' sudah digunakan oleh '{existing_prefix.poli}'.")

    new_poli = storage.TabelPoli(poli=clean_poli, prefix=clean_prefix)
    db.add(new_poli); db.commit(); db.refresh(new_poli)
    try: csv_utils.append_to_csv("tabel_poli_normal.csv", {"poli": new_poli.poli, "prefix": new_poli.prefix})
    except: pass
    return new_poli

@router_admin.put("/polis/{poli_name}", response_model=schemas.PoliSchema)
def update_poli(poli_name: str, payload: schemas.PoliCreate, db: Session = Depends(get_db)):
    old_poli = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == poli_name).first()
    if not old_poli: raise HTTPException(404, "Poli lama tidak ditemukan.")
    
    clean_new_name = payload.poli.strip()
    clean_new_prefix = payload.prefix.strip().upper()

    # Cek Prefix Unik (exclude diri sendiri)
    ex_pre = db.query(storage.TabelPoli).filter(storage.TabelPoli.prefix == clean_new_prefix).first()
    if ex_pre and ex_pre.poli != poli_name:
        raise HTTPException(400, f"Prefix '{clean_new_prefix}' sudah dipakai '{ex_pre.poli}'.")

    # Skenario 1: Ganti Nama (Rename) -> Migrasi Data
    if clean_new_name != poli_name:
        if db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == clean_new_name).first():
            raise HTTPException(400, f"Nama Poli '{clean_new_name}' sudah ada.")
            
        new_poli = storage.TabelPoli(poli=clean_new_name, prefix=clean_new_prefix)
        db.add(new_poli); db.commit()
        
        # Pindahkan Dokter & Update Kode
        docs = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()
        for d in docs:
            d.poli = clean_new_name
            try: num = d.doctor_code.split('-')[-1]
            except: num = "000"
            d.doctor_code = f"{clean_new_prefix}-{num}"
            
        # Pindahkan History
        db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.poli == poli_name).update({storage.TabelPelayanan.poli: clean_new_name}, synchronize_session=False)
        db.query(storage.TabelGabungan).filter(storage.TabelGabungan.poli == poli_name).update({storage.TabelGabungan.poli: clean_new_name, storage.TabelGabungan.prefix_poli: clean_new_prefix}, synchronize_session=False)
        
        db.delete(old_poli); db.commit()
        return new_poli

    # Skenario 2: Hanya Ganti Prefix
    else:
        old_poli.prefix = clean_new_prefix
        docs = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()
        for d in docs:
            try: num = d.doctor_code.split('-')[-1]
            except: num = "000"
            d.doctor_code = f"{clean_new_prefix}-{num}"
            
        db.query(storage.TabelGabungan).filter(storage.TabelGabungan.poli == poli_name).update({storage.TabelGabungan.prefix_poli: clean_new_prefix}, synchronize_session=False)
        db.commit(); db.refresh(old_poli)
        return old_poli

@router_admin.delete("/polis/{poli_name}")
def delete_poli(poli_name: str, db: Session = Depends(get_db)):
    poli = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == poli_name).first()
    if not poli: raise HTTPException(404, "Poli tidak ditemukan")
    
    # Cascade Delete
    docs = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()
    for doc in docs:
        db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == doc.doctor_id).delete()
        db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == doc.doctor_id).delete()
        db.delete(doc)
    db.delete(poli); db.commit()
    return {"message": "Poli terhapus."}

# =================================================================
# 3. ADMIN: MANAJEMEN DOKTER (CRUD)
# =================================================================
@router_admin.get("/doctors", response_model=List[schemas.DoctorSchema])
def get_all_doctors(db: Session = Depends(get_db)):
    return db.query(storage.TabelDokter).all()

@router_admin.get("/doctors/{doctor_id}", response_model=schemas.DoctorSchema)
def get_single_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == doctor_id).first()
    if not doc: raise HTTPException(404, "Dokter tidak ditemukan")
    return doc

@router_admin.post("/doctors", response_model=schemas.DoctorSchema)
def add_doctor(payload: schemas.DoctorCreate, db: Session = Depends(get_db)):
    poli = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == payload.poli).first()
    if not poli: raise HTTPException(404, "Poli tidak ditemukan.")
    
    if db.query(storage.TabelDokter).filter(storage.TabelDokter.dokter == payload.dokter).first():
        raise HTTPException(400, f"Dokter '{payload.dokter}' sudah ada.")

    final_id = payload.doctor_id or ((db.query(storage.TabelDokter).order_by(storage.TabelDokter.doctor_id.desc()).first().doctor_id + 1) if db.query(storage.TabelDokter).first() else 1)
    
    last_doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == payload.poli).order_by(storage.TabelDokter.doctor_id.desc()).first()
    next_num = 1
    if last_doc:
        try: next_num = int(last_doc.doctor_code.split('-')[-1]) + 1
        except: next_num = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == payload.poli).count() + 1
    new_code = f"{poli.prefix}-{next_num:03d}"
    
    try: t_start, t_end = datetime.strptime(payload.practice_start_time, "%H:%M").time(), datetime.strptime(payload.practice_end_time, "%H:%M").time()
    except: raise HTTPException(400, "Format waktu salah HH:MM")

    new_doc = storage.TabelDokter(doctor_id=final_id, dokter=payload.dokter, poli=payload.poli, practice_start_time=t_start, practice_end_time=t_end, doctor_code=new_code, max_patients=payload.max_patients)
    db.add(new_doc); db.commit(); db.refresh(new_doc)
    
    try: csv_utils.append_to_csv("tabel_dokter_normal.csv", {"dokter": new_doc.dokter, "doctor_id": new_doc.doctor_id, "practice_start_time": payload.practice_start_time, "practice_end_time": payload.practice_end_time, "doctor_code": new_code, "max_patients": new_doc.max_patients, "poli": new_doc.poli, "prefix": poli.prefix})
    except: pass
    return new_doc

@router_admin.put("/doctors/{doctor_id}", response_model=schemas.DoctorSchema)
def update_doctor(doctor_id: int, payload: schemas.DoctorUpdate, db: Session = Depends(get_db)):
    doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == doctor_id).first()
    if not doc: raise HTTPException(404, "Dokter tidak ditemukan")
    
    # Update Nama -> Cascade ke History
    if payload.dokter and payload.dokter != doc.dokter:
        db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == doctor_id).update({storage.TabelPelayanan.dokter: payload.dokter}, synchronize_session=False)
        db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == doctor_id).update({storage.TabelGabungan.dokter: payload.dokter}, synchronize_session=False)
        doc.dokter = payload.dokter

    if payload.max_patients: doc.max_patients = payload.max_patients
    if payload.practice_start_time:
        try: doc.practice_start_time = datetime.strptime(payload.practice_start_time, "%H:%M").time()
        except: pass
    if payload.practice_end_time:
        try: doc.practice_end_time = datetime.strptime(payload.practice_end_time, "%H:%M").time()
        except: pass
        
    # Pindah Poli -> Update Code & History
    if payload.poli and payload.poli != doc.poli:
        poli_new = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == payload.poli).first()
        if poli_new:
            doc.poli = payload.poli
            last_doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == payload.poli).order_by(storage.TabelDokter.doctor_id.desc()).first()
            next_n = int(last_doc.doctor_code.split('-')[-1]) + 1 if last_doc else 1
            doc.doctor_code = f"{poli_new.prefix}-{next_n:03d}"
            
            db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == doctor_id).update({storage.TabelPelayanan.poli: payload.poli}, synchronize_session=False)
            db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == doctor_id).update({storage.TabelGabungan.poli: payload.poli, storage.TabelGabungan.prefix_poli: poli_new.prefix}, synchronize_session=False)

    db.commit(); db.refresh(doc)
    return doc

@router_admin.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == doctor_id).first()
    if not doc: raise HTTPException(404, "Dokter tidak ditemukan")
    db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == doctor_id).delete()
    db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == doctor_id).delete()
    db.delete(doc); db.commit()
    return {"message": "Dokter dihapus."}

# =================================================================
# 4. PUBLIC & OPS
# =================================================================
@router_public.get("/polis", response_model=List[schemas.PoliSchema])
def get_public_polis(db: Session = Depends(get_db)): return db.query(storage.TabelPoli).all()

@router_public.get("/available-doctors", response_model=List[schemas.DoctorSchema])
def get_public_doctors(poli_name: str, visit_date: date, db: Session = Depends(get_db)): return db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()

@router_public.get("/find-ticket", response_model=List[schemas.PelayananSchema])
def find_ticket_by_name(nama: str, target_date: Optional[date] = None, db: Session = Depends(get_db)):
    query = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.nama_pasien.ilike(f"%{nama}%"))
    if target_date: query = query.filter(storage.TabelPelayanan.visit_date == target_date)
    tickets = query.order_by(storage.TabelPelayanan.visit_date.desc()).all()
    if not tickets: raise HTTPException(404, "Tiket tidak ditemukan.")
    return tickets

@router_public.post("/submit", response_model=schemas.PelayananSchema)
def register_patient(payload: schemas.RegistrationFinal, db: Session = Depends(get_db)):
    if payload.visit_date < date.today(): raise HTTPException(400, "Tanggal tidak boleh masa lalu.")
    
    dokter = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == payload.doctor_id).first()
    if not dokter: raise HTTPException(404, "Dokter tidak ditemukan")
    if dokter.poli != payload.poli: raise HTTPException(400, f"Dokter tidak ada di {payload.poli}")
    
    last_q = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == payload.doctor_id, storage.TabelPelayanan.visit_date == payload.visit_date).order_by(storage.TabelPelayanan.queue_sequence.desc()).first()
    next_seq = (last_q.queue_sequence + 1) if last_q else 1
    if next_seq > 999: raise HTTPException(400, "Kuota penuh.")

    try: doc_code_only = dokter.doctor_code.split('-')[-1]
    except: doc_code_only = "000"
    formatted_queue = f"{dokter.poli_rel.prefix}-{doc_code_only}-{next_seq:03d}"

    pelayanan = storage.TabelPelayanan(
        nama_pasien=payload.nama_pasien, poli=dokter.poli, dokter=dokter.dokter,
        doctor_id_ref=dokter.doctor_id, visit_date=payload.visit_date,
        checkin_time=None, status_pelayanan="Terdaftar", 
        queue_number=formatted_queue, queue_sequence=next_seq
    )
    db.add(pelayanan)
    gabungan = storage.TabelGabungan(
        nama_pasien=payload.nama_pasien, poli=dokter.poli, prefix_poli=dokter.poli_rel.prefix,
        dokter=dokter.dokter, doctor_code=dokter.doctor_code, doctor_id=dokter.doctor_id,
        visit_date=payload.visit_date, checkin_time=None, status_pelayanan="Terdaftar", 
        queue_number=formatted_queue, queue_sequence=next_seq
    )
    db.add(gabungan); db.commit(); db.refresh(pelayanan)
    return pelayanan

@router_ops.post("/scan-barcode")
def scan_barcode_action(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    srv = None
    clean_input = payload.barcode_data.strip()
    if clean_input.isdigit(): srv = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.id == int(clean_input)).first()
    if not srv: srv = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.queue_number == clean_input).first()
    if not srv: raise HTTPException(404, "Data Tiket tidak ditemukan.")
    
    msg = ""
    if payload.location == "arrival":
        if srv.checkin_time: return {"status": "Info", "message": "Sudah check-in."}
        srv.checkin_time = datetime.now(); srv.status_pelayanan = "Menunggu"; msg = "Check-in OK."
    elif payload.location == "clinic":
        if not srv.checkin_time: raise HTTPException(400, "Belum check-in!"); 
        srv.clinic_entry_time = datetime.now(); srv.status_pelayanan = "Melayani"; msg = "Masuk poli."
    elif payload.location == "finish":
        if not srv.clinic_entry_time: raise HTTPException(400, "Belum masuk poli!"); 
        srv.completion_time = datetime.now(); srv.status_pelayanan = "Selesai"; msg = "Selesai."
    else: raise HTTPException(400, "Lokasi salah.")
    
    gab = db.query(storage.TabelGabungan).filter(storage.TabelGabungan.id == srv.id).first() 
    if gab: gab.checkin_time, gab.clinic_entry_time, gab.completion_time, gab.status_pelayanan = srv.checkin_time, srv.clinic_entry_time, srv.completion_time, srv.status_pelayanan
    db.commit()
    return {"status": "Success", "message": msg, "current_status": srv.status_pelayanan}

# --- ANALYTICS ---
@router_analytics.get("/comprehensive-report")
def get_comprehensive_analytics(db: Session = Depends(get_db)):
    query = db.query(storage.TabelPelayanan).all()
    all_doctors = db.query(storage.TabelDokter).all()
    if not query: return {"status": "No Data"}
    
    data = []
    for q in query:
        data.append({
            "poli": q.poli, "dokter": q.dokter,
            "entry_time": pd.to_datetime(q.clinic_entry_time) if q.clinic_entry_time else None,
            "completion_time": pd.to_datetime(q.completion_time) if q.completion_time else None,
            "status": q.status_pelayanan
        })
    df = pd.DataFrame(data)
    df['service_minutes'] = (df['completion_time'] - df['entry_time']).dt.total_seconds() / 60

    poli_volume = df['poli'].value_counts(ascending=True).to_dict()
    df_valid = df.dropna(subset=['service_minutes'])
    avg_svc_poli = df_valid.groupby('poli')['service_minutes'].mean().round(1).sort_values(ascending=True).to_dict()
    
    avg_svc_doc = df_valid.groupby('dokter')['service_minutes'].mean()
    staff_eff = (60 / avg_svc_doc[avg_svc_doc > 0]).round(1).sort_values(ascending=True).to_dict() if not avg_svc_doc.empty else {}

    active_docs = df['dokter'].unique().tolist()
    idle_docs = [d.dokter for d in all_doctors if d.dokter not in active_docs]

    summary = df.groupby('poli').agg(count=('status','count'), speed=('service_minutes','mean')).dropna()
    corr_coef = round(summary['count'].corr(summary['speed']), 2) if len(summary) > 1 else 0
    
    return {
        "poli_volume": poli_volume, "poli_speed": avg_svc_poli, "staff_effectiveness": staff_eff,
        "correlation": {"coef": corr_coef},
        "ghost_rate": round((len(df[df['status']=='Terdaftar'])/len(df)*100), 1),
        "idle_doctors": idle_docs, "total_active_doctors": len(active_docs), "total_doctors_registered": len(all_doctors)
    }

@router_monitor.get("/dashboard", response_model=List[schemas.ClinicStats])
def get_dashboard(db: Session = Depends(get_db), target_date: date = None):
    filter_date = target_date if target_date else datetime.now().date()
    stats = []
    polis = db.query(storage.TabelPoli).all()
    for p in polis:
        doc_count = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == p.poli).count()
        services = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.poli == p.poli, storage.TabelPelayanan.visit_date == filter_date).all()
        stats.append({
            "poli_name": p.poli, "total_doctors": doc_count, "total_patients_today": len(services),
            "patients_waiting": sum(1 for s in services if s.status_pelayanan == "Menunggu"),
            "patients_being_served": sum(1 for s in services if s.status_pelayanan == "Melayani"),
            "patients_finished": sum(1 for s in services if s.status_pelayanan == "Selesai")
        })
    return stats

@router_monitor.get("/queue-board", response_model=List[schemas.PelayananSchema])
def get_queue_board(db: Session = Depends(get_db)):
    today = datetime.now().date()
    queues = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.visit_date == today, storage.TabelPelayanan.status_pelayanan.in_(["Menunggu", "Melayani"])).order_by(storage.TabelPelayanan.status_pelayanan.asc(), storage.TabelPelayanan.queue_sequence.asc()).all()
    return queues

app.include_router(router_admin)
app.include_router(router_public)
app.include_router(router_ops)
app.include_router(router_monitor)
app.include_router(router_analytics)