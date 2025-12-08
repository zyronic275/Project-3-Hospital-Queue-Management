import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time
import time as time_lib
import qrcode
import io
import cv2
import numpy as np
import json
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- KONFIGURASI ---
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Sistem RS Pintar", layout="wide", page_icon="🏥")

# --- CSS CUSTOM ---
st.markdown("""
<style>
    div.stButton > button:first-child { border-radius: 8px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #007bff; }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 0. SETUP SESSION
# =================================================================
if 'token' not in st.session_state:
    st.session_state.update({'token': None, 'role': None, 'nama_user': None, 'status_member': None, 'selected_doc': None})

# --- HELPERS ---
def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json.dumps(data))
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
# A. LOGIKA LOGIN / REGISTER
# =================================================================
if st.session_state['token'] is None:
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🏥 Sistem Rumah Sakit Pintar</h1>", unsafe_allow_html=True)
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🔐 Login")
        u = st.text_input("Username", key="lu")
        p = st.text_input("Password", type="password", key="lp")
        if st.button("Masuk", type="primary", use_container_width=True):
            try:
                r = requests.post(f"{API_URL}/auth/login", data={"username": u, "password": p})
                if r.status_code == 200:
                    d = r.json()
                    st.session_state.update({'token': d['access_token'], 'role': d['role'], 'nama_user': d['nama'], 'status_member': d.get('status_member')})
                    st.rerun()
                else: st.error(r.json().get('detail'))
            except Exception as e: st.error(f"Error Koneksi: {e}")

    with c2:
        st.subheader("📝 Daftar Pasien Baru")
        rn = st.text_input("Nama Lengkap", key="rn")
        ru = st.text_input("Username", key="ru")
        rp = st.text_input("Password", type="password", key="rp")
        if st.button("Daftar", use_container_width=True):
            if rn and ru and rp:
                try:
                    r = requests.post(f"{API_URL}/auth/register", json={"username": ru, "password": rp, "nama_lengkap": rn, "role": "pasien"})
                    if r.status_code == 200:
                        d = r.json()
                        st.session_state.update({'token': d['access_token'], 'role': d['role'], 'nama_user': d['nama'], 'status_member': "Pasien Baru"})
                        st.success("Berhasil!"); st.rerun()
                    else: st.error(r.json().get('detail'))
                except: st.error("Error Koneksi")

# =================================================================
# B. APLIKASI UTAMA (SETELAH LOGIN)
# =================================================================
else:
    role = st.session_state['role']
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.sidebar.write(f"Halo, **{st.session_state['nama_user']}**")
    st.sidebar.caption(f"Akses: {role.upper()}")
    
    if st.sidebar.button("Logout"):
        st.session_state.clear(); st.rerun()
    st.sidebar.markdown("---")

    # --- DEFINISI MENU ---
    MENU_DAFTAR = "📝 Pendaftaran"
    MENU_RIWAYAT = "📂 Riwayat & Tiket"
    MENU_SCAN = "📠 Scanner QR"
    MENU_DOKTER = "👨‍⚕️ Ruang Periksa"
    MENU_TV = "📺 Layar Antrean"
    MENU_ADMIN = "📊 Dashboard Admin"
    MENU_ANALISIS = "📈 Analisis Data"

    # --- LOGIKA HAK AKSES (SESUAI REQUEST) ---
    menu_opts = []

    # 1. ADMIN (Bisa Semua)
    if role == "super_admin" or role == "admin":
        menu_opts = [MENU_DAFTAR, MENU_SCAN, MENU_DOKTER, MENU_TV, MENU_ADMIN, MENU_ANALISIS]

    # 2. PERAWAT (Scanner + Ruang Periksa)
    elif role == "perawat":
        menu_opts = [MENU_SCAN, MENU_DOKTER]

    # 3. ADMINISTRASI (Pendaftaran, Scanner, TV)
    elif role == "administrasi":
        menu_opts = [MENU_DAFTAR, MENU_SCAN, MENU_TV]

    # 4. PASIEN (Pendaftaran, Layar Antrean + Riwayat)
    elif role == "pasien":
        menu_opts = [MENU_DAFTAR, MENU_RIWAYAT, MENU_TV]

    else:
        menu_opts = [MENU_TV]

    menu = st.sidebar.radio("Navigasi", menu_opts)
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}

    # =================================================================
    # 1. MENU PENDAFTARAN
    # =================================================================
    if menu == MENU_DAFTAR:
        st.header("📝 Pendaftaran Pasien")
        
        try: p_map = {p['poli']: p for p in sorted(requests.get(f"{API_URL}/public/polis").json(), key=lambda x: x['poli'])}
        except: p_map = {}

        c1, c2 = st.columns(2)
        # Auto-Fill Nama jika Pasien
        def_nm = st.session_state['nama_user'] if role == 'pasien' else ""
        lock = True if role == 'pasien' else False
        
        nm = c1.text_input("Nama Pasien", value=def_nm, disabled=lock)
        pl = c1.selectbox("Poli Tujuan", list(p_map.keys()) if p_map else [], index=None, placeholder="Pilih Poli...")
        tg = c2.date_input("Tanggal", min_value=datetime.today())

        if pl:
            st.markdown("### Pilih Dokter")
            try:
                docs = requests.get(f"{API_URL}/public/available-doctors", params={"poli_name": pl}).json()
                if docs:
                    cols = st.columns(3)
                    for i, d in enumerate(docs):
                        with cols[i % 3]:
                            with st.container(border=True):
                                st.subheader(d['dokter'])
                                st.info(f"🕒 {str(d['practice_start_time'])[:5]} - {str(d['practice_end_time'])[:5]}")
                                st.caption(f"Sisa Kuota: {d['max_patients']}")
                                if st.button("Pilih", key=d['doctor_id'], use_container_width=True):
                                    st.session_state['selected_doc'] = d
                                    st.rerun()
                else: st.warning("Dokter libur/tidak tersedia.")
            except: pass
        
        if st.session_state['selected_doc']:
            doc = st.session_state['selected_doc']
            st.success(f"Dokter: {doc['dokter']}")
            if st.button("✅ Konfirmasi", type="primary"):
                try:
                    r = requests.post(f"{API_URL}/public/submit", 
                                      json={"nama_pasien": nm, "poli": pl, "doctor_id": doc['doctor_id'], "visit_date": str(tg)},
                                      headers=headers)
                    if r.status_code == 200:
                        d = r.json()
                        st.balloons()
                        with st.container(border=True):
                            cq, ct = st.columns([1, 2])
                            with cq:
                                buf = io.BytesIO(); generate_qr({"id": d['id'], "antrean": d['queue_number']}).save(buf, format="PNG")
                                st.image(buf, use_container_width=True)
                            with ct:
                                st.subheader(f"No. {d['queue_number']}")
                                st.write(f"**{d['poli']}** - {d['dokter']}")
                                st.write(f"📅 {d['visit_date']}")
                                jam = d.get('doctor_schedule', '-')
                                st.write(f"🕒 {jam}")
                        st.session_state['selected_doc'] = None
                    else: st.error(r.text)
                except Exception as e: st.error(str(e))

    # =================================================================
    # 2. MENU RIWAYAT
    # =================================================================
    elif menu == MENU_RIWAYAT:
        st.header("📂 Tiket & Riwayat Saya")
        try:
            r = requests.get(f"{API_URL}/public/my-history", headers=headers)
            data = r.json()
            if not data: st.info("Belum ada riwayat.")
            else:
                for t in data:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([1, 3, 1])
                        with c1:
                            buf = io.BytesIO(); generate_qr({"id": t['id'], "antrean": t['queue_number']}).save(buf, format="PNG")
                            st.image(buf)
                        with c2:
                            st.subheader(t['queue_number'])
                            st.write(f"**{t['poli']}** | {t['dokter']}")
                            st.caption(f"{t['visit_date']} | {t.get('doctor_schedule', '')}")
                            if t.get('catatan_medis'): st.info(f"Catatan: {t['catatan_medis']}")
                        with c3:
                            st.write(f"Status: **{t['status_pelayanan']}**")
        except: st.error("Gagal load data.")

    # =================================================================
    # 3. MENU SCANNER (Perawat & Administrasi)
    # =================================================================
    elif menu == MENU_SCAN:
        st.header("📠 Scanner QR")
        loc_map = {"Pintu Masuk (Check-in)": "arrival", "Masuk Poli (Panggil)": "clinic", "Selesai (Pulang)": "finish"}
        sel_loc = loc_map[st.radio("Lokasi Scan:", list(loc_map.keys()), horizontal=True)]
        
        t1, t2 = st.tabs(["Kamera", "Manual"])
        with t1:
            img = st.camera_input("Arahkan ke QR")
            if img:
                code = decode_qr_from_image(img)
                if code:
                    try: val = str(json.loads(code.replace("'", '"')).get("antrean", code))
                    except: val = str(code)
                    
                    should_rerun = False
                    try:
                        r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": val, "location": sel_loc})
                        d = r.json()
                        if r.status_code == 200:
                            if d['status'] == 'Success': st.success(f"✅ {d['message']}"); st.balloons(); should_rerun = True
                            elif d['status'] == 'Warning': st.warning(f"⚠️ {d['message']}")
                            else: st.error(f"⛔ {d['message']}")
                        else: st.error(f"❌ {r.text}")
                    except Exception as e: st.error(f"Koneksi: {e}")
                    
                    if should_rerun: time_lib.sleep(2); st.rerun()

        with t2:
            mc = st.text_input("Kode Antrean (Contoh: A-001-001)", key="man_code")
            if st.button("Proses"):
                should_rerun = False
                try:
                    r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": mc, "location": sel_loc})
                    d = r.json()
                    if r.status_code == 200:
                        if d['status'] == 'Success': st.success(f"✅ {d['message']}"); should_rerun=True
                        elif d['status'] == 'Warning': st.warning(f"⚠️ {d['message']}")
                        else: st.error(f"⛔ {d['message']}")
                    else: st.error(f"❌ {r.text}")
                except Exception as e: st.error(f"Koneksi: {e}")
                
                if should_rerun: time_lib.sleep(1); st.rerun()

    # =================================================================
    # 4. MENU RUANG PERIKSA (Perawat & Admin)
    # =================================================================
    elif menu == MENU_DOKTER:
        st.header("👨‍⚕️ Ruang Periksa (Input Medis)")
        st.info("Pilih dokter untuk melihat pasien yang sedang ditangani.")
        
        try:
            res_docs = requests.get(f"{API_URL}/admin/doctors")
            doc_list = [d['dokter'] for d in res_docs.json()] if res_docs.status_code == 200 else []
            selected_doc = st.selectbox("Pilih Dokter Bertugas:", doc_list)
        except: st.error("Gagal load dokter."); st.stop()

        st.markdown("---")
        current_p = None
        try:
            q_data = requests.get(f"{API_URL}/monitor/queue-board").json()
            current_p = next((p for p in q_data if p['dokter'] == selected_doc and p['status_pelayanan'] == "Sedang Dilayani"), None)
        except: pass

        if current_p:
            with st.container(border=True):
                st.info(f"🟢 PASIEN AKTIF: **{current_p['nama_pasien']}**")
                st.write(f"No: {current_p['queue_number']}")
                catatan = st.text_area("Hasil Diagnosa / Resep:")
                if st.button("✅ Simpan & Selesaikan", type="primary", use_container_width=True):
                    requests.put(f"{API_URL}/ops/medical-notes/{current_p['queue_number']}", json={"catatan": catatan})
                    requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": current_p['queue_number'], "location": "finish"})
                    st.success("Tersimpan!"); time_lib.sleep(1); st.rerun()
        else:
            st.warning(f"Tidak ada pasien di ruangan dr. {selected_doc}.")
            st.caption("Scan 'Masuk Poli' pada tiket pasien untuk memulai sesi.")

    # =================================================================
    # 5. MENU TV ANTREAN (FILTER POLI)
    # =================================================================
    elif menu == MENU_TV:
        st.markdown("<h1 style='text-align: center; color:#007bff;'>📺 JADWAL ANTREAN</h1>", unsafe_allow_html=True)
        try:
            pol_res = requests.get(f"{API_URL}/public/polis")
            poli_list = ["SEMUA POLI"] + [p['poli'] for p in pol_res.json()] if pol_res.status_code == 200 else ["SEMUA POLI"]
        except: poli_list = ["SEMUA POLI"]

        col_f, _ = st.columns([1, 3])
        target_poli = col_f.selectbox("Tampilkan Poli:", poli_list)
        st.markdown("---")

        try:
            r = requests.get(f"{API_URL}/monitor/queue-board")
            if r.status_code == 200:
                df = pd.DataFrame(r.json())
                if not df.empty:
                    df = df[['queue_number', 'poli', 'dokter', 'status_pelayanan']]
                    if target_poli != "SEMUA POLI": df = df[df['poli'] == target_poli]
                    
                    if not df.empty:
                        srv = df[df['status_pelayanan']=='Sedang Dilayani']
                        wait = df[df['status_pelayanan']=='Menunggu']
                        c1, c2 = st.columns(2)
                        with c1: 
                            st.success(f"🔊 DIPANGGIL ({len(srv)})")
                            st.dataframe(srv, hide_index=True, use_container_width=True)
                        with c2:
                            st.warning(f"🕒 MENUNGGU ({len(wait)})")
                            st.dataframe(wait, hide_index=True, use_container_width=True)
                    else: st.info(f"Tidak ada antrean untuk {target_poli}.")
                else: st.info("Tidak ada antrean aktif.")
        except: pass
        time_lib.sleep(5); st.rerun()

    # =================================================================
    # 6. ADMIN PANEL (4 TAB LENGKAP)
    # =================================================================
    elif menu == MENU_ADMIN:
        st.header("🛠️ Dashboard Admin")
        t_stat, t_doc, t_pol, t_imp = st.tabs(["Statistik", "Kelola Dokter", "Kelola Poli", "Import"])
        
        # Helper untuk dropdown poli di tab dokter
        try: p_opts = [x['poli'] for x in requests.get(f"{API_URL}/public/polis").json()]
        except: p_opts = []

        with t_stat:
            tgl = st.date_input("Pilih Tanggal", value=datetime.today())
            if st.button("Refresh Stat"): st.rerun()
            try: st.dataframe(pd.DataFrame(requests.get(f"{API_URL}/monitor/dashboard", params={"target_date": str(tgl)}).json()), use_container_width=True)
            except: pass

        with t_doc:
            st.subheader("Daftar Dokter")
            try: st.dataframe(pd.DataFrame(requests.get(f"{API_URL}/admin/doctors").json())[['doctor_id','dokter','poli','doctor_code', 'max_patients']], use_container_width=True, hide_index=True)
            except: pass
            
            with st.expander("➕ Tambah Dokter"):
                with st.form("add_doc"):
                    dn = st.text_input("Nama (Contoh: Ryan)"); dp = st.selectbox("Poli", p_opts)
                    ts = st.time_input("Mulai", time(8,0)); te = st.time_input("Selesai", time(16,0)); dm = st.number_input("Kuota", 20)
                    if st.form_submit_button("Simpan"):
                        requests.post(f"{API_URL}/admin/doctors", json={"dokter": dn, "poli": dp, "practice_start_time": ts.strftime("%H:%M"), "practice_end_time": te.strftime("%H:%M"), "max_patients": dm})
                        st.success("OK"); st.rerun()
            
            with st.expander("✏️ Edit Dokter"):
                ide = st.number_input("ID Edit", 1); 
                if st.button("Load"): st.session_state['ed_doc'] = requests.get(f"{API_URL}/admin/doctors/{ide}").json()
                if 'ed_doc' in st.session_state:
                    dd = st.session_state['ed_doc']
                    with st.form("edit_doc"):
                        en = st.text_input("Nama", dd['dokter']); ep = st.selectbox("Poli", p_opts, index=p_opts.index(dd['poli']) if dd['poli'] in p_opts else 0)
                        et1 = st.time_input("Mulai", datetime.strptime(dd['practice_start_time'][:5], "%H:%M").time())
                        et2 = st.time_input("Selesai", datetime.strptime(dd['practice_end_time'][:5], "%H:%M").time())
                        em = st.number_input("Kuota", dd['max_patients'])
                        if st.form_submit_button("Update"):
                            requests.put(f"{API_URL}/admin/doctors/{ide}", json={"dokter": en, "poli": ep, "practice_start_time": et1.strftime("%H:%M"), "practice_end_time": et2.strftime("%H:%M"), "max_patients": em})
                            st.success("Updated"); del st.session_state['ed_doc']; st.rerun()

            with st.expander("❌ Hapus Dokter"):
                did = st.number_input("ID Hapus", 1)
                if st.button("Hapus"): requests.delete(f"{API_URL}/admin/doctors/{did}"); st.success("Deleted"); st.rerun()

        with t_pol:
            try: 
                pol_data = requests.get(f"{API_URL}/public/polis").json()
                st.dataframe(pd.DataFrame(pol_data), use_container_width=True, hide_index=True)
                p_names = [p['poli'] for p in pol_data]
            except: p_names=[]
            
            with st.expander("➕ Tambah Poli"):
                pn = st.text_input("Nama Poli"); pp = st.text_input("Prefix")
                if st.button("Simpan Poli"): requests.post(f"{API_URL}/admin/polis", json={"poli": pn, "prefix": pp}); st.rerun()
            
            with st.expander("✏️ Edit Poli"):
                pe = st.selectbox("Pilih Poli Edit", p_names)
                new_n = st.text_input("Nama Baru"); new_p = st.text_input("Prefix Baru")
                if st.button("Update Poli"): 
                    requests.put(f"{API_URL}/admin/polis/{pe}", json={"new_name": new_n, "new_prefix": new_p})
                    st.success("Updated"); st.rerun()

            with st.expander("❌ Hapus Poli"):
                pd_del = st.selectbox("Pilih Hapus", p_names)
                if st.button("Hapus Poli"): requests.delete(f"{API_URL}/admin/polis/{pd_del}"); st.rerun()

        with t_imp:
            cnt = st.number_input("Jumlah Data", 10)
            if st.button("Import Data"):
                with st.spinner("Importing..."):
                    r = requests.get(f"{API_URL}/admin/import-random-data", params={"count": cnt})
                    st.success(r.json()['message'])

    # =================================================================
    # 7. ANALISIS DATA (PRO MAX - SINGLE PAGE)
    # =================================================================
    elif menu == MENU_ANALISIS:
        st.header("📈 Business Intelligence & Analytics")
        st.caption("Dashboard performa operasional rumah sakit berbasis data.")
        
        # --- 1. FILTER SECTION ---
        with st.container(border=True):
            col_filter, col_btn = st.columns([3, 1])
            
            with col_filter:
                filter_mode = st.selectbox(
                    "📅 Pilih Periode Analisis:", 
                    ["Hari Ini", "Minggu Ini", "Bulan Ini", "Tahun Ini", "Semua Waktu"]
                )
            
            with col_btn:
                st.write("") # Spacer
                st.write("")
                refresh = st.button("🔄 Terapkan Filter", type="primary", use_container_width=True)

        # Logika Tanggal
        today = datetime.today()
        start_date = None
        end_date = today # Default sampai hari ini

        if filter_mode == "Hari Ini":
            start_date = today
        elif filter_mode == "Minggu Ini":
            # Mulai dari Senin minggu ini
            start_date = today - pd.Timedelta(days=today.weekday())
        elif filter_mode == "Bulan Ini":
            start_date = today.replace(day=1)
        elif filter_mode == "Tahun Ini":
            start_date = today.replace(day=1, month=1)
        else: # Semua Waktu
            start_date = None
            end_date = None

        # --- 2. FETCH DATA ---
        params = {}
        if start_date: params['start_date'] = str(start_date.date())
        if end_date: params['end_date'] = str(end_date.date())

        data_loaded = False
        try:
            # Tampilkan spinner biar user tau sedang loading
            with st.spinner(f"Menganalisis data {filter_mode.lower()}..."):
                r = requests.get(f"{API_URL}/analytics/comprehensive-report", params=params)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("status") == "No Data":
                        st.warning(f"⚠️ Tidak ada data transaksi untuk periode: **{filter_mode}**")
                    else:
                        data_loaded = True
                else:
                    st.error("Gagal mengambil data dari server.")
        except Exception as e:
            st.error(f"Koneksi Error: {e}")

        # --- 3. VISUALISASI DASHBOARD ---
        if data_loaded:
            # A. SCORECARDS (METRICS)
            st.markdown("### 📊 Key Performance Indicators (KPI)")
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                st.metric("Total Pasien", d['total_patients'], border=True)
            
            with c2:
                # Jam Tersibuk
                peak = "-"
                if d['peak_hours']:
                    peak_val = max(d['peak_hours'], key=d['peak_hours'].get)
                    peak = f"{int(float(peak_val)):02d}:00"
                st.metric("Jam Tersibuk", peak, border=True)
                
            with c3:
                st.metric("Ghosting Rate", f"{d['ghost_rate']}%", 
                          help="% Pasien daftar tapi tidak hadir", border=True)
            
            with c4:
                corr = d['correlation']
                label = "Stabil"
                color = "off"
                if corr > 0.4: label = "Melambat"; color = "inverse"
                elif corr < -0.4: label = "Ngebut"; color = "normal"
                st.metric("Respon Dokter", label, delta=corr, delta_color=color, 
                          help="Korelasi kepadatan vs kecepatan (-1 s.d 1)", border=True)

            st.write("") # Spacer

            # B. CHARTS ROW 1 (VOLUME & EFISIENSI)
            col_left, col_right = st.columns(2)
            
            with col_left:
                with st.container(border=True):
                    st.subheader("🏥 Volume Pasien per Poli")
                    df_vol = pd.DataFrame(list(d['poli_volume'].items()), columns=['Poli', 'Jumlah'])
                    if not df_vol.empty:
                        # Bar Chart Horizontal yang lebih bersih
                        fig_vol = px.bar(df_vol, y='Poli', x='Jumlah', text='Jumlah', orientation='h',
                                         color='Jumlah', color_continuous_scale='Blues')
                        fig_vol.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                        st.plotly_chart(fig_vol, use_container_width=True)
            
            with col_right:
                with st.container(border=True):
                    st.subheader("⏱️ Efisiensi Waktu (Menit)")
                    eff_data = []
                    for poli, m in d['poli_efficiency'].items():
                        eff_data.append({'Poli': poli, 'Jenis': 'Menunggu', 'Menit': m['wait_minutes']})
                        eff_data.append({'Poli': poli, 'Jenis': 'Diperiksa', 'Menit': m['service_minutes']})
                    
                    df_eff = pd.DataFrame(eff_data)
                    if not df_eff.empty:
                        # Grouped Bar Chart
                        fig_eff = px.bar(df_eff, x='Poli', y='Menit', color='Jenis', barmode='group',
                                         color_discrete_map={'Menunggu': '#ff7675', 'Diperiksa': '#00b894'})
                        st.plotly_chart(fig_eff, use_container_width=True)

            # C. CHARTS ROW 2 (TREN & DOKTER)
            c_tren, c_doc = st.columns([1, 1])
            
            with c_tren:
                with st.container(border=True):
                    st.subheader("⏰ Pola Kedatangan (Jam)")
                    if d['peak_hours']:
                        df_peak = pd.DataFrame(list(d['peak_hours'].items()), columns=['Jam', 'Jumlah'])
                        df_peak['Jam'] = df_peak['Jam'].astype(float).astype(int)
                        df_peak = df_peak.sort_values('Jam')
                        
                        # Area Chart Smooth
                        fig_peak = px.area(df_peak, x='Jam', y='Jumlah', markers=True,
                                           line_shape='spline', color_discrete_sequence=['#6c5ce7'])
                        fig_peak.update_xaxes(dtick=1)
                        st.plotly_chart(fig_peak, use_container_width=True)
                    else:
                        st.info("Belum ada data waktu check-in.")

            with c_doc:
                with st.container(border=True):
                    st.subheader("⚡ Kecepatan Dokter (Pasien/Jam)")
                    df_doc = pd.DataFrame(list(d['doctor_throughput'].items()), columns=['Dokter', 'Speed'])
                    if not df_doc.empty:
                        df_doc = df_doc.sort_values('Speed', ascending=True)
                        # Lollipop Chart (Dot Plot) agar beda dari Bar biasa
                        fig_doc = px.scatter(df_doc, x='Speed', y='Dokter', size='Speed', color='Speed',
                                             color_continuous_scale='Viridis', size_max=15)
                        # Tambahkan garis batang manual biar jadi lollipop
                        for i in range(len(df_doc)):
                            fig_doc.add_shape(type='line',
                                              x0=0, y0=df_doc.iloc[i]['Dokter'],
                                              x1=df_doc.iloc[i]['Speed'], y1=df_doc.iloc[i]['Dokter'],
                                              line=dict(color='gray', width=1))
                        
                        st.plotly_chart(fig_doc, use_container_width=True)
                    else:
                        st.info("Belum ada data pemeriksaan selesai.")

 # D. TEXT MINING (VERSI DEBUG)
            with st.container(border=True):
                st.subheader("☁️ Analisis Keluhan & Diagnosa")
                
                text_data = d.get('text_mining', '')
                
                # [DEBUG] Tampilkan info data yang diterima
                st.caption(f"Status Data: Diterima {len(text_data)} karakter.")
                
                # Tampilkan data mentah di expander untuk bukti
                with st.expander("🔍 Lihat Data Mentah (Debug)"):
                    if text_data:
                        st.write(text_data)
                    else:
                        st.error("Data teks KOSONG dari Backend. Cek import data.")

                if len(text_data) > 5: # Turunkan syarat minimal jadi 5 huruf aja
                    # Kita kurangi stopwords agar tidak terlalu agresif membuang kata
                    stopwords = ["dan", "yang", "di", "ke", "dari", "ini", "itu", "untuk", "tidak", "ada", "dengan", "pada"]
                    
                    try:
                        # Generate WordCloud
                        wc = WordCloud(
                            width=1000, 
                            height=400, 
                            background_color='white', 
                            stopwords=stopwords, 
                            colormap='Reds', # <--- GANTI 'firebrick' JADI 'Reds'
                            min_font_size=10
                        ).generate(text_data)
                        
                        # Plotting
                        fig_wc, ax = plt.subplots(figsize=(12, 4))
                        ax.imshow(wc, interpolation='bilinear')
                        ax.axis("off")
                        st.pyplot(fig_wc)
                        
                    except Exception as e:
                        st.error(f"🔥 Error System WordCloud: {str(e)}")
                else:
                    st.warning("Teks terlalu sedikit untuk dibuat WordCloud.")