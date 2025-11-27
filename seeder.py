import random
from datetime import date, timedelta
from db import models
from db.database import SessionLocal, engine

db = SessionLocal()

def seed_data():
    # models.Base.metadata.drop_all(bind=engine)
    # models.Base.metadata.create_all(bind=engine)
    # ^buat bersiin data
    
    # clinics
    print("Creating clinics")
    clinics_list = [
        {"name": "Poli Umum", "location": "Building A, Floor 1"},
        {"name": "Poli Gigi", "location": "Building B, Floor 2"},
        {"name": "Poli Anak", "location": "Building A, Floor 1"},
        {"name": "Poli Jantung", "location": "Building C, Floor 3"},
    ]
    
    db_clinics = []
    for c in clinics_list:
        clinic = models.Clinic(name=c["name"], location=c["location"])
        db.add(clinic)
        db_clinics.append(clinic)
    db.commit()
    
    for c in db_clinics: db.refresh(c)

    # doctors
    print("Creating doctors")
    doctors_list = [
        ("Dr. Budi Santoso", "General Practitioner", db_clinics[0].id),
        ("Dr. Siti Aminah", "General Practitioner", db_clinics[0].id),
        ("Dr. Andi Wijaya", "Dentist", db_clinics[1].id),
        ("Dr. Ratna Dewi", "Pediatrician", db_clinics[2].id),
        ("Dr. Hartono", "Cardiologist", db_clinics[3].id),
    ]

    db_doctors = []
    for name, spec, cid in doctors_list:
        doc = models.Doctor(name=name, specialization=spec, clinic_id=cid)
        db.add(doc)
        db_doctors.append(doc)
    db.commit()
    for d in db_doctors: db.refresh(d)

    # patients
    print("elara Creating 50 Patients...")
    first_names = ["Agus", "Budi", "Citra", "Dewi", "Eko", "Fajar", "Gita", "Hana", "Indra", "Joko", "Lestari", "Maya"]
    last_names = ["Susanto", "Pratama", "Putri", "Wibowo", "Lestari", "Kusuma", "Hidayat", "Saputra", "Siregar"]
    
    db_patients = []
    for i in range(50):
        f_name = random.choice(first_names)
        l_name = random.choice(last_names)
        nik_val = f"31750{i:05d}001" 
        
        patient = models.Patient(
            name=f"{f_name} {l_name}",
            age=random.randint(5, 80),
            gender=random.choice(["Male", "Female"]),
            nik=nik_val,
            phone=f"0812{random.randint(10000000, 99999999)}",
            dob=date(1990, 1, 1)
        )
        db.add(patient)
        db_patients.append(patient)
    db.commit()
    for p in db_patients: db.refresh(p)

    # visits
    print("Creating visiss")
    today = date.today()
    tomorrow = today + timedelta(days=1)
    queue_tracker = {}

    for i, patient in enumerate(db_patients):
        doctor = random.choice(db_doctors)
        visit_date = today if i % 2 == 0 else tomorrow
        
        tracker_key = (doctor.id, visit_date)
        current_q = queue_tracker.get(tracker_key, 0)
        new_q = current_q + 1
        queue_tracker[tracker_key] = new_q
        
        status = random.choice(["waiting", "waiting", "waiting", "in_progress", "completed"])
        notes = None
        if status == "completed":
            notes = "Patient healthy. Prescribed vitamins."

        visit = models.Visit(
            patient_id=patient.id,
            doctor_id=doctor.id,
            date_visit=visit_date,
            queue_number=new_q,
            status=status,
            medical_notes=notes
        )
        db.add(visit)
    
    db.commit()
    print("Seeding complete")

if __name__ == "__main__":
    seed_data()