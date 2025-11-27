CREATE DATABASE IF NOT EXISTS hospital_db;
USE hospital_db;

-- clinics (poliklinik)
CREATE TABLE IF NOT EXISTS clinics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- doctor
CREATE TABLE IF NOT EXISTS doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100),
    clinic_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (clinic_id) REFERENCES clinics(id) ON DELETE SET NULL
);

-- patient
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT,
    gender VARCHAR(10),
    nik VARCHAR(16) UNIQUE NOT NULL,
    phone VARCHAR(20),
    dob DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- visits
CREATE TABLE IF NOT EXISTS visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    date_visit DATE NOT NULL,
    queue_number INT NOT NULL, -- (1, 2, dst)
    status ENUM('waiting', 'in_progress', 'completed', 'cancelled') DEFAULT 'waiting',
    medical_notes TEXT, --  catatan hasil pemeriksaan
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);