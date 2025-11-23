from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def queue_root():
    return {"module": "Queue", "status": "Ready to implement endpoints (ambil antrian, panggil antrian, dll.)"}