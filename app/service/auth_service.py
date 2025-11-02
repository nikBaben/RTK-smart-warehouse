import logging
from fastapi import HTTPException
from app.schemas.auth import AuthResponse, UserResponse
from app.service.keycloak_service import KeycloakService
from app.service.user_service import UserService

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, keycloak_service: KeycloakService, user_service: UserService):
        self.keycloak_service = keycloak_service
        self.user_service = user_service

    async def login(self, email: str, password: str) -> AuthResponse:
        """Аутентификация пользователя с автоматическим созданием в БД и связью с Keycloak"""
        try:
            # Аутентификация в Keycloak
            auth_data = await self.keycloak_service.login(email, password)
            
            # Получаем информацию о пользователе из Keycloak
            user_info = await self.keycloak_service.get_user_info(auth_data['access_token'])
            kkid = user_info.get('sub')  # Keycloak ID
            
            if not kkid:
                raise HTTPException(status_code=400, detail="Invalid user info from Keycloak")
            
            # Получаем или создаем пользователя в нашей БД
            user = await self.user_service.get_or_create_user_from_keycloak(
                kkid=kkid,
                email=email,
                user_info=user_info,
                password=password
            )
            
            # Формируем ответ
            return AuthResponse(
                token=auth_data['access_token'],
                user={
                    "id": user.id,
                    "name": user.name,
                    "role": user.role,
                    "email": user.email
                }
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error in login: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def refresh_token(self, refresh_token: str) -> AuthResponse:
        """Обновление токена"""
        try:
            auth_data = await self.keycloak_service.refresh_token(refresh_token)
            user_info = await self.keycloak_service.get_user_info(auth_data['access_token'])
            
            # Получаем пользователя из БД
            user = await self.user_service.get_user_by_kkid(user_info.get('sub'))
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return AuthResponse(
                token=auth_data['access_token'],
                user={
                    "id": user.id,
                    "name": user.name,
                    "role": user.role
                }
            )
        except Exception as e:
            logger.error(f"Refresh token error: {e}")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

    async def logout(self, refresh_token: str) -> dict:
        """Выход из системы"""
        success = await self.keycloak_service.logout(refresh_token)
        return {"success": success, "message": "Logged out successfully"}
    

    async def get_current_user(self, access_token: str) -> UserResponse:
        try:
            user_info = await self.keycloak_service.get_identity_from_token(access_token)
            kkid = user_info["sub"]

            user = await self.user_service.get_user_by_kkid(kkid)
            if not user:
                # Если хотите автосоздание — раскомментируйте этот блок
                # email = user_info.get("email")
                # if not email:
                #     raise HTTPException(status_code=400, detail="Email claim is missing")
                # user = await self.user_service.get_or_create_user_from_keycloak(
                #     kkid=kkid,
                #     email=email,
                #     user_info=user_info
                # )
                raise HTTPException(status_code=404, detail="User not found")

            return UserResponse(
                id=user.id,
                name=user.name,
                role=user.role,
                email=user.email
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"get_current_user error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")