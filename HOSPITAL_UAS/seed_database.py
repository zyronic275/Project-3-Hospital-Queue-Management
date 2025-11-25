import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from modules.database import engine, SessionLocal, Base
from modules.master.models import Doctor, Service, GenderRestriction 
from modules.queue.models import Visit, VisitStatus # Import VisitStatus
from modules.auth.models import User, RoleEnum
from passlib.context import CryptContext
import hashlib
import datetime
from datetime import time
from sqlalchemy.orm import joinedload 

# --- KONSTANTA ---
CSV_FILE = "data_final_hospital.csv"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mapping untuk PREFIX, BATAS USIA, dan JENIS KELAMIN (Logika Klinis)
SERVICE_CODE_MAP = {'Poli Umum': 'U', 'Poli Gigi': 'G', 'Poli Mata': 'M', 'Poli Paru': 'R', 'Poli Anak': 'A', 'Poli Kandungan': 'K', 'Jantung': 'X'}
AGE_LIMIT_MAP = {
    'Poli Umum': {'min_age': 0, 'max_age': 100}, 'Poli Gigi': {'min_age': 5, 'max_age': 100}, 
    'Poli Mata': {'min_age': 0, 'max_age': 100}, 'Poli Paru': {'min_age': 10, 'max_age': 100}, 
    'Poli Anak': {'min_age': 0, 'max_age': 18}, 'Poli Kandungan': {'min_age': 15, 'max_age': 55},
    'Jantung': {'min_age': 0, 'max_age': 100},
}
GENDER_LIMIT_MAP = {
    'Poli Umum': GenderRestriction.NONE.value, 'Poli Gigi': GenderRestriction.NONE.value, 
    'Poli Mata': GenderRestriction.NONE.value, 'Poli Paru': GenderRestriction.NONE.value, 
    'Poli Anak': GenderRestriction.NONE.value, 'Poli Kandungan': GenderRestriction.FEMALE.value, 
    'Jantung': GenderRestriction.NONE.value,
}


# ------------------------------------------------------------
#  [ADMIN, SERVICES, DOCTORS SEEDING FUNCTIONS - SAMA SEPERTI SEBELUMNYA]
# ------------------------------------------------------------

def create_default_admin(db: Session):
    user = db.query(User).filter(User.username == "admin_rs").first()
    if user:
        print("☑️ Admin already exists")
        return
    admin = User(
        username="admin_rs",
        hashed_password=pwd_context.hash("password123"),
        role=RoleEnum.ADMIN,
        full_name="Super Admin Hospital"
    )
    db.add(admin)
    db.commit()
    print("✅ Admin created: admin_rs")


def seed_services_from_csv(db: Session):
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)
    df['clinic_code'] = df['clinic_code'].str.strip()
    df_service = df[["clinic_code"]].dropna().drop_duplicates()
    
    inserted = 0
    service_map = {} 
    
    for _, row in df_service.iterrows():
        clinic_name = str(row["clinic_code"]).strip()
        prefix = SERVICE_CODE_MAP.get(clinic_name, 'X')
        age_limits = AGE_LIMIT_MAP.get(clinic_name, {'min_age': 0, 'max_age': 100})
        gender_limit = GENDER_LIMIT_MAP.get(clinic_name, GenderRestriction.NONE.value)
        
        exists = db.query(Service).filter(Service.prefix == prefix).first()
        
        if not exists:
            new_service = Service(
                name=clinic_name,
                prefix=prefix,
                min_age=age_limits['min_age'],
                max_age=age_limits['max_age'],
                gender_restriction=gender_limit,
                is_active=True
            )
            db.add(new_service)
            db.flush() 
            service_map[clinic_name] = new_service.id
            inserted += 1
        else:
            exists.min_age = age_limits['min_age']
            exists.max_age = age_limits['max_age']
            exists.gender_restriction = gender_limit
            service_map[clinic_name] = exists.id
    
    db.commit()
    print(f"✅ Inserted {inserted} services")
    return service_map


def seed_doctors_from_csv(db: Session, service_map: dict):
    if not os.path.exists(CSV_FILE):
        return

    df = pd.read_csv(CSV_FILE)
    df['doctor_name'] = df['doctor_name'].str.strip()
    df['clinic_code'] = df['clinic_code'].str.strip()
    df_doc = df[["doctor_name", "clinic_code"]].dropna().drop_duplicates()

    inserted = 0
    doctor_code_counter = 1 
    
    start_time = time(8, 0, 0)
    end_time = time(17, 0, 0)
    
    for _, row in df_doc.iterrows():
        doctor_name = row["doctor_name"].strip()
        clinic_name = row["clinic_code"].strip()

        service_id = service_map.get(clinic_name)
        if not service_id: continue 

        exists = db.query(Doctor).filter(Doctor.doctor_name == doctor_name).first()

        if not exists:
            db.add(Doctor(
                doctor_name=doctor_name,
                service_id=service_id, 
                doctor_code=doctor_code_counter, 
                max_patients=50, 
                practice_start_time=start_time, 
                practice_end_time=end_time, 
                is_active=True
            ))
            doctor_code_counter += 1
            inserted += 1

    db.commit()
    print(f"✅ Inserted {inserted} doctors")


