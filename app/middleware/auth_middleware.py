from fastapi import Request, HTTPException, status
import re
from app.service.auth_service import auth_service


# Публичные пути, не требующие аутентификации
PUBLIC_PATHS = [
    r"^/$",
    r"^/docs",
    r"^/redoc",
    r"^/openapi\.json",
    r"^/health",
    r"^/api/v1/auth/login",
    r"^/api/v1/auth/refresh", 
    r"^/api/v1/auth/validate",
    r"^/api/v1/health",
    r"^/api/v1/config",
]

async def auth_middleware(request: Request, call_next):
    path = request.url.path
    print(f"Middleware checking path: {path}")
    
    is_public = False
    for pattern in PUBLIC_PATHS:
        if re.match(pattern, path):
            is_public = True
            print(f"Public path matched: {pattern} -> {path}")
            break
    
    if is_public:
        return await call_next(request)

    print(f"Protected path: {path}")

    auth_header = request.headers.get("Authorization")
    print(f"Authorization header: {auth_header}")
    
    token = auth_header
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    print(f"Token: {token[7:]}...")

    try:
        is_valid = await auth_service.validate_token_internal(token[7:])
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )

    response = await call_next(request)
    return response