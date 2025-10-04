# hospital_api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine

# HANYA IMPORT ROUTER YANG BARU
from .routers import registration, admin


# Perintah ini akan membuat semua tabel baru di database Anda
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hospital Queue Management API (Revised)",
    description="API for patient registration based on selected services/diseases.",
    version="2.0.0"
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

# HANYA SERTAKAN ROUTER YANG BARU
app.include_router(registration.router)
app.include_router(admin.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Revised Hospital Queue Management API"}