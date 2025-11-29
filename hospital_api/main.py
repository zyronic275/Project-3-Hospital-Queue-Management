from fastapi import FastAPI, Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, date, time
import pandas as pd
import numpy as np

# Import modul lokal
import storage
import schemas
import csv_utils

# Init Database
storage.init_db()

app = FastAPI(title="Sistem Manajemen Antrean RS Terintegrasi")

# Setup Router
router_admin = APIRouter(prefix="/admin", tags=["Admin: Manajemen Data"])
router_public = APIRouter(prefix="/public",tags=["Public: Pendaftaran"])
router_ops = APIRouter(prefix="/ops", tags=["Medical Staff: Operasional"])
router_monitor = APIRouter(prefix="/monitor", tags=["Admin: Monitoring & Dashboard"])

# Dependency Database
def get_db():
    db = storage.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- HELPER: Parsing Waktu Pintar ---
def parse_datetime_smart(date_val, time_val=None):
    if pd.isna(date_val) or str(date_val).strip() == "": return None
    try:
        d_obj = pd.to_datetime(str(date_val)).date()
        if pd.isna(time_val) or str(time_val).strip() == "": return datetime.combine(d_obj, time(0,0))
        t_obj = pd.to_datetime(str(time_val).strip()).time()
        return datetime.combine(d_obj, t_obj)
    except: return None

# =================================================================
# 1. ADMIN: IMPORT DATA (CSV)
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
                poli_obj = storage.TabelPoli(poli=poli_clean, prefix=row.get('prefix', 'POL'))
                db.add(poli_obj); db.commit()
            
            # B. Dokter
            try: csv_doc_id = int(float(row['doctor_id']))
            except: csv_doc_id = 0
            
            doc_obj = None
            if csv_doc_id > 0: 
                doc_obj = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == csv_doc_id).first()
            
            if not doc_obj:
                final_doc_id = csv_doc_id if csv_doc_id > 0 else (db.query(storage.TabelDokter).count() + 1)
                
                # Format Code: PREFIX-ID
                try: raw_code_num = int(float(row['doctor_code'])) if row['doctor_code'] else final_doc_id
                except: raw_code_num = final_doc_id
                formatted_doc_code = f"{poli_obj.prefix}-{raw_code_num:03d}"

                try:
                    t_start = pd.to_datetime(str(row['practice_start_time'])).time()
                    t_end = pd.to_datetime(str(row['practice_end_time'])).time()
                except: t_start, t_end = time(8,0), time(16,0)

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
            
            real_status = row['status_pelayanan']
            if not real_status:
                if real_completion: real_status = "Selesai"
                elif real_entry: real_status = "Melayani"
                else: real_status = "Menunggu"

            # Ambil Sequence & String Queue
            csv_queue_str = str(row['queue_number']) if row['queue_number'] else ""
            try: real_seq = int(float(row['queue_sequence']))
            except: real_seq = 999
            
            if not csv_queue_str or csv_queue_str == "nan":
                 # Format ulang jika kosong
                 doc_suffix = doc_obj.doctor_code.split('-')[-1]
                 csv_queue_str = f"{poli_obj.prefix}-{doc_suffix}-{real_seq:03d}"

            pelayanan = storage.TabelPelayanan(
                nama_pasien=row['nama_pasien'] or "Pasien", poli=poli_clean, dokter=doc_obj.dokter,
                doctor_id_ref=doc_obj.doctor_id, visit_date=real_visit_date,
                checkin_time=real_checkin, clinic_entry_time=real_entry, completion_time=real_completion,
                status_pelayanan=real_status, 
                queue_number=csv_queue_str, 
                queue_sequence=real_seq     
            )
            db.add(pelayanan)
            
            gabungan = storage.TabelGabungan(
                nama_pasien=row['nama_pasien'] or "Pasien", poli=poli_clean, prefix_poli=poli_obj.prefix,
                dokter=doc_obj.dokter, doctor_code=doc_obj.doctor_code, doctor_id=doc_obj.doctor_id,
                visit_date=real_visit_date, checkin_time=real_checkin, clinic_entry_time=real_entry,
                completion_time=real_completion, status_pelayanan=real_status,
                queue_number=csv_queue_str, 
                queue_sequence=real_seq     
            )
            db.add(gabungan)
            imported += 1
            
        db.commit()
        return {"message": f"Sukses import {imported} data."}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, detail=str(e))

# =================================================================
# 2. ADMIN: MANAJEMEN POLI
# =================================================================

