from fastapi import FastAPI

# Import database engine dan Base
from database import engine, Base

# Import models dari masing-masing modul supaya SQLAlchemy
# dapat membuat tabel (Base.metadata.create_all)
from modules.auth import models as auth_models
from modules.master import models as master_models
from modules.queue import models as queue_models

# Import Routers dari masing-masing modul
from modules.auth.router import router as auth_router
from modules.master.router import router as master_router
from modules.queue.router import router as queue_router


# --- Setup Database ---
# Perintah ini akan mencoba membuat tabel di database MySQL
# jika tabel-tabel tersebut belum ada, berdasarkan model yang diimpor.
Base.metadata.create_all(bind=engine)
# --- End Setup Database ---


# --- Inisialisasi Aplikasi FastAPI ---
app = FastAPI(
    title="Hospital Queue System (UAS)",
    description="Sistem Antrian Rumah Sakit menggunakan FastAPI, SQLAlchemy, dan MySQL.",
    version="1.0.0"
)
# --- End Inisialisasi Aplikasi FastAPI ---


# --- Registrasi Routers ---
# Mendaftarkan router dengan prefix dan tags yang terstruktur
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
app.include_router(
    master_router,
    prefix="/api/v1/master",
    tags=["Master Data (Poli, Dokter)"]
)
app.include_router(
    queue_router,
    prefix="/api/v1/queue",
    tags=["Queue Management"]
)
# --- End Registrasi Routers ---


@app.get("/", tags=["Root"])
def root():
    """
    Endpoint utama untuk mengecek status sistem.
    """
    return {
        "message": "System Online",
        "db": "MySQL Connected"
    }

# Untuk menjalankan aplikasi ini, gunakan perintah:
# uvicorn main:app --reload