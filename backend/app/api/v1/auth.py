from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
router = APIRouter(prefix="/auth", tags=["Authentication"])
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a user")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if not any(c.isupper() for c in body.password) or not any(c.islower() for c in body.password) or not any(c.isdigit() for c in body.password):
        raise HTTPException(422, "Password must contain upper-case, lower-case, and numeric characters")
    if db.scalar(select(User).where(User.email == body.email.lower())): raise HTTPException(409, "Email is already registered")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password)); db.add(user); db.commit(); db.refresh(user); return user
@router.post("/login", response_model=TokenResponse, summary="Log in and get a bearer token")
def login(body: RegisterRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(str(user.id)))
@router.get("/me", response_model=UserResponse, summary="Get current user")
def me(current_user: User = Depends(get_current_user)): return current_user
