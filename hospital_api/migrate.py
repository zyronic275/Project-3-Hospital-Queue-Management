import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
import os
import random

# Import models
from storage import Service, Doctor, Patient, Queue

def get_prefix(poli_name):
    """Smart prefix generator for names like 'Poli Umum' -> 'UMUM'"""
    name_upper = poli_name.upper()
    if "POLI" in name_upper:
        parts = name_upper.split()
        if len(parts) > 1:
            return parts[1][:4]
    return name_upper[:4]

def seed_data(db: Session, count: int):
    """
    Mengambil data dari CSV dan mengimport sejumlah 'count' baris secara acak.
    """
    print(f"Memulai proses seeding untuk {count} data...")
    
    # 1. Load CSV
    csv_path = os.path.join(os.path.dirname(__file__), "healthcare_dataset_altered.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File CSV tidak ditemukan di: {csv_path}")
        
    df = pd.read_csv(csv_path)
    
    # Ambil sample random sejumlah 'count' (atau max baris jika count > total)
    real_count = min(count, len(df))
    df_sample = df.sample(n=real_count)
    
    print(f"Mengambil {real_count} baris acak dari dataset.")

    # Cache dictionaries untuk mencegah duplikasi saat loop
    poli_map = {}
    doctor_map = {}
    
    created_services = 0
    created_doctors = 0
    created_patients = 0
    created_queues = 0

    # Loop setiap baris sample
    for i, row in df_sample.iterrows():
        
        # --- A. Handle Service (Poli) ---
        poli_name = row['Poli']
        
        # Cek apakah service sudah ada di DB atau di cache map
        if poli_name not in poli_map:
            service = db.query(Service).filter(Service.name == poli_name).first()
            if not service:
                service = Service(name=poli_name, prefix=get_prefix(poli_name))
                db.add(service)
                db.commit()
                db.refresh(service)
                created_services += 1
            poli_map[poli_name] = service
        
        current_service = poli_map[poli_name]

        # --- B. Handle Doctor ---
        doc_name = row['Doctor']
        
        if doc_name not in doctor_map:
            doctor = db.query(Doctor).filter(Doctor.name == doc_name).first()
            if not doctor:
                # Generate random code & time jika tidak ada info detail di CSV
                doc_code = str(random.randint(100, 999))
                # Default practice time
                t_start = datetime.strptime("08:00", "%H:%M").time()
                t_end = datetime.strptime("16:00", "%H:%M").time()
                
                doctor = Doctor(
                    doctor_code=doc_code,
                    name=doc_name,
                    practice_start_time=t_start,
                    practice_end_time=t_end,
                    max_patients=20
                )
                db.add(doctor)
                db.commit()
                db.refresh(doctor)
                created_doctors += 1
            
            # Pastikan dokter terhubung ke service ini
            if current_service not in doctor.services:
                doctor.services.append(current_service)
                db.commit()
                
            doctor_map[doc_name] = doctor
            
        current_doctor = doctor_map[doc_name]

        # --- C. Handle Patient ---
        # Parse Tanggal Lahir
        try:
            dob_str = str(row['Date of Birth'])
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            dob = None

        # Selalu buat pasien baru untuk simulasi queue (atau bisa cek nama jika ingin unik)
        # Disini kita buat baru agar history tercatat sesuai baris CSV
        p = Patient(
            name=row['Name'], 
            age=row['Age'], 
            gender=row['Gender'],
            date_of_birth=dob
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        created_patients += 1

        # --- D. Handle Queue ---
        visit_date_str = row['Visit Date']
        arrival_time_str = row['Arrival Time']
        
        try:
            reg_time = datetime.strptime(f"{visit_date_str} {arrival_time_str}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            reg_time = datetime.now()

        # Generate nomor antrian sederhana
        queue_num = i + 1
        q_display = f"{current_service.prefix}-{current_doctor.doctor_code}-{queue_num:04d}"

        q = Queue(
            queue_id_display=q_display,
            queue_number=queue_num,
            status="selesai", # Anggap data historis CSV sebagai selesai
            registration_time=reg_time,
            patient_id=p.id,
            service_id=current_service.id,
            doctor_id=current_doctor.id
        )
        db.add(q)
        created_queues += 1
    
    db.commit()
    
    return {
        "requested": count,
        "processed": real_count,
        "new_services": created_services,
        "new_doctors": created_doctors,
        "new_patients": created_patients,
        "new_queues": created_queues
    }