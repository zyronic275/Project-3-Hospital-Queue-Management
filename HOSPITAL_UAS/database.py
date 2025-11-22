from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
# Import find_dotenv untuk mencari file .env di direktori yang berbeda
from dotenv import load_dotenv, find_dotenv
import os
import pymysql # Tambahkan ini untuk memastikan pymysql diimpor

# PERBAIKAN: Gunakan find_dotenv() untuk memastikan file .env ditemukan
# find_dotenv akan mencari file .env di direktori saat ini dan direktori induk.
load_dotenv(find_dotenv())

# Koneksi MySQL
# Pastikan tidak ada spasi di dalam variabel .env yang dibaca (e.g. 'DB_PORT').
# os.getenv() akan mengembalikan None jika tidak ditemukan. Kita tambahkan
# fallback value jika variabel .env tidak terdefinisi (misalnya 3306 untuk port)
SQLALCHEMY_DATABASE_URL = \
f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'kapita_selekta_uas')}"

# Pastikan URL koneksi Anda terlihat benar di konsol untuk debugging
print(f"DEBUG: DB URL: {SQLALCHEMY_DATABASE_URL}")
print(f"DEBUG: DB_PORT check: {os.getenv('DB_PORT')}")


engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  
