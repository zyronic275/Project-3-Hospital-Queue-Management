import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time
import time as time_lib
import qrcode
import io
import cv2
import numpy as np

# --- KONFIGURASI ---
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Sistem RS Terintegrasi", layout="wide", page_icon="🏥")

st.title("🏥 Sistem Manajemen Antrean RS")
st.markdown("---")

menu = st.sidebar.radio("Navigasi", ["📝 Pendaftaran Pasien", "📠 Scanner (Pos RS)", "📺 Layar Antrean TV", "📊 Dashboard Admin"])

# --- HELPERS ---
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

# =================================================================
# 1. PENDAFTARAN (TIKET LENGKAP)
# =================================================================
if menu == "📝 Pendaftaran Pasien":
    st.header("Layanan Pasien")
    tab_daftar, tab_cek = st.tabs(["📝 Daftar Baru", "🔍 Cek Tiket Saya"])
    
    with tab_daftar:
        try:
            res_poli = requests.get(f"{API_URL}/public/polis")
            if res_poli.status_code == 200:
                pol_list = sorted(res_poli.json(), key=lambda x: x['poli'])
                p_map = {p['poli']: p for p in pol_list}
                
                c1, c2 = st.columns(2)
                with c1:
                    nama = st.text_input("Nama Lengkap", key="reg_nama")
                    poli_pilih = st.selectbox("Pilih Poliklinik", list(p_map.keys()), key="reg_poli")
                with c2:
                    tgl = st.date_input("Tanggal Kunjungan", min_value=datetime.today(), key="reg_tgl")
                
                if poli_pilih:
                    res_doc = requests.get(f"{API_URL}/public/available-doctors", params={"poli_name": poli_pilih, "visit_date": str(tgl)})
                    docs = res_doc.json()
                    
                    if not docs: st.warning(f"Tidak ada dokter di {poli_pilih}.")
                    else:
                        doc_opts = {}
                        for d in docs:
                            start = str(d['practice_start_time'])[:5]
                            end = str(d['practice_end_time'])[:5]
                            # FORMAT LABEL DROPDOWN
                            label = f"{d['dokter']} ({start}-{end})"
                            doc_opts[label] = d['doctor_id']
                        
                        pilih_doc_label = st.selectbox("Pilih Dokter", list(doc_opts.keys()), key="reg_doc")
                        
                        if st.button("Daftar & Cetak Tiket", type="primary", key="btn_daftar"):
                            if not nama: st.error("Nama wajib diisi!")
                            else:
                                payload = {"nama_pasien": nama, "poli": poli_pilih, "doctor_id": doc_opts[pilih_doc_label], "visit_date": str(tgl)}
                                r = requests.post(f"{API_URL}/public/submit", json=payload)
                                if r.status_code == 200:
                                    d = r.json()
                                    st.success("✅ Berhasil!")
                                    st.divider()
                                    
                                    # TAMPILAN TIKET LENGKAP
                                    cL, cR = st.columns([1, 2])
                                    with cL:
                                        buf = io.BytesIO()
                                        generate_qr(d['id']).save(buf, format="PNG")
                                        st.image(buf, caption=f"ID System: {d['id']}", width=200)
                                    with cR:
                                        st.subheader(f"Nomor Antrean: {d['queue_number']}")
                                        st.markdown(f"**Nama Pasien:** {d['nama_pasien']}")
                                        st.markdown(f"**Poli Tujuan:** {d['poli']}")
                                        # Tampilkan Dokter & Jadwal dari label dropdown yang dipilih
                                        st.markdown(f"**Dokter & Jadwal:** {pilih_doc_label}")
                                        st.markdown(f"**Tanggal:** {tgl.strftime('%d %B %Y')}")
                                        st.info("Simpan QR Code ini untuk check-in.")
                                else: st.error(r.text)
            else: st.error("Gagal load Poli.")
        except Exception as e: st.error(f"Koneksi Error: {e}")

    # --- TAB 2: CEK TIKET SAYA (DENGAN FILTER TANGGAL) ---
    with tab_cek:
        st.subheader("Cari Tiket Anda")
        st.write("Cari riwayat pendaftaran Anda untuk melihat kembali Barcode/Nomor Antrean.")
        
        # Layout Input
        c_src1, c_src2 = st.columns([2, 1])
        
        with c_src1:
            cari_nama = st.text_input("Masukkan Nama Pasien", placeholder="Contoh: Budi", key="search_name")
        
        with c_src2:
            # Checkbox untuk mengaktifkan filter tanggal
            filter_tgl = st.checkbox("Filter Tanggal?", value=True, key="chk_filter_tgl")
            if filter_tgl:
                cari_tgl = st.date_input("Pilih Tanggal", value=datetime.today(), key="search_date")
            else:
                cari_tgl = None

        if st.button("🔍 Cari Tiket", key="btn_search"):
            if cari_nama:
                try:
                    # Susun Parameter Request
                    params = {"nama": cari_nama}
                    if filter_tgl and cari_tgl:
                        params["target_date"] = str(cari_tgl)

                    # Request ke Backend
                    r = requests.get(f"{API_URL}/public/find-ticket", params=params)
                    
                    if r.status_code == 200:
                        results = r.json()
                        st.success(f"Ditemukan {len(results)} tiket.")
                        
                        # Tampilkan Hasil
                        for ticket in results:
                            with st.container(border=True):
                                c_qr, c_info = st.columns([1, 3])
                                
                                with c_qr:
                                    buf = io.BytesIO()
                                    # Generate QR Code ulang dari ID
                                    generate_qr(ticket['id']).save(buf, format="PNG")
                                    st.image(buf, width=130, caption="Scan Me")
                                
                                with c_info:
                                    # Header Status (Warna-warni dikit biar bagus)
                                    status = ticket['status_pelayanan']
                                    if status == "Menunggu": icon = "🕒"
                                    elif status == "Melayani": icon = "🔊"
                                    elif status == "Selesai": icon = "✅"
                                    else: icon = "📝"
                                    
                                    st.subheader(f"{ticket['queue_number']}")
                                    st.caption(f"{icon} Status: **{status}**")
                                    
                                    st.markdown(f"**Pasien:** {ticket['nama_pasien']}")
                                    st.markdown(f"**Poli:** {ticket['poli']} | **Dokter:** {ticket['dokter']}")
                                    st.markdown(f"**Tanggal:** {ticket['visit_date']}")
                    else:
                        # Tampilkan pesan error dari backend (misal: Tidak ditemukan)
                        st.warning(f"❌ {r.json().get('detail', 'Data tidak ditemukan.')}")
                except Exception as e:
                    st.error(f"Error Koneksi: {e}")
            else:
                st.warning("Mohon isi nama pasien terlebih dahulu.")

