from fastapi import FastAPI
from database import engine, Base

# Import models supaya tabel dibuat otomaƟs
from modules.auth import models as auth_models
from modules.master import models as master_models
from modules.queue import models as queue_models

# Create Tables

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital Queue System (UAS)")

@app.get("/")
def root():
    return {"message": "System Online 띙띚띞띟띛띜띝", "db": "MySQL Connected"}