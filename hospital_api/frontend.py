import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time
import time as time_lib
import qrcode
import io
import cv2
import numpy as np

# --- CONFIG ---
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Sistem RS Pintar", layout="wide", page_icon="🏥")
st.title("🏥 Sistem Manajemen Antrean RS")
st.markdown("---")
menu = st.sidebar.radio("Navigasi", ["📝 Pendaftaran Pasien", "📠 Scanner (Pos RS)", "📺 Layar Antrean TV", "📊 Dashboard Admin", "📈 Analisis Data"])

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
    t1, t2 = st.tabs(["Daftar Baru", "Cek Tiket"])
    with t1:
        if 'selected_doc' not in st.session_state: st.session_state['selected_doc'] = None
        try:
            res_poli = requests.get(f"{API_URL}/public/polis")
            if res_poli.status_code == 200:
                p_list = sorted(res_poli.json(), key=lambda x: x['poli'])
                p_map = {p['poli']: p for p in p_list}
                c1, c2 = st.columns(2)
                nm = c1.text_input("Nama Pasien", key="reg_nm")
                pl = c1.selectbox("Poliklinik", list(p_map.keys()), key="reg_pl", on_change=lambda: st.session_state.update({'selected_doc': None}))
                tg = c2.date_input("Tanggal", min_value=datetime.today(), key="reg_tg")
                st.markdown("### 👨‍⚕️ Pilih Dokter")
                if pl:
                    res_doc = requests.get(f"{API_URL}/public/available-doctors", params={"poli_name": pl, "visit_date": str(tg)})
                    docs = res_doc.json()
                    if not docs: st.warning(f"Tidak ada dokter di {pl}.")
                    else:
                        if st.session_state['selected_doc'] is None:
                            cols = st.columns(3)
                            for idx, d in enumerate(docs):
                                with cols[idx % 3]:
                                    with st.container(border=True):
                                        st.subheader(d['dokter'])
                                        st.caption(f"{str(d['practice_start_time'])[:5]} - {str(d['practice_end_time'])[:5]}")
                                        if st.button(f"Pilih", key=f"d_{d['doctor_id']}", use_container_width=True):
                                            st.session_state['selected_doc'] = d
                                            st.rerun()
                        else:
                            doc = st.session_state['selected_doc']
                            st.success(f"Pilihan: **{doc['dokter']}**")
                            c_act1, c_act2 = st.columns([1, 3])
                            if c_act1.button("❌ Ganti", use_container_width=True):
                                st.session_state['selected_doc'] = None
                                st.rerun()
                            if c_act2.button("✅ Konfirmasi", type="primary", use_container_width=True):
                                if not nm.strip(): st.error("Isi Nama!")
                                else:
                                    py = {"nama_pasien": nm, "poli": pl, "doctor_id": doc['doctor_id'], "visit_date": str(tg)}
                                    r = requests.post(f"{API_URL}/public/submit", json=py)
                                    if r.status_code == 200:
                                        d = r.json()
                                        st.balloons()
                                        st.success("Terdaftar!")
                                        with st.container(border=True):
                                            st.markdown("#### 🎫 E-TIKET")
                                            st.divider()
                                            tc1, tc2 = st.columns([1, 2])
                                            with tc1:
                                                buf = io.BytesIO(); generate_qr(d['id']).save(buf, format="PNG")
                                                st.image(buf, use_container_width=True)
                                                st.caption(f"REF: {d['id']}")
                                            with tc2:
                                                st.title(d['queue_number'])
                                                st.write(f"**{d['nama_pasien']}**")
                                                st.write(f"{d['poli']} | {d['dokter']}")
                                                st.info("Simpan QR ini.")
                                        if st.button("Selesai"): st.session_state['selected_doc'] = None; st.rerun()
                                    else: st.error(f"Gagal: {r.text}")
        except Exception as e: st.error(f"Error: {e}")

    with t2:
        snm = st.text_input("Nama Pasien", key="src_nm")
        if st.button("Cari"):
            r = requests.get(f"{API_URL}/public/find-ticket", params={"nama": snm})
            if r.status_code == 200:
                for t in r.json():
                    with st.container(border=True):
                        st.subheader(t['queue_number'])
                        st.write(f"{t['nama_pasien']} ({t['status_pelayanan']})")
                        st.caption(f"{t['poli']} | {t['visit_date']}")
            else: st.warning("Tidak ditemukan.")

