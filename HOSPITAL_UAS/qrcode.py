# modules/queue/routers/qr_code_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from io import BytesIO
import qrcode
from PIL import Image

# Asumsi lokasi file: database.py ada di root, models di modules/queue/
from database import get_db
from modules.queue import models as queue_models 

router = APIRouter()

# --- Fungsi Bantuan untuk Membuat QR Code ---
def generate_qr_code_image(data: str):
    """Menghasilkan gambar QR Code dari string data dan mengembalikannya sebagai bytes PNG."""
    # Pastikan Anda sudah menginstal: pip install qrcode[pil]
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M, 
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


@router.get(
    "/generate/{queue_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "Gambar QR Code"}},
    tags=["QR Code"]
)
def get_qr_code(queue_id: int, db: Session = Depends(get_db)):
    """
    Menghasilkan gambar QR Code yang dienkripsi dengan URL scan langsung menggunakan queue_id.
    """
    queue_record = db.query(queue_models.Queue).filter(queue_models.Queue.id == queue_id).first()
    
    if not queue_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antrian tidak ditemukan")

    # Data yang dienkripsi adalah URL untuk mengupdate status
    # Gunakan 'http://localhost:8000' hanya sebagai contoh. Ganti dengan domain server Anda di produksi.
    qr_data_url = f"http://localhost:8000/api/v1/queue/qr/scan/{queue_id}"
    
    qr_image_bytes = generate_qr_code_image(qr_data_url)
    
    # Mengembalikan gambar PNG
    return Response(content=qr_image_bytes, media_type="image/png")


@router.post("/scan/{queue_id}", tags=["QR Code"])
def scan_qr_code_update_status(queue_id: int, db: Session = Depends(get_db)):
    """
    Memperbarui status antrian saat QR Code di-scan, berdasarkan queue_id yang dibaca.
    """
    
    # 1. Ambil data antrian dari database
    queue_record = db.query(queue_models.Queue).filter(queue_models.Queue.id == queue_id).first()
    
    if not queue_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antrian tidak ditemukan")

    # Asumsi kolom 'status' ada di model Queue
    current_status = queue_record.status 
    
    # 2. Logika Update Status (Contoh Alur Check-in Rumah Sakit)
    new_status = ""
    message = ""
    
    if current_status == "registered":
        new_status = "checkin"
        message = f"Antrian {queue_id} berhasil di-Checkin."
    elif current_status == "checkin":
        # Pindah ke tahap berikutnya
        new_status = "triage"
        message = f"Antrian {queue_id} statusnya diubah menjadi Triage."
    elif current_status == "triage":
        # Pindah ke tahap berikutnya (Asumsi)
        new_status = "clinic_entry"
        message = f"Antrian {queue_id} statusnya diubah menjadi Menuju Poli."
    else:
        # Jika status saat ini tidak perlu diupdate
        message = f"Status Antrian {queue_id} ({current_status}) tidak dapat diupdate otomatis dari QR."
        return {"status": "unchanged", "message": message, "current_status": current_status}
        
    if new_status:
        # Perbarui status di database
        queue_record.status = new_status
        db.commit()
        db.refresh(queue_record)
        return {"status": "success", "message": message, "new_status": new_status, "queue_id": queue_id}

    return {"status": "error", "message": "Gagal memproses update status."}