# hospital_api/main.py

from fastapi import FastAPI
from .routers import clinics, doctors, queues
from typing import Optional

app = FastAPI(
    title="Hospital Queue Management API (In-Memory)",
    description="API using only in-memory dictionaries for storage. Data is not persistent.",
    version="2.0.0"
)

app.include_router(clinics.router)
app.include_router(doctors.router)
app.include_router(queues.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the In-Memory Hospital API. Data will reset on server restart."}