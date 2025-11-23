from fastapi import FastAPI

# Import database engine dan Base
from database import engine, Base

# Import models dari masing-masing modul
from modules.auth import models as auth_models
from modules.master import models as master_models
from modules.queue import models as queue_models

# Import Routers dari masing-masing modul (Asumsi nama file adalah &#39;routers.py&#39;)
from modules.auth.routers import router as auth_router # Menggunakan &#39;routers&#39;
from modules.master.routers import router as master_router # Menggunakan &#39;routers&#39;
from modules.queue.routers import router as queue_router # Menggunakan &#39;routers&#39;

# --- Setup Database ---

# Perintah ini akan mencoba membuat tabel di database MySQL
Base.metadata.create_all(bind=engine)
# --- End Setup Database ---

# --- Inisialisasi Aplikasi FastAPI ---
app = FastAPI(
title=&quot;Hospital Queue System (UAS)&quot;,
description=&quot;Sistem Antrian Rumah Sakit menggunakan FastAPI, SQLAlchemy, dan MySQL.&quot;,
version=&quot;1.0.0&quot;
)
# --- End Inisialisasi Aplikasi FastAPI ---

# --- Registrasi Routers ---
app.include_router(
auth_router,
prefix=&quot;/api/v1/auth&quot;,
tags=[&quot;Authentication&quot;]
)
app.include_router(
master_router,
prefix=&quot;/api/v1/master&quot;,
tags=[&quot;Master Data (Poli, Dokter)&quot;]
)
app.include_router(
queue_router,
prefix=&quot;/api/v1/queue&quot;,
tags=[&quot;Queue Management&quot;]
)
# --- End Registrasi Routers ---

@app.get(&quot;/&quot;, tags=[&quot;Root&quot;])
def root():
&quot;&quot;&quot;
Endpoint utama untuk mengecek status sistem.
&quot;&quot;&quot;
return {
&quot;message&quot;: &quot;System Online&quot;,
&quot;db&quot;: &quot;MySQL Connected&quot;
}