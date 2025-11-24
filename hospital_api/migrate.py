# hospital_api/migrate.py

import pandas as pd
from datetime import datetime, timedelta, date # Tambahkan date
from sqlalchemy.orm import Session
import os
import numpy as np
from sqlalchemy import func

# 👇 MENGGUNAKAN RELATIVE IMPORT
from .storage import init_db, SessionLocal, Service, Doctor, Patient, Queue 

def get_prefix(poli_name):
    """Smart prefix generator for names like 'Poli Umum' -> 'UMUM'"""
    name_upper = poli_name.upper()
    if "POLI" in name_upper:
        parts = name_upper.split()
        if len(parts) > 1:
            return parts[1][:4]
    return name_upper[:4]

def run_migration():
    # Path ke root directory (tempat CSV berada, satu level di atas hospital_api/)
    root_dir = os.path.dirname(os.path.dirname(__file__)) 
    db_path = os.path.join(root_dir, "hospital.db")
    
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed old database.")
        
    print("Initializing Database...")
    init_db()
    db = SessionLocal()
    
    print("Reading CSV...")
    csv_path = os.path.join(root_dir, "healthcare_dataset_altered.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}. Please place it in the project root directory.")
        db.close()
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

    # --- 3. Import Patients (Diperbaiki Penanganan Data) ---
    print("Importing Patients...")
    unique_patients = df[['Name', 'Age', 'Gender', 'Date of Birth']].drop_duplicates(subset=['Name', 'Date of Birth']) 
    patient_map = {}
    
    for _, row in unique_patients.iterrows():
        dob_dt = None
        # Penanganan Date of Birth
        try:
            dob_date_obj = datetime.strptime(str(row['Date of Birth']), "%Y-%m-%d").date()
            dob_dt = datetime.combine(dob_date_obj, datetime.min.time()) # Konversi date ke datetime
        except (ValueError, TypeError):
            dob_dt = None 
            
        # Penanganan nilai Age (pastikan int atau None)
        age_val = None
        if pd.notna(row['Age']):
            try:
                # Gunakan int(float(value)) untuk menangani angka yang mungkin berupa float (misal: 45.0)
                age_val = int(float(row['Age'])) 
            except ValueError:
                age_val = None
        
        # Penanganan nilai Gender
        gender_val = row['Gender'] if pd.notna(row['Gender']) else None

        p = Patient(
            name=row['Name'], 
            age=age_val,
            gender=gender_val,
            date_of_birth=dob_dt
        )
        
        db.add(p)
        db.commit()
        db.refresh(p)
        patient_map[(row['Name'], row['Date of Birth'])] = p 

    # --- 4. Import Queues (History) ---
    print("Importing Queues (History)...")
    queues_to_add = []
    
    for i, row in df.iterrows():
        patient_key = (row['Name'], row['Date of Birth'])
        patient = patient_map.get(patient_key)

        if not patient or row['Poli'] not in poli_map or row['Doctor'] not in doctor_map:
            continue
            
        service = poli_map[row['Poli']]
        doctor = doctor_map[row['Doctor']]
        
        visit_date_str = row['Visit Date']
        arrival_time_str = row['Arrival Time']
        
        try:
            reg_time = datetime.strptime(f"{visit_date_str} {arrival_time_str}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            reg_time = datetime.now()

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