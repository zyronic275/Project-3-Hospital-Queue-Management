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
import plotly.express as px  # Library Chart Baru
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- KONFIGURASI ---
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Sistem RS Pintar", layout="wide", page_icon="🏥")
st.title("🏥 Sistem Manajemen Antrean RS")
st.markdown("---")

menu = st.sidebar.radio("Navigasi", ["📝 Pendaftaran Pasien", "📠 Scanner (Pos RS)", "👨‍⚕️ Ruang Periksa","📺 Layar Antrean TV", "📊 Dashboard Admin", "📈 Analisis Data"])

# --- HELPERS ---
def generate_qr(data):
    qr_content = json.dumps(data)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_content)
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
                                        # Data QR JSON
                                        qr_data = {"id": d['id'], "nama": d['nama_pasien'], "poli": d['poli'], "dokter": d['dokter'], "jadwal": d['doctor_schedule'], "tgl": d['visit_date']}
                                        
                                        with st.container(border=True):
                                            st.markdown("#### 🎫 E-TIKET")
                                            st.divider()
                                            tc1, tc2 = st.columns([1, 2])
                                            with tc1:
                                                buf = io.BytesIO(); generate_qr(qr_data).save(buf, format="PNG")
                                                st.image(buf, use_container_width=True)
                                                st.caption(f"REF: {d['id']}")
                                            with tc2:
                                                st.title(d['queue_number'])
                                                st.write(f"**{d['nama_pasien']}**")
                                                st.write(f"{d['poli']} | {d['dokter']}")
                                                st.write(f"Jadwal: {d['doctor_schedule']}")
                                                st.info("Simpan QR ini.")
                                        if st.button("Selesai"): st.session_state['selected_doc'] = None; st.rerun()
                                    else: st.error(f"Gagal: {r.text}")
        except Exception as e: st.error(f"Error: {e}")

    with t2:
        st.subheader("🔍 Cari Tiket Saya")
        
        # [BARU] Layout Kolom untuk Nama & Tanggal
        c_cari1, c_cari2 = st.columns([3, 2])
        
        with c_cari1:
            snm = st.text_input("Masukkan Nama Pasien", key="src_nm", placeholder="Contoh: Budi")
            
        with c_cari2:
            # Checkbox agar user bisa memilih mau filter tanggal atau tidak
            filter_tgl = st.checkbox("Filter Tanggal Kunjungan")
            # Input Tanggal (Aktif jika checkbox dicentang)
            tgl_cari = st.date_input("Pilih Tanggal", value=datetime.today(), disabled=not filter_tgl, label_visibility="collapsed")

        if st.button("Cari Tiket", use_container_width=True, type="primary"):
            if not snm.strip():
                st.warning("⚠️ Harap isi nama pasien.")
            else:
                # [BARU] Logika Parameter
                params = {"nama": snm}
                if filter_tgl:
                    params["target_date"] = str(tgl_cari)

                try:
                    r = requests.get(f"{API_URL}/public/find-ticket", params=params)
                    
                    if r.status_code == 200:
                        results = r.json()
                        st.success(f"Ditemukan {len(results)} tiket.")
                        
                        for t in results:
                            with st.container(border=True):
                                cQ, cI = st.columns([1, 4])
                                with cQ:
                                    # Generate QR Code
                                    qr_data = {"id": t['id'], "nama": t['nama_pasien'], "antrean": t['queue_number']}
                                    buf = io.BytesIO()
                                    generate_qr(qr_data).save(buf, format="PNG")
                                    st.image(buf, use_container_width=True)
                                
                                with cI:
                                    st.subheader(f"{t['queue_number']}")
                                    
                                    # Status Badge
                                    status = t['status_pelayanan']
                                    if status == "Menunggu": st.warning(f"🕒 {status}")
                                    elif status == "Sedang Dilayani": st.success(f"🔊 {status}")
                                    elif status == "Selesai": st.info(f"✅ {status}")
                                    else: st.markdown(f"📝 **{status}**")

                                    st.divider()
                                    st.markdown(f"**Pasien:** {t['nama_pasien']}")
                                    st.markdown(f"**Poli:** {t['poli']} | **Dokter:** {t['dokter']}")
                                    st.caption(f"📅 {t['visit_date']}")
                    else: 
                        st.warning("Tiket tidak ditemukan. Cek kembali nama atau tanggal.")
                except Exception as e:
                    st.error(f"Gagal mencari: {e}")

