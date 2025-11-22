import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from datetime import datetime
import os
import sys

# Tambahkan path ke root folder aplikasi agar modul bisa diimpor
# Ini adalah praktik umum untuk seeder/script di luar lingkup FastAPI utama
# jika Anda menjalankan script langsung.
# Namun, dalam lingkungan standar, ini mungkin tidak diperlukan jika Anda
# menjalankan script dari root folder. Kita tetap tambahkan untuk robustness.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# PERBAIKAN: Import Model dengan Path dan Nama Kelas yang Benar
# Nama kelas yang benar adalah Doctor, Patient, dan Visit (bukan Model/Model)
from modules.master.models import Doctor
from modules.queue.models import Patient, Visit, VisitStatus
from modules.auth.models import User, RoleEnum # Diperlukan jika ingin menambahkan user default

# Buat tabel jika belum ada (Opsional, tapi bagus untuk memastikan)
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
   
    # Pastikan file CSV sudah ada
    csv_filename = 'data_final_hospital.csv'
   
    try:
        df = pd.read_csv(csv_filename)
        print(f"🚀 Reading file {csv_filename}...")
    except FileNotFoundError:
        print(f"❌ Error: File '{csv_filename}' not found.")
        db.close()
        return
   
    count_success = 0
   
    # --- Opsional: Buat User Admin Default jika belum ada ---
    try:
        if not db.query(User).filter(User.username == "admin").first():
            from security import get_password_hash # Asumsi ada file security.py untuk hashing
            # Karena file security.py tidak disertakan, kita akan skip hashing
            # dan hanya menggunakan password placeholder (TOLONG GANTI INI DENGAN LOGIC HASH SEBENARNYA)
           
            # import bcrypt # Contoh jika menggunakan bcrypt
            # hashed_password = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Kita gunakan placeholder string
            hashed_password_placeholder = "$2b$12$fK3M1kP9mQ9pQ9rQ9sQ9tO.E.O/w.w"
           
            admin_user = User(
                username="admin",
                hashed_password=hashed_password_placeholder,
                role=RoleEnum.ADMIN,
                full_name="Administrator System"
            )
            db.add(admin_user)
            db.commit()
            print("✅ Default ADMIN user created.")
    except Exception as e:
         print(f"⚠️ Could not create default admin user (Database error or missing security.py): {e}")
         db.rollback()
    # -----------------------------------------------------

    for index, row in df.iterrows():
        try:
            # --- 1. DOCTOR ---
            # Menggunakan class Doctor yang benar
            doctor = db.query(Doctor).filter(Doctor.doctor_name == row['doctor_name']).first()
            if not doctor:
                doctor = Doctor(
                    doctor_name=row['doctor_name'],
                    clinic_code=row['clinic_code']
                )
                db.add(doctor)
                db.commit()
                db.refresh(doctor)
           
            # --- 2. PATIENT ---
            # Menggunakan class Patient yang benar
            patient = db.query(Patient).filter(Patient.patient_name == row['patient_name']).first()
            if not patient:
                gender_input = row['gender']
                if gender_input in ['Male', 'L', 'M', 'Laki-laki']:
                    gender_db = "Male"
                elif gender_input in ['Female', 'P', 'Perempuan']:
                    gender_db = "Female"
                else:
                    gender_db = "Unknown"
               
                email_dummy = row['patient_name'].replace(" ", ".").lower().replace("'", "") + "@example.com"
               
                patient = Patient(
                    patient_name=row['patient_name'],
                    email=email_dummy,
                    # Pastikan format tanggal sesuai: '%Y-%m-%d'
                    date_of_birth=datetime.strptime(str(row['date_of_birth']), '%Y-%m-%d'),
                    gender=gender_db,
                    age=int(row['age']),
                    insurance=row['insurance']
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

            # --- 3. VISIT ---
            visit_date = str(row['visit_date']).split(" ")[0] # Ambil hanya tanggal jika ada timestamp
            fmt = "%Y-%m-%d %H:%M:%S"
           
            # Menggunakan class Visit yang benar. Status default di DB adalah REGISTERED,
            # tapi karena ini data historis, kita set ke COMPLETED.
            visit = Visit(
                patient_id=patient.id,
                doctor_id=doctor.id,
                registration_time = datetime.strptime(f"{visit_date} {row['registration_time']}", fmt),
                checkin_time      = datetime.strptime(f"{visit_date} {row['checkin_time']}", fmt),
                triage_time       = datetime.strptime(f"{visit_date} {row['triage_time']}", fmt),
                clinic_entry_time = datetime.strptime(f"{visit_date} {row['clinic_entry_time']}", fmt),
                doctor_call_time  = datetime.strptime(f"{visit_date} {row['doctor_call_time']}", fmt),
                completion_time   = datetime.strptime(f"{visit_date} {row['completion_time']}", fmt),
                status=VisitStatus.COMPLETED
            )
            db.add(visit)
            count_success += 1
           
        except Exception as e:
            db.rollback()
            print(f"⚠️ Error at row {index} (Data: {row.get('patient_name', 'N/A')}): {e}")
            continue

    db.commit()
    db.close()
    print(f"✅ Success! {count_success} rows imported to MySQL.")

if __name__ == "__main__":
    seed_data()