from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Annotated, List, Optional
from datetime import datetime

# Impor Dependency dan Models
from database import get_db
import auth # Untuk otorisasi dan hashing
import models
import schemas # Menggunakan import penuh untuk semua schemas
from schemas import KlinikCreate, KunjunganCreate, ScanData, DokterCreate

# Import utility untuk QR Code
import qrcode
from io import BytesIO

router = APIRouter(
    prefix="/workflow",
    tags=["Workflow & Antrean"],
)

# --- Dependency untuk Otorisasi Role ---

def check_role(required_roles: list):
    def role_checker(user_info: dict = Depends(auth.get_current_user_role)):
        if user_info["role"] not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user_info['role']}' not authorized for this action.",
            )
        return user_info
    return role_checker

# --- 1. CRUD MASTER ---

# Endpoint CRUD Klinik (Hanya Admin)
@router.post("/kliniks", status_code=status.HTTP_201_CREATED, # response_model=schemas.Klinik, (Opsional)
             dependencies=[Depends(check_role(["admin"]))])
def create_klinik(klinik: KlinikCreate, db: Session = Depends(get_db)):
    # Pastikan kode poli unik dan uppercase
    kode_poli_upper = klinik.kode_poli.upper()
    existing = db.query(models.Klinik).filter(models.Klinik.kode_poli == kode_poli_upper).first()
    if existing:
        raise HTTPException(status_code=400, detail="Kode poli sudah ada.")

    db_klinik = models.Klinik(
        nama=klinik.nama,
        kode_poli=kode_poli_upper
    )
    db.add(db_klinik)
    db.commit()
    db.refresh(db_klinik)
    return db_klinik

# Endpoint CRUD Dokter (Hanya Admin) - Implementasi Penuh
@router.post("/dokters", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(check_role(["admin"]))])
def create_dokter(user: DokterCreate, db: Session = Depends(get_db)):
    # Pastikan username unik
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username sudah digunakan.")

    # Buat User baru dengan hashing password
    db_user = models.User(
        username=user.username,
        role=models.RoleEnum(user.role), # Menggunakan Enum
        password_hash=auth.hash_password(user.password) # Menggunakan auth helper
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": f"User {user.role} {db_user.username} berhasil dibuat.", "user_id": db_user.id}


# --- 2. PENDAFTARAN PASIEN (Kunjungan) ---

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_pasien(kunjungan: KunjunganCreate, db: Session = Depends(get_db)):
    """
    Pendaftaran pasien baru (On-the-spot atau Pre-booking).
    Menerima field Gender, Umur, Insurance yang baru (Sinkron dengan Schemas).
    """
    klinik = db.query(models.Klinik).get(kunjungan.klinik_id)
    if not klinik:
        raise HTTPException(status_code=404, detail="Klinik tidak ditemukan.")

    # Validasi Gender ke Enum
    try:
        gender_enum = models.GenderEnum(kunjungan.gender)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nilai gender tidak valid. Harus 'Laki-laki' atau 'Perempuan'.")

    # Membuat entri kunjungan baru
    db_kunjungan = models.Kunjungan(
        nama_pasien=kunjungan.nama_pasien.upper(), # Auto Uppercase
        email=kunjungan.email,
        tgl_lahir=kunjungan.tgl_lahir,
        # === Menerima FIELD BARU ===
        gender=gender_enum,
        umur=kunjungan.umur,
        insurance=kunjungan.insurance,
        # ==========================
        tanggal_kunjungan=kunjungan.tanggal_kunjungan,
        klinik_id=kunjungan.klinik_id,
        dokter_id=kunjungan.dokter_id,
        status=models.StatusKunjungan.TERDAFTAR # Default status
    )

    db.add(db_kunjungan)
    db.commit()
    db.refresh(db_kunjungan)
    return {"message": "Pendaftaran berhasil", "kunjungan_id": db_kunjungan.id}

# --- 3. QR CODE GENERATOR ---

@router.get("/kunjungan/{kunjungan_id}/barcode")
def get_barcode(kunjungan_id: int, db: Session = Depends(get_db)):
    """
    Menghasilkan QR code untuk ID kunjungan tertentu.
    """
    kunjungan = db.query(models.Kunjungan).get(kunjungan_id)
    if not kunjungan:
        raise HTTPException(status_code=404, detail="Kunjungan tidak ditemukan.")

    data_to_encode = str(kunjungan_id)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data_to_encode)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return Response(content=buffer.getvalue(), media_type="image/png")

# --- 4. ALUR KERJA INTERAKTIF (SCAN BARCODE) ---

@router.post("/scan",
             dependencies=[Depends(check_role(["staff", "dokter"]))])
