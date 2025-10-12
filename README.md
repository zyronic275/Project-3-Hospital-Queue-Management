Hospital Queue Management API
Proyek ini adalah sebuah API untuk sistem manajemen antrean rumah sakit yang dikembangkan sebagai bagian dari Ujian Tengah Semester mata kuliah Kapita Selekta Analitika Data. API ini dibangun menggunakan FastAPI dan dirancang untuk mengelola pendaftaran pasien, data master (dokter dan layanan), serta menyediakan data monitoring secara real-time.

Sesuai batasan tugas, proyek ini tidak menggunakan database dan menyimpan seluruh data secara in-memory.

✨ Fitur Utama
Manajemen Admin: Menyediakan endpoint CRUD (Create, Read, Update, Delete) lengkap untuk mengelola data Layanan (Poli) dan Dokter.

Pendaftaran Pasien: Alur pendaftaran cerdas yang mencakup:

Penugasan dokter otomatis jika hanya ada satu yang tersedia.

Pengecekan kuota pasien secara real-time.

Pembuatan nomor antrean unik harian per dokter.

Pengelolaan Antrean: Kemampuan untuk mengubah status pasien (menunggu, sedang dilayani, selesai).

Dasbor Monitoring: Sebuah endpoint yang mengagregasi data untuk menampilkan kepadatan, jumlah pasien menunggu, dan total pasien di setiap poli.

Validasi Data: Aturan bisnis yang kokoh untuk memastikan keunikan data, seperti prefix poli dan kode dokter per poli.

Dokumentasi Otomatis: Dokumentasi API interaktif tersedia melalui Swagger UI dan ReDoc.

🛠️ Teknologi yang Digunakan
Backend: FastAPI

Server: Uvicorn

Validasi Data: Pydantic

Pengujian: Pytest & freezegun

🚀 Cara Menjalankan Proyek
Untuk menjalankan proyek ini di lingkungan lokal Anda, ikuti langkah-langkah berikut.

1. Prasyarat
Python 3.9+ terinstal di sistem Anda.

2. Instalasi
Clone repository ini:

git clone [URL_REPOSITORY_ANDA]
cd [NAMA_FOLDER_PROYEK]

Buat dan aktifkan virtual environment:

# Untuk Windows
python -m venv .venv
.\.venv\Scripts\activate

# Untuk macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

Install semua dependensi yang dibutuhkan:

pip install -r requirements.txt

3. Menjalankan Server
Dari direktori utama proyek, jalankan server Uvicorn dengan perintah:

uvicorn hospital_api.main:app --reload

Server API akan berjalan dan dapat diakses di http://127.0.0.1:8000.

4. Menjalankan Pengujian
Untuk memastikan semua fungsionalitas berjalan sesuai harapan, jalankan unit test dengan Pytest dari direktori utama:

pytest

🖥️ Antarmuka Pengguna (Frontend)
Proyek ini dilengkapi dengan sebuah dasbor admin index.html yang berfungsi sebagai antarmuka pengguna.

Cara Menggunakan: Cukup buka file index.html di browser Anda setelah server backend berjalan.

Dasbor ini memungkinkan Anda untuk berinteraksi secara visual dengan semua fitur API, termasuk pendaftaran, manajemen data, dan monitoring.

📄 Dokumentasi API
Setelah server berjalan, dokumentasi API interaktif dapat diakses melalui:

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc

Melalui Swagger UI, Anda dapat mencoba setiap endpoint secara langsung dari browser.

👥 Tim Pengembang
Eiya Perimsa Karina Pinem (6162101144)
Justin Ryan Pangestu (6162201005)
Cecilia Christabel Sukmadi (6162201009)
Gabrielle Agneta (6162201015) 
Darrell Zachary Gunawan (6162201069) 
Theresia Aurelia (6162201101)