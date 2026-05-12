import hashlib
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _pre_hash_password(password: str) -> str:
    """Helper to bypass bcrypt 72-byte limit by pre-hashing with SHA256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verifyPassword(plainPassword: str, hashedPassword: str) -> bool:
    return pwd_context.verify(_pre_hash_password(plainPassword), hashedPassword)

def getPasswordHash(password: str) -> str:
    return pwd_context.hash(_pre_hash_password(password))

def createAccessToken(subject: Union[str, Any], role: str = "USER", expiresDelta: timedelta = None) -> str:
    if expiresDelta:
        expire = datetime.utcnow() + expiresDelta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    toEncode = {"exp": expire, "sub": str(subject), "role": role}
    return jwt.encode(toEncode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def createRefreshToken(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    toEncode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(toEncode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
