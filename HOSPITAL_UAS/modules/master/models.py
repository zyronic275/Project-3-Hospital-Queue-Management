from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relaƟonship
from database import Base

class Doctor(Base):
__tablename__ = "doctors"
id = Column(Integer, primary_key=True, index=True)
doctor_name = Column(String(100), nullable=False)
clinic_code = Column(String(50), nullable=False)
is_acƟve = Column(Boolean, default=True)

# Relasi ke module queue
visits = relaƟonship("modules.queue.models.Visit", back_populates="doctor")