from . import crud, schemas

def test_create_clinic():
    clinic = schemas.ClinicCreate(name="Klinik Umum")
    result = crud.create_clinic(clinic)
    assert result["name"] == "Klinik Umum"
    assert result["id"] == 1

def test_create_doctor():
    doctor = schemas.DoctorCreate(name="Dr. Budi", clinic_id=1)
    result = crud.create_doctor(doctor)
    assert result["name"] == "Dr. Budi"
    assert result["clinic_id"] == 1

def test_create_queue():
    queue = schemas.QueueCreate(patient_name="Andi", clinic_id=1, doctor_id=1)
    result = crud.create_queue(queue)
    assert result["patient_name"] == "Andi"
    assert result["status"] == schemas.QueueStatus.MENUNGGU

def test_update_queue_status():
    updated = crud.update_queue_status(1, schemas.QueueStatus.SELESAI)
    assert updated["status"] == schemas.QueueStatus.SELESAI

def test_get_visit_history():
    history = crud.get_visit_history("Andi")
    assert len(history) == 1
    assert history[0]["patient_name"] == "Andi"
