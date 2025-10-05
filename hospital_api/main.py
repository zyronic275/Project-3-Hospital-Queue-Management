# hospital_api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine

# Import semua router yang sudah kita buat
from .routers import registration, admin, queue_management, reports

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hospital Queue Management API (Full Version)",
    description="API lengkap untuk manajemen antrean, admin, dokter, dan laporan.",
    version="3.0.0"
)

# Pengaturan CORS
origins = ["null"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sertakan semua router
app.include_router(registration.router)
app.include_router(admin.router)
app.include_router(queue_management.router)
app.include_router(reports.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Full Hospital Queue Management API"}