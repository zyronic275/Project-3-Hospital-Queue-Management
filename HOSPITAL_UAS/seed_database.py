import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal, engine
# Import Model English
from modules.antrean.models import Base, PaƟentModel, DoctorModel, VisitModel
from dateƟme import dateƟme

# Buat tabel jika belum ada
Base.metadata.create_all(bind=engine)

def seed_data():
db = SessionLocal()

# GANTI DENGAN NAMA FILE CSV KAMU YANG SUDAH BAHASA INGGRIS
csv_filename = 'data_final_hospital.csv'

try:
df = pd.read_csv(csv_filename)
print(f"띙띚띞띟띛띜띝 Reading file {csv_filename}...")
except FileNotFoundError:
print(f" Error: File '{csv_filename}' not found.")
return

count_success = 0

for index, row in df.iterrows():
try:
# --- 1. DOCTOR ---
# Header CSV English: doctor_name, clinic_code
doctor = db.query(DoctorModel).filter(DoctorModel.doctor_name ==
row['doctor_name']).first()
if not doctor:
doctor = DoctorModel(
doctor_name=row['doctor_name'],
clinic_code=row['clinic_code']
)
db.add(doctor)
db.commit()
db.refresh(doctor)

# --- 2. PATIENT ---
# Header CSV English: paƟent_name, gender, date_of_birth, age, insurance
paƟent = db.query(PaƟentModel).filter(PaƟentModel.paƟent_name ==
row['paƟent_name']).first()
if not paƟent:

# Gender logic: Asumsi di CSV isinya 'Male'/'Female'
gender_input = row['gender']
# Mapping jika inputnya variaƟf
if gender_input in ['Male', 'L', 'M']:
gender_db = "Male"
else:
gender_db = "Female"

email_dummy = row['paƟent_name'].replace(" ", ".").lower() + "@example.com"

paƟent = PaƟentModel(
paƟent_name=row['paƟent_name'],
email=email_dummy,
date_of_birth=dateƟme.strpƟme(row['date_of_birth'], '%Y-%m-%d'),
gender=gender_db,
age=row['age'],
insurance=row['insurance']
)
db.add(paƟent)
db.commit()
db.refresh(paƟent)

# --- 3. VISIT ---
# Header CSV English: visit_date, registraƟon_Ɵme, etc.
visit_date = row['visit_date']
fmt = "%Y-%m-%d %H:%M:%S"

visit = VisitModel(
paƟent_id=paƟent.id,
doctor_id=doctor.id,
registraƟon_Ɵme = dateƟme.strpƟme(f"{visit_date} {row['registraƟon_Ɵme']}", fmt),

checkin_Ɵme = dateƟme.strpƟme(f"{visit_date} {row['checkin_Ɵme']}", fmt),
triage_Ɵme = dateƟme.strpƟme(f"{visit_date} {row['triage_Ɵme']}", fmt),
clinic_entry_Ɵme = dateƟme.strpƟme(f"{visit_date} {row['clinic_entry_Ɵme']}", fmt),
doctor_call_Ɵme = dateƟme.strpƟme(f"{visit_date} {row['doctor_call_Ɵme']}", fmt),
compleƟon_Ɵme = dateƟme.strpƟme(f"{visit_date} {row['compleƟon_Ɵme']}", fmt),
status="COMPLETED"
)
db.add(visit)
count_success += 1

except ExcepƟon as e:
print(f" Error at row {index}: {e}")
conƟnue

db.commit()
db.close()
print(f"膆 Success! {count_success} rows imported to MySQL.")

if __name__ == "__main__":
seed_data()

Jalankan di terminal:
Bash
python seed_database.py