# =================================================================
# 2. SCANNER (AUTO-PROCESS MODE)
# =================================================================
elif menu == "📠 Scanner (Pos RS)":
    st.header("📠 Scanner Barcode Otomatis")
    
    # 1. SETUP POSISI (Dilakukan sekali oleh petugas)
    # Petugas memilih dia sedang jaga di mana
    st.info("👇 Pilih lokasi tugas Anda saat ini:")
    mode_tugas = st.radio("Posisi Scanner:", 
                          ["1. Pintu Masuk (Arrival)", "2. Masuk Poli (Clinic)", "3. Pulang (Finish)"], 
                          horizontal=True)
    
    # Mapping ke bahasa API
    loc_map = {
        "1. Pintu Masuk (Arrival)": "arrival",
        "2. Masuk Poli (Clinic)": "clinic",
        "3. Pulang (Finish)": "finish"
    }
    selected_loc = loc_map[mode_tugas]

    st.divider()

    t_cam, t_man = st.tabs(["📷 Kamera Otomatis", "⌨️ Input Manual"])
    
    # --- TAB KAMERA (AUTO) ---
    with t_cam:
        st.write(f"Siap memindai untuk posisi: **{mode_tugas}**")
        
        # Input Kamera
        img = st.camera_input("Arahkan QR Code ke kamera")
        
        if img:
            # 1. Decode QR Otomatis
            res_code = decode_qr_from_image(img)
            
            if res_code:
                # Bersihkan data (kadang QR baca JSON string)
                scan_val = res_code
                try:
                    data_json = json.loads(res_code.replace("'", '"'))
                    scan_val = str(data_json.get("antrean", data_json.get("id", res_code)))
                except: pass
                
                st.toast(f"QR Terbaca: {scan_val}")
                
                # 2. KIRIM KE BACKEND LANGSUNG (Tanpa Tombol)
                try:
                    with st.spinner("Memproses..."):
                        # Khusus Finish: Kita kosongkan catatan medis jika pakai auto-scan 
                        # (Asumsi dokter sudah isi lewat menu 'Ruang Periksa')
                        r = requests.post(f"{API_URL}/ops/scan-barcode", json={
                            "barcode_data": scan_val, 
                            "location": selected_loc
                        })
                        
                    if r.status_code == 200:
                        d = r.json()
                        st.success(f"✅ SUKSES! Status: {d['current_status']}")
                        if d.get('message'): st.info(d['message'])
                        
                        # Bunyi 'Ding' (Optional - Visual)
                        st.balloons() 
                        
                        # 3. AUTO RESET (Penting agar bisa scan pasien berikutnya)
                        time_lib.sleep(2) # Tahan 2 detik biar petugas lihat pesan sukses
                        st.rerun()
                        
                    else:
                        err_msg = r.json().get('detail', r.text)
                        st.error(f"❌ Gagal: {err_msg}")
                        # Tetap rerun agar kamera nyala lagi
                        time_lib.sleep(3)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error Koneksi: {e}")
            else:
                st.warning("QR Code tidak terbaca. Coba dekatkan/jauhkan.")

    # --- TAB MANUAL (BACKUP) ---
    with t_man:
        st.caption("Gunakan ini jika kamera bermasalah.")
        mc = st.text_input("Ketik Kode Antrean:", key="mc_auto")
        
        # Di manual, kita tetap pakai tombol biar gak error saat baru ngetik separuh
        if st.button("Proses Manual", type="primary"):
            if not mc.strip():
                st.error("Isi kode dulu.")
            else:
                r = requests.post(f"{API_URL}/ops/scan-barcode", json={
                    "barcode_data": mc, 
                    "location": selected_loc
                })
                if r.status_code == 200:
                    st.success("✅ Berhasil Update Status")
                else:
                    st.error(f"Gagal: {r.text}")

