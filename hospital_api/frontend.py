import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time
import time as time_lib # Untuk sleep di layar TV
import qrcode
from PIL import Image
import io
import cv2
import numpy as np

# --- KONFIGURASI ---
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Sistem RS Terintegrasi", layout="wide", page_icon="🏥")

# --- HEADER ---
st.title("🏥 Sistem Manajemen Antrean RS")
st.markdown("---")

# --- SIDEBAR MENU ---
menu = st.sidebar.radio(
    "Navigasi Utama",
    ["📝 Pendaftaran Pasien", "📠 Scanner (Pos RS)", "📺 Layar Antrean TV", "📊 Dashboard Admin"]
)

# --- FUNGSI BANTUAN ---
def generate_qr(data):
    """Membuat QR Code dari string data"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(str(data))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

def decode_qr_from_image(image_buffer):
    """Membaca QR Code dari input kamera"""
    try:
        file_bytes = np.asarray(bytearray(image_buffer.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        return data if data else None
    except:
        return None

# =================================================================
# 1. MENU PENDAFTARAN PASIEN
# =================================================================
if menu == "📝 Pendaftaran Pasien":
    st.header("Pendaftaran Pasien Mandiri")
    st.info("Isi data untuk mendapatkan Nomor Antrean dan Barcode.")
    
    try:
        res_poli = requests.get(f"{API_URL}/public/polis")
        if res_poli.status_code == 200:
            # Sortir poli
            pol_list = sorted(res_poli.json(), key=lambda x: x['poli'])
            p_map = {p['poli']: p for p in pol_list}
            
            c1, c2 = st.columns(2)
            with c1:
                nama_pasien = st.text_input("Nama Lengkap Pasien")
                pilih_poli = st.selectbox("Pilih Poliklinik", list(p_map.keys()))
            
            with c2:
                tgl_kunjungan = st.date_input("Tanggal Kunjungan", min_value=datetime.today())
            
            if pilih_poli:
                res_doc = requests.get(f"{API_URL}/public/available-doctors", params={"poli_name": pilih_poli, "visit_date": str(tgl_kunjungan)})
                docs = res_doc.json()
                
                if not docs:
                    st.warning(f"Tidak ada dokter tersedia di {pilih_poli}.")
                else:
                    # Dropdown: Nama Dokter (08:00 - 16:00)
                    doc_opts = {}
                    for d in docs:
                        start = str(d['practice_start_time'])[:5]
                        end = str(d['practice_end_time'])[:5]
                        label = f"{d['dokter']} ({start} - {end})"
                        doc_opts[label] = d['doctor_id']
                    
                    pilih_dokter = st.selectbox("Pilih Dokter", list(doc_opts.keys()))
                    
                    if st.button("Daftar & Cetak Tiket", type="primary"):
                        if not nama_pasien:
                            st.error("Nama Pasien wajib diisi!")
                        else:
                            payload = {
                                "nama_pasien": nama_pasien,
                                "poli": pilih_poli,
                                "doctor_id": doc_opts[pilih_dokter],
                                "visit_date": str(tgl_kunjungan)
                            }
                            
                            try:
                                r = requests.post(f"{API_URL}/public/submit", json=payload)
                                if r.status_code == 200:
                                    data = r.json()
                                    st.balloons()
                                    st.success("✅ Pendaftaran Berhasil!")
                                    st.divider()
                                    
                                    # TIKET
                                    t_col1, t_col2 = st.columns([1, 2])
                                    with t_col1:
                                        qr_img = generate_qr(data['id']) # QR isi ID Database
                                        buf = io.BytesIO()
                                        qr_img.save(buf, format="PNG")
                                        st.image(buf, caption=f"ID System: {data['id']}", width=220)
                                        
                                    with t_col2:
                                        st.subheader(f"Nomor Antrean: {data['queue_number']}")
                                        st.markdown(f"**Nama:** {data['nama_pasien']}")
                                        st.markdown(f"**Poli:** {data['poli']}")
                                        st.markdown(f"**Dokter:** {data['dokter']}")
                                        st.info("Status: Terdaftar (Silakan Check-in di Lobi)")
                                        st.warning("📸 Harap simpan/screenshot tiket ini.")
                                else:
                                    st.error(f"Gagal: {r.text}")
                            except Exception as e:
                                st.error(f"Error Submit: {e}")
        else:
            st.error("Gagal koneksi ke Backend.")
    except Exception as e:
        st.error(f"Koneksi Error: {e}")

# =================================================================
# 2. MENU SCANNER
# =================================================================
elif menu == "📠 Scanner (Pos RS)":
    st.header("Scanner Barcode & Update Status")
    
    tab_cam, tab_man = st.tabs(["📷 Scan via Kamera", "⌨️ Input Manual"])
    
    # --- KAMERA ---
    with tab_cam:
        st.info("Arahkan QR Code pasien ke kamera webcam.")
        loc_cam = st.radio("Lokasi Pos:", ["arrival", "clinic", "finish"], 
                           format_func=lambda x: x.upper(), horizontal=True, key="rad_cam")
        
        img_file = st.camera_input("Kamera")
        if img_file:
            res_text = decode_qr_from_image(img_file)
            if res_text:
                st.success(f"QR Terdeteksi: **{res_text}**")
                if st.button(f"Proses '{res_text}' di {loc_cam.upper()}?", type="primary"):
                    payload = {"barcode_data": res_text, "location": loc_cam}
                    try:
                        r = requests.post(f"{API_URL}/ops/scan-barcode", json=payload)
                        if r.status_code == 200:
                            st.success(f"✅ Sukses: {r.json()['message']}")
                            st.metric("Status Baru", r.json()['current_status'])
                        else:
                            st.error(f"❌ Gagal: {r.json().get('detail', r.text)}")
                    except Exception as e:
                        st.error(f"Error API: {e}")
            else:
                st.warning("QR tidak terbaca.")

    # --- MANUAL ---
    with tab_man:
        st.write("Input ID (Angka) atau No. Antrean (String).")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            manual_code = st.text_input("Input Kode")
        with c_m2:
            manual_loc = st.selectbox("Lokasi Pos", ["arrival", "clinic", "finish"], format_func=lambda x: x.upper())
            
        if st.button("Proses Update Status"):
            if manual_code:
                payload = {"barcode_data": manual_code, "location": manual_loc}
                try:
                    r = requests.post(f"{API_URL}/ops/scan-barcode", json=payload)
                    if r.status_code == 200:
                        st.success(f"✅ Sukses: {r.json()['message']}")
                    else:
                        st.error(f"❌ Gagal: {r.json().get('detail', r.text)}")
                except Exception as e:
                    st.error(f"Error API: {e}")

# =================================================================
# 3. LAYAR ANTREAN TV (FIDS)
# =================================================================
elif menu == "📺 Layar Antrean TV":
    st.markdown("<h1 style='text-align: center; color: #007bff;'>JADWAL ANTREAN RUMAH SAKIT</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center;'>{datetime.now().strftime('%A, %d %B %Y')}</h4>", unsafe_allow_html=True)
    st.markdown("---")

    table_placeholder = st.empty()
    do_refresh = st.checkbox("🔄 Auto-Refresh (5 detik)", value=True)

    try:
        res = requests.get(f"{API_URL}/monitor/queue-board")
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                df = df[['queue_number', 'poli', 'dokter', 'status_pelayanan']]
                df.columns = ['NO. ANTREAN', 'POLIKLINIK', 'DOKTER', 'STATUS']

                with table_placeholder.container():
                    # SECTION 1: SEDANG DILAYANI
                    serving = df[df['STATUS'] == 'Melayani']
                    if not serving.empty:
                        st.warning("🔊 SEDANG MEMANGGIL / DILAYANI")
                        st.dataframe(serving, use_container_width=True, hide_index=True)
                    
                    st.divider()
                    
                    # SECTION 2: MENUNGGU
                    waiting = df[df['STATUS'] == 'Menunggu']
                    if not waiting.empty:
                        st.info("🕒 ANTREAN BERIKUTNYA")
                        st.dataframe(waiting, use_container_width=True, hide_index=True)
                    
                    if serving.empty and waiting.empty:
                        st.success("🎉 Tidak ada antrean aktif saat ini.")
            else:
                st.info("Belum ada antrean yang masuk (Check-in).")
        else:
            st.error("Gagal mengambil data antrean.")
            
    except Exception as e:
        st.error(f"Server Offline: {e}")

    if do_refresh:
        time_lib.sleep(5)
        st.rerun()

# =================================================================
# 4. DASHBOARD ADMIN
# =================================================================
elif menu == "📊 Dashboard Admin":
    st.header("Dashboard & Manajemen Data")
    
    t1, t2, t3, t4 = st.tabs(["📈 Statistik & Riwayat", "👨‍⚕️ Kelola Dokter", "🏥 Kelola Poli", "📥 Import Data"])
    
    # --- TAB 1: STATISTIK ---
    with t1:
        c_filter1, c_filter2 = st.columns([1, 4])
        with c_filter1:
            tgl_pilih = st.date_input("Pilih Tanggal Laporan", value=datetime.today())
        with c_filter2:
            st.write("") 
            if st.button("Lihat Data"): st.rerun()
            
        try:
            res = requests.get(f"{API_URL}/monitor/dashboard", params={"target_date": str(tgl_pilih)})
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                if not df.empty:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Pasien", df['total_patients_today'].sum())
                    m2.metric("Menunggu", df['patients_waiting'].sum())
                    m3.metric("Sedang Periksa", df['patients_being_served'].sum())
                    m4.metric("Selesai", df['patients_finished'].sum())
                    
                    st.bar_chart(df.set_index("poli_name")["total_patients_today"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"Tidak ada data pada {tgl_pilih}.")
        except Exception as e: st.error(f"Error: {e}")

    # --- TAB 2: KELOLA DOKTER ---
    with t2:
        st.subheader("Tambah Dokter")
        with st.form("fd"):
            dn = st.text_input("Nama Dokter")
            try: p_opts = [x['poli'] for x in requests.get(f"{API_URL}/public/polis").json()]
            except: p_opts = []
            dp = st.selectbox("Poli", p_opts)
            c1, c2 = st.columns(2)
            t1 = c1.time_input("Mulai", value=time(8,0))
            t2 = c2.time_input("Selesai", value=time(16,0))
            dm = st.number_input("Kuota", value=20)
            if st.form_submit_button("Simpan"):
                pl = {"dokter": dn, "poli": dp, "practice_start_time": t1.strftime("%H:%M"), "practice_end_time": t2.strftime("%H:%M"), "max_patients": dm}
                r = requests.post(f"{API_URL}/admin/doctors", json=pl)
                if r.status_code == 200: st.success("Sukses")
                else: st.error(r.text)
        
        st.divider()
        did = st.number_input("Hapus ID Dokter", min_value=1)
        if st.button("Hapus Dokter"): 
            requests.delete(f"{API_URL}/admin/doctors/{did}")
            st.success("Terhapus")

    # --- TAB 3: KELOLA POLI ---
    with t3:
        st.subheader("Tambah Poli")
        pn = st.text_input("Nama Poli")
        pp = st.text_input("Prefix")
        if st.button("Simpan Poli"):
            r = requests.post(f"{API_URL}/admin/polis", json={"poli": pn, "prefix": pp})
            if r.status_code == 200: st.success("Sukses")
            else: st.error(r.text)
        
        pd_name = st.text_input("Hapus Poli (Nama)")
        if st.button("Hapus Poli"):
            requests.delete(f"{API_URL}/admin/polis/{pd_name}")
            st.success("Terhapus")

    # --- TAB 4: IMPORT ---
    with t4:
        st.subheader("Import CSV")
        cnt = st.number_input("Jumlah Data", value=10)
        if st.button("Mulai Import"):
            r = requests.get(f"{API_URL}/admin/import-random-data", params={"count": cnt})
            if r.status_code == 200: st.success(r.json()['message'])
            else: st.error(r.text)