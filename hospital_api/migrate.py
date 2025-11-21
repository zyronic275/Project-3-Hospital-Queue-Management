import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import os

# Import from storage (NOT schemas)
from storage import init_db, SessionLocal, Service, Doctor, Patient, Queue

def get_prefix(poli_name):
    """Smart prefix generator for names like 'Poli Umum' -> 'UMUM'"""
    name_upper = poli_name.upper()
    if "POLI" in name_upper:
        parts = name_upper.split()
        if len(parts) > 1:
            return parts[1][:4]
    return name_upper[:4]

def run_migration():
    # Ensure we are looking at the DB in the same folder
    db_path = os.path.join(os.path.dirname(__file__), "hospital.db")
    
    # Optional: Remove old DB to start fresh
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed old database.")
        
    print("Initializing Database...")
    init_db()
    db = SessionLocal()
    
    print("Reading CSV...")
    # Make sure the CSV is in the same folder as this script
    csv_path = os.path.join(os.path.dirname(__file__), "healthcare_dataset_altered.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)

    # --- 1. Import Services (Poli) ---
    print("Importing Services...")
    poli_map = {} 
    
    for poli_name in df['Poli'].unique():
        prefix = get_prefix(poli_name)
        service = Service(name=poli_name, prefix=prefix)
        db.add(service)
        db.commit()
        db.refresh(service)
        poli_map[poli_name] = service

    # --- 2. Import Doctors ---
    print("Importing Doctors...")
    doctor_groups = df.groupby('Doctor')['Poli'].apply(set)
    doctor_map = {}
    code_counter = 1
    
    for name, polis in doctor_groups.items():
        doc = Doctor(
            name=name,
            doctor_code=f"{code_counter:03d}",
            practice_start_time=datetime.strptime("08:00:00", "%H:%M:%S").time(),
            practice_end_time=datetime.strptime("17:00:00", "%H:%M:%S").time(),
            max_patients=50
        )
        for poli in polis:
            doc.services.append(poli_map[poli])
            
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doctor_map[name] = doc
        code_counter += 1

    # --- 3. Import Patients ---
    print("Importing Patients...")
    unique_patients = df[['Name', 'Age', 'Gender', 'Date of Birth']].drop_duplicates(subset=['Name'])
    patient_map = {}
    
    for _, row in unique_patients.iterrows():
        try:
            dob = datetime.strptime(row['Date of Birth'], "%Y-%m-%d").date()
        except ValueError:
            dob = None # Handle invalid dates if any

        p = Patient(
            name=row['Name'], 
            age=row['Age'], 
            gender=row['Gender'],
            date_of_birth=dob
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        patient_map[row['Name']] = p

    # --- 4. Import Queues (History) ---
    print("Importing Queues (History)...")
    queues_to_add = []
    
    for i, row in df.iterrows():
        service = poli_map[row['Poli']]
        doctor = doctor_map[row['Doctor']]
        patient = patient_map[row['Name']]
        
        visit_date_str = row['Visit Date']
        arrival_time_str = row['Arrival Time']
        
        reg_time = datetime.strptime(f"{visit_date_str} {arrival_time_str}", "%Y-%m-%d %H:%M:%S")
        
        q = Queue(
            queue_id_display=f"{service.prefix}-{doctor.doctor_code}-{i+1:04d}",
            queue_number=i+1,
            status="selesai",
            registration_time=reg_time,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor.id
        )
        queues_to_add.append(q)
        
        if len(queues_to_add) >= 1000:
            db.add_all(queues_to_add)
            db.commit()
            queues_to_add = []

    db.add_all(queues_to_add)
    db.commit()
    print("Migration Complete!")
    db.close()

if __name__ == "__main__":
    run_migration()