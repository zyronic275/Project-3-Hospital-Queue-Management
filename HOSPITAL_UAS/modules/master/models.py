from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# --- Service Model ---
class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    prefix = Column(String(4), unique=True, nullable=False) # Contoh: 'U' untuk Umum, 'G' untuk Gigi
    is_active = Column(Boolean, default=True)

    # Hubungan ke Dokter (One-to-Many: Satu Service memiliki banyak Doctors)
    doctors = relationship("Doctor", back_populates="service")


# --- Doctor Model (DIUBAH) ---
class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String(100), nullable=False)
    
    # DIUBAH: clinic_code diubah menjadi service_id (ForeignKey)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    
    is_active = Column(Boolean, default=True)

    # Hubungan ke Layanan (Many-to-One: Banyak Doctors terhubung ke satu Service)
    service = relationship("Service", back_populates="doctors")
    
    # Hubungan ke Visit tetap sama
    visits = relationship("modules.queue.models.Visit", back_populates="doctor")

# Catatan: Di Model Visit, doctor_id (ForeignKey("doctors.id")) tetap benar.