# cek_dokter_users.py
from storage import SessionLocal, TabelUser
import pandas as pd

db = SessionLocal()
# Ambil user yang rolenya 'dokter' atau 'admin'
users = db.query(TabelUser).filter(TabelUser.role.in_(['dokter', 'admin'])).all()
df = pd.DataFrame([{"Username": u.username, "Role": u.role, "Nama Asli": u.nama_lengkap} for u in users])
print(df)
db.close()