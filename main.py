from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse # Ditambahkan: Untuk mengirim gambar QR
from sqlalchemy.orm import Session, joinedload # Ditambahkan: joinedload untuk join data
from typing import List, Optional
from datetime import date
from db import models
from db import schemas
from db.database import engine, get_db

# --- Library QR Code ---
import qrcode
from io import BytesIO
# qrcode.make_image menggunakan Pillow (PIL)
# ---

# create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital Queue System")

# ... (Clinic, Doctor, Patient Endpoints tetap sama) ...
# clinic endpoints
@app.post("/clinics/", response_model=schemas.ClinicResponse, tags=["Clinics"])
def create_clinic(clinic: schemas.ClinicCreate, db: Session = Depends(get_db)):
    db_clinic = models.Clinic(**clinic.dict())
    db.add(db_clinic)
    db.commit()
    db.refresh(db_clinic)
    return db_clinic

@app.get("/clinics/", response_model=List[schemas.ClinicResponse], tags=["Clinics"])
def read_clinics(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Clinic).offset(skip).limit(limit).all()

# doctor endpoints
@app.post("/doctors/", response_model=schemas.DoctorResponse, tags=["Doctors"])
def create_doctor(doctor: schemas.DoctorCreate, db: Session = Depends(get_db)):
    db_doctor = models.Doctor(**doctor.dict())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

@app.get("/doctors/", response_model=List[schemas.DoctorResponse], tags=["Doctors"])
def read_doctors(db: Session = Depends(get_db)):
    return db.query(models.Doctor).all()

# patient endpoints
@app.post("/patients/", response_model=schemas.PatientResponse, tags=["Patients"])
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    existing_patient = db.query(models.Patient).filter(models.Patient.nik == patient.nik).first()
    if existing_patient:
        raise HTTPException(status_code=400, detail="Patient with this NIK already exists")
    
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

# visit endpoints
@app.post("/visits/", response_model=schemas.VisitResponse, tags=["Queue"])
def register_visit(visit: schemas.VisitCreate, db: Session = Depends(get_db)):
    # queue number logic
    count = db.query(models.Visit).filter(
        models.Visit.doctor_id == visit.doctor_id,
        models.Visit.date_visit == visit.date_visit
    ).count()
    
    new_queue_number = count + 1

    # create visit entry
    db_visit = models.Visit(
        patient_id=visit.patient_id,
        doctor_id=visit.doctor_id,
        date_visit=visit.date_visit,
        queue_number=new_queue_number,
        status="waiting"
    )
    
    db.add(db_visit)
    db.commit()
    db.refresh(db_visit)
    # Catatan: Endpoint ini sekarang mengembalikan ID Kunjungan (db_visit.id) yang diperlukan untuk membuat QR Code.
    return db_visit

# --- ENDPOINT BARU: GENERATE QR CODE ---
@app.get("/visits/{visit_id}/qr", tags=["Queue"])
def generate_qr_code(visit_id: int, db: Session = Depends(get_db)):
    
    # 1. Fetch Visit data, termasuk Patient, Doctor, dan Clinic untuk informasi lengkap
    # Catatan: Endpoint ini memerlukan 'relationship' di model SQLAlchemy Anda agar joinedload berfungsi.
    visit = db.query(models.Visit).options(
        joinedload(models.Visit.patient),
        joinedload(models.Visit.doctor).joinedload(models.Doctor.clinic)
    ).filter(models.Visit.id == visit_id).first()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if not visit.patient or not visit.doctor or not visit.doctor.clinic:
        raise HTTPException(status_code=500, detail="Incomplete data (Patient/Doctor/Clinic not found)")

    # 2. Tentukan Prefix (diambil dari huruf pertama nama klinik)
    # ASUMSI: Karena model Anda belum memiliki field prefix, kita gunakan huruf pertama nama klinik.
    # REKOMENDASI: Tambahkan kolom `prefix` di tabel `clinics` untuk penomoran yang stabil (misal: 'A' untuk Poli Anak, 'G' untuk Poli Gigi).
    try:
        clinic_name = visit.doctor.clinic.name
        prefix = clinic_name[0].upper() if clinic_name else 'Q'
    except Exception:
        prefix = 'Q' # Default jika gagal

    # Format nomor antrean (misal: A001)
    formatted_queue = f"{prefix}{visit.queue_number:03d}"
    
    # 3. Data yang dienkripsi ke dalam QR Code
    # Data ini berisi NIK, No. Antrean, dan ID Kunjungan
    qr_data = f"Antrean:{formatted_queue}|NIK:{visit.patient.nik}|VisitID:{visit.id}"
    
    # 4. Generate QR Code Image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # 5. Save gambar ke buffer memori
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    # 6. Kirim gambar sebagai respons file
    return StreamingResponse(buffer, media_type="image/png")

# ... (Endpoints get_queue dan update_visit_status tetap sama) ...
@app.get("/visits/", response_model=List[schemas.VisitResponse], tags=["Queue"])
def get_queue(date_filter: Optional[date] = None, doctor_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Visit)
    if date_filter:
        query = query.filter(models.Visit.date_visit == date_filter)
    if doctor_id:
        query = query.filter(models.Visit.doctor_id == doctor_id)
        
    return query.order_by(models.Visit.queue_number).all()

@app.put("/visits/{visit_id}/status", response_model=schemas.VisitResponse, tags=["Queue"])
def update_visit_status(visit_id: int, update_data: schemas.VisitUpdateStatus, db: Session = Depends(get_db)):
    visit = db.query(models.Visit).filter(models.Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    visit.status = update_data.status
    if update_data.medical_notes:
        visit.medical_notes = update_data.medical_notes
        
    db.commit()
    db.refresh(visit)
    return visit