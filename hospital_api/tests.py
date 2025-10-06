from fastapi.testclient import TestClient
from ..main import app
from .. import storage
import pytest

# Create a client to make requests to the API
client = TestClient(app)

# A pytest fixture to reset the in-memory storage before each test
@pytest.fixture(autouse=True)
def reset_storage():
    """This runs before each test function to ensure a clean state."""
    storage.CLINICS.clear()
    storage.DOCTORS.clear()
    storage.QUEUES.clear()
    storage.next_clinic_id = 1
    storage.next_doctor_id = 1
    storage.next_queue_id = 1
    yield # The test runs here

# --- Tests ---

def test_create_clinic():
    response = client.post("/clinics/", json={"name": "Poli Umum"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Poli Umum"
    assert data["id"] == 1
    assert 1 in storage.CLINICS

def test_create_doctor_success():
    # First, create a clinic
    client.post("/clinics/", json={"name": "Poli Jantung"})
    
    # Then, create a doctor for that clinic
    response = client.post(
        "/doctors/", 
        json={"name": "Dr. Budi", "specialization": "Cardiologist", "clinic_id": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dr. Budi"
    assert data["clinic_id"] == 1
    assert 1 in storage.DOCTORS

def test_fail_to_create_second_doctor_for_same_clinic():
    # Create a clinic and a doctor
    client.post("/clinics/", json={"name": "Poli Jantung"})
    client.post(
        "/doctors/", 
        json={"name": "Dr. Budi", "specialization": "Cardiologist", "clinic_id": 1}
    )

    # Attempt to create a second doctor for the same clinic
    response = client.post(
        "/doctors/", 
        json={"name": "Dr. Ani", "specialization": "Cardiologist", "clinic_id": 1}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Clinic already has an assigned doctor"

def test_register_patient_queue():
    # Setup clinic and doctor
    client.post("/clinics/", json={"name": "Poli Umum"})
    client.post(
        "/doctors/", 
        json={"name": "Dr. Susi", "specialization": "General Practitioner", "clinic_id": 1}
    )

    # Register a patient
    response = client.post(
        "/register-patient/",
        json={"patient_name": "Wawan", "clinic_id": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_name"] == "Wawan"
    assert data["queue_number"] == 1
    assert data["clinic_id"] == 1
    assert data["doctor_id"] == 1 # Automatically assigned
    assert data["status"] == "menunggu"

    # Register a second patient to the same clinic
    response = client.post(
        "/register-patient/",
        json={"patient_name": "Tuti", "clinic_id": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["queue_number"] == 2