# =================================================================
# 2. SCANNER (Pos RS)
# =================================================================
elif menu == "📠 Scanner (Pos RS)":
    st.header("Scanner Barcode")
    tab_cam, tab_man = st.tabs(["📷 Kamera", "⌨️ Manual"])
    with tab_cam:
        st.info("Arahkan QR Code pasien ke kamera webcam dengan jelas.")
        
        loc_cam = st.radio("Lokasi Pos:", ["arrival", "clinic", "finish"], 
                           format_func=lambda x: x.upper(), horizontal=True, key="rad_cam")
        
        img_file = st.camera_input("Kamera", key="cam_input")
        
        if img_file:
            # Tampilkan spinner loading
            with st.spinner("Sedang memindai..."):
                res_text = decode_qr_from_image(img_file)
            
            if res_text:
                # JIKA BERHASIL BACA
                st.success(f"✅ QR Code Terdeteksi: **{res_text}**")
                st.write("Klik tombol di bawah untuk memproses:")
                
                # Tombol Aksi
                if st.button(f"🚀 Proses di {loc_cam.upper()}", key="btn_proc_cam", type="primary"):
                    payload = {"barcode_data": res_text, "location": loc_cam}
                    try:
                        r = requests.post(f"{API_URL}/ops/scan-barcode", json=payload)
                        if r.status_code == 200:
                            st.balloons()
                            st.success(f"✅ SUKSES: {r.json()['message']}")
                            st.metric("Status Baru", r.json()['current_status'])
                        else:
                            st.error(f"❌ Gagal Server: {r.json().get('detail', r.text)}")
                    except Exception as e:
                        st.error(f"Error Koneksi API: {e}")
            else:
                # JIKA GAGAL BACA
                st.warning("⚠️ QR Code tidak terbaca.")
                st.info("Tips: Dekatkan QR Code ke kamera, pastikan cahaya cukup, dan QR tidak buram.")
    with tab_man:
        m_code = st.text_input("Input Kode", key="man_code")
        m_loc = st.selectbox("Lokasi", ["arrival", "clinic", "finish"], key="man_loc")
        if st.button("Proses", key="btn_proc_man"):
            try:
                r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": m_code, "location": m_loc})
                if r.status_code == 200: st.success("Sukses!")
                else: st.error(r.text)
            except: st.error("Gagal.")

