from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String(100), nullable=False)
    clinic_code = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)

    # Relasi ke Visit — gunakan "Visit", bukan dotted path
    visits = relationship(
        "Visit",          # <--- sudah benar
        back_populates="doctor"
    )