# =================================================================
# 3. TV (FULL TABEL - ANTI DUPLIKAT & KONFLIK)
# =================================================================
elif menu == "📺 Layar Antrean TV":
    st.markdown("<h1 style='text-align: center; color:#007bff;'>JADWAL ANTREAN RS</h1>", unsafe_allow_html=True)
    
    # --- 1. FILTER POLI ---
    try:
        res_poli = requests.get(f"{API_URL}/public/polis")
        if res_poli.status_code == 200:
            poli_options = ["SEMUA POLI"] + [p['poli'] for p in res_poli.json()]
        else:
            poli_options = ["SEMUA POLI"]
    except:
        poli_options = ["SEMUA POLI"]

    c_filt, _ = st.columns([1, 3])
    with c_filt:
        target_poli = st.selectbox("Tampilkan Poli:", poli_options)

    st.markdown("---")

    # --- 2. TAMPILAN ANTREAN ---
    ph = st.empty()
    
    if st.checkbox("Auto Refresh (5s)", value=True):
        try:
            r = requests.get(f"{API_URL}/monitor/queue-board")
            if r.status_code == 200:
                data_list = r.json()
                df = pd.DataFrame(data_list)
                
                with ph.container():
                    if not df.empty:
                        # 1. Standarisasi Kolom
                        df = df[['queue_number', 'poli', 'dokter', 'status_pelayanan']]
                        df.columns = ['NO ANTREAN', 'POLI', 'DOKTER', 'STATUS']
                        
                        # 2. [LOGIKA BARU] HAPUS DUPLIKAT & KONFLIK STATUS
                        # Kita beri 'ranking': Melayani (0) lebih penting dari Menunggu (1)
                        # Agar saat disortir, 'Melayani' ada di atas.
                        priority_map = {'Sedang Dilayani': 0, 'Menunggu': 1}
                        df['priority'] = df['STATUS'].map(priority_map).fillna(99)
                        
                        # Sortir berdasarkan Nomor Antrean dan Prioritas
                        df = df.sort_values(by=['NO ANTREAN', 'priority'])
                        
                        # Hapus duplikat Nomor Antrean (Keep First = simpan yang Melayani)
                        df = df.drop_duplicates(subset=['NO ANTREAN'], keep='first')
                        
                        # 3. Filter Poli (Sesuai Pilihan User)
                        if target_poli != "SEMUA POLI":
                            df = df[df['POLI'] == target_poli]

                        # 4. Pisahkan Data
                        serving = df[df['STATUS']=='Sedang Dilayani']
                        waiting = df[df['STATUS']=='Menunggu']
                        
                        c1, c2 = st.columns(2)
                        
                        # --- KIRI: SEDANG DILAYANI ---
                        with c1:
                            st.success(f"🔊 SEDANG DILAYANI ({len(serving)})")
                            if not serving.empty:
                                st.dataframe(
                                    serving[['NO ANTREAN', 'DOKTER', 'POLI']], 
                                    use_container_width=True, 
                                    hide_index=True
                                )
                            else:
                                st.write("Belum ada yang dipanggil.")

                        # --- KANAN: MENUNGGU ---
                        with c2:
                            st.warning(f"🕒 MENUNGGU ({len(waiting)})")
                            if not waiting.empty:
                                st.dataframe(
                                    waiting[['NO ANTREAN', 'DOKTER', 'POLI']], 
                                    use_container_width=True, 
                                    hide_index=True
                                )
                            else:
                                st.write("Antrean kosong.")

                    else: 
                        st.info("Saat ini tidak ada antrean aktif.")
                        
        except Exception as e: 
            st.error(f"Gagal koneksi ke server: {e}")
        
        time_lib.sleep(5)
        st.rerun()
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
                        if not enm.strip(): st.error("Nama wajib diisi!")
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
# 5. ANALISIS (VISUALISASI PRO + ANALISIS 5 & 6)
# =================================================================
# --- (Bagian atas frontend.py tetap sama) ---
# GANTI TOTAL BAGIAN menu == "📈 Analisis Data" dengan ini:

