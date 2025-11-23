import os
import pandas as pd
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base

from modules.master.models import Doctor
from modules.queue.models import Visit
from modules.auth.models import User, RoleEnum

from passlib.context import CryptContext
import hashlib
import pandas as pd

CSV_FILE = "data_final_hospital.csv"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------
#  CREATE DEFAULT ADMIN
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
#  SEED DOCTORS (MATCHING YOUR CSV)
# ------------------------------------------------------------
def seed_doctors_from_csv(db: Session):
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

        exists = db.query(Doctor).filter(
            Doctor.doctor_name == doctor_name,
            Doctor.clinic_code == clinic_code
        ).first()

        if not exists:
            db.add(Doctor(
                doctor_name=doctor_name,
                clinic_code=clinic_code,
                is_active=True
            ))
            inserted += 1

    db.commit()
    print(f"✅ Inserted {inserted} doctors")


# ------------------------------------------------------------
#  SEED VISITS (MATCHING YOUR CSV)
# ------------------------------------------------------------
def seed_visits_from_csv(db: Session):
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

    # mapping doctor → ID
    doctor_map = {
        (doc.doctor_name, doc.clinic_code): doc.id
        for doc in db.query(Doctor).all()
    }

    visits_to_add = []
    queue_counter = {}  # auto-generate queue number per doctor per day

    for _, row in df.iterrows():
        d_key = (str(row["doctor_name"]).strip(), str(row["clinic_code"]).strip())

        if d_key not in doctor_map:
            print(f"⚠️ Doctor not found: {d_key}")
            continue

        doctor_id = doctor_map[d_key]

        visit_date = str(row["visit_date"]).strip()

        # counter queue per doctor per day
        key = (doctor_id, visit_date)
        queue_counter[key] = queue_counter.get(key, 0) + 1
        queue_number = queue_counter[key]

        # auto-generate MR number
        patient_mr = hashlib.md5(row["patient_name"].encode()).hexdigest()[:10]

        visit = Visit(
            queue_number=queue_number,
            patient_name=row["patient_name"],
            patient_mr_number=patient_mr,
            gender=row["gender"],
            age=int(row["age"]),
            insurance_type=row["insurance"],
            doctor_id=doctor_id,

            t_register=pd.to_datetime(row["registration_time"]),
            t_in_queue=pd.to_datetime(row["checkin_time"]),
            t_called=pd.to_datetime(row["triage_time"]),
            t_in_service=pd.to_datetime(row["clinic_entry_time"]),
            t_service_finish=pd.to_datetime(row["doctor_call_time"]),
            t_finished=pd.to_datetime(row["completion_time"]),
        )

        visits_to_add.append(visit)

    if visits_to_add:
        db.add_all(visits_to_add)
        db.commit()
        print(f"✅ Inserted {len(visits_to_add)} visits")
    else:
        print("☑️ No visits inserted")


# ------------------------------------------------------------
#  MAIN RUNNER
# ------------------------------------------------------------
def main():
    print("🔧 Initializing DB...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("=== START SEEDING ===")
        create_default_admin(db)
        seed_doctors_from_csv(db)
        seed_visits_from_csv(db)
        print("=== DONE SEEDING ===")
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()