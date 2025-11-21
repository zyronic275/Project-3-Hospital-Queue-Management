import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import os

# Import from our storage module
from storage import init_db, SessionLocal, Service, Doctor, Patient, Queue

def get_prefix(poli_name):
    """Smart prefix generator for names like 'Poli Umum' -> 'UMUM'"""
    name_upper = poli_name.upper()
    if "POLI" in name_upper:
        # Split "Poli Umum" -> ["Poli", "Umum"] -> take "Umum"
        parts = name_upper.split()
        if len(parts) > 1:
            return parts[1][:4]
    # Fallback for "Jantung" or others
    return name_upper[:4]

def run_migration():
    # Remove old DB if exists to start fresh
    if os.path.exists("hospital.db"):
        os.remove("hospital.db")
        
    print("Initializing Database...")
    init_db()
    db = SessionLocal()
    
    print("Reading CSV...")
    # Update filename to the new dataset
    df = pd.read_csv("healthcare_dataset_altered.csv")

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
    # Drop duplicates by Name to avoid double entry
    unique_patients = df[['Name', 'Age', 'Gender', 'Date of Birth']].drop_duplicates(subset=['Name'])
    patient_map = {}
    
    for _, row in unique_patients.iterrows():
        # Parse Date of Birth (YYYY-MM-DD)
        dob = datetime.strptime(row['Date of Birth'], "%Y-%m-%d").date()
        
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
        
        # Parse Visit Date + Arrival Time
        visit_date_str = row['Visit Date'] # YYYY-MM-DD
        arrival_time_str = row['Arrival Time'] # HH:MM:SS
        
        reg_time = datetime.strptime(f"{visit_date_str} {arrival_time_str}", "%Y-%m-%d %H:%M:%S")
        
        # Determine Queue Number (Simple increment per doctor per day would be ideal, 
        # but for migration we can just use row index or simple 1-based)
        
        q = Queue(
            queue_id_display=f"{service.prefix}-{doctor.doctor_code}-{i+1:04d}",
            queue_number=i+1,
            status="selesai", # Assume historical data is done
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
    print("Migration Complete! 'hospital.db' created with new dataset.")
    db.close()

if __name__ == "__main__":
    run_migration()