import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db
from storage import Base

# Setup In-Memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_root_dashboard_empty():
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert response.json() == []

def test_create_service_and_doctor():
    # 1. Create Service
    service_payload = {"name": "Poli Mata", "prefix": "MATA"}
    res_service = client.post("/admin/services/", json=service_payload)
    assert res_service.status_code == 200
    service_id = res_service.json()["id"]

    # 2. Create Doctor
    doctor_payload = {
        "doctor_code": "007",
        "name": "dr. James Bond",
        "practice_start_time": "00:00:00", # Full day practice for testing
        "practice_end_time": "23:59:59",
        "max_patients": 10,
        "services": [service_id]
    }
    res_doctor = client.post("/admin/doctors/", json=doctor_payload)
    assert res_doctor.status_code == 200

def test_patient_registration_flow():
    # Setup
    s_res = client.post("/admin/services/", json={"name": "Poli Gigi", "prefix": "GIGI"})
    service_id = s_res.json()["id"]
    
    d_res = client.post("/admin/doctors/", json={
        "doctor_code": "101", "name": "drg. Gigi", 
        "practice_start_time": "00:00:00", "practice_end_time": "23:59:59", 
        "max_patients": 5, "services": [service_id]
    })
    doctor_id = d_res.json()["id"]

    # Register
    reg_payload = {
        "patient_name": "Budi Santoso",
        "date_of_birth": "1990-01-01", # New Field Test
        "service_ids": [service_id],
        "doctor_id": doctor_id
    }
    res_reg = client.post("/register", json=reg_payload)
    assert res_reg.status_code == 201
    
    # Verify Queue
    res_queue = client.get(f"/queues/{service_id}")
    assert len(res_queue.json()) == 1