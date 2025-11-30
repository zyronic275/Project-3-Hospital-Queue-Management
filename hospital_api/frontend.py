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

menu = st.sidebar.radio(
    "Navigasi",
    ["📝 Pendaftaran Pasien", "📠 Scanner (Pos RS)", "📺 Layar Antrean TV", "📊 Dashboard Admin", "📈 Analisis Data Lanjutan"]
)

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
# 1. PENDAFTARAN
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
                                    cL, cR = st.columns([1, 2])
                                    with cL:
                                        buf = io.BytesIO()
                                        generate_qr(d['id']).save(buf, format="PNG")
                                        st.image(buf, caption=f"ID System: {d['id']}", width=200)
                                    with cR:
                                        st.subheader(f"Antrean: {d['queue_number']}")
                                        st.markdown(f"**Nama:** {d['nama_pasien']}")
                                        st.markdown(f"**Poli:** {d['poli']} | **Dokter:** {d['dokter']}")
                                        st.markdown(f"**Jadwal:** {pilih_doc_label.split('(')[-1][:-1]}")
                                        st.info("Status: Terdaftar (Belum Check-in)")
                                else: st.error(r.text)
            else: st.error("Gagal load Poli.")
        except Exception as e: st.error(f"Koneksi Error: {e}")

    with tab_cek:
        st.subheader("Cari Tiket")
        c_src1, c_src2 = st.columns([2, 1])
        with c_src1: cari_nama = st.text_input("Nama Pasien", key="search_name")
        with c_src2: 
            filter_tgl = st.checkbox("Filter Tanggal", value=True, key="chk_filter")
            if filter_tgl: cari_tgl = st.date_input("Pilih Tgl", value=datetime.today(), key="search_date")
            else: cari_tgl = None

        if st.button("🔍 Cari", key="btn_search"):
            if cari_nama:
                try:
                    params = {"nama": cari_nama}
                    if filter_tgl and cari_tgl: params["target_date"] = str(cari_tgl)
                    r = requests.get(f"{API_URL}/public/find-ticket", params=params)
                    if r.status_code == 200:
                        res = r.json()
                        st.success(f"Ditemukan {len(res)} tiket.")
                        for t in res:
                            with st.container(border=True):
                                cQ, cI = st.columns([1, 3])
                                with cQ:
                                    buf = io.BytesIO()
                                    generate_qr(t['id']).save(buf, format="PNG")
                                    st.image(buf, width=120)
                                with cI:
                                    st.subheader(t['queue_number'])
                                    st.write(f"**Poli:** {t['poli']} | **Dokter:** {t['dokter']}")
                                    st.write(f"**Status:** {t['status_pelayanan']}")
                    else: st.warning("Tidak ditemukan.")
                except: st.error("Error.")

# =================================================================
# 2. SCANNER
# =================================================================
elif menu == "📠 Scanner (Pos RS)":
    st.header("Scanner Barcode")
    tab_cam, tab_man = st.tabs(["📷 Kamera", "⌨️ Manual"])
    with tab_cam:
        loc_cam = st.radio("Lokasi:", ["arrival", "clinic", "finish"], horizontal=True, key="rad_cam")
        img_file = st.camera_input("Kamera", key="cam_input")
        if img_file:
            res = decode_qr_from_image(img_file)
            if res:
                st.success(f"QR: {res}")
                if st.button(f"Proses di {loc_cam}?", key="btn_proc_cam"):
                    try:
                        r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": res, "location": loc_cam})
                        if r.status_code == 200: st.success("Sukses!"); st.metric("Status", r.json()['current_status'])
                        else: st.error(r.text)
                    except: st.error("Gagal.")
    with tab_man:
        m_code = st.text_input("Input Kode", key="man_code")
        m_loc = st.selectbox("Lokasi", ["arrival", "clinic", "finish"], key="man_loc")
        if st.button("Proses", key="btn_proc_man"):
            try:
                r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": m_code, "location": m_loc})
                if r.status_code == 200: st.success("Sukses!"); st.metric("Status", r.json()['current_status'])
                else: st.error(r.text)
            except: st.error("Gagal.")

