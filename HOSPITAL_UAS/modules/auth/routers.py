from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Import komponen DB dan model
from database import get_db
from . import models as auth_models
from . import schemas as auth_schemas

from passlib.context import CryptContext

router = APIRouter()

# Inisialisasi Password Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post(
    "/register",
    response_model=auth_schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user: auth_schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk registrasi user baru.
    """

    # 1. Hash Password
    hashed_password = pwd_context.hash(user.password)

    # 2. Buat objek User SQLAlchemy
    db_user = auth_models.User(
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name  # opsional
        # role default = STAFF
    )

    # 3. Simpan ke database
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )

    # 4. Kembalikan user yang berhasil dibuat
    return db_user


@router.get("/")
def auth_root():
    return {
        "module": "Authentication",
        "status": "Ready to implement endpoints"
    }

