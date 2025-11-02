from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from app.schemas.auth import LoginRequest, AuthResponse, RefreshRequest, TokenResponse
from app.schemas.user import UserResponse  
from app.service.auth_service import AuthService
from app.api.deps import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

#Аутентификация пользователя с автоматическим созданием в БД и связью с Keycloak
@router.post("/login", response_model=AuthResponse)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.login(login_data.email, login_data.password)

#Обновление токена
@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.refresh_token(refresh_data.refresh_token)

#Выход из системы
@router.post("/logout")
async def logout(
    refresh_data: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.logout(refresh_data.refresh_token)


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.get("/config")
async def get_config():
    from app.core.config import settings
    return {
        "keycloak_url": settings.KEYCLOAK_URL,
        "keycloak_realm": settings.KEYCLOAK_REALM,
        "keycloak_client_id": settings.KEYCLOAK_CLIENT_ID,
        "keycloak_client_secret": "***" if settings.KEYCLOAK_CLIENT_SECRET else None,
        "debug": settings.DEBUG
    }