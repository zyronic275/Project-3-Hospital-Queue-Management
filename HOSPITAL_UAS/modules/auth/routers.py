from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # Diperlukan untuk error handling DB

# Import komponen yang diperlukan
from database import get_db
from . import models as auth_models
from . import schemas as auth_schemas # Import Skema Pydantic

from passlib.context import CryptContext

router = APIRouter()

# Inisialisasi Password Context
pwd_context = CryptContext(schemes=[&quot;bcrypt&quot;], deprecated=&quot;auto&quot;)

@router.post(
&quot;/register&quot;,
response_model=auth_schemas.UserResponse, # Response yang dikembalikan akan diformat
sebagai UserResponse
status_code=status.HTTP_201_CREATED # Status HTTP 201 untuk &quot;Created&quot;
)
# Perbaikan: Menerima &#39;user: auth_schemas.UserCreate&#39; sebagai Request Body
def register_user(user: auth_schemas.UserCreate, db: Session = Depends(get_db)):

# 1. Hash Password
hashed_password = pwd_context.hash(user.password)

# 2. Buat objek User SQLAlchemy dari data Pydantic
db_user = auth_models.User(
username=user.username,
hashed_password=hashed_password,
full_name=user.full_name # Menggunakan full_name dari input user (jika ada)
# role akan menggunakan default STAFF
)

# 3. Tambahkan ke database dengan Error Handling
try:
db.add(db_user)
db.commit()
db.refresh(db_user)
except IntegrityError:
# Error handling jika username sudah ada (unique=True)
db.rollback()
raise HTTPException(
status_code=status.HTTP_400_BAD_REQUEST,
detail=&quot;Username already registered.&quot;
)

# 4. Mengembalikan objek yang telah dibuat (sesuai format UserResponse)
return db_user

@router.get(&quot;/&quot;)
def auth_root():
return {&quot;module&quot;: &quot;Authentication&quot;, &quot;status&quot;: &quot;Ready to implement endpoints&quot;}