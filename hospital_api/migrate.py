import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from storage import init_db, SessionLocal, Service, Doctor, Patient, Queue

def run_migration():
    print("Initializing Database...")
    init_db()
    db = SessionLocal()
    
    print("Reading CSV...")
    df = pd.read_csv("healthcare_dataset_cleaned.csv")

    # --- 1. Import Services (Poli) ---
    print("Importing Services...")
    poli_map = {} # To map Name -> DB Object
    prefixes = {"Umum": "UMUM", "Gigi": "GIGI", "Jantung": "JANT", "Laboratorium": "LAB"}
    
    for poli_name in df['Poli'].unique():
        prefix = prefixes.get(poli_name, poli_name[:4].upper())
        service = Service(name=poli_name, prefix=prefix)
        db.add(service)
        db.commit()
        db.refresh(service)
        poli_map[poli_name] = service

    # --- 2. Import Doctors ---
    print("Importing Doctors...")
    # Group by Doctor Name to find all Polis they work in
    doctor_groups = df.groupby('Doctor')['Poli'].apply(set)
    
    doctor_map = {} # Name -> DB Object
    code_counter = 1
    
    for name, polis in doctor_groups.items():
        # Create Doctor
        doc = Doctor(
            name=name,
            doctor_code=f"{code_counter:03d}", # Generate code like 001, 002
            practice_start_time=datetime.strptime("08:00:00", "%H:%M:%S").time(), # Default
            practice_end_time=datetime.strptime("17:00:00", "%H:%M:%S").time(),   # Default
            max_patients=50
        )
        
        # Link Services
        for poli in polis:
            doc.services.append(poli_map[poli])
            
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doctor_map[name] = doc
        code_counter += 1

    # --- 3. Import Patients ---
    print("Importing Patients...")
    # Drop duplicates to avoid creating the same patient twice
    unique_patients = df[['Name', 'Age', 'Gender']].drop_duplicates(subset=['Name'])
    patient_map = {}
    
    for _, row in unique_patients.iterrows():
        p = Patient(name=row['Name'], age=row['Age'], gender=row['Gender'])
        db.add(p)
        db.commit()
        db.refresh(p)
        patient_map[row['Name']] = p

    # --- 4. Import Queues (History) ---
    print("Importing Queues (this may take a moment)...")
    # We will treat these as historical data (completed)
    
    queues_to_add = []
    # Use a fixed date for history so it doesn't mess up "today's" queue
    history_date = datetime.now() - timedelta(days=1) 
    
    for i, row in df.iterrows():
        service = poli_map[row['Poli']]
        doctor = doctor_map[row['Doctor']]
        patient = patient_map[row['Name']]
        
        # Parse times
        arr_time = datetime.strptime(row['Arrival Time'], "%H:%M:%S").time()
        
        # Combine history date with time
        reg_time = datetime.combine(history_date.date(), arr_time)
        
        q = Queue(
            queue_id_display=f"{service.prefix}-{doctor.doctor_code}-{i+1:04d}",
            queue_number=i+1,
            status="selesai", # Mark as finished
            registration_time=reg_time,
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor.id
        )
        queues_to_add.append(q)
        
        # Batch commit every 1000 rows
        if len(queues_to_add) >= 1000:
            db.add_all(queues_to_add)
            db.commit()
            queues_to_add = []

    db.add_all(queues_to_add)
    db.commit()
    print("Migration Complete! 'hospital.db' created.")
    db.close()

if __name__ == "__main__":
    run_migration()