import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time

# Konfigurasi URL API (Pastikan backend running di port 8000)
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="RS Queue System", layout="wide")

st.title("🏥 Sistem Manajemen Antrean RS")

# Sidebar Menu
menu = st.sidebar.selectbox(
    "Menu Utama",
    ["Pendaftaran Pasien", "Dashboard Admin & Data", "Operasional Dokter"]
)

# =================================================================
# 1. HALAMAN PENDAFTARAN PASIEN
# =================================================================
if menu == "Pendaftaran Pasien":
    st.header("📝 Pendaftaran Pasien Baru")
    
    # Step 1: Ambil Data Poli
    try:
        res_poli = requests.get(f"{API_URL}/public/polis")
        if res_poli.status_code == 200:
            polis = res_poli.json()
            list_poli = {p['poli']: p for p in polis}
            
            col1, col2 = st.columns(2)
            with col1:
                nama_pasien = st.text_input("Nama Lengkap Pasien")
                pilih_poli = st.selectbox("Pilih Poliklinik", list(list_poli.keys()))
            
            with col2:
                tgl_kunjungan = st.date_input("Tanggal Kunjungan", min_value=datetime.today())
            
            # Step 2: Ambil Dokter berdasarkan Poli
            if pilih_poli:
                res_doc = requests.get(f"{API_URL}/public/available-doctors", params={"poli_name": pilih_poli, "visit_date": str(tgl_kunjungan)})
                doctors = res_doc.json()
                
                if doctors:
                    dict_docs = {f"{d['dokter']} ({d['practice_start_time']}-{d['practice_end_time']})": d['doctor_id'] for d in doctors}
                    pilih_dokter_label = st.selectbox("Pilih Dokter", list(dict_docs.keys()))
                    selected_doc_id = dict_docs[pilih_dokter_label]
                    
                    if st.button("Ambil Nomor Antrean", type="primary"):
                        if not nama_pasien:
                            st.error("Nama pasien harus diisi!")
                        else:
                            # Submit Data
                            payload = {
                                "nama_pasien": nama_pasien,
                                "poli": pilih_poli,
                                "doctor_id": selected_doc_id,
                                "visit_date": str(tgl_kunjungan)
                            }
                            res_submit = requests.post(f"{API_URL}/public/submit", json=payload)
                            
                            if res_submit.status_code == 200:
                                data = res_submit.json()
                                st.success("✅ Pendaftaran Berhasil!")
                                st.metric(label="Nomor Antrean Anda", value=data['queue_number'])
                                st.info(f"Silakan menunggu dipanggil di {pilih_poli}.")
                            else:
                                st.error(f"Gagal: {res_submit.text}")
                else:
                    st.warning("Tidak ada dokter tersedia di poli ini pada tanggal tersebut.")
        else:
            st.error("Gagal mengambil data Poli. Pastikan server backend menyala.")
    except Exception as e:
        st.error(f"Error koneksi: {e}")