@router_admin.post("/polis", response_model=schemas.PoliSchema)
def create_poli(payload: schemas.PoliCreate, db: Session = Depends(get_db)):
    clean_poli = payload.poli.strip()
    clean_prefix = payload.prefix.strip().upper()

    if db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == clean_poli).first():
        raise HTTPException(400, f"Poli '{clean_poli}' sudah ada.")
    if db.query(storage.TabelPoli).filter(storage.TabelPoli.prefix == clean_prefix).first():
        raise HTTPException(400, f"Prefix '{clean_prefix}' sudah digunakan.")

    new_poli = storage.TabelPoli(poli=clean_poli, prefix=clean_prefix)
    db.add(new_poli); db.commit(); db.refresh(new_poli)
    
    try: csv_utils.append_to_csv("tabel_poli_normal.csv", {"poli": new_poli.poli, "prefix": new_poli.prefix})
    except: pass
    
    return new_poli

@router_admin.delete("/polis/{poli_name}")
def delete_poli(poli_name: str, db: Session = Depends(get_db)):
    poli = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == poli_name).first()
    if not poli: raise HTTPException(404, "Poli tidak ditemukan")

    doctors = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()
    for doc in doctors:
        db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == doc.doctor_id).delete()
        db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == doc.doctor_id).delete()
        db.delete(doc)

    db.delete(poli)
    db.commit()
    return {"message": f"Poli {poli_name} beserta dokter dan riwayatnya berhasil dihapus."}

# =================================================================
# 3. ADMIN: MANAJEMEN DOKTER
# =================================================================

@router_admin.post("/doctors", response_model=schemas.DoctorSchema)
def add_doctor(payload: schemas.DoctorCreate, db: Session = Depends(get_db)):
    # Cek Poli Wajib Ada
    poli = db.query(storage.TabelPoli).filter(storage.TabelPoli.poli == payload.poli).first()
    if not poli: raise HTTPException(404, f"Poli '{payload.poli}' tidak ditemukan. Buat poli dahulu.")
    
    # Auto ID
    final_id = payload.doctor_id
    if not final_id:
        last = db.query(storage.TabelDokter).order_by(storage.TabelDokter.doctor_id.desc()).first()
        final_id = (last.doctor_id + 1) if last else 1

    # Auto Code (Cari ID terakhir di poli tersebut + 1)
    last_doc_in_poli = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == payload.poli).order_by(storage.TabelDokter.doctor_id.desc()).first()
    next_num = 1
    if last_doc_in_poli:
        try: next_num = int(last_doc_in_poli.doctor_code.split('-')[-1]) + 1
        except: next_num = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == payload.poli).count() + 1
            
    new_code = f"{poli.prefix}-{next_num:03d}"
    
    try:
        t_start = datetime.strptime(payload.practice_start_time, "%H:%M").time()
        t_end = datetime.strptime(payload.practice_end_time, "%H:%M").time()
    except: raise HTTPException(400, "Format waktu salah (HH:MM)")

    new_doc = storage.TabelDokter(
        doctor_id=final_id, dokter=payload.dokter, poli=payload.poli,
        practice_start_time=t_start, practice_end_time=t_end,
        doctor_code=new_code, max_patients=payload.max_patients
    )
    db.add(new_doc); db.commit(); db.refresh(new_doc)
    
    try:
        csv_utils.append_to_csv("tabel_dokter_normal.csv", {
            "dokter": new_doc.dokter, "doctor_id": new_doc.doctor_id,
            "practice_start_time": payload.practice_start_time, "practice_end_time": payload.practice_end_time,
            "doctor_code": new_code, "max_patients": new_doc.max_patients, "poli": new_doc.poli
        })
    except: pass
    return new_doc

@router_admin.put("/doctors/{doctor_id}", response_model=schemas.DoctorSchema)
def update_doctor(doctor_id: int, payload: schemas.DoctorUpdate, db: Session = Depends(get_db)):
    doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == doctor_id).first()
    if not doc: raise HTTPException(404, "Dokter tidak ditemukan")
    
    if payload.dokter: doc.dokter = payload.dokter
    if payload.max_patients: doc.max_patients = payload.max_patients
    if payload.practice_start_time:
        try: doc.practice_start_time = datetime.strptime(payload.practice_start_time, "%H:%M").time()
        except: pass
    if payload.practice_end_time:
        try: doc.practice_end_time = datetime.strptime(payload.practice_end_time, "%H:%M").time()
        except: pass
        
    db.commit(); db.refresh(doc)
    return doc

@router_admin.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doc = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == doctor_id).first()
    if not doc: raise HTTPException(404, "Dokter tidak ditemukan")
    
    # Cascade Delete
    db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.doctor_id_ref == doctor_id).delete()
    db.query(storage.TabelGabungan).filter(storage.TabelGabungan.doctor_id == doctor_id).delete()
    
    db.delete(doc); db.commit()
    return {"message": f"Dokter {doc.dokter} berhasil dihapus."}

# =================================================================
# 4. MONITORING
# =================================================================
@router_monitor.get("/dashboard", response_model=List[schemas.ClinicStats])
def get_dashboard(db: Session = Depends(get_db)):
    today = datetime.now().date()
    stats = []
    polis = db.query(storage.TabelPoli).all()
    for p in polis:
        doc_count = db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == p.poli).count()
        services = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.poli == p.poli, storage.TabelPelayanan.visit_date == today).all()
        stats.append({
            "poli_name": p.poli, "total_doctors": doc_count, "total_patients_today": len(services),
            "patients_waiting": sum(1 for s in services if s.status_pelayanan == "Menunggu"),
            "patients_being_served": sum(1 for s in services if s.status_pelayanan == "Melayani"),
            "patients_finished": sum(1 for s in services if s.status_pelayanan == "Selesai")
        })
    return stats

# =================================================================
# 5. PUBLIC & OPS
# =================================================================
@router_public.get("/polis", response_model=List[schemas.PoliSchema])
def get_public_polis(db: Session = Depends(get_db)):
    return db.query(storage.TabelPoli).all()

@router_public.get("/available-doctors", response_model=List[schemas.DoctorSchema])
def get_public_doctors(poli_name: str, visit_date: date, db: Session = Depends(get_db)):
    return db.query(storage.TabelDokter).filter(storage.TabelDokter.poli == poli_name).all()

@router_public.post("/submit", response_model=schemas.PelayananSchema)
def register_patient(payload: schemas.RegistrationFinal, db: Session = Depends(get_db)):
    # Cek Dokter
    dokter = db.query(storage.TabelDokter).filter(storage.TabelDokter.doctor_id == payload.doctor_id).first()
    if not dokter: raise HTTPException(404, "Dokter tidak ditemukan")
    
    # Validasi Poli (Fitur Baru)
    if dokter.poli != payload.poli:
        raise HTTPException(400, f"Dokter {dokter.dokter} tidak ada di {payload.poli} (tetapi di {dokter.poli}).")

    last_q = db.query(storage.TabelPelayanan).filter(
        storage.TabelPelayanan.doctor_id_ref == payload.doctor_id,
        storage.TabelPelayanan.visit_date == payload.visit_date
    ).order_by(storage.TabelPelayanan.queue_sequence.desc()).first()
    
    next_seq = (last_q.queue_sequence + 1) if last_q else 1
    
    try: doc_code_only = dokter.doctor_code.split('-')[-1]
    except: doc_code_only = "000"
        
    formatted_queue = f"{dokter.poli_rel.prefix}-{doc_code_only}-{next_seq:03d}"

    pelayanan = storage.TabelPelayanan(
        nama_pasien=payload.nama_pasien, poli=dokter.poli, dokter=dokter.dokter,
        doctor_id_ref=dokter.doctor_id, visit_date=payload.visit_date,
        checkin_time=datetime.now(), status_pelayanan="Menunggu", 
        queue_number=formatted_queue, queue_sequence=next_seq
    )
    db.add(pelayanan)
    
    gabungan = storage.TabelGabungan(
        nama_pasien=payload.nama_pasien, poli=dokter.poli, prefix_poli=dokter.poli_rel.prefix,
        dokter=dokter.dokter, doctor_code=dokter.doctor_code, doctor_id=dokter.doctor_id,
        visit_date=payload.visit_date, checkin_time=datetime.now(), status_pelayanan="Menunggu", 
        queue_number=formatted_queue, queue_sequence=next_seq
    )
    db.add(gabungan)
    db.commit(); db.refresh(pelayanan)
    return pelayanan

@router_ops.put("/update-status/{pelayanan_id}")
def update_ops_status(pelayanan_id: int, payload: schemas.UpdateQueueStatus, db: Session = Depends(get_db)):
    srv = db.query(storage.TabelPelayanan).filter(storage.TabelPelayanan.id == pelayanan_id).first()
    if not srv: raise HTTPException(404, "Data tidak ditemukan")
    if payload.action == "call_patient": srv.clinic_entry_time = datetime.now(); srv.status_pelayanan = "Melayani"
    elif payload.action == "finish": srv.completion_time = datetime.now(); srv.status_pelayanan = "Selesai"
    db.commit()
    return {"status": "Updated", "current_status": srv.status_pelayanan}

app.include_router(router_admin)
app.include_router(router_public)
app.include_router(router_ops)
app.include_router(router_monitor)