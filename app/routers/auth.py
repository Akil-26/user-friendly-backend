from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from ..models import User, ArticleChunk, ChatSession
from ..schemas import (
    RegisterRequest, LoginRequest,
    TokenResponse, UserResponse, InterestsUpdate
)
from ..dependencies import get_current_user
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from ..database import get_db
import bcrypt
import jwt
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── helpers ──────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}  # sub must be string
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── routes ───────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # 1. check email already exists
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. hash password — NEVER store plain text
    hashed = hash_password(data.password)

    # 3. save user
    user = User(
        name=data.name,
        email=data.email,
        password=hashed,
        interests=data.interests
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 4. return JWT token
    return {"access_token": create_token(user.id)}


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # 1. find user
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid email or password")

    # 2. check password
    if not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=401, detail="Invalid email or password")

    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        print(form_data.username)
        print(form_data.password)

    # 3. return JWT token
    return {"access_token": create_token(user.id)}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    # get_current_user handles token verification automatically
    return current_user


@router.put("/me/interests", response_model=UserResponse)
def update_interests(
    data: InterestsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.interests = data.interests
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password")
def change_password(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(data["current_password"], current_user.password):
        raise HTTPException(
            status_code=400, detail="Current password is incorrect")
    current_user.password = hash_password(data["new_password"])
    db.commit()
    return {"message": "Password changed successfully"}


@router.delete("/me")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    password: str = Body(..., embed=True),
):
    # verify password
    if not verify_password(password, current_user.password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect password"
        )

    # delete related data first
    db.query(ArticleChunk).filter(
        ArticleChunk.user_id == current_user.id
    ).delete()
    db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).delete()

    # delete user
    db.delete(current_user)
    db.commit()

    return {"message": "Account deleted successfully"}
