# Sistem Manajemen RS Pintar (Full-Stack + Auth)

Sistem manajemen antrean dan operasional rumah sakit berbasis Full-Stack
Python. Proyek ini telah ditingkatkan dari sekadar pembaca CSV menjadi
aplikasi berbasis Database (MySQL) dengan sistem Autentikasi (Login) dan
Otorisasi Bertingkat (Role-Based).

Sistem ini memisahkan logika bisnis (Backend API) dengan antarmuka
pengguna (Frontend Dashboard), dan menggunakan file CSV lama sebagai
referensi data arsip.

## 🚀 Fitur Utama (Pembaruan)

-   🔐 **Keamanan Terintegrasi**: Sistem Login menggunakan JWT dengan
    enkripsi password.
-   👤 **Multi-Role User**: Akses berbeda untuk Admin, Dokter, Perawat,
    Administrasi, dan Pasien.
-   🗄️ **Database Persistent**: Data disimpan di MySQL via SQLAlchemy.
-   📊 **Dashboard Real-time**: Visualisasi antrean dan analitik.

## 🏗️ Struktur Proyek Baru

    ├── main.py                   # Backend FastAPI
    ├── frontend.py               # Frontend Streamlit
    ├── storage.py                # MySQL ORM Models
    ├── security.py               # Password hashing & JWT
    ├── schemas.py                # Pydantic models
    ├── init_users.py             # Membuat user default
    ├── reset_db.py               # Reset database
    ├── csv_utils.py              # CSV helper
    ├── requirements.txt
    ├── tabel_dokter_normal.csv
    ├── tabel_poli_normal.csv
    └── tabel_pelayanan_normal.csv

## 🛠️ Persiapan Awal (Database Setup)

### 1. Instalasi

Pastikan Python & MySQL sudah terinstal.

    pip install -r requirements.txt

### 2. Inisialisasi Database

Reset & buat tabel kosong:

    python reset_db.py

Buat akun staf & admin:

    python init_users.py

## ⚡ Cara Menjalankan Aplikasi

### Terminal 1 (Backend API):

    fastapi dev main.py

### Terminal 2 (Frontend):

    streamlit run frontend.py

## 🔑 Akun Default

Password default: **123**

| Role | Username | Akses |
| :---: | :--- | :--- |
| Super Admin | admin | Akses penuh |
| Administrasi | admin_depan | Pendaftaran & antrean
| Perawat | perawat | Manajemen status pasien


## 📚 Dokumentasi API

Buka:

    http://127.0.0.1:8000/docs

Endpoint tersedia:

-   `/auth/token`
-   `/admin/*`
-   `/ops/*`
-   `/monitor/*`

## ⚠️ Catatan Penting

1.  Pastikan kredensial MySQL benar di `storage.py`.
2.  File CSV sekarang hanya berfungsi sebagai data awal dan arsip.
