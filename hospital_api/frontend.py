import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time
import qrcode
from PIL import Image
import io
import cv2
import numpy as np

API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="RS Queue System", layout="wide", page_icon="🏥")

st.title("🏥 Sistem Antrean RS (Camera & Barcode)")
menu = st.sidebar.radio("Navigasi", ["Pendaftaran Pasien", "Scanner (Pos RS)", "Dashboard Admin"])

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(str(data))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

def decode_qr_from_image(image_buffer):
    try:
        file_bytes = np.asarray(bytearray(image_buffer.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        return data if data else None
    except: return None

if menu == "Pendaftaran Pasien":
    st.header("📝 Pendaftaran Mandiri")
    st.info("Silakan isi data diri untuk mendapatkan Tiket Antrean & Barcode.")
    
    try:
        res_poli = requests.get(f"{API_URL}/public/polis")
        if res_poli.status_code == 200:
            # Sorting agar poli urut abjad
            pol_list = sorted(res_poli.json(), key=lambda x: x['poli'])
            p_map = {p['poli']: p for p in pol_list}
            
            c1, c2 = st.columns(2)
            with c1:
                nama = st.text_input("Nama Pasien")
                poli_pilih = st.selectbox("Pilih Poliklinik", list(p_map.keys()))
            with c2:
                tgl = st.date_input("Tanggal Kunjungan", min_value=datetime.today())
            
            if poli_pilih:
                res_doc = requests.get(f"{API_URL}/public/available-doctors", params={"poli_name": poli_pilih, "visit_date": str(tgl)})
                docs = res_doc.json()
                
                if not docs:
                    st.warning("Tidak ada dokter tersedia.")
                else:
                    # --- PERBAIKAN DISINI: Menampilkan Jam Praktik ---
                    doc_opts = {}
                    for d in docs:
                        # Ambil 5 karakter pertama jam (08:00:00 -> 08:00)
                        start_time = str(d['practice_start_time'])[:5]
                        end_time = str(d['practice_end_time'])[:5]
                        label = f"{d['dokter']} ({start_time} - {end_time})"
                        doc_opts[label] = d['doctor_id']
                    # -------------------------------------------------

                    doc_label = st.selectbox("Pilih Dokter", list(doc_opts.keys()))
                    
                    if st.button("Daftar & Cetak Tiket", type="primary"):
                        if not nama: st.error("Nama wajib diisi")
                        else:
                            payload = {"nama_pasien": nama, "poli": poli_pilih, "doctor_id": doc_opts[doc_label], "visit_date": str(tgl)}
                            r = requests.post(f"{API_URL}/public/submit", json=payload)
                            
                            if r.status_code == 200:
                                data = r.json()
                                st.success("✅ Pendaftaran Berhasil!")
                                st.divider()
                                
                                # TIKET DIGITAL
                                col_ticket_l, col_ticket_r = st.columns([1, 2])
                                with col_ticket_l:
                                    img = generate_qr(data['id'])
                                    buf = io.BytesIO()
                                    img.save(buf, format="PNG")
                                    st.image(buf, caption=f"ID Tiket: {data['id']}", width=200)
                                
                                with col_ticket_r:
                                    st.subheader(f"Antrean: {data['queue_number']}")
                                    st.write(f"**Nama:** {data['nama_pasien']}")
                                    st.write(f"**Poli:** {data['poli']}")
                                    st.write(f"**Dokter:** {data['dokter']}")
                                    st.write(f"**Jadwal:** {start_time} - {end_time}") # Tampilkan jam juga di tiket
                                    st.warning("📸 Mohon screenshot tiket ini.")
                            else:
                                st.error(f"Gagal: {r.text}")
        else:
            st.error("Gagal koneksi ke Backend.")
    except Exception as e:
        st.error(f"Connection Error: {e}")
elif menu == "Scanner (Pos RS)":
    st.header("📠 Scanner")
    tabs = st.tabs(["📷 Kamera", "⌨️ Manual"])
    
    with tabs[0]:
        st.info("Arahkan QR ke Kamera.")
        loc = st.radio("Lokasi:", ["arrival", "clinic", "finish"], horizontal=True, format_func=lambda x: x.upper())
        img = st.camera_input("Cam")
        if img:
            res = decode_qr_from_image(img)
            if res:
                st.success(f"Terdeteksi: {res}")
                if st.button(f"Proses di {loc.upper()}?"):
                    r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": res, "location": loc})
                    if r.status_code == 200: st.success(f"Sukses: {r.json()['message']}")
                    else: st.error(r.text)
            else: st.warning("QR tidak terbaca.")
            
    with tabs[1]:
        st.write("Input ID atau No Antrean (B-001)")
        m_code = st.text_input("Code")
        m_loc = st.selectbox("Lokasi", ["arrival", "clinic", "finish"])
        if st.button("Proses"):
            r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": m_code, "location": m_loc})
            if r.status_code == 200: st.success(f"Sukses: {r.json()['message']}")
            else: st.error(r.text)

elif menu == "Dashboard Admin":
    st.header("Admin")
    t1, t2, t3, t4 = st.tabs(["Dash", "Dokter", "Poli", "Import"])
    with t1:
        if st.button("Refresh"): st.rerun()
        try:
            df = pd.DataFrame(requests.get(f"{API_URL}/monitor/dashboard").json())
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Wait", df['patients_waiting'].sum())
                c2.metric("Serve", df['patients_being_served'].sum())
                c3.metric("Done", df['patients_finished'].sum())
        except: pass

    with t2:
        with st.form("fd"):
            dn = st.text_input("Nama")
            try: po = [p['poli'] for p in requests.get(f"{API_URL}/public/polis").json()]
            except: po = []
            dp = st.selectbox("Poli", po)
            ts = st.time_input("Start", value=time(8,0))
            te = st.time_input("End", value=time(16,0))
            if st.form_submit_button("Simpan"):
                requests.post(f"{API_URL}/admin/doctors", json={"dokter": dn, "poli": dp, "practice_start_time": ts.strftime("%H:%M"), "practice_end_time": te.strftime("%H:%M"), "max_patients": 20})
                st.success("OK")
        did = st.number_input("Hapus ID", min_value=1)
        if st.button("Hapus"): requests.delete(f"{API_URL}/admin/doctors/{did}"); st.success("Deleted")

    with t3:
        pn = st.text_input("Nama Poli")
        pp = st.text_input("Prefix")
        if st.button("Add Poli"): requests.post(f"{API_URL}/admin/polis", json={"poli": pn, "prefix": pp}); st.success("OK")
        
    with t4:
        cnt = st.number_input("Count", value=10)
        if st.button("Import"): requests.get(f"{API_URL}/admin/import-random-data", params={"count": cnt}); st.success("OK")