# =================================================================
# 3. LAYAR TV
# =================================================================
elif menu == "📺 Layar Antrean TV":
    st.markdown("<h1 style='text-align: center;'>JADWAL ANTREAN RS</h1>", unsafe_allow_html=True)
    ph = st.empty()
    do_ref = st.checkbox("Auto-Refresh", value=True, key="chk_refresh")
    try:
        r = requests.get(f"{API_URL}/monitor/queue-board")
        if r.status_code == 200:
            df = pd.DataFrame(r.json())
            with ph.container():
                if not df.empty:
                    df = df[['queue_number', 'poli', 'dokter', 'status_pelayanan']]
                    df.columns = ['NO', 'POLI', 'DOKTER', 'STATUS']
                    serving = df[df['STATUS']=='Melayani']
                    if not serving.empty:
                        st.warning("🔊 SEDANG DILAYANI")
                        st.dataframe(serving, use_container_width=True, hide_index=True)
                    waiting = df[df['STATUS']=='Menunggu']
                    if not waiting.empty:
                        st.info("🕒 MENUNGGU")
                        st.dataframe(waiting, use_container_width=True, hide_index=True)
                else: st.success("Tidak ada antrean.")
    except: pass
    if do_ref:
        time_lib.sleep(5)
        st.rerun()

