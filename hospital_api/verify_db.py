from sqlalchemy import inspect, text
from storage import engine

def check_database():
    print(f"Mencoba koneksi ke: {engine.url}")
    
    try:
        # 1. Tes Koneksi Dasar
        with engine.connect() as connection:
            # Menjalankan query SQL sederhana "SELECT 1" untuk tes ping
            connection.execute(text("SELECT 1"))
            print("✅ Koneksi ke Database BERHASIL!")
            
        # 2. Cek Keberadaan Tabel
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Daftar tabel yang seharusnya ada sesuai kode kita
        expected_tables = ["services", "doctors", "patients", "queues", "doctor_services"]
        print(f"\nTabel yang ditemukan di database: {tables}")
        
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if not missing_tables:
            print("✅ Struktur Valid: Semua tabel yang diharapkan sudah ada.")
        else:
            print(f"❌ Struktur Tidak Lengkap. Tabel yang hilang: {missing_tables}")
            print("Tip: Pastikan storage.init_db() sudah dijalankan setidaknya sekali (via main.py).")
            
        # 3. Cek Detail Kolom (Struktur Tabel)
        if tables:
            print("\n--- Detail Struktur Tabel ---")
            for table in tables:
                print(f"\n[Tabel: {table}]")
                columns = inspector.get_columns(table)
                for col in columns:
                    # Menampilkan Nama Kolom dan Tipe Datanya (INTEGER, VARCHAR, dll)
                    print(f"  - {col['name']} : {col['type']}")

    except Exception as e:
        print(f"\n❌ GAGAL Terkoneksi: {e}")
        print("Tip: Cek username, password, nama database, dan pastikan server MySQL menyala.")

if __name__ == "__main__":
    check_database()