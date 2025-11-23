import pandas as pd
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base # Mengimpor komponen DB
from modules.master import models as master_models
from modules.auth import models as auth_models
import os

# Nama file CSV yang akan digunakan sebagai sumber data
CSV_FILE = &#39;data_final_hospital.csv&#39;
# Nama user Admin default
DEFAULT_ADMIN_USERNAME = os.environ.get(&quot;ADMIN_USER&quot;, &quot;admin_rs&quot;)
DEFAULT_ADMIN_PASSWORD = os.environ.get(&quot;ADMIN_PASS&quot;, &quot;password123&quot;)

# Import utilitas password (asumsi passlib diinstal)

try:
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=[&quot;bcrypt&quot;], deprecated=&quot;auto&quot;)
except ImportError:
print(&quot;Warning: passlib not installed. Cannot hash default admin password.&quot;)
pwd_context = None

def create_default_admin(db: Session):
&quot;&quot;&quot;Membuat user admin default jika belum ada.&quot;&quot;&quot;
existing_admin = db.query(auth_models.User).filter(
auth_models.User.username == DEFAULT_ADMIN_USERNAME
).first()

if existing_admin is None:
if pwd_context:
hashed_password = pwd_context.hash(DEFAULT_ADMIN_PASSWORD)
else:
# Jika passlib tidak diinstal, simpan password tanpa hash (TIDAK AMAN!)
print(&quot;WARNING: Default admin password stored without hashing!&quot;)
hashed_password = DEFAULT_ADMIN_PASSWORD

admin_user = auth_models.User(
username=DEFAULT_ADMIN_USERNAME,
hashed_password=hashed_password,
role=auth_models.RoleEnum.ADMIN,
full_name=&quot;Super Admin Hospital&quot;
)
db.add(admin_user)
db.commit()
print(f&quot;✅ Default Admin user &#39;{DEFAULT_ADMIN_USERNAME}&#39; created.&quot;)

else:
print(f&quot;☑️ Admin user &#39;{DEFAULT_ADMIN_USERNAME}&#39; already exists.&quot;)

def seed_doctors_from_csv(db: Session):
&quot;&quot;&quot;Mengisi tabel &#39;doctors&#39; dari file CSV.&quot;&quot;&quot;
if not os.path.exists(CSV_FILE):
print(f&quot;❌ Error: File CSV &#39;{CSV_FILE}&#39; not found. Skipping doctor seeding.&quot;)
return

try:
df = pd.read_csv(CSV_FILE)
except Exception as e:
print(f&quot;❌ Error reading CSV file: {e}. Skipping doctor seeding.&quot;)
return

# Ambil daftar unik nama dokter dan kode klinik dari CSV
# ASUMSI: Kolom &#39;Doctor_Name&#39; dan &#39;Clinic_Code&#39; ada di CSV Anda
# Jika nama kolom berbeda, sesuaikan di bawah ini:
required_columns = [&#39;Doctor_Name&#39;, &#39;Clinic_Code&#39;]

if not all(col in df.columns for col in required_columns):
print(f&quot;❌ Error: CSV file must contain columns: {required_columns}. Skipping doctor seeding.&quot;)
return

# Menghapus duplikasi dan baris kosong
unique_doctors = df[required_columns].dropna().drop_duplicates()

doctors_to_add = []

for index, row in unique_doctors.iterrows():

doctor_name = str(row[&#39;Doctor_Name&#39;]).strip()
clinic_code = str(row[&#39;Clinic_Code&#39;]).strip()

# Cek apakah dokter sudah ada di database
exists = db.query(master_models.Doctor).filter(
master_models.Doctor.doctor_name == doctor_name,
master_models.Doctor.clinic_code == clinic_code
).first()

if not exists:
doctors_to_add.append(master_models.Doctor(
doctor_name=doctor_name,
clinic_code=clinic_code,
is_active=True
))

if doctors_to_add:
db.add_all(doctors_to_add)
db.commit()
print(f&quot;✅ Successfully seeded {len(doctors_to_add)} new doctors into the database.&quot;)
else:
print(&quot;☑️ Doctor table already populated. No new doctors added.&quot;)

def main():
&quot;&quot;&quot;Fungsi utama untuk menjalankan proses seeding.&quot;&quot;&quot;
# Pastikan semua tabel sudah dibuat (biasanya dilakukan di main.py, tapi diulang di sini untuk
keamanan)
print(&quot;Initializing database tables...&quot;)
Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
print(&quot;--- Starting Database Seeding ---&quot;)
create_default_admin(db)
seed_doctors_from_csv(db)
print(&quot;--- Database Seeding Complete ---&quot;)
except Exception as e:
db.rollback()
print(f&quot;❌ An error occurred during seeding: {e}&quot;)
finally:
db.close()

if __name__ == &quot;__main__&quot;:
main()