# =================================================================
# 4. DASHBOARD ADMIN (UPDATE: EDIT DOKTER & POLI)
# =================================================================
elif menu == "📊 Dashboard Admin":
    st.header("Admin Panel")
    t1, t2, t3, t4 = st.tabs(["Dash", "Dokter", "Poli", "Import"])
    
    with t1:
        tgl = st.date_input("Tanggal", value=datetime.today(), key="dash_date")
        if st.button("Refresh", key="btn_dash_ref"): st.rerun()
        try:
            r = requests.get(f"{API_URL}/monitor/dashboard", params={"target_date": str(tgl)})
            if r.status_code == 200:
                df = pd.DataFrame(r.json())
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    c1, c2 = st.columns(2)
                    c1.metric("Total Pasien", df['total_patients_today'].sum())
                    c2.metric("Selesai", df['patients_finished'].sum())
                else: st.info("No Data.")
        except: pass

    with t2:
        st.subheader("Kelola Dokter")
        with st.expander("➕ Tambah Dokter Baru"):
            with st.form("f_doc_add"):
                dn = st.text_input("Nama Dokter")
                try: pols = [x['poli'] for x in requests.get(f"{API_URL}/public/polis").json()]
                except: pols = []
                dp = st.selectbox("Poli", pols)
                c1, c2 = st.columns(2)
                t1_ = c1.time_input("Start", value=time(8,0))
                t2_ = c2.time_input("End", value=time(16,0))
                dm = st.number_input("Kuota", value=20)
                if st.form_submit_button("Simpan"):
                    requests.post(f"{API_URL}/admin/doctors", json={"dokter": dn, "poli": dp, "practice_start_time": t1_.strftime("%H:%M"), "practice_end_time": t2_.strftime("%H:%M"), "max_patients": dm})
                    st.success("OK")
        
        with st.expander("✏️ Edit Dokter"):
            id_edit = st.number_input("ID Dokter yg akan diedit", min_value=1, key="id_edit_doc")
            if st.button("Load Data", key="btn_load_doc"):
                r = requests.get(f"{API_URL}/admin/doctors/{id_edit}")
                if r.status_code == 200:
                    st.session_state['edit_doc_data'] = r.json()
                    st.success("Data loaded.")
                else: st.error("Tidak ditemukan.")
            
            if 'edit_doc_data' in st.session_state:
                ddata = st.session_state['edit_doc_data']
                with st.form("f_doc_edit"):
                    ed_nama = st.text_input("Nama", value=ddata['dokter'])
                    # Parsing jam lama untuk default value
                    def_t1 = datetime.strptime(ddata['practice_start_time'][:5], "%H:%M").time()
                    def_t2 = datetime.strptime(ddata['practice_end_time'][:5], "%H:%M").time()
                    ed_t1 = st.time_input("Start", value=def_t1)
                    ed_t2 = st.time_input("End", value=def_t2)
                    ed_max = st.number_input("Kuota", value=ddata['max_patients'])
                    
                    if st.form_submit_button("Update Dokter"):
                        payload = {
                            "dokter": ed_nama,
                            "practice_start_time": ed_t1.strftime("%H:%M"),
                            "practice_end_time": ed_t2.strftime("%H:%M"),
                            "max_patients": ed_max
                        }
                        r = requests.put(f"{API_URL}/admin/doctors/{id_edit}", json=payload)
                        if r.status_code == 200: st.success("Updated!"); del st.session_state['edit_doc_data']
                        else: st.error(r.text)

        with st.expander("❌ Hapus Dokter"):
            did = st.number_input("ID Hapus", min_value=1, key="del_doc_id")
            if st.button("Hapus", key="btn_del_doc"): 
                requests.delete(f"{API_URL}/admin/doctors/{did}")
                st.success("Deleted")

    with t3:
        st.subheader("Kelola Poli")
        with st.expander("➕ Tambah Poli"):
            pn = st.text_input("Nama Poli", key="new_pol_name")
            pp = st.text_input("Prefix", key="new_pol_pre")
            if st.button("Simpan Poli", key="btn_save_pol"): 
                r = requests.post(f"{API_URL}/admin/polis", json={"poli": pn, "prefix": pp})
                if r.status_code == 200: st.success("OK")
                else: st.error(r.text)
        
        with st.expander("✏️ Edit Poli (Prefix)"):
            ep_name = st.text_input("Nama Poli yg diedit", key="ep_name")
            ep_new_pre = st.text_input("Prefix Baru", key="ep_new_pre")
            if st.button("Update Prefix", key="btn_upd_pol"):
                r = requests.put(f"{API_URL}/admin/polis/{ep_name}", json={"poli": ep_name, "prefix": ep_new_pre})
                if r.status_code == 200: st.success("Updated!")
                else: st.error(r.text)

        with st.expander("❌ Hapus Poli"):
            pd = st.text_input("Hapus Nama Poli", key="del_pol_name")
            if st.button("Hapus Poli", key="btn_del_pol"): 
                requests.delete(f"{API_URL}/admin/polis/{pd}")
                st.success("Deleted")

    with t4:
        cnt = st.number_input("Jml Data", value=10, key="imp_cnt")
        if st.button("Import CSV", key="btn_imp"): 
            requests.get(f"{API_URL}/admin/import-random-data", params={"count": cnt})
            st.success("OK")