# =================================================================
# 2. SCANNER
# =================================================================
elif menu == "📠 Scanner (Pos RS)":
    st.header("Scanner")
    t1, t2 = st.tabs(["Kamera", "Manual"])
    with t1:
        loc = st.radio("Posisi:", ["arrival", "clinic", "finish"], horizontal=True, format_func=lambda x: x.upper(), key="rc")
        img = st.camera_input("Cam", key="ci")
        if img:
            res = decode_qr_from_image(img)
            if res:
                st.success(f"QR: {res}")
                if st.button(f"Proses {loc}?", key="bp"):
                    r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": res, "location": loc})
                    if r.status_code==200: st.success("Sukses!"); st.metric("Status", r.json()['current_status'])
                    else: st.error(r.json().get('detail', r.text))
            else: st.error("QR Gagal.")
    with t2:
        mc = st.text_input("Kode", key="mc")
        ml = st.selectbox("Posisi", ["arrival", "clinic", "finish"], key="ml")
        if st.button("Proses", key="bm"):
            if not mc.strip(): st.error("Isi kode!")
            else:
                r = requests.post(f"{API_URL}/ops/scan-barcode", json={"barcode_data": mc, "location": ml})
                if r.status_code==200: st.success("Sukses!"); st.metric("Status", r.json()['current_status'])
                else: st.error(r.json().get('detail', r.text))

# =================================================================
# 3. TV
# =================================================================
elif menu == "📺 Layar Antrean TV":
    st.markdown("<h1 style='text-align: center;'>JADWAL ANTREAN</h1>", unsafe_allow_html=True)
    ph = st.empty()
    if st.checkbox("Auto Refresh", value=True):
        try:
            r = requests.get(f"{API_URL}/monitor/queue-board")
            if r.status_code == 200:
                df = pd.DataFrame(r.json())
                with ph.container():
                    if not df.empty:
                        df = df[['queue_number', 'poli', 'dokter', 'status_pelayanan']]
                        df.columns = ['NO', 'POLI', 'DOKTER', 'STATUS']
                        serving = df[df['STATUS']=='Melayani']
                        waiting = df[df['STATUS']=='Menunggu']
                        if not serving.empty:
                            st.warning("🔊 SEDANG DILAYANI")
                            st.dataframe(serving, use_container_width=True, hide_index=True)
                        if not waiting.empty:
                            st.info("🕒 MENUNGGU")
                            st.dataframe(waiting, use_container_width=True, hide_index=True)
                    else: st.success("Kosong.")
        except: pass
        time_lib.sleep(5); st.rerun()