# =================================================================
# 3. TV
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
# 4. DASHBOARD ADMIN
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
        with st.expander("➕ Tambah"):
            with st.form("f_doc"):
                dn = st.text_input("Nama")
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
        with st.expander("✏️ Edit"):
            ide = st.number_input("ID Edit", min_value=1, key="id_ed")
            if st.button("Load"):
                r = requests.get(f"{API_URL}/admin/doctors/{ide}")
                if r.status_code == 200: st.session_state['ed_data'] = r.json(); st.success("Loaded")
            if 'ed_data' in st.session_state:
                with st.form("fe"):
                    enm = st.text_input("Nama", value=st.session_state['ed_data']['dokter'])
                    # ... simple update form ...
                    if st.form_submit_button("Update"):
                        requests.put(f"{API_URL}/admin/doctors/{ide}", json={"dokter": enm})
                        st.success("Updated")
        
        did = st.number_input("ID Hapus", min_value=1, key="del_doc_id")
        if st.button("Hapus Dokter", key="btn_del_doc"): 
            requests.delete(f"{API_URL}/admin/doctors/{did}")
            st.success("Deleted")

    with t3:
        with st.expander("➕ Tambah"):
            pn = st.text_input("Nama Poli", key="new_pol_name")
            pp = st.text_input("Prefix", key="new_pol_pre")
            if st.button("Simpan Poli", key="btn_save_pol"): 
                requests.post(f"{API_URL}/admin/polis", json={"poli": pn, "prefix": pp})
                st.success("OK")
        with st.expander("✏️ Edit Prefix"):
            pe_nm = st.text_input("Nama Poli", key="pe_nm")
            pe_pr = st.text_input("New Prefix", key="pe_pr")
            if st.button("Update", key="btn_upe"):
                requests.put(f"{API_URL}/admin/polis/{pe_nm}", json={"poli": pe_nm, "prefix": pe_pr})
                st.success("Updated")
        
        pd = st.text_input("Hapus Nama Poli", key="del_pol_name")
        if st.button("Hapus Poli", key="btn_del_pol"): 
            requests.delete(f"{API_URL}/admin/polis/{pd}")
            st.success("Deleted")

    with t4:
        cnt = st.number_input("Jml Data", value=10, key="imp_cnt")
        if st.button("Import CSV", key="btn_imp"): 
            requests.get(f"{API_URL}/admin/import-random-data", params={"count": cnt})
            st.success("OK")

# =================================================================
# 5. ANALISIS DATA LANJUTAN (NEW FEATURE)
# =================================================================
elif menu == "📈 Analisis Data Lanjutan":
    st.header("📈 Pusat Analisis Data & Prediksi")
    if st.button("🔄 Muat Ulang Analisis", key="btn_reload_anl"): st.rerun()
        
    try:
        with st.spinner("Menghitung statistik..."):
            res = requests.get(f"{API_URL}/analytics/comprehensive-report")
            
        if res.status_code == 200:
            data = res.json()
            if "status" in data and data["status"] == "No Data":
                st.warning("Belum ada data.")
            else:
                kpi1, kpi2, kpi3 = st.columns(3)
                waits = data['avg_wait_per_poli']
                slowest = max(waits, key=waits.get) if waits else "-"
                kpi1.metric("Prediksi Besok", f"{data['prediction']} Org")
                kpi2.metric("Jam Sibuk", f"{data['correlation']['peak_hour']}:00")
                kpi3.metric("Antrean Terlama", f"{waits.get(slowest, 0)} Min", f"di {slowest}")
                st.markdown("---")

                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("📅 Tren Harian")
                    if data['trend_daily']:
                        st.line_chart(pd.DataFrame(list(data['trend_daily'].items()), columns=['Tgl', 'Jml']).set_index('Tgl'))
                with c2:
                    st.subheader("⏰ Jam Sibuk")
                    if data['peak_hours']:
                        st.bar_chart(pd.DataFrame(list(data['peak_hours'].items()), columns=['Jam', 'Jml']).set_index('Jam'))

                st.subheader("⏱️ Efisiensi")
                t1, t2 = st.tabs(["Waktu Tunggu", "Durasi Dokter"])
                with t1: st.bar_chart(data['avg_wait_per_poli'], horizontal=True)
                with t2: st.bar_chart(data['avg_service_per_doc'], horizontal=True)

                st.markdown("---")
                st.subheader("🧠 Insights")
                cor = data['correlation']
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.metric("Avg Tunggu Global", f"{cor['global_avg_wait']} Min")
                    st.metric(f"Avg Tunggu Jam {cor['peak_hour']}", f"{cor['peak_avg_wait']} Min")
                with col_b:
                    diff = cor['increase_pct']
                    if diff > 20: st.error(f"⚠️ Lonjakan {diff}% saat jam sibuk! Tambah dokter.")
                    else: st.success("✅ Antrean terkendali.")
    except Exception as e: st.error(f"Error: {e}")