elif menu == "📈 Analisis Data":
    st.header("📈 Analisis Performa RS 360°")
    
    if st.button("🔄 Segarkan Data"): st.rerun()
        
    try:
        with st.spinner("Sedang menganalisis data..."):
            res = requests.get(f"{API_URL}/analytics/comprehensive-report")
            
        if res.status_code == 200:
            d = res.json()
            
            if d.get("status") == "No Data":
                st.warning("Data belum tersedia. Silakan Import Data terlebih dahulu di Dashboard Admin.")
            else:
                # 1. KPI CARD
                k1, k2, k3, k4 = st.columns(4)
                
                # --- KPI 1: GHOSTING RATE ---
                k1.metric("Ghosting Rate", f"{d['ghost_rate']}%", help="% Pasien yang sudah daftar tapi tidak hadir (Status tetap 'Terdaftar').")
                
                # --- KPI 2: JAM TERSIBUK (FIX "11.0:00") ---
                peak_h = "-"
                if d['peak_hours']:
                    # Cari jam dengan jumlah pasien terbanyak
                    raw_peak = max(d['peak_hours'], key=d['peak_hours'].get)
                    try:
                        # Konversi "11.0" -> 11.0 -> 11 (Int) agar bersih
                        peak_h_clean = int(float(raw_peak))
                        peak_h = f"{peak_h_clean}:00"
                    except:
                        peak_h = f"{raw_peak}" # Fallback jika gagal
                
                k2.metric("Jam Tersibuk", peak_h, help="Jam dengan jumlah kedatangan pasien paling tinggi.")
                
                # --- KPI 3: KORELASI (TAMBAH KETERANGAN) ---
                # Penjelasan: Korelasi Pearson (-1 s.d 1).
                # Positif: Makin ramai, makin lama layanannya.
                # Negatif: Makin ramai, justru makin cepat (dokter ngebut).
                k3.metric("Korelasi Antrean", d['correlation']['coef'], 
                          help="Hubungan kepadatan vs kecepatan. \n+1 (Positif): Makin ramai, layanan makin lambat. \n-1 (Negatif): Makin ramai, layanan makin cepat (dokter buru-buru).")
                
                # --- KPI 4: DOKTER AKTIF ---
                k4.metric("Dokter Aktif", f"{d['total_active_doctors']}/{d['total_doctors_registered']}", help="Jumlah dokter yang melayani pasien hari ini vs Total dokter terdaftar.")
                
                st.divider()
                
                # 2. VISUALISASI UTAMA
                c_vol, c_speed = st.columns(2)
                
                with c_vol:
                    st.subheader("📊 Volume Pasien per Poli")
                    df_vol = pd.DataFrame(list(d['poli_volume'].items()), columns=['Poli', 'Total'])
                    if not df_vol.empty:
                        fig_vol = px.bar(df_vol, x='Poli', y='Total', color='Total', color_continuous_scale='Oranges')
                        st.plotly_chart(fig_vol, use_container_width=True)
                
                with c_speed:
                    st.subheader("⏱️ Kecepatan Dokter (Menit)")
                    df_spd = pd.DataFrame(list(d['poli_speed'].items()), columns=['Poli', 'Menit'])
                    if not df_spd.empty:
                        fig_spd = px.bar(df_spd, x='Menit', y='Poli', orientation='h', color='Menit', color_continuous_scale='RdYlGn_r')
                        st.plotly_chart(fig_spd, use_container_width=True)

                st.markdown("---")

                # 3. ANALISIS EFISIENSI
                st.subheader("⏳ Efisiensi: Menunggu vs Dilayani")
                st.caption("Grafik ini membandingkan rata-rata waktu pasien menunggu (Merah) dengan waktu diperiksa dokter (Hijau).")
                
                wait_data = pd.DataFrame(list(d['poli_wait'].items()), columns=['Poli', 'Menit']).assign(Tipe='Menunggu')
                svc_data = pd.DataFrame(list(d['poli_speed'].items()), columns=['Poli', 'Menit']).assign(Tipe='Diperiksa')
                
                if not wait_data.empty and not svc_data.empty:
                    df_eff = pd.concat([wait_data, svc_data])
                    fig_eff = px.bar(df_eff, x='Menit', y='Poli', color='Tipe', orientation='h', 
                                     color_discrete_map={'Menunggu': '#ff4d4d', 'Diperiksa': '#00cc44'}, barmode='stack')
                    st.plotly_chart(fig_eff, use_container_width=True)
                else:
                    st.info("Data waktu belum cukup untuk analisis efisiensi.")

                # 4. JAM SIBUK & EFEKTIVITAS
                c_peak, c_staff = st.columns(2)
                
                with c_peak:
                    st.subheader("⏰ Persebaran Jam Kedatangan")
                    if d['peak_hours']:
                        df_peak = pd.DataFrame(list(d['peak_hours'].items()), columns=['Jam', 'Jumlah'])
                        # PERBAIKAN GRAFIK JUGA (Supaya sinkron)
                        df_peak['Jam'] = df_peak['Jam'].astype(float).astype(int)
                        df_peak = df_peak.sort_values('Jam')
                        
                        fig_peak = px.line(df_peak, x='Jam', y='Jumlah', markers=True)
                        st.plotly_chart(fig_peak, use_container_width=True)
                
                with c_staff:
                    st.subheader("⭐ Top Dokter (Pasien/Jam)")
                    if d['staff_effectiveness']:
                        df_staff = pd.DataFrame(list(d['staff_effectiveness'].items()), columns=['Dokter', 'Rate']).head(10)
                        fig_staff = px.bar(df_staff, x='Rate', y='Dokter', orientation='h', color='Rate', color_continuous_scale='Viridis')
                        st.plotly_chart(fig_staff, use_container_width=True)
                st.markdown("---")
                
                # 5. TEXT MINING: WORD CLOUD PENYAKIT
                st.subheader("☁️ Peta Sebaran Kata Diagnosa")
                st.caption("Visualisasi kata-kata yang paling sering muncul dalam catatan dokter.")
                
                text_data = d.get('medical_notes_text', '')
                
                if text_data and len(text_data) > 10:
                    # Setup WordCloud
                    # stopwords = kata umum yang mau dibuang (dan, yang, di, dll)
                    stopwords_indo = ["dan", "yang", "di", "ke", "dari", "ini", "itu", "untuk", "pada", "adalah", "pasien", "mengeluh", "sejak", "hari", "lalu", "diberikan", "sudah", "disarankan"]
                    
                    wc = WordCloud(width=800, height=400, background_color='white', 
                                   stopwords=stopwords_indo, colormap='Reds').generate(text_data)
                    
                    # Plot menggunakan Matplotlib
                    fig_wc, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wc, interpolation='bilinear')
                    ax.axis("off")
                    st.pyplot(fig_wc)
                    
                    # Tampilkan Sample Data Mentah
                    with st.expander("Lihat Data Mentah Catatan"):
                        st.write(text_data[:500] + "...")
                else:
                    st.info("Belum cukup data catatan medis untuk membuat Word Cloud.")
    except Exception as e:
        st.error(f"Error memuat analisis: {e}")




