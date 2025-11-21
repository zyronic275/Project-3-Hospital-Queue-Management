import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

#import data
hospital_data= r"healthcare_dataset.csv"
df = pd.read_csv('healthcare_dataset.csv')
df = df.sample(n=1000, random_state=42)


# Hapus kolom yang tidak diperlukan
kolom_hapus = [ "Blood Type", "Medical Condition", "Date of Admission", "Hospital",
    "Billing Amount", "Room Number", "Admission Type", "Discharge Date",
    "Medication", "Test Results", "Insurance Provider", "Doctor"]
df = df.drop(columns=kolom_hapus)


#tambah kolom
#####################TAMBAH KOLOM TANGGAL LAHIR#############################
# --- Generate Tanggal Lahir dari Umur ---
birthdates = []

for age in df["Age"]:
    tahun_lahir = datetime.now().year - age

    # bulan & hari random agar realistis
    bulan  = np.random.randint(1, 13)
    hari   = np.random.randint(1, 28)

    tgl_lahir = datetime(tahun_lahir, bulan, hari)
    birthdates.append(tgl_lahir.date())

df["Date of Birth"] = birthdates

##########################TAMBAH KOLOM ASURANSI DAN POLI#####################

df["Insurance Provider"] = np.random.choice(["BPJS", "Pribadi", "Asuransi"], size=len(df))
df["Poli"] = np.random.choice(["Umum", "Gigi", "Jantung", "Laboratorium"], size=len(df))

###########################START TIME DAN END TIME#######################
start_time = pd.to_datetime("08:00")
end_time   = pd.to_datetime("15:00")

# buat list waktu dengan interval random 20–40 menit
times = []
current = start_time

while current <= end_time:
    times.append(current.time())
    step = np.random.randint(2, 10)
    current += timedelta(minutes=step)

departure_times = [] # Initialize departure_times here
df["Arrival Time"] = np.random.choice(times, size=len(df))

for t in df["Arrival Time"]:
    # convert ke datetime agar bisa ditambah menit
    base = datetime.combine(pd.Timestamp.today(), t)

    # langkah random 20–40 menit
    dur = np.random.randint(20, 41)

    dep = base + timedelta(minutes=dur)
    departure_times.append(dep.time())

df["Departure Time"] = departure_times

########################### TAMBAHKAN TANGGAL (TERPISAH) #######################

# Buat tanggal kunjungan random
start_date = pd.to_datetime("2023-01-01")
end_date   = pd.to_datetime("2023-01-31")

jumlah_hari = (end_date - start_date).days

df["Visit Date"] = [
    (start_date + timedelta(days=np.random.randint(0, jumlah_hari + 1))).date()
    for _ in range(len(df))
]


############################DATA DOKTER##################################
# Kelompok dokter berdasarkan poli
poli_umum = ["Dr. Abel", "Dr. Darell"]
poli_gigi = ["Dr. Justin", "Dr. Riel"]
poli_jantung  = ["Dr. There", "Dr. Eiya"]
poli_mata = ["Dr. Selena Gomez", "Dr. Tatang Suherman"]
poli_paru = ["Dr. Justin Bieber", "Dr. Donald Duck"]


# Membuat daftar semua dokter
all_doctors = poli_umum + poli_gigi + poli_jantung + poli_mata + poli_paru

# Random dokter sesuai kelompok
def pilih_dokter():
    pilihan = np.random.choice(all_doctors)

    # tentukan poli-nya
    if pilihan in poli_umum:
        poli = "Poli Umum"
    elif pilihan in poli_gigi:
        poli = "Poli Gigi"
    else:
        poli = "Jantung"
        if pilihan == "Dr. There":
            poli = "Poli Mata"
        elif pilihan == "Dr. Eiya":
            poli = "Poli Paru"

    return pilihan, poli

# Generate kolom Doctor & Poli
dokter = []
poli = []

for _ in range(len(df)):
    d, p = pilih_dokter()
    dokter.append(d)
    poli.append(p)

df["Doctor"] = dokter
df["Poli"] = poli

df = df[[
    "Name",
    "Gender",
    "Date of Birth",
    "Age",
    "Poli",
    "Doctor",
    "Visit Date",
    "Arrival Time",
    "Departure Time",
    "Insurance Provider"
]]

df = df.sample(n=1000, random_state=42).reset_index(drop=True)

# Save to new dataset
df.to_csv('healthcare_dataset_altered.csv', index=False)
print("File saved as healthcare_dataset_altered.csv")
print(df)