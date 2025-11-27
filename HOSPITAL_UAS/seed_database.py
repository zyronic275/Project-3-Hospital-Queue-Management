import os
import pandas as pd
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base

# Import Model Service yang baru
from modules.master.models import Doctor, Service 
from modules.queue.models import Visit
from modules.auth.models import User, RoleEnum

from passlib.context import CryptContext
import hashlib
import pandas as pd
import datetime 

CSV_FILE = "data_final_hospital.csv"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------
# CREATE DEFAULT ADMIN 
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


# ------------------------------------------------------------
# BARU: SEED SERVICES (DIBUTUHKAN UNTUK FOREIGN KEY)
# ------------------------------------------------------------
def seed_services_from_csv(db: Session):
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)
    # Ambil semua kode klinik unik dari CSV
    df_service = df[["clinic_code"]].dropna().drop_duplicates()
    
    inserted = 0
    service_map = {} # mapping clinic_code ke service_id
    
    for _, row in df_service.iterrows():
        clinic_code = str(row["clinic_code"]).strip()
        
        # Cek apakah Service sudah ada berdasarkan prefix (clinic_code)
        exists = db.query(Service).filter(Service.prefix == clinic_code).first()
        
        if not exists:
            new_service = Service(
                # Name dibuat dari Clinic Code, misalnya 'Klinik U'
                name=f"Klinik {clinic_code}",
                prefix=clinic_code,
                is_active=True
            )
            db.add(new_service)
            db.flush() # Ambil ID yang dibuat
            service_map[clinic_code] = new_service.id
            inserted += 1
        else:
            service_map[clinic_code] = exists.id
    
    db.commit()
    print(f"✅ Inserted {inserted} services")
    return service_map


# ------------------------------------------------------------
# DIUBAH: SEED DOCTORS (MENGGUNAKAN SERVICE ID)
# ------------------------------------------------------------
def seed_doctors_from_csv(db: Session, service_map: dict):
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)

    if "doctor_name" not in df.columns or "clinic_code" not in df.columns:
        print("❌ CSV must contain doctor_name & clinic_code columns")
        return

    df_doc = df[["doctor_name", "clinic_code"]].dropna().drop_duplicates()

    inserted = 0
    for _, row in df_doc.iterrows():
        doctor_name = row["doctor_name"].strip()
        clinic_code = row["clinic_code"].strip()

        service_id = service_map.get(clinic_code)
        if not service_id:
            print(f"⚠️ Service ID not found for code: {clinic_code}. Skipping doctor.")
            continue

        # Cek duplikasi menggunakan service_id baru
        exists = db.query(Doctor).filter(
            Doctor.doctor_name == doctor_name,
            Doctor.service_id == service_id 
        ).first()

        if not exists:
            db.add(Doctor(
                doctor_name=doctor_name,
                service_id=service_id, # Menggunakan Foreign Key baru
                is_active=True
            ))
            inserted += 1

    db.commit()
    print(f"✅ Inserted {inserted} doctors")


# ------------------------------------------------------------
# DIUBAH: SEED VISITS (MENGGUNAKAN SERVICE ID UNTUK MAPPING DOCTOR)
# ------------------------------------------------------------
def seed_visits_from_csv(db: Session, service_map: dict):
    # ... (cek CSV dan kolom wajib)

    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)

    required = [
        "patient_name", "gender", "age",
        "clinic_code", "doctor_name", "insurance",
        "visit_date", "registration_time",
        "checkin_time", "triage_time",
        "clinic_entry_time", "doctor_call_time",
        "completion_time"
    ]

    for col in required:
        if col not in df.columns:
            print(f"❌ Missing column: {col}")
            return

    print("⏳ Seeding visits...")

    # mapping doctor → ID (menggunakan doctor_name dan service_id)
    # Kita perlu membuat ulang peta ini berdasarkan service_id
    doctor_map = {}
    for doc in db.query(Doctor).all():
        service = db.query(Service).get(doc.service_id)
        if service:
             # Key sekarang adalah (nama dokter, kode klinik) -> doctor_id
             d_key = (doc.doctor_name, service.prefix)
             doctor_map[d_key] = doc.id
    
    visits_to_add = []
    queue_counter = {} # auto-generate queue number per doctor per day

    for _, row in df.iterrows():
        # d_key harus sama dengan key yang dibuat di doctor_map
        d_key = (str(row["doctor_name"]).strip(), str(row["clinic_code"]).strip())

        if d_key not in doctor_map:
            # print(f"⚠️ Doctor not found in map: {d_key}")
            continue
        doctor_id = doctor_map[d_key]

        # ... (Logika pembuatan Visit sama, hanya memastikan doctor_id benar)
        visit_date = str(row["visit_date"]).strip()

        # counter queue per doctor per day
        key = (doctor_id, visit_date)
        queue_counter[key] = queue_counter.get(key, 0) + 1
        queue_number = queue_counter[key]

        # auto-generate MR number
        patient_mr = hashlib.md5(row["patient_name"].encode()).hexdigest()[:10]

        try:
            visit = Visit(
                queue_number=queue_number,
                patient_name=row["patient_name"],
                patient_mr_number=patient_mr,
                gender=row["gender"],
                age=int(row["age"]),
                insurance_type=row["insurance"],
                doctor_id=doctor_id,

                # Menggunakan pd.to_datetime dan .to_pydatetime()
                t_register=pd.to_datetime(row["registration_time"]).to_pydatetime() if pd.notna(row["registration_time"]) else None,
                t_in_queue=pd.to_datetime(row["checkin_time"]).to_pydatetime() if pd.notna(row["checkin_time"]) else None,
                t_called=pd.to_datetime(row["triage_time"]).to_pydatetime() if pd.notna(row["triage_time"]) else None,
                t_in_service=pd.to_datetime(row["clinic_entry_time"]).to_pydatetime() if pd.notna(row["clinic_entry_time"]) else None,
                t_service_finish=pd.to_datetime(row["doctor_call_time"]).to_pydatetime() if pd.notna(row["doctor_call_time"]) else None,
                t_finished=pd.to_datetime(row["completion_time"]).to_pydatetime() if pd.notna(row["completion_time"]) else None,
            )
            visits_to_add.append(visit)
        except ValueError as e:
            print(f"❌ Error converting date/time for row: {row}. Error: {e}")
            continue
        except Exception as e:
             # Menangani error jika kolom tidak valid
            print(f"❌ Error creating Visit object for row: {row}. Error: {e}")
            continue

    if visits_to_add:
        # Perlu menghapus Visits lama untuk seeding yang bersihm
        db.query(Visit).delete() 
        db.add_all(visits_to_add)
        db.commit()
        print(f"✅ Inserted {len(visits_to_add)} visits")
    else:
        print("☑️ No visits inserted")


# ------------------------------------------------------------
# MAIN RUNNER (DIUBAH URUTAN)
# ------------------------------------------------------------
def main():
    print("🔧 Initializing DB...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("=== START SEEDING ===")
        create_default_admin(db)
        
        # 1. Seed Services (Service harus ada sebelum Doctor)
        service_map = seed_services_from_csv(db) 
        
        # 2. Seed Doctors (memerlukan map dari Service)
        seed_doctors_from_csv(db, service_map)
        
        # 3. Seed Visits (memerlukan map dari Service dan Doctor)
        seed_visits_from_csv(db, service_map)
        
        print("=== DONE SEEDING ===")
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()