# =================================================================
# 2. HALAMAN ADMIN (DASHBOARD & DATA)
# =================================================================
elif menu == "Dashboard Admin & Data":
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👨‍⚕️ Kelola Dokter", "🏥 Kelola Poli", "📥 Import Data"])
    
    # --- TAB 1: DASHBOARD ---
    with tab1:
        st.subheader("Monitoring Antrean Hari Ini")
        if st.button("Refresh Data"):
            st.rerun()
            
        try:
            res = requests.get(f"{API_URL}/monitor/dashboard")
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    
                    # Simple Metrics
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Total Pasien Menunggu", df['patients_waiting'].sum())
                    col_b.metric("Sedang Dilayani", df['patients_being_served'].sum())
                    col_c.metric("Selesai", df['patients_finished'].sum())
                else:
                    st.info("Belum ada data antrean hari ini.")
        except:
            st.error("Gagal koneksi ke server.")

    # --- TAB 2: KELOLA DOKTER ---
    with tab2:
        st.subheader("Tambah Dokter Baru")
        
        # Form Tambah Dokter
        with st.form("add_doc"):
            # Ambil list poli dulu
            try:
                pol_data = requests.get(f"{API_URL}/public/polis").json()
                poli_opts = [p['poli'] for p in pol_data]
            except: poli_opts = []
            
            d_name = st.text_input("Nama Dokter (ex: Dr. Budi)")
            d_poli = st.selectbox("Poli", poli_opts)
            c1, c2 = st.columns(2)
            t_start = c1.time_input("Jam Mulai", value=time(8,0))
            t_end = c2.time_input("Jam Selesai", value=time(16,0))
            d_max = st.number_input("Kuota Pasien", value=20)
            
            submitted = st.form_submit_button("Simpan Dokter")
            if submitted:
                payload = {
                    "dokter": d_name,
                    "poli": d_poli,
                    "practice_start_time": t_start.strftime("%H:%M"),
                    "practice_end_time": t_end.strftime("%H:%M"),
                    "max_patients": d_max
                }
                r = requests.post(f"{API_URL}/admin/doctors", json=payload)
                if r.status_code == 200:
                    st.success(f"Dokter {d_name} berhasil ditambahkan! Kode: {r.json()['doctor_code']}")
                else:
                    st.error(f"Gagal: {r.text}")

        st.divider()
        st.subheader("Hapus Dokter")
        doc_id_del = st.number_input("ID Dokter yang akan dihapus", min_value=1, step=1)
        if st.button("Hapus Dokter"):
            r = requests.delete(f"{API_URL}/admin/doctors/{doc_id_del}")
            if r.status_code == 200:
                st.success("Dokter berhasil dihapus.")
            else:
                st.error(r.text)

    # --- TAB 3: KELOLA POLI ---
    with tab3:
        st.subheader("Tambah Poli Baru")
        with st.form("add_poli"):
            p_name = st.text_input("Nama Poli (ex: Poli Kulit)")
            p_prefix = st.text_input("Prefix Kode (ex: KULIT)")
            
            if st.form_submit_button("Simpan Poli"):
                r = requests.post(f"{API_URL}/admin/polis", json={"poli": p_name, "prefix": p_prefix})
                if r.status_code == 200:
                    st.success(f"Poli {p_name} berhasil dibuat.")
                else:
                    st.error(r.text)
        
        st.subheader("Hapus Poli")
        st.warning("Menghapus poli akan menghapus semua dokter dan riwayatnya!")
        poli_del = st.text_input("Nama Poli yang akan dihapus")
        if st.button("Hapus Poli Permanen"):
            r = requests.delete(f"{API_URL}/admin/polis/{poli_del}")
            if r.status_code == 200:
                st.success(f"Poli {poli_del} berhasil dihapus.")
            else:
                st.error(r.text)

    # --- TAB 4: IMPORT ---
    with tab4:
        st.subheader("Import Data Random")
        count = st.number_input("Jumlah data", min_value=1, value=10)
        if st.button("Mulai Import CSV"):
            with st.spinner("Sedang mengimport..."):
                r = requests.get(f"{API_URL}/admin/import-random-data", params={"count": count})
                if r.status_code == 200:
                    st.success(r.json()['message'])
                else:
                    st.error("Gagal import.")

# =================================================================
# 3. HALAMAN OPERASIONAL DOKTER
# =================================================================
elif menu == "Operasional Dokter":
    st.header("🩺 Operasional Dokter")
    
    st.write("Masukkan ID Pelayanan Pasien untuk mengubah status.")
    st.info("Tips: ID Pelayanan bisa dilihat di database atau tabel gabungan.")
    
    svc_id = st.number_input("ID Pelayanan (Ticket ID)", min_value=1)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📢 Panggil Pasien (Melayani)", use_container_width=True):
            r = requests.put(f"{API_URL}/ops/update-status/{svc_id}", json={"action": "call_patient"})
            if r.status_code == 200:
                st.success("Status: SEDANG DILAYANI")
            else:
                st.error(r.text)
                
    with col2:
        if st.button("✅ Selesai (Finish)", type="primary", use_container_width=True):
            r = requests.put(f"{API_URL}/ops/update-status/{svc_id}", json={"action": "finish"})
            if r.status_code == 200:
                st.success("Status: SELESAI")
            else:
                st.error(r.text)