from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
from sqlalchemy import func
import qrcode
from io import BytesIO
import base64

# Local imports
from hospital_api import storage
from hospital_api import schemas

app = FastAPI(
    title="Hospital Queue API (Updated Dataset)",
    version="2.1.0"
)

router_public = APIRouter(tags=["Public Info & Registration"])
router_admin_services = APIRouter(prefix="/admin/services", tags=["Admin: Services"])
router_admin_doctors = APIRouter(prefix="/admin/doctors", tags=["Admin: Doctors"])
router_monitoring = APIRouter(prefix="/admin", tags=["Admin: Monitoring"])
router_queue_management = APIRouter(prefix="/admin/queue", tags=["Admin: Queue Management"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = storage.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- QR Code Utility ---
def generate_qr_code_base64(data: str) -> str:
    """Menghasilkan QR Code untuk data tertentu dan mengembalikan string Base64."""
    
    # Konfigurasi QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, # Koreksi tinggi, cocok untuk barcode yang di-scan berulang
        box_size=4,
        border=4,
    )
    
    # Menambahkan data (ID Antrean Display)
    qr.add_data(data)
    qr.make(fit=True)
    
    # Membuat gambar
    img = qr.make_image(fill_color='black', back_color='white')
    
    # Menyimpan gambar ke buffer memori (BytesIO)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    
    # Mengkodekan ke Base64
    base64_encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return base64_encoded_image

# =================================================================
# PUBLIC ENDPOINTS
# =================================================================

def time_to_seconds(t: datetime.time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second

@router_public.get("/services/{service_id}/available-doctors", response_model=List[schemas.DoctorAvailableSchema])
def get_available_doctors(service_id: int, db: Session = Depends(get_db)):
    # ... (kode fungsi get_available_doctors yang sudah ada) ...
    service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    today = datetime.date.today()
    current_time = datetime.datetime.now().time()
    available_doctors = []

    for doctor in service.doctors:
        if time_to_seconds(doctor.practice_start_time) <= time_to_seconds(current_time) <= time_to_seconds(doctor.practice_end_time):
            
            # Hitung jumlah pasien yang sudah mendaftar hari ini untuk dokter ini
            registered_today = db.query(storage.Queue).filter(
                storage.Queue.doctor_id == doctor.id,
                func.date(storage.Queue.registration_time) == today
            ).count()

            # Hanya tampilkan jika kuota masih tersisa
            remaining_quota = doctor.max_patients - registered_today
            if remaining_quota > 0:
                available_doctors.append(schemas.DoctorAvailableSchema.model_validate(doctor, update={"remaining_quota": remaining_quota}))
                
    return available_doctors

@router_public.post("/registration", response_model=schemas.RegistrationResponse, status_code=201)
def register_patient(request: schemas.RegistrationRequest, db: Session = Depends(get_db)):
    
    # 1. Validasi Service IDs dan Ambil Data Dokter yang Valid
    valid_doctor_services = []
    
    for service_id in request.service_ids:
        # Cek ketersediaan dokter
        available_doctors = db.query(storage.Doctor).join(storage.Doctor.services).filter(
            storage.Service.id == service_id
        ).all()

        if not available_doctors:
            raise HTTPException(status_code=400, detail=f"No doctors available for service ID {service_id}")

        # Jika doctor_id spesifik diminta, validasi apakah dokter tersebut melayani service ini
        selected_doctor = None
        if request.doctor_id:
            selected_doctor = db.query(storage.Doctor).filter(
                storage.Doctor.id == request.doctor_id
            ).first()
            
            if not selected_doctor or service_id not in [s.id for s in selected_doctor.services]:
                raise HTTPException(status_code=400, detail="Requested doctor does not serve this service.")
        
        # Jika tidak ada doctor_id spesifik, pilih dokter yang paling sedikit antreannya
        if not selected_doctor:
            today = datetime.date.today()
            
            # Hitung antrean aktif (menunggu/dilayani) untuk setiap dokter
            doctor_queues = {}
            for doctor in available_doctors:
                active_queues = db.query(storage.Queue).filter(
                    storage.Queue.doctor_id == doctor.id,
                    func.date(storage.Queue.registration_time) == today,
                    storage.Queue.status.in_(["menunggu", "sedang dilayani"])
                ).count()
                doctor_queues[doctor] = active_queues
            
            # Pilih dokter dengan antrean paling sedikit
            selected_doctor = min(doctor_queues, key=doctor_queues.get)
            
        valid_doctor_services.append({'service_id': service_id, 'doctor': selected_doctor})

    # 2. Registrasi Pasien (atau temukan yang sudah ada)
    patient = db.query(storage.Patient).filter(
        storage.Patient.name == request.patient_name,
        func.date(storage.Patient.date_of_birth) == request.date_of_birth
    ).first()

    if not patient:
        patient = storage.Patient(
            name=request.patient_name, 
            date_of_birth=request.date_of_birth
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    # 3. Buat Antrean (Queue) untuk setiap Layanan yang valid
    new_tickets = []
    for item in valid_doctor_services:
        service = db.query(storage.Service).filter(storage.Service.id == item['service_id']).first()
        doctor = item['doctor']
        
        # Hitung nomor antrean berikutnya (queue_number) untuk hari ini
        today = datetime.date.today()
        latest_queue = db.query(storage.Queue).filter(
            storage.Queue.doctor_id == doctor.id,
            func.date(storage.Queue.registration_time) == today
        ).order_by(storage.Queue.queue_number.desc()).first()
        
        next_queue_number = (latest_queue.queue_number + 1) if latest_queue else 1
        
        # Format queue_id_display: PREFIX-DXXX-NNNN
        # DXXX adalah Doctor Code (dari Doctor)
        # NNNN adalah queue_number (4 digit)
        queue_id_display = f"{service.prefix}-{doctor.doctor_code}-{next_queue_number:04d}"
        
        # Buat objek Queue baru
        new_queue = storage.Queue(
            queue_id_display=queue_id_display,
            queue_number=next_queue_number,
            status="menunggu",
            registration_time=datetime.datetime.now(),
            patient_id=patient.id,
            service_id=service.id,
            doctor_id=doctor.id
        )
        db.add(new_queue)
        db.commit()
        db.refresh(new_queue)
        
        # Menghasilkan QR Code Base64 untuk Queue ID Display
        qr_code_base64 = generate_qr_code_base64(queue_id_display)
        
        new_tickets.append(schemas.Ticket(
            service=schemas.ServiceSchema.model_validate(service),
            queue_number=queue_id_display, # Menggunakan ID Display sebagai nomor tiket
            doctor=schemas.DoctorSchema.model_validate(doctor),
            qr_code_base64=qr_code_base64 # Tambahkan QR code ke tiket
        ))
        
    # 4. Kembalikan Respon
    return schemas.RegistrationResponse(
        patient=schemas.PatientSchema.model_validate(patient),
        tickets=new_tickets
    )

# ... (Fungsi router_public.get("/queue/by-clinic/{service_id}") yang sudah ada) ...

@router_public.get("/queue/by-clinic/{service_id}", response_model=List[schemas.QueueSchema])
def get_queue_by_clinic(service_id: int, db: Session = Depends(get_db)):
    """Mengambil daftar antrean yang sedang aktif ('menunggu' atau 'sedang dilayani') untuk klinik tertentu hari ini."""
    today = datetime.date.today()
    
    queues = db.query(storage.Queue).filter(
        storage.Queue.service_id == service_id,
        func.date(storage.Queue.registration_time) == today,
        storage.Queue.status.in_(["menunggu", "sedang dilayani"])
    ).order_by(storage.Queue.queue_number.asc()).all()

    return queues

# =================================================================
# ADMIN QUEUE MANAGEMENT ENDPOINTS (New)
# =================================================================

@router_queue_management.put("/update-status/{queue_id_display}", 
    response_model=schemas.QueueSchema, 
    summary="Update status antrean berdasarkan Queue ID Display (via QR/Barcode Scan)")
def update_queue_status(
    queue_id_display: str, 
    update: schemas.QueueStatusUpdate, # Menggunakan schema dari schemas.py
    db: Session = Depends(get_db)
):
    """
    Endpoint ini digunakan oleh aplikasi scanner/admin untuk mengubah status antrean pasien.
    """
    # 1. Cari antrean berdasarkan queue_id_display
    queue = db.query(storage.Queue).filter(
        storage.Queue.queue_id_display == queue_id_display
    ).first()

    if not queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan.")

    # 2. Validasi status baru
    valid_statuses = ["menunggu", "sedang dilayani", "selesai", "tidak hadir"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status tidak valid. Harus salah satu dari: {', '.join(valid_statuses)}")

    # 3. Update status
    queue.status = update.status
    db.commit()
    db.refresh(queue)

    return queue

# =================================================================
# ADMIN DOCTORS ENDPOINTS
# ... (kode fungsi router_admin_doctors yang sudah ada) ...
@router_admin_doctors.post("/", response_model=schemas.DoctorSchema)
def create_doctor(doctor: schemas.DoctorCreate, db: Session = Depends(get_db)):
    # 1. Pastikan Doctor Code unik
    existing_doctor = db.query(storage.Doctor).filter(storage.Doctor.doctor_code == doctor.doctor_code).first()
    if existing_doctor:
        raise HTTPException(status_code=400, detail="Doctor Code already registered")

    # 2. Buat objek Doctor
    db_doctor = storage.Doctor(
        doctor_code=doctor.doctor_code,
        name=doctor.name,
        practice_start_time=doctor.practice_start_time,
        practice_end_time=doctor.practice_end_time,
        max_patients=doctor.max_patients
    )
    
    # 3. Asosiasikan dengan Services
    services = db.query(storage.Service).filter(storage.Service.id.in_(doctor.services)).all()
    if len(services) != len(doctor.services):
        raise HTTPException(status_code=404, detail="One or more service IDs not found")
        
    db_doctor.services = services
    
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

@router_admin_doctors.get("/", response_model=List[schemas.DoctorSchema])
def get_all_doctors(db: Session = Depends(get_db)):
    return db.query(storage.Doctor).all()

@router_admin_doctors.put("/{doctor_id}", response_model=schemas.DoctorSchema)
def update_doctor(doctor_id: int, update: schemas.DoctorUpdate, db: Session = Depends(get_db)):
    doctor = db.query(storage.Doctor).filter(storage.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if update.doctor_code is not None and update.doctor_code != doctor.doctor_code:
        existing_doctor = db.query(storage.Doctor).filter(storage.Doctor.doctor_code == update.doctor_code).first()
        if existing_doctor and existing_doctor.id != doctor_id:
            raise HTTPException(status_code=400, detail="New Doctor Code already in use")

    update_data = update.model_dump(exclude_unset=True)
    
    # Handle services association separately
    if "services" in update_data:
        service_ids = update_data.pop("services")
        services = db.query(storage.Service).filter(storage.Service.id.in_(service_ids)).all()
        if len(services) != len(service_ids):
            raise HTTPException(status_code=404, detail="One or more service IDs not found")
        doctor.services = services

    for key, value in update_data.items():
        setattr(doctor, key, value)
        
    db.commit()
    db.refresh(doctor)
    return doctor

@router_admin_doctors.delete("/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(storage.Doctor).filter(storage.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    db.delete(doctor)
    db.commit()
    return

# =================================================================
# ADMIN SERVICES ENDPOINTS
# ... (kode fungsi router_admin_services yang sudah ada) ...
@router_admin_services.post("/", response_model=schemas.ServiceSchema)
def create_service(service: schemas.ServiceCreate, db: Session = Depends(get_db)):
    db_service = storage.Service(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router_admin_services.get("/", response_model=List[schemas.ServiceSchema])
def get_all_services(db: Session = Depends(get_db)):
    return db.query(storage.Service).all()

@router_admin_services.put("/{service_id}", response_model=schemas.ServiceSchema)
def update_service(service_id: int, update: schemas.ServiceUpdate, db: Session = Depends(get_db)):
    service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(service, key, value)
        
    db.commit()
    db.refresh(service)
    return service

@router_admin_services.delete("/{service_id}", status_code=204)
def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(storage.Service).filter(storage.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    