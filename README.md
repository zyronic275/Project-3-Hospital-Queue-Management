# 🏥 Sistem Manajemen Antrean Pasien Rumah Sakit (FastAPI)

Proyek ini adalah implementasi sistem *Manajemen Antrean Pasien* berbasis *API* yang dibangun menggunakan framework *FastAPI* yang cepat dan modern. Sistem ini dirancang untuk mempermudah proses pendaftaran pasien, pengelolaan alur antrean oleh staf medis, serta pencatatan riwayat kunjungan di lingkungan rumah sakit.

---

## 🎯 Tujuan Utama

Sistem ini bertujuan untuk menyediakan solusi API yang efisien dan andal, mendukung fungsi-fungsi berikut:

1.  *Pendaftaran Otomatis: Pasien dapat mendaftar dan secara otomatis mendapatkan **nomor antrean yang berurutan* berdasarkan waktu pendaftaran.
2.  *Manajemen Master Data: Memungkinkan Admin rumah sakit untuk **menambah, memperbarui, dan menghapus* data dokter dan klinik.
3.  *Alur Pelayanan: Dokter atau tenaga medis dapat **memanggil pasien, memperbarui **status pelayanan* (misalnya: menunggu, dilayani, selesai), dan *mencatat hasil kunjungan* pasien.
4.  *Pemantauan: Rumah sakit dapat **memantau riwayat kunjungan* dan *kepadatan antrean* di setiap klinik secara real-time.

---

## ⚙ Fitur Kunci

| Ikon | Fitur | Deskripsi |
| :---: | :--- | :--- |
| 📋 | *Pendaftaran & Penomoran Otomatis* | Pasien didaftarkan dan mendapatkan nomor antrean secara otomatis. |
| 🧑‍⚕ | *Manajemen Master Data (CRUD)* | Pengelolaan data dokter dan klinik. |
| ⏱ | *Pembaruan Status Antrean* | Mengubah status antrean pasien (menunggu, dilayani, selesai). |
| 🩺 | *Pencatatan Hasil Kunjungan* | Endpoint untuk mencatat diagnosis atau hasil pelayanan medis. |
| 📊 | *Pemantauan Riwayat & Statistik* | Melihat riwayat kunjungan dan statistik kepadatan antrean per klinik. |

---

## 🧪 Pengujian dan Dokumentasi

Semua endpoint API dirancang dengan fokus pada kualitas dan kemudahan penggunaan:

* *Unit Test: Seluruh *endpoint *dilengkapi dengan *unit test** untuk menjamin fungsionalitas berjalan dengan benar dan stabil.
* *Dokumentasi Otomatis: API **dapat diuji langsung* melalui interface interaktif *Swagger UI* (/docs) dan *Redoc* (/redoc) yang disediakan otomatis oleh FastAPI.
    * *Akses dokumentasi setelah server berjalan di: http://127.0.0.1:8000/docs*

---

## ⚠ Batasan Implementasi

Penting untuk dicatat bahwa proyek ini adalah implementasi API dasar untuk tujuan studi/prototyping dan memiliki batasan berikut:

* *Data Non-Persistent: **Tidak menggunakan database relasional* atau NoSQL. Data *hanya disimpan sementara* menggunakan struktur data sederhana (list dan dictionary) selama server berjalan. *Data akan hilang* setelah server dihentikan.
* *Tanpa Autentikasi: **Tidak mengimplementasikan mekanisme autentikasi* (seperti JWT atau Basic Auth) untuk menjaga fokus pada alur bisnis inti manajemen antrean.


Jangan lupa setting koneksi mysql di database.py dulu sebelum menjalankan aplikasi!!!
Untuk menjalankan project: uvicorn main:app --reload
Untuk seeding database: python seeder.py