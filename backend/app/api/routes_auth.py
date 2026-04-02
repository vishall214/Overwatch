"""
OVERWATCH — Authentication API Routes
=====================================
JWT-based signup/login endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database.crud import create_user, get_user_by_email
from app.database.database import get_db
from app.schemas.auth_schema import TokenResponse, UserCreate, UserLogin

router = APIRouter(tags=["Auth"])


@router.post("/auth/signup", response_model=TokenResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    existing = get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(user.password)
    new_user = create_user(db, user.email, hashed)

    token = create_access_token({"sub": str(new_user.id)})
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    db_user = get_user_by_email(db, user.email)

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(db_user.id)})
    return TokenResponse(access_token=token)
