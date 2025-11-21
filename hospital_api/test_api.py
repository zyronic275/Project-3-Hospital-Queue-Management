import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import your application and database models
from main import app, get_db
from storage import Base

# 1. SETUP TEST DATABASE (In-Memory SQLite)
# We use StaticPool so the in-memory data persists across multiple requests within one test session
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. OVERRIDE DEPENDENCY
# This tells FastAPI: "When a route asks for 'get_db', give them this test database instead."
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# 3. INITIALIZE CLIENT & TABLES
client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    """
    This fixture runs automatically before every test function.
    It creates fresh tables, runs the test, and then drops the tables.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables (clean slate for next test)
    Base.metadata.drop_all(bind=engine)

# =================================================================
# TEST CASES
# =================================================================

def test_root_dashboard_empty():
    """Test that the dashboard loads empty initially."""
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert response.json() == []

def test_create_service_and_doctor():
    """
    Integration test:
    1. Create a Service (Poli)
    2. Create a Doctor assigned to that Poli
    3. Verify they exist
    """
    # 1. Create Service
    service_payload = {"name": "Poli Mata", "prefix": "MATA"}
    res_service = client.post("/admin/services/", json=service_payload)
    assert res_service.status_code == 200
    service_data = res_service.json()
    assert service_data["name"] == "Poli Mata"
    service_id = service_data["id"]

    # 2. Create Doctor
    doctor_payload = {
        "doctor_code": "007",
        "name": "dr. James Bond",
        "practice_start_time": "08:00:00",
        "practice_end_time": "16:00:00",
        "max_patients": 10,
        "services": [service_id] # Link to the service we just created
    }
    res_doctor = client.post("/admin/doctors/", json=doctor_payload)
    assert res_doctor.status_code == 200
    doc_data = res_doctor.json()
    assert doc_data["name"] == "dr. James Bond"
    assert doc_data["services"] == [service_id]

def test_patient_registration_flow():
    """
    Full Flow:
    1. Setup Service & Doctor
    2. Patient Registers
    3. Check Queue
    4. Update Status
    """
    # --- SETUP DATA ---
    # Create Service
    s_res = client.post("/admin/services/", json={"name": "Poli Gigi", "prefix": "GIGI"})
    service_id = s_res.json()["id"]
    
    # Create Doctor
    d_payload = {
        "doctor_code": "101", "name": "drg. Gigi", 
        "practice_start_time": "00:00:00", "practice_end_time": "23:59:59", 
        "max_patients": 5, "services": [service_id]
    }
    d_res = client.post("/admin/doctors/", json=d_payload)
    doctor_id = d_res.json()["id"]

    # --- 1. REGISTER PATIENT ---
    reg_payload = {
        "patient_name": "Budi Santoso",
        "service_ids": [service_id],
        "doctor_id": doctor_id
    }
    res_reg = client.post("/register", json=reg_payload)
    assert res_reg.status_code == 201
    data_reg = res_reg.json()
    
    # Verify Ticket
    assert data_reg["patient"]["name"] == "Budi Santoso"
    ticket = data_reg["tickets"][0]
    assert ticket["queue_number"] == "GIGI-101-001"

    # --- 2. CHECK QUEUE ---
    res_queue = client.get(f"/queues/{service_id}")
    assert res_queue.status_code == 200
    queue_list = res_queue.json()
    assert len(queue_list) == 1
    assert queue_list[0]["status"] == "menunggu"
    queue_id = queue_list[0]["id"]

    # --- 3. UPDATE STATUS (Layani) ---
    res_status = client.put(f"/queues/{queue_id}/status", json={"status": "sedang dilayani"})
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "sedang dilayani"

    # --- 4. CHECK DASHBOARD ---
    res_dash = client.get("/admin/dashboard")
    dash_data = res_dash.json()
    # Find our service in dashboard
    target_service = next(item for item in dash_data if item["service_id"] == service_id)
    assert target_service["patients_serving"] == 1
    assert target_service["patients_waiting"] == 0

def test_registration_validation_full_quota():
    """Test that registration fails if doctor is full."""
    # Setup Service & Doctor with max_patients = 1
    s_res = client.post("/admin/services/", json={"name": "Poli Umum", "prefix": "UMUM"})
    sid = s_res.json()["id"]
    
    client.post("/admin/doctors/", json={
        "doctor_code": "A1", "name": "dr. Limited", 
        "practice_start_time": "00:00:00", "practice_end_time": "23:59:59", 
        "max_patients": 1, "services": [sid]
    })
    # Fetch available doctors to get ID
    docs = client.get(f"/services/{sid}/available-doctors").json()
    did = docs[0]["id"]

    # Register Patient 1 (Success)
    client.post("/register", json={"patient_name": "P1", "service_ids": [sid], "doctor_id": did})

    # Register Patient 2 (Should Fail)
    res_fail = client.post("/register", json={"patient_name": "P2", "service_ids": [sid], "doctor_id": did})
    assert res_fail.status_code == 400
    assert "full" in res_fail.json()["detail"] or "penuh" in res_fail.json()["detail"]