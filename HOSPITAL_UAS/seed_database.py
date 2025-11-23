import pandas as pd
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from modules.master import models as master_models
from modules.auth import models as auth_models
import os

# Nama file CSV
CSV_FILE = "data_final_hospital.csv"

# Default admin
DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin_rs")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "password123")

# Import utilitas password
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    print("Warning: passlib not installed. Cannot hash default admin password.")
    pwd_context = None


def create_default_admin(db: Session):
    """Membuat user admin default jika belum ada."""
    existing_admin = (
        db.query(auth_models.User)
        .filter(auth_models.User.username == DEFAULT_ADMIN_USERNAME)
        .first()
    )

    if existing_admin is None:
        if pwd_context:
            hashed_password = pwd_context.hash(DEFAULT_ADMIN_PASSWORD)
        else:
            print("WARNING: Default admin password stored without hashing!")
            hashed_password = DEFAULT_ADMIN_PASSWORD

        admin_user = auth_models.User(
            username=DEFAULT_ADMIN_USERNAME,
            hashed_password=hashed_password,
            role=auth_models.RoleEnum.ADMIN,
            full_name="Super Admin Hospital"
        )

        db.add(admin_user)
        db.commit()
        print(f"✅ Default Admin user '{DEFAULT_ADMIN_USERNAME}' created.")
    else:
        print(f"☑️ Admin user '{DEFAULT_ADMIN_USERNAME}' already exists.")


def seed_doctors_from_csv(db: Session):
    """Mengisi tabel 'doctors' dari file CSV."""
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: File CSV '{CSV_FILE}' not found. Skipping doctor seeding.")
        return

    try:
        df = pd.read_csv(CSV_FILE)
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}. Skipping doctor seeding.")
        return

    required_columns = ["Doctor_Name", "Clinic_Code"]

    if not all(col in df.columns for col in required_columns):
        print(f"❌ Error: CSV file must contain columns: {required_columns}. Skipping doctor seeding.")
        return

    unique_doctors = df[required_columns].dropna().drop_duplicates()

    doctors_to_add = []

    for index, row in unique_doctors.iterrows():
        doctor_name = str(row["Doctor_Name"]).strip()
        clinic_code = str(row["Clinic_Code"]).strip()

        exists = db.query(master_models.Doctor).filter(
            master_models.Doctor.doctor_name == doctor_name,
            master_models.Doctor.clinic_code == clinic_code
        ).first()

        if not exists:
            doctors_to_add.append(
                master_models.Doctor(
                    doctor_name=doctor_name,
                    clinic_code=clinic_code,
                    is_active=True
                )
            )

    if doctors_to_add:
        db.add_all(doctors_to_add)
        db.commit()
        print(f"✅ Successfully seeded {len(doctors_to_add)} new doctors into the database.")
    else:
        print("☑️ Doctor table already populated. No new doctors added.")


def main():
    """Fungsi utama untuk menjalankan proses seeding."""
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("--- Starting Database Seeding ---")
        create_default_admin(db)
        seed_doctors_from_csv(db)
        print("--- Database Seeding Complete ---")
    except Exception as e:
        db.rollback()
        print(f"❌ An error occurred during seeding: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

