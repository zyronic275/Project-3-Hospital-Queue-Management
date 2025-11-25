from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def master_root():
    return {"module": "Master", "status": "Ready to implement endpoints (poli, dokter, dll.)"}
