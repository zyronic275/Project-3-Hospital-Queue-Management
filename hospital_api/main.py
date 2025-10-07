# hospital_api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import admin, registration, doctor_view

app = FastAPI(title="In-Memory Hospital API")

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(registration.router)
app.include_router(doctor_view.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the In-Memory Hospital API"}