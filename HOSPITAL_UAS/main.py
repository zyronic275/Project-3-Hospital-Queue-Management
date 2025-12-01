import uvicorn
from fastapi import FastAPI
from app.api import router  # Import router dari folder app

# Inisialisasi App
app = FastAPI(title="Sistem RS Modular")

# Pasang Router dari app/api.py
app.include_router(router)

@app.get("/", tags=["General"])
def root():
    return {"message": "Sistem RS Berjalan. Akses /docs untuk menu."}

# Block ini agar bisa dijalankan langsung dengan 'python main.py'
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)