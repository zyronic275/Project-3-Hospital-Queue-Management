  from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base # Perbaikan: 'declarative_base'
from dotenv import load_dotenv
import os

load_dotenv()

# Koneksi MySQL
# Perbaikan SyntaxError: URL harus didefinisikan dalam satu baris, atau menggunakan tanda kurung.
# Kami menggunakan satu baris untuk kejelasan.
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Inisialisasi Engine dan Session
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() # Menggunakan versi yang benar

# Dependency untuk mendapatkan koneksi DB
def get_db():
    db = SessionLocal() # Perbaikan Indentasi
    try:
        yield db
    finally:
        db.close()