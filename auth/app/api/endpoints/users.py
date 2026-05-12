from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()

def getCurrentUser(db: Session = Depends(get_db), authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

def getCurrentAdminUser(currentUser: User = Depends(getCurrentUser)):
    if currentUser.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: se requiere rol ADMIN")
    return currentUser

@router.get("/me", response_model=UserResponse)
def readUserMe(currentUser: User = Depends(getCurrentUser)):
    return currentUser

@router.get("/", response_model=List[UserResponse])
def readUsers(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    currentAdmin: User = Depends(getCurrentAdminUser)
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.post("/", response_model=UserResponse)
def createUser(
    *,
    db: Session = Depends(get_db),
    userIn: UserCreate,
    currentAdmin: User = Depends(getCurrentAdminUser)
):
    user = db.query(User).filter(User.email == userIn.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario con este email",
        )
    
    userData = userIn.dict()
    password = userData.pop("password")
    userData["password_hash"] = security.getPasswordHash(password)
    
    user = User(**userData)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{userId}", response_model=UserResponse)
def updateUser(
    *,
    db: Session = Depends(get_db),
    userId: int,
    userIn: UserUpdate,
    currentAdmin: User = Depends(getCurrentAdminUser)
):
    user = db.query(User).filter(User.id == userId).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if userId == currentAdmin.id and userIn.is_active is False:
        raise HTTPException(status_code=400, detail="Un administrador no puede desactivar su propia cuenta")

    updateData = userIn.dict(exclude_unset=True)
    if "password" in updateData:
        password = updateData.pop("password")
        user.password_hash = security.getPasswordHash(password)
    
    for field in updateData:
        setattr(user, field, updateData[field])
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{userId}", response_model=UserResponse)
def deleteUser(
    *,
    db: Session = Depends(get_db),
    userId: int,
    currentAdmin: User = Depends(getCurrentAdminUser)
):
    user = db.query(User).filter(User.id == userId).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if userId == currentAdmin.id:
        raise HTTPException(status_code=400, detail="Un administrador no puede eliminarse a sí mismo")
    
    # Soft delete: solo desactiva, no borra
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
