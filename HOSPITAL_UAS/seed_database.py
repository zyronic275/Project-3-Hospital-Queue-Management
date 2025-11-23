import pandas as pd
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from modules.master.models import Doctor
# IMPOR MODEL TERKAIT UNTUK MEMASTIKAN SEMUA MAPPED CLASS DIMUAT OLEH SQLAlchemy
from modules.queue.models import Visit
from modules.auth.models import User, RoleEnum
import os

CSV_FILE = "data_final_hospital.csv"

# Variabel ini mungkin membaca nilai dari .env atau shell
DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin_rs")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "password123")

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_default_admin(db: Session):
    """Membuat user admin default jika belum ada."""
    existing_admin = (
        db.query(User)
        .filter(User.username == DEFAULT_ADMIN_USERNAME)
        .first()
    )

    if existing_admin is None:
        # PENTING: Bersihkan whitespace, lalu potong untuk kepatuhan BCrypt
        password_clean = DEFAULT_ADMIN_PASSWORD.strip()
        password_to_hash = password_clean[:72]
       
        # Diagnostik: Print panjang password sebelum di-hash
        print(f"DEBUG: Password length before hashing: {len(password_to_hash)} chars.")
       
        # Hashing akan dilakukan pada string yang sudah dibersihkan dan dipotong
        hashed_password = pwd_context.hash(password_to_hash)

        admin_user = User(
            username=DEFAULT_ADMIN_USERNAME,
            hashed_password=hashed_password,
            role=RoleEnum.ADMIN,
            full_name="Super Admin Hospital"
        )

        db.add(admin_user)
        db.commit()
        print(f"✅ Default Admin user '{DEFAULT_ADMIN_USERNAME}' created (Password length: {len(password_to_hash)}).")
    else:
        print(f"☑️ Admin user '{DEFAULT_ADMIN_USERNAME}' already exists.")


def seed_doctors_from_csv(db: Session):
    """Mengisi data dokter dari file CSV."""
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: File CSV '{CSV_FILE}' not found. Skipping doctor seeding.")
        return

    df = pd.read_csv(CSV_FILE)

    required_columns = ["Doctor_Name", "Clinic_Code"]

    if not all(col in df.columns for col in required_columns):
        print(f"❌ Error: CSV must contain: {required_columns}")
        return

    unique_doctors = df[required_columns].dropna().drop_duplicates()
    doctors_to_add = []

    for _, row in unique_doctors.iterrows():
        name = str(row["Doctor_Name"]).strip()
        code = str(row["Clinic_Code"]).strip()

        # Cek apakah dokter dengan nama dan kode klinik yang sama sudah ada
        exists = db.query(Doctor).filter(
            Doctor.doctor_name == name,
            Doctor.clinic_code == code
        ).first()

        if not exists:
            doctors_to_add.append(
                Doctor(
                    doctor_name=name,
                    clinic_code=code,
                    is_active=True
                )
            )

    if doctors_to_add:
        db.add_all(doctors_to_add)
        db.commit()
        print(f"✅ Added {len(doctors_to_add)} doctors.")
    else:
        print("☑️ Doctors already up-to-date.")


def main():
    print("Initializing DB...")
    # PENTING: Base.metadata.create_all harus dipanggil setelah semua model diimpor
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("--- Seeding ---")
        create_default_admin(db)
        seed_doctors_from_csv(db)
        print("--- Done ---")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding process: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

