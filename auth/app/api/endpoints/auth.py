from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()

@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), formData: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(
        or_(User.email == formData.username, User.username == formData.username)
    ).first()
    if not user or not security.verifyPassword(formData.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    accessToken = security.createAccessToken(user.email, role=user.role.value)
    refreshToken = security.createRefreshToken(user.email)
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": accessToken,
        "refresh_token": refreshToken,
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserResponse)
def register(userIn: UserCreate, db: Session = Depends(get_db)):
    userExists = db.query(User).filter(
        or_(User.email == userIn.email, User.username == userIn.username)
    ).first()
    if userExists:
        raise HTTPException(status_code=400, detail="El correo o el nombre de usuario ya está en uso.")
    
    newUser = User(
        email=userIn.email,
        username=userIn.username,
        full_name=userIn.full_name or userIn.username,
        password_hash=security.getPasswordHash(userIn.password),
        role=userIn.role,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(newUser)
    db.commit()
    db.refresh(newUser)
    return newUser

@router.post("/logout")
def logout():
    # In search of simplicity for Sprint 1, logout will be handled client-side
    # by clearing tokens. Blacklist could be added here.
    return {"message": "Has cerrado sesión correctamente"}
