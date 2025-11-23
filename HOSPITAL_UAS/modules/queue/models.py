from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum

# --- ENUM untuk Status Antrian ---
# Ini membantu melacak status pasien dengan jelas
class VisitStatus(str, enum.Enum):
WAITING_REG = &quot;Menunggu Pendaftaran&quot;
IN_QUEUE = &quot;Dalam Antrean&quot;
CALLED = &quot;Dipanggil Dokter&quot;
IN_SERVICE = &quot;Sedang Dilayani&quot;
FINISHED = &quot;Selesai Pelayanan&quot;

CANCELED = &quot;Dibatalkan&quot;

# --- MODEL UTAMA: VISIT ---
class Visit(Base):
__tablename__ = &quot;visits&quot;

# Kunci Utama dan Indeks
id = Column(Integer, primary_key=True, index=True)
queue_number = Column(Integer, index=True, nullable=False)

# Data Pasien
patient_name = Column(String(100), nullable=False)
patient_mr_number = Column(String(20), index=True) # Medical Record Number

# Kunci Asing (Foreign Key)
# Menghubungkan kunjungan ini ke dokter tertentu
doctor_id = Column(Integer, ForeignKey(&quot;doctors.id&quot;), nullable=False)

# Status Antrian
status = Column(Enum(VisitStatus), default=VisitStatus.WAITING_REG)

# --- 6 Timestamp Penting (VisitHistory) ---
# 1. Waktu Pendaftaran (Saat entri dibuat, dari QR code scan)
t_register = Column(DateTime, default=datetime.datetime.utcnow)

# 2. Waktu Masuk Antrean (Setelah dokumen pendaftaran diverifikasi)
t_in_queue = Column(DateTime)

# 3. Waktu Dipanggil Dokter
t_called = Column(DateTime)

# 4. Waktu Masuk Ruangan Dokter (Mulai Pelayanan)
t_in_service = Column(DateTime)

# 5. Waktu Selesai Pelayanan Dokter
t_service_finish = Column(DateTime)

# 6. Waktu Selesai Proses Administrasi (Keluar dari Sistem Antrian)
t_finished = Column(DateTime)

# Relasi balik ke tabel Doctor
# Ini harus sesuai dengan back_populates=&quot;visits&quot; di modules/master/models.py
doctor = relationship(&quot;Doctor&quot;, back_populates=&quot;visits&quot;)