# =================================================================
# 4. DASHBOARD ADMIN
# =================================================================
elif menu == "📊 Dashboard Admin":
    st.header("Admin Panel")
    t_stat, t_doc, t_pol, t_imp = st.tabs(["Statistik", "Kelola Dokter", "Kelola Poli", "Import"])
    
    try: p_opts = [x['poli'] for x in requests.get(f"{API_URL}/public/polis").json()]
    except: p_opts = []

    with t_doc:
        st.subheader("Daftar Dokter")
        try:
            all_docs = requests.get(f"{API_URL}/admin/doctors").json()
            if all_docs: st.dataframe(pd.DataFrame(all_docs)[['doctor_id','dokter','poli','doctor_code']], use_container_width=True, hide_index=True)
        except: pass
        
        with st.expander("➕ Tambah Dokter"):
            with st.form("add_doc"):
                dn = st.text_input("Nama")
                dp = st.selectbox("Poli", p_opts)
                c1, c2 = st.columns(2)
                t1 = c1.time_input("Start", value=time(8,0))
                t2 = c2.time_input("End", value=time(16,0))
                dm = st.number_input("Kuota", value=20)
                if st.form_submit_button("Simpan"):
                    if not dn.strip(): st.error("Isi Nama!")
                    else:
                        pl = {"dokter": dn, "poli": dp, "practice_start_time": t1.strftime("%H:%M"), "practice_end_time": t2.strftime("%H:%M"), "max_patients": dm}
                        r = requests.post(f"{API_URL}/admin/doctors", json=pl)
                        if r.status_code == 200: st.success("Sukses"); st.rerun()
                        else: st.error(r.json().get('detail', r.text))

        with st.expander("✏️ Edit Dokter"):
            ide = st.number_input("ID Edit", min_value=1, key="ide_in")
            if st.button("Load"):
                r = requests.get(f"{API_URL}/admin/doctors/{ide}")
                if r.status_code == 200: st.session_state['ed_data'] = r.json(); st.success("Loaded")
                else: st.error("Not Found")
            
            if 'ed_data' in st.session_state:
                dd = st.session_state['ed_data']
                with st.form("edit_doc"):
                    enm = st.text_input("Nama", value=dd['dokter'])
                    try: pidx = p_opts.index(dd['poli'])
                    except: pidx = 0
                    epol = st.selectbox("Poli", p_opts, index=pidx)
                    t1_old = datetime.strptime(dd['practice_start_time'][:5], "%H:%M").time()
                    t2_old = datetime.strptime(dd['practice_end_time'][:5], "%H:%M").time()
                    ec1, ec2 = st.columns(2)
                    ets = ec1.time_input("Start", value=t1_old)
                    ete = ec2.time_input("End", value=t2_old)
                    emx = st.number_input("Kuota", value=dd['max_patients'])
                    
                    if st.form_submit_button("Update"):
                        if not enm.strip(): st.error("Isi Nama!")
                        else:
                            upd = {"dokter": enm, "poli": epol, "practice_start_time": ets.strftime("%H:%M"), "practice_end_time": ete.strftime("%H:%M"), "max_patients": emx}
                            r = requests.put(f"{API_URL}/admin/doctors/{ide}", json=upd)
                            if r.status_code == 200: st.success("Updated"); del st.session_state['ed_data']; st.rerun()
                            else: st.error(r.json().get('detail', r.text))

        with st.expander("❌ Hapus Dokter"):
            did = st.number_input("ID Hapus", min_value=1, key="did_in")
            if st.button("Hapus"): 
                r = requests.delete(f"{API_URL}/admin/doctors/{did}")
                if r.status_code == 200: st.success("Deleted"); st.rerun()
                else: st.error(r.text)

    with t_pol:
        st.subheader("Manajemen Poli")
        try:
            curr_polis = requests.get(f"{API_URL}/public/polis").json()
            p_names = [p['poli'] for p in curr_polis]
            st.dataframe(pd.DataFrame(curr_polis), use_container_width=True, hide_index=True)
        except: p_names = []

        with st.expander("➕ Tambah Poli"):
            pn = st.text_input("Nama Poli", key="pn")
            pp = st.text_input("Prefix", key="pp")
            if st.button("Simpan", key="bps"):
                if not pn.strip() or not pp.strip(): st.error("Isi Nama & Prefix!")
                else:
                    r = requests.post(f"{API_URL}/admin/polis", json={"poli": pn, "prefix": pp})
                    if r.status_code==200: st.success("OK"); st.rerun()
                    else: st.error(r.json().get('detail', r.text))

        with st.expander("✏️ Edit Poli"):
            if p_names:
                old_p = st.selectbox("Poli Lama", p_names, key="sel_old_p")
                new_p = st.text_input("Nama Baru", key="new_p")
                new_pr = st.text_input("Prefix Baru", key="new_pr")
                if st.button("Update"):
                    final_nm = new_p if new_p.strip() else old_p
                    if not new_pr.strip(): st.error("Prefix harus diisi!")
                    else:
                        r = requests.put(f"{API_URL}/admin/polis/{old_p}", json={"poli": final_nm, "prefix": new_pr})
                        if r.status_code==200: st.success("OK"); st.rerun()
                        else: st.error(r.json().get('detail', r.text))

        with st.expander("❌ Hapus Poli"):
            if p_names:
                pd_del = st.selectbox("Pilih Hapus", p_names, key="sel_del")
                if st.button("Hapus Poli"):
                    r = requests.delete(f"{API_URL}/admin/polis/{pd_del}")
                    if r.status_code == 200: st.success("Terhapus"); st.rerun()
                    else: st.error(r.text)

    with t_imp:
        cnt = st.number_input("Jml Data", value=10)
        if st.button("Start Import"):
            r = requests.get(f"{API_URL}/admin/import-random-data", params={"count": cnt})
            if r.status_code == 200: st.success(r.json()['message'])
            else: st.error(r.text)
    
    with t_stat:
        tgl = st.date_input("Tanggal", value=datetime.today())
        if st.button("Refresh"): st.rerun()
        try:
            d = requests.get(f"{API_URL}/monitor/dashboard", params={"target_date": str(tgl)}).json()
            st.dataframe(pd.DataFrame(d), use_container_width=True)
        except: pass

# =================================================================
# 5. ANALISIS
# =================================================================
elif menu == "📈 Analisis Data":
    st.header("Analisis")
    if st.button("Refresh"): st.rerun()
    try:
        d = requests.get(f"{API_URL}/analytics/comprehensive-report").json()
        if d.get("status") == "No Data": st.warning("No Data")
        else:
            k1,k2,k3 = st.columns(3)
            k1.metric("Ghosting", f"{d['ghost_rate']}%")
            k2.metric("Active Docs", f"{d['total_active_doctors']}/{d['total_doctors_registered']}")
            k3.metric("Corr", d['correlation']['coef'])
            c1,c2 = st.columns(2)
            with c1: st.subheader("Volume"); st.bar_chart(d['poli_volume'])
            with c2: st.subheader("Speed"); st.bar_chart(d['poli_speed'])
            st.subheader("Effectiveness"); st.bar_chart(d['staff_effectiveness'])
            if d['idle_doctors']: st.error(f"Idle: {', '.join(d['idle_doctors'])}")
    except Exception as e: st.error(f"Err: {e}")