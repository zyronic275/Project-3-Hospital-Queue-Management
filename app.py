from flask import Flask, request, jsonify, send_file
import qrcode
from io import BytesIO
import datetime

# --- MOCK DATA STATE (MEREPLIKASI DATA JS) ---
# Data Antrean (Visits) dan Pasien hanya disimpan di memori saat server berjalan.
mock_patients = {} # {nik: patient_data}
mock_visits = []
next_queue_number = 1
mock_services = {
    1: {'name': 'Poli Umum', 'prefix': 'A'},
    2: {'name': 'Poli Gigi', 'prefix': 'B'}
}
mock_doctors = {
    1: {'name': 'Andi Pratama', 'clinic_id': 1, 'specialization': 'Umum'},
    3: {'name': 'Citra Dewi', 'clinic_id': 2, 'specialization': 'Ortodonti'},
}

app = Flask(__name__)

# --- ENDPOINT UTAMA REGISTRASI ---
@app.route('/visits/register', methods=['POST'])
def register_visit():
    global next_queue_number
    
    # 1. Ambil data dari permintaan POST (simulasi dari form HTML)
    data = request.json
    
    patient_nik = data.get('patient_nik')
    doctor_id = data.get('doctor_id')
    
    if not patient_nik or not doctor_id:
        return jsonify({"error": "Data NIK dan Doctor ID diperlukan"}), 400

    # 2. Cari/Buat Pasien (Simulasi database NIK unik)
    if patient_nik not in mock_patients:
        # Jika pasien baru, simpan datanya
        mock_patients[patient_nik] = {
            'name': data.get('patient_name'),
            'nik': patient_nik,
            # ... data pasien lainnya
        }
    
    patient = mock_patients[patient_nik]
    doctor = mock_doctors.get(doctor_id)

    if not doctor:
        return jsonify({"error": "Dokter tidak ditemukan"}), 404
    
    clinic = mock_services.get(doctor['clinic_id'])
    clinic_prefix = clinic['prefix']
    
    # 3. Buat Nomor Antrean (Antrean unik harian per klinik)
    today = datetime.date.today().isoformat()
    
    # Filter antrean hari ini untuk klinik ini
    current_clinic_visits = [
        v for v in mock_visits if v['visit_date'] == today and v['clinic_id'] == doctor['clinic_id']
    ]
    
    queue_index = len(current_clinic_visits) + 1
    queue_number = f"{clinic_prefix}{queue_index:03d}"
    
    # 4. Simpan Kunjungan (Visit)
    new_visit = {
        'queue_number': queue_number,
        'patient_nik': patient_nik,
        'doctor_id': doctor_id,
        'clinic_id': doctor['clinic_id'],
        'visit_date': today,
        'status': 'waiting'
    }
    mock_visits.append(new_visit)
    
    # 5. Kembalikan data yang diperlukan untuk QR Code
    return jsonify({
        "visit": new_visit,
        "patient": patient,
        "doctor": doctor,
        "message": "Pendaftaran berhasil"
    }), 201

# --- ENDPOINT PEMBUATAN QR CODE ---
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.json
    queue_number = data.get('queue_number')
    patient_nik = data.get('patient_nik')

    if not queue_number or not patient_nik:
        return jsonify({"error": "Data antrean dan NIK diperlukan"}), 400

    # Data yang dienkripsi
    qr_data = f"Antrean:{queue_number}|NIK:{patient_nik}"
    
    # Logika pembuatan QR Code (menggunakan library qrcode)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Simpan gambar ke buffer memori
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    # Kirim gambar sebagai respons file
    return send_file(
        buffer,
        mimetype='image/png',
        as_attachment=False, # Jangan dipaksa download
        download_name=f'qrcode_{queue_number}.png'
    )

if __name__ == '__main__':
    # Gunakan port lain agar tidak bentrok dengan front-end Anda jika ada
    app.run(debug=True, port=5000)