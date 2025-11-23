from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship # **DIPERBAIKI: &#39;relationship&#39;**
from database import Base

class Doctor(Base):
__tablename__ = &quot;doctors&quot;
id = Column(Integer, primary_key=True, index=True)
doctor_name = Column(String(100), nullable=False)
clinic_code = Column(String(50), nullable=False)
is_active = Column(Boolean, default=True) # **DIPERBAIKI: &#39;is_active&#39;**

# Relasi ke module queue
visits = relationship(&quot;modules.queue.models.Visit&quot;, back_populates=&quot;doctor&quot;)