# =================================================================
# MENU BARU: RUANG PERIKSA DOKTER (REALISTIS)
# =================================================================
elif menu == "👨‍⚕️ Ruang Periksa":
    st.header("👨‍⚕️ Dashboard Dokter")
    
    # 1. SIMULASI LOGIN DOKTER
    # Di dunia nyata, ini otomatis dari login. Di sini kita pilih manual.
    try:
        res_docs = requests.get(f"{API_URL}/admin/doctors")
        if res_docs.status_code == 200:
            doc_list = [d['dokter'] for d in res_docs.json()]
            selected_doc = st.selectbox("Siapa nama Anda?", doc_list)
        else:
            st.error("Gagal memuat data dokter.")
            st.stop()
    except:
        st.error("Koneksi server terputus.")
        st.stop()

    st.markdown("---")

    # 2. CARI PASIEN YANG SEDANG DILAYANI OLEH DOKTER INI
    # Kita ambil dari queue-board lalu filter
    current_patient = None
    try:
        r_board = requests.get(f"{API_URL}/monitor/queue-board")
        if r_board.status_code == 200:
            data = r_board.json()
            # Cari pasien yang statusnya 'Sedang Dilayani' DAN Dokternya sama dengan yang dipilih
            for p in data:
                if p['dokter'] == selected_doc and p['status_pelayanan'] == "Sedang Dilayani":
                    current_patient = p
                    break
    except: pass

    # 3. TAMPILAN DASHBOARD
    if current_patient:
        # TAMPILAN EMR (Electronic Medical Record)
        st.info(f"🟢 PASIEN AKTIF SAAT INI")
        
        with st.container(border=True):
            # Header Pasien
            c1, c2 = st.columns([1, 3])
            with c1:
                st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100) # Ikon User
            with c2:
                st.title(current_patient['nama_pasien'])
                st.subheader(f"No: {current_patient['queue_number']}")
                st.caption(f"Poli: {current_patient['poli']} | Tgl: {current_patient['visit_date']}")
            
            st.divider()
            
            # Input Diagnosa
            st.markdown("### 🩺 Diagnosa & Catatan")
            catatan = st.text_area("Isi hasil pemeriksaan di sini:", height=150, placeholder="Contoh: Pasien mengalami demam, resep paracetamol diberikan...")
            
            # Tombol Aksi
            col_btn1, col_btn2 = st.columns(2)
            
            if col_btn2.button("✅ Simpan & Selesaikan Sesi", type="primary", use_container_width=True):
                if not catatan.strip():
                    st.warning("⚠️ Mohon isi catatan medis terlebih dahulu!")
                else:
                    # --- DEBUGGING (Hapus baris ini nanti kalau sudah fix) ---
                    st.info(f"Mengirim catatan untuk ID: {current_patient['queue_number']}")
                    # ---------------------------------------------------------

                    # 1. STEP PERTAMA: Simpan Catatan
                    try:
                        # Pastikan URL benar: /ops/medical-notes/{queue_number}
                        url_catatan = f"{API_URL}/ops/medical-notes/{current_patient['queue_number']}"
                        r_note = requests.put(url_catatan, json={"catatan": catatan})
                        
                        # [PENTING] Cek Status Code Catatan Dulu!
                        if r_note.status_code != 200:
                            st.error(f"❌ Gagal menyimpan catatan! Server menjawab: {r_note.status_code}")
                            st.error(f"Detail Error: {r_note.text}")
                            st.stop() # BERHENTI DI SINI, JANGAN FINISH DULU
                            
                    except Exception as e:
                        st.error(f"❌ Error Koneksi saat simpan catatan: {e}")
                        st.stop()

                    # 2. STEP KEDUA: Update Status jadi 'Selesai'
                    # (Hanya jalan kalau Step 1 Sukses)
                    try:
                        r_finish = requests.post(f"{API_URL}/ops/scan-barcode", json={
                            "barcode_data": current_patient['queue_number'], 
                            "location": "finish"
                        })
                        
                        if r_finish.status_code == 200:
                            st.balloons()
                            st.success("✅ Catatan Tersimpan & Sesi Selesai!")
                            time_lib.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Gagal update status selesai: {r_finish.text}")
                            
                    except Exception as e:
                        st.error(f"Error koneksi finish: {e}")

    else:
        # JIKA TIDAK ADA PASIEN AKTIF
        st.warning("Tidak ada pasien yang sedang diperiksa.")
        st.markdown(f"""
        **Cara Memulai:**
        1. Gunakan menu **Scanner** atau minta Asisten untuk memanggil pasien masuk.
        2. Status pasien harus **'Sedang Dilayani'** agar muncul di sini.
        """)
        
        # (Opsional) Tampilkan siapa yang mengantre selanjutnya buat dokter tahu
        st.markdown("#### 🕒 Antrean Berikutnya:")
        try:
            # Filter yang statusnya Menunggu untuk dokter ini
            waiting_list = [p for p in data if p['dokter'] == selected_doc and p['status_pelayanan'] == "Menunggu"]
            if waiting_list:
                df_wait = pd.DataFrame(waiting_list)[['queue_number', 'nama_pasien']]
                st.dataframe(df_wait, hide_index=True, use_container_width=True)
            else:
                st.caption("Tidak ada antrean.")
        except: pass