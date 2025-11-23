from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum


# --- ENUM untuk Status Antrian ---
class VisitStatus(str, enum.Enum):
    WAITING_REG = "Menunggu Pendaftaran"
    IN_QUEUE = "Dalam Antrean"
    CALLED = "Dipanggil Dokter"
    IN_SERVICE = "Sedang Dilayani"
    FINISHED = "Selesai Pelayanan"
    CANCELED = "Dibatalkan"


# --- MODEL UTAMA: VISIT ---
class Visit(Base):
    __tablename__ = "visits"

    # Kunci Utama
    id = Column(Integer, primary_key=True, index=True)

    # Nomor Antrian
    queue_number = Column(Integer, index=True, nullable=False)

    # Data Pasien
    patient_name = Column(String(100), nullable=False)
    patient_mr_number = Column(String(20), index=True)

    # Relasi ke Doctor (FK)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)

    # Status Antrian
    status = Column(Enum(VisitStatus), default=VisitStatus.WAITING_REG)

    # Timestamps
    t_register = Column(DateTime, default=datetime.datetime.utcnow)
    t_in_queue = Column(DateTime)
    t_called = Column(DateTime)
    t_in_service = Column(DateTime)
    t_service_finish = Column(DateTime)
    t_finished = Column(DateTime)

    # Relasi balik ke Doctor
    doctor = relationship("modules.master.models.Doctor", back_populates="visits")