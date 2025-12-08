# seed_doctors.py
import pandas as pd
from storage import SessionLocal, TabelDokter, TabelPoli, TabelUser
import security
from datetime import datetime

FILE_DOKTER = "tabel_dokter_normal.csv"

def seed_doctors_from_csv():
    db = SessionLocal()
    try:
        print(f"🔄 Membaca {FILE_DOKTER}...")
        df = pd.read_csv(FILE_DOKTER)
        
        # Bersihkan nama kolom jika ada spasi
        df.columns = df.columns.str.strip()
        
        count = 0
        for _, row in df.iterrows():
            # 1. Pastikan Poli Ada (Foreign Key Safety)
            nama_poli = row['poli'].strip()
            cek_poli = db.query(TabelPoli).filter(TabelPoli.poli == nama_poli).first()
            if not cek_poli:
                # Jika poli belum ada, buat dulu (opsional, biar gak error)
                print(f"⚠️ Poli {nama_poli} belum ada, melewati dokter {row['dokter']}...")
                continue

            # 2. Masukkan Data Dokter ke TabelDokter
            dokter_name = row['dokter'].strip()
            
            # Cek duplikat dokter
            cek_doc = db.query(TabelDokter).filter(TabelDokter.dokter == dokter_name).first()
            if not cek_doc:
                # Parse jam praktik
                t_start = datetime.strptime(row['practice_start_time'], "%H:%M:%S").time()
                t_end = datetime.strptime(row['practice_end_time'], "%H:%M:%S").time()
                
                new_doc = TabelDokter(
                    doctor_id=row['doctor_id'],
                    dokter=dokter_name,
                    poli=nama_poli,
                    practice_start_time=t_start,
                    practice_end_time=t_end,
                    doctor_code=row['doctor_code'],
                    max_patients=row['max_patients']
                )
                db.add(new_doc)
                
                # 3. OTOMATIS BUAT USER LOGIN DOKTER
                # Logic: dr. Ryan -> dr_ryan
                username_doc = dokter_name.lower().replace(" ", "_").replace(".", "").replace("dr_", "dr_")
                if not username_doc.startswith("dr_"): username_doc = "dr_" + username_doc
                
                # Cek user user biar gak double
                if not db.query(TabelUser).filter(TabelUser.username == username_doc).first():
                    new_user = TabelUser(
                        username=username_doc,
                        password=security.get_password_hash("123"), # Password default
                        role="dokter",
                        nama_lengkap=dokter_name # Harus sama persis dgn TabelDokter
                    )
                    db.add(new_user)
                    print(f"✅ Dokter & Akun Login dibuat: {dokter_name} ({username_doc})")
                
                count += 1
            else:
                print(f"ℹ️ Dokter {dokter_name} sudah ada.")
        
        db.commit()
        print(f"🎉 Selesai import {count} dokter baru dari CSV.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_doctors_from_csv()