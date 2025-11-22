from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any

# --- KONFIGURASI KEAMANAN ---
# Kunci rahasia (Ganti dengan string acak yang kuat di production)
SECRET_KEY = "rahasia_super_aman_uas_2025"
ALGORITHM = "HS256"

# Konteks untuk hashing kata sandi (menggunakan bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Skema OAuth2PasswordBearer untuk dependency injection di FastAPI
# tokenUrl harus sesuai dengan endpoint login Anda (misalnya /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- UTILITY PASSWORD (Passlib) ---

def hash_password(password: str) -> str:
    """Mengembalikan hash kata sandi menggunakan bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Memverifikasi password biasa dengan hash yang tersimpan."""
    return pwd_context.verify(plain_password, hashed_password)

# --- UTILITY JWT (JSON Web Token) ---

def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Membuat Access Token JWT dengan data dan waktu kadaluarsa."""
    to_encode = data.copy()

    # Set waktu kadaluarsa default jika tidak disediakan
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default 60 menit
        expire = datetime.utcnow() + timedelta(minutes=60)

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_role(token: str = Depends(oauth2_scheme)) -> Dict[str, str]:
    """Dependency Function: Mendekode token dan mengembalikan role pengguna."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Dekode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Ekstrak data yang diperlukan (username disimpan sebagai 'sub')
        username: str = payload.get("sub")
        role: str = payload.get("role")

        if username is None or role is None:
            # Jika payload tidak valid
            raise credentials_exception

        return {"username": username, "role": role}

    except JWTError:
        # Jika token rusak atau kadaluarsa
        raise credentials_exception