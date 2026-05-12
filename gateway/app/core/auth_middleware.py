from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from app.core.config import settings
import functools

def get_auth_payload(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def auth_middleware(request: Request, call_next):
    # Public paths that don't require authentication
    public_paths = [
        "/api/v1/auth/login",
        "/api/v1/auth/register", # If implemented
        "/health",
        "/docs",
        "/openapi.json"
    ]
    
    # Check if the path is a health check (either direct or proxied)
    is_health_path = request.url.path.endswith("/health") or "/health/" in request.url.path
    
    # Check if path is in public paths list
    is_public_path = any(request.url.path.startswith(path) for path in public_paths)
    
    # Bypass authentication for:
    # 1. OPTIONS requests (CORS preflight)
    # 2. Explicit health check paths
    # 3. Known public endpoints
    if request.method == "OPTIONS" or is_health_path or is_public_path:
        return await call_next(request)
    
    payload = get_auth_payload(request)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Store payload in request state for downstream use/role checks
    request.state.user = payload
    
    return await call_next(request)

def require_role(roles: list):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request or not hasattr(request.state, "user"):
                raise HTTPException(status_code=401, detail="No autenticado")
            
            user_role = request.state.user.get("role")
            if user_role not in roles:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Acceso denegado: se requiere uno de los roles {roles}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
