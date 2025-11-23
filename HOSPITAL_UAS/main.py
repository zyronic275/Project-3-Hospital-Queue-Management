from fastapi import FastAPI

from database import engine, Base

# Model harus diimport supaya SQLAlchemy tahu mereka ada
from modules.auth import models as auth_models
from modules.master import models as master_models
from modules.queue import models as queue_models

# Router
from modules.auth.routers import router as auth_router
from modules.master.routers import router as master_router
from modules.queue.routers import router as queue_router


# --- Setup Database ---
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Hospital Queue System (UAS)",
    description="Sistem Antrian Rumah Sakit menggunakan FastAPI, SQLAlchemy, dan MySQL.",
    version="1.0.0"
)


# Routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(master_router, prefix="/api/v1/master", tags=["Master Data (Poli, Dokter)"])
app.include_router(queue_router, prefix="/api/v1/queue", tags=["Queue Management"])


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "System Online",
        "db": "MySQL Connected"
    }