def scan_update_status(scan_data: ScanData, db: Session = Depends(get_db)):
    """
    Memperbarui status kunjungan berdasarkan QR code scan (Logika lengkap).
    """
    kunjungan = db.query(models.Kunjungan).get(scan_data.qr_code_id)

    if not kunjungan:
        raise HTTPException(status_code=404, detail="Kunjungan aktif tidak ditemukan.")

    new_status = scan_data.next_status.upper()
    current_status = kunjungan.status.value

    # 1. Logic: CHECKIN
    if new_status == models.StatusKunjungan.CHECKIN.value:
        if current_status != models.StatusKunjungan.TERDAFTAR.value:
             raise HTTPException(status_code=400, detail="Status tidak valid. Harus 'TERDAFTAR' sebelum 'CHECKIN'.")
        kunjungan.waktu_checkin = datetime.now()
        kunjungan.status = models.StatusKunjungan.CHECKIN
        message = "Pasien Check-in berhasil (Scan Tensi/Frontdesk)."

    # 2. Logic: MENUNGGU
    elif new_status == models.StatusKunjungan.MENUNGGU.value:
        if current_status != models.StatusKunjungan.CHECKIN.value:
             raise HTTPException(status_code=400, detail="Status tidak valid. Harus 'CHECKIN' sebelum 'MENUNGGU'.")
        kunjungan.status = models.StatusKunjungan.MENUNGGU
        message = "Pasien masuk antrean poli (MENUNGGU)."

    # 3. Logic: DIPANGGIL
    elif new_status == models.StatusKunjungan.DIPANGGIL.value:
        if current_status != models.StatusKunjungan.MENUNGGU.value:
            raise HTTPException(status_code=400, detail="Status tidak valid. Harus 'MENUNGGU' sebelum 'DIPANGGIL'.")

        kunjungan.waktu_panggil = datetime.now()
        kunjungan.status = models.StatusKunjungan.DIPANGGIL
        message = "Pasien **DIPANGGIL** Dokter. Waktu panggil dicatat."

    # 4. Logic: SELESAI (Pindah ke Riwayat/Monitoring)
    elif new_status == models.StatusKunjungan.SELESAI.value:
        if current_status != models.StatusKunjungan.DIPANGGIL.value:
            raise HTTPException(status_code=400, detail="Status tidak valid. Harus 'DIPANGGIL' sebelum 'SELESAI'.")

        kunjungan.waktu_selesai = datetime.now()
        kunjungan.status = models.StatusKunjungan.SELESAI

        # LOGIKA KRUSIAL: Pindahkan ke RiwayatKunjungan (Salin semua field BARU)
        riwayat_data = models.RiwayatKunjungan(
            **{k: v for k, v in kunjungan.__dict__.items() if not k.startswith('_')}
        )
        riwayat_data.id = None
        riwayat_data.status = models.StatusKunjungan.SELESAI

        db.add(riwayat_data)
        db.delete(kunjungan)
        message = "Pelayanan **SELESAI**. Data dipindahkan ke Modul Monitoring."

    # 5. Logic: CANCEL / NO_SHOW (Pindah ke Riwayat/Monitoring)
    elif new_status in [models.StatusKunjungan.CANCEL.value, models.StatusKunjungan.NO_SHOW.value]:
        if current_status == models.StatusKunjungan.SELESAI.value:
             raise HTTPException(status_code=400, detail="Tidak dapat mengubah status dari 'SELESAI'.")

        kunjungan.status = models.StatusKunjungan(new_status)

        # Buat entri Riwayat dengan flags (Salin semua field BARU)
        riwayat_data = models.RiwayatKunjungan(
            **{k: v for k, v in kunjungan.__dict__.items() if not k.startswith('_')}
        )
        riwayat_data.id = None
        riwayat_data.is_cancelled = (new_status == models.StatusKunjungan.CANCEL.value)
        riwayat_data.is_noshow = (new_status == models.StatusKunjungan.NO_SHOW.value)

        db.add(riwayat_data)
        db.delete(kunjungan)
        message = f"Kunjungan diubah menjadi **{new_status}**. Data dipindahkan ke Modul Monitoring."

    # 6. Logic: Error Handling Status Invalid
    else:
        try:
             kunjungan.status = models.StatusKunjungan(new_status)
        except ValueError:
             raise HTTPException(status_code=400, detail=f"Status {new_status} tidak valid.")
        message = f"Status kunjungan berhasil diperbarui menjadi {new_status} (General Update)."

    db.commit()
    return {"message": message, "kunjungan_id": scan_data.qr_code_id}