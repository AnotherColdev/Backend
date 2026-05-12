from typing import Dict
from jose import jwt, JWTError
from fastapi import HTTPException, Security, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

def decode_access_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict:
    token = credentials.credentials
    payload = decode_access_token(token)
    
    username: str = payload.get("sub")
    role: str = payload.get("role")
    
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
        
    return {"username": username, "role": role}

def require_role(allowed_roles: list[str]):
    def role_checker(request: Request, user: dict = Depends(get_current_user)):
        user_role = user.get("role")
        if not user_role or user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient restricted permissions")
        request.state.user = user
        return user
    return role_checker
