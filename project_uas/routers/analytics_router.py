from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, extract
from database import get_db
import models
from auth import get_current_user_role
from datetime import timedelta, datetime
from typing import Dict, Any

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# --- DEPENDENCY UNTUK OTORISASI ADMIN/DOKTER ---
def check_analytics_role(user: dict = Depends(get_current_user_role)):
    if user['role'] not in [models.RoleEnum.admin.value, models.RoleEnum.dokter.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Hanya Admin atau Dokter yang dapat mengakses analitik."
        )
    return user

# --- ENDPOINT UTAMA DASHBOARD ANALITIK ---

@router.get("/dashboard")
def get_analytics(user: dict = Depends(check_analytics_role), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Menyajikan data analitik kunci (Rata-rata Waktu Tunggu, Durasi Layanan, Tren, dan Analisis Baru).
    """

    # Kriteria Filter Sukses: SELESAI DAN bukan CANCEL/NO SHOW
    success_filter = [
        models.RiwayatKunjungan.status == models.StatusKunjungan.SELESAI,
        models.RiwayatKunjungan.is_cancelled == False,
        models.RiwayatKunjungan.is_noshow == False
    ]

    # 1. Ambil data RIWAYAT kunjungan yang sukses (untuk perhitungan total)
    visits_success = db.query(models.RiwayatKunjungan).filter(*success_filter).all()

    total_wait_minutes = timedelta(0)
    count_wait = 0
    total_service_minutes = timedelta(0)
    count_service = 0

    for v in visits_success:
        # Hitung Waktu Tunggu (Panggil - Checkin)
        if v.waktu_panggil and v.waktu_checkin:
            wait_time = v.waktu_panggil - v.waktu_checkin
            if wait_time > timedelta(0):
                total_wait_minutes += wait_time
                count_wait += 1

        # Hitung Durasi Layanan (Selesai - Panggil)
        if v.waktu_selesai and v.waktu_panggil:
            service_time = v.waktu_selesai - v.waktu_panggil
            if service_time > timedelta(0):
                total_service_minutes += service_time
                count_service += 1

    # Konversi total_seconds ke menit
    avg_wait = total_wait_minutes.total_seconds() / (count_wait * 60) if count_wait > 0 else 0
    avg_service = total_service_minutes.total_seconds() / (count_service * 60) if count_service > 0 else 0

    # 2. Pasien per Klinik (Poli Paling Ramai)
    pasien_per_klinik = db.query(
        models.Klinik.nama, func.count(models.RiwayatKunjungan.id)
    ).join(
        models.Klinik, models.Klinik.id == models.RiwayatKunjungan.klinik_id
    ).filter(*success_filter
    ).group_by(models.Klinik.nama).order_by(func.count(models.RiwayatKunjungan.id).desc()).all()


    # 3. IDENTIFIKASI JAM SIBUK (Peak Hours Pendaftaran)
    peak_hours = db.query(
        extract('hour', models.RiwayatKunjungan.waktu_daftar).label('hour'),
        func.count(models.RiwayatKunjungan.id).label('count')
    ).filter(
        models.RiwayatKunjungan.waktu_daftar != None # Filter data yang tidak memiliki waktu daftar
    ).group_by('hour').order_by(func.count(models.RiwayatKunjungan.id).desc()).limit(3).all()

    # 4. Dokter dengan Pasien Terbanyak
    Dokter = aliased(models.User)
    top_doctors = db.query(
        Dokter.username, func.count(models.RiwayatKunjungan.id)
    ).join(
        Dokter, Dokter.id == models.RiwayatKunjungan.dokter_id
    ).filter(
        *success_filter,
        Dokter.role == models.RoleEnum.dokter
    ).group_by(Dokter.username).order_by(func.count(models.RiwayatKunjungan.id).desc()).limit(5).all()

    # 5. BARU: Rata-rata Durasi Pelayanan per Klinik (Lama/Cepat Pelayanan)
    # Menghitung selisih waktu_selesai - waktu_panggil dan merata-ratakannya per Klinik
    avg_service_per_clinic = db.query(
        models.Klinik.nama,
        func.avg(
            (func.julianday(models.RiwayatKunjungan.waktu_selesai) - func.julianday(models.RiwayatKunjungan.waktu_panggil)) * 24 * 60
        ).label('avg_service_min') # Konversi hari ke menit
    ).join(
        models.Klinik, models.Klinik.id == models.RiwayatKunjungan.klinik_id
    ).filter(
        models.RiwayatKunjungan.waktu_selesai != None,
        models.RiwayatKunjungan.waktu_panggil != None,
        *success_filter
    ).group_by(models.Klinik.nama).order_by('avg_service_min').all()


    # 6. BARU: Analisis Korelasi (Waktu Tunggu vs Jam Sibuk)
    # Ini adalah cara sederhana untuk menguji korelasi tanpa statistik kompleks
    # Kita ambil rata-rata waktu tunggu global (sudah dihitung di atas) dan waktu tunggu saat jam sibuk
    # Asumsikan jam sibuk adalah 'jam' dari top_busy_hours (misal: jam 9, 10, 11)

    busy_hours_list = [int(h) for h, c in peak_hours]

    # Hitung rata-rata waktu tunggu saat jam sibuk
    avg_wait_busy_query = db.query(
        func.avg(
            (func.julianday(models.RiwayatKunjungan.waktu_panggil) - func.julianday(models.RiwayatKunjungan.waktu_checkin)) * 24 * 60
        )
    ).filter(
        models.RiwayatKunjungan.waktu_panggil != None,
        models.RiwayatKunjungan.waktu_checkin != None,
        extract('hour', models.RiwayatKunjungan.waktu_checkin).in_(busy_hours_list),
        *success_filter
    ).scalar()

    avg_wait_busy = round(avg_wait_busy_query, 2) if avg_wait_busy_query else 0

    correlation_message = (
        f"Global Avg Wait: {round(avg_wait, 2)} min. Avg Wait during Peak Hours ({', '.join(map(str, busy_hours_list))}:00): {avg_wait_busy} min. "
        f"Antrean lebih lama pada jam sibuk: {avg_wait_busy > avg_wait}"
    )


    return {
        "summary": {
            "total_patients_success": len(visits_success),
            "avg_waiting_time_minutes": round(avg_wait, 2),
            "avg_service_time_minutes": round(avg_service, 2),
        },
        "trends": {
            "patients_by_clinic": [{"klinik": k, "jumlah": v} for k, v in pasien_per_klinik],
            "top_busy_hours": [{"hour": int(h), "count": c} for h, c in peak_hours],
            "top_doctors": [{"dokter": d, "patients": c} for d, c in top_doctors],
            # === OUTPUT BARU ===
            "avg_service_time_per_clinic": [{"klinik": k, "avg_service_minutes": round(v, 2)} for k, v in avg_service_per_clinic],
            "correlation_analysis": correlation_message
        }
    }

# --- IMPLEMENTASI BATASAN PREDIKSI (OPSIONAL) ---
@router.get("/prediction", dependencies=[Depends(check_analytics_role)])
def predict_visits():
    """
    Endpoint untuk prediksi kunjungan (Opsional: Regresi Linier Sederhana).
    """
    return {
        "message": "Fitur prediksi menggunakan Regresi Linier Sederhana (Simulasi). Implementasi membutuhkan library eksternal.",
        "prediction_next_month": 185,
        "prediction_next_week": 45
    }