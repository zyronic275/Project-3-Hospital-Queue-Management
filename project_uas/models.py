from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

## ENUMS (Jenis Data Pilihan)
# ---

class GenderEnum(str, enum.Enum):
    laki_laki = "Laki-laki"
    perempuan = "Perempuan"

class RoleEnum(str, enum.Enum):
    admin = "admin"
    dokter = "dokter"
    staff = "staff"

class StatusKunjungan(str, enum.Enum):
    TERDAFTAR = "TERDAFTAR"      # Baru booking/daftar
    CHECKIN = "CHECKIN"          # Sudah scan di Tensi/Frontdesk
    MENUNGGU = "MENUNGGU"        # Masuk antrean poli (Pasien siap dipanggil)
    DIPANGGIL = "DIPANGGIL"      # Sedang diperiksa dokter
    SELESAI = "SELESAI"          # Pelayanan selesai (masuk riwayat)
    CANCEL = "CANCEL"            # Dibatalkan oleh staf/pasien
    NO_SHOW = "NO_SHOW"          # Tidak hadir saat jadwal kunjungan

# ---

## TABEL MASTER (Data Master)
# ---

class User(Base):
    """Model untuk Staf, Dokter, dan Admin (terkait Autentikasi JWT)"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(RoleEnum))

class Klinik(Base):
    """Model untuk Data Klinik/Poli"""
    __tablename__ = "kliniks"
    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String)
    kode_poli = Column(String, unique=True) # Wajib unik

# ---

## TABEL TRANSAKSI (Antrean Aktif & Analisis)
# ---

class Kunjungan(Base):
    """Model untuk Antrean Aktif (dihapus setelah status 'SELESAI')"""
    __tablename__ = "kunjungan"
    id = Column(Integer, primary_key=True, index=True)

    # Data Pasien BARU DITAMBAHKAN
    nama_pasien = Column(String)
    email = Column(String)
    tgl_lahir = Column(String)

    # TAMBAHAN BARU DARI KEBUTUHAN KELOMPOK
    gender = Column(Enum(GenderEnum), nullable=True) # <--- BARU
    umur = Column(Integer, nullable=True)             # <--- BARU (Umur saat ini atau saat kunjungan)
    insurance = Column(String, nullable=True)         # <--- BARU

    # Data Kunjungan & Pre-booking
    tanggal_kunjungan = Column(DateTime)
    klinik_id = Column(Integer, ForeignKey("kliniks.id"))
    dokter_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    status = Column(Enum(StatusKunjungan), default=models.StatusKunjungan.TERDAFTAR)

    # TIMESTAMP WAJIB untuk Analisis Waktu Tunggu & Durasi Layanan
    waktu_daftar = Column(DateTime, default=datetime.now)
    waktu_checkin = Column(DateTime, nullable=True)
    waktu_panggil = Column(DateTime, nullable=True)
    waktu_selesai = Column(DateTime, nullable=True)

    # Relasi SQLAlchemy
    klinik = relationship("Klinik")
    dokter = relationship("User", foreign_keys=[dokter_id])

class RiwayatKunjungan(Base):
    """Model Monitoring (Archive permanen untuk Modul Analisis Data)"""
    __tablename__ = "riwayat_kunjungan"
    id = Column(Integer, primary_key=True, index=True)

    # Data Kunjungan (Mirror dari Kunjungan)
    nama_pasien = Column(String)
    email = Column(String)
    tgl_lahir = Column(String)

    # TAMBAHAN BARU DARI KEBUTUHAN KELOMPOK (Mirror)
    gender = Column(Enum(GenderEnum), nullable=True) # <--- BARU (Mirror)
    umur = Column(Integer, nullable=True)             # <--- BARU (Mirror)
    insurance = Column(String, nullable=True)         # <--- BARU (Mirror)

    tanggal_kunjungan = Column(DateTime)

    # ID Klinik dan Dokter (Disimpan sebagai Integer biasa setelah SELESAI)
    klinik_id = Column(Integer)
    dokter_id = Column(Integer, nullable=True)

    # Status & Flags
    status = Column(Enum(StatusKunjungan))
    is_cancelled = Column(Boolean, default=False)
    is_noshow = Column(Boolean, default=False)

    # TIMESTAMP WAJIB untuk Analisis (Mirror dari Kunjungan)
    waktu_daftar = Column(DateTime)
    waktu_checkin = Column(DateTime, nullable=True)
    waktu_panggil = Column(DateTime, nullable=True)
    waktu_selesai = Column(DateTime, nullable=True)