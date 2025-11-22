from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declaraƟve_base
from dotenv import load_dotenv
import os

load_dotenv()

# Koneksi MySQL
SQLALCHEMY_DATABASE_URL =
f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{o
s.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declaraƟve_base()

def get_db():
db = SessionLocal()
try:
yield db
finally:
db.close()