# ------------------------------------------------------------
#  4. SEED VISITS (Dengan Logika Inferensi Status Baru)
# ------------------------------------------------------------
def seed_visits_from_csv(db: Session):
    if not os.path.exists(CSV_FILE):
        return

    df = pd.read_csv(CSV_FILE)
    df['doctor_name'] = df['doctor_name'].str.strip()
    df['clinic_code'] = df['clinic_code'].str.strip()
    df['registration_time'] = df['registration_time'].astype(str)
    
    doctor_map = {}
    for doc in db.query(Doctor).options(joinedload(Doctor.service)).all():
         d_key = (doc.doctor_name, doc.service.name)
         doctor_map[d_key] = doc.id
    
    visits_to_add = []
    queue_counter = {}

    for _, row in df.iterrows():
        d_key = (str(row["doctor_name"]).strip(), str(row["clinic_code"]).strip())

        if d_key not in doctor_map:
            continue

        doctor_id = doctor_map[d_key]
        visit_date = str(row["visit_date"]).strip()

        # Logic Penomoran Antrean
        key = (doctor_id, visit_date)
        queue_counter[key] = queue_counter.get(key, 0) + 1
        queue_sequence = queue_counter[key] 

        patient_mr = hashlib.md5(row["patient_name"].encode()).hexdigest()[:10]

        try:
            # Konversi Timestamps
            t_finished = pd.to_datetime(row["completion_time"]).to_pydatetime() if pd.notna(row["completion_time"]) else None
            t_in_service = pd.to_datetime(row["clinic_entry_time"]).to_pydatetime() if pd.notna(row["clinic_entry_time"]) else None
            t_called = pd.to_datetime(row["triage_time"]).to_pydatetime() if pd.notna(row["triage_time"]) else None
            
            # --- INFERENSI STATUS BARU ---
            current_status = VisitStatus.IN_QUEUE # Default
            if t_finished:
                current_status = VisitStatus.FINISHED
            elif t_in_service:
                current_status = VisitStatus.IN_SERVICE
            elif t_called:
                current_status = VisitStatus.CALLED
                
            visit = Visit(
                queue_sequence=queue_sequence,
                patient_name=row["patient_name"],
                patient_mr_number=patient_mr,
                gender=row["gender"].strip().upper(),
                age=int(row["age"]),
                insurance_type=row["insurance"].strip(),
                doctor_id=doctor_id,
                status=current_status, # Menggunakan status yang diinferensikan

                t_register=pd.to_datetime(row["registration_time"]).to_pydatetime() if pd.notna(row["registration_time"]) else None,
                t_in_queue=pd.to_datetime(row["checkin_time"]).to_pydatetime() if pd.notna(row["checkin_time"]) else None,
                t_called=t_called,
                t_in_service=t_in_service,
                t_service_finish=pd.to_datetime(row["doctor_call_time"]).to_pydatetime() if pd.notna(row["doctor_call_time"]) else None,
                t_finished=t_finished,
            )
            visits_to_add.append(visit)
        except Exception as e:
             continue 

    if visits_to_add:
        db.query(Visit).delete() 
        db.add_all(visits_to_add)
        db.commit()
        print(f"✅ Inserted {len(visits_to_add)} visits")
    else:
        print("☑️ No visits inserted")


# ------------------------------------------------------------
# MAIN RUNNER (Dengan DROP & CREATE untuk sinkronisasi skema)
# ------------------------------------------------------------
def main():
    print("🔧 Initializing DB...")
    
    # Buat koneksi sementara untuk menjalankan perintah SQL mentah
    with engine.connect() as connection:
        
        # 1. NONAKTIFKAN PEMERIKSAAN KUNCI ASING (Wajib di sesi ini)
        print("🔓 Disabling Foreign Key Checks...")
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        connection.commit()

        # --- RESET SKEMA KRUSIAL ---
        print("🗑️ Dropping and rebuilding schema...")
        
        # 2. Hapus dan Buat Ulang Tabel (Harus dilakukan setelah disable FK)
        Base.metadata.drop_all(bind=engine) 
        Base.metadata.create_all(bind=engine) 
        
        # 3. AKTIFKAN KEMBALI PEMERIKSAAN KUNCI ASING
        print("🔒 Enabling Foreign Key Checks...")
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        connection.commit()

    db = SessionLocal()
    try:
        print("=== START SEEDING ===")
        
        # Cleanup data lama (hanya User, karena tabel sudah kosong)
        db.query(User).delete() 
        db.commit()
        
        # ... (Lanjutkan dengan seeding data master dan kunjungan) ...
        create_default_admin(db)
        service_map = seed_services_from_csv(db) 
        seed_doctors_from_csv(db, service_map)
        db.expunge_all() 
        seed_visits_from_csv(db)
        
        print("=== DONE SEEDING ===")
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()