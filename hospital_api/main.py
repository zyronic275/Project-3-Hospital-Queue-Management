# hospital_api/main.py

from fastapi import FastAPI
from . import models
from .database import engine
from .routers import clinics, doctors, queues

# This command creates all the tables in the database based on the models
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hospital Queue Management API",
    description="API for managing patient queues, doctors, and clinics.",
    version="1.0.0"
)

# Include the routers from the routers directory
app.include_router(clinics.router)
app.include_router(doctors.router)
app.include_router(queues.router)


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Hospital Queue Management API"}