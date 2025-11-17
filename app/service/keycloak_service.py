# app/service/keycloak_service.py
import logging
import httpx
from typing import Dict, Any, Optional

from keycloak import KeycloakOpenID, KeycloakAdmin
from keycloak.exceptions import KeycloakError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# =======================
# ЖЁСТКО ЗАДАННЫЕ НАСТРОЙКИ (без .env)
# =======================
# Базовый URL Keycloak (без завершающего /)
KC_URL = "http://keycloak:8080"

# Realm, где живут пользователи приложения
KC_REALM = "warehouse"

# Клиент приложения (используется для логина/refresh через password grant)
OIDC_CLIENT_ID = "smart-warehouse"
OIDC_CLIENT_SECRET = "45zKeS6G7pTkMXyRYjQXe0kTOqy1c0Ym"

# Админ-клиент с включённым Service Account в ЭТОМ ЖЕ realm (warehouse)
ADMIN_CLIENT_ID = "smart-warehouse-admin"
ADMIN_CLIENT_SECRET = "j3mIv6rNqbjPsxma9W3wsfzPlmGh8YEd"

# =======================


class KeycloakService:
    def __init__(self):
        logger.info(
            "Initializing Keycloak (hardcoded settings)",
            extra=dict(
                url=KC_URL,
                realm=KC_REALM,
                client=OIDC_CLIENT_ID,
                admin_client=ADMIN_CLIENT_ID,
                mode="service-account",
            ),
        )

        # --- OIDC клиент для пользовательской аутентификации (логин/refresh и userinfo) ---
        self.keycloak_openid = KeycloakOpenID(
            server_url=KC_URL,          # без / в конце
            realm_name=KC_REALM,
            client_id=OIDC_CLIENT_ID,
            client_secret_key=OIDC_CLIENT_SECRET,
            verify=True,
        )

        # --- Админ-клиент (Service Account) в ТОМ ЖЕ realm (KC_REALM) ---
        # В админке у клиента smart-warehouse-admin ДОЛЖЕН быть включён Service Accounts,
        # а сервис-аккаунту выданы роли из realm-management: manage-users, query-users, view-users.
        self.keycloak_admin = KeycloakAdmin(
            server_url=KC_URL,
            realm_name=KC_REALM,                # управляем пользователями в этом realm
            client_id=ADMIN_CLIENT_ID,
            client_secret_key=ADMIN_CLIENT_SECRET,
            verify=True,
        )

        # Быстрый пробный вызов для явной диагностики
        try:
            _ = self.keycloak_admin.get_server_info()
            self.keycloak_admin.get_users({"max": 1})
            logger.info("KeycloakAdmin probe OK in realm=%s", KC_REALM)
        except Exception as e:
            logger.error("KeycloakAdmin probe failed in realm=%s: %s", KC_REALM, e)
            # Поднимем исключение — чтобы сразу увидеть проблему конфигурации
            raise

    # =======================
    # Пользовательские операции
    # =======================

    async def create_verified_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str = "",
        username: Optional[str] = None,
    ) -> str:
        """
        Создать пользователя в Keycloak (enabled + emailVerified) и выдать постоянный пароль.
        Возвращает user_id (UUID в Keycloak).
        """
        try:
            username = username or email
            payload = {
                "email": email,
                "username": username,
                "firstName": (first_name or "").strip(),
                "lastName": (last_name or "").strip(),
                "enabled": True,
                "emailVerified": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": password,
                        "temporary": False,
                    }
                ],
            }

            user_id = self.keycloak_admin.create_user(payload)
            logger.info("✅ User created in Keycloak: %s (%s)", user_id, email)
            return user_id

        except KeycloakError as e:
            msg = str(e)
            logger.error("❌ Keycloak error creating user %s: %s", email, msg)
            # типичные коллизии
            if "User exists" in msg or "User exists with same" in msg or "409" in msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User {email} already exists in Keycloak",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create user in Keycloak: {msg}",
            )
        except Exception as e:
            logger.exception("Unexpected error creating user in Keycloak")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}",
            )

    async def delete_user(self, user_id: str) -> bool:
        try:
            self.keycloak_admin.delete_user(user_id)
            logger.info("✅ User deleted from Keycloak: %s", user_id)
            return True
        except KeycloakError as e:
            logger.error("❌ Keycloak error deleting user %s: %s", user_id, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to delete user from Keycloak: {str(e)}",
            )
        except Exception as e:
            logger.exception("Unexpected error deleting user from Keycloak")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}",
            )

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            users = self.keycloak_admin.get_users({"email": email})
            return users[0] if users else None
        except Exception as e:
            logger.error("Error searching user by email %s: %s", email, e)
            return None

    # =======================
    # Аутентификация/токены
    # =======================

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Password grant для клиента приложения (OIDC_CLIENT_ID/SECRET в KC_REALM).
        """
        try:
            token = self.keycloak_openid.token(
                username=email,
                password=password,
                grant_type="password",
            )
            return {
                "user_id": token.get("sub"),
                "email": email,
                "access_token": token["access_token"],
                "refresh_token": token["refresh_token"],
                "expires_in": token["expires_in"],
                "refresh_expires_in": token["refresh_expires_in"],
                "token_type": token["token_type"],
            }
        except KeycloakError as e:
            msg = str(e)
            logger.error("Login error for %s: %s", email, msg)
            if "Invalid user credentials" in msg:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )
        except Exception as e:
            logger.exception("Unexpected login error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during authentication",
            )

    async def logout(self, refresh_token: str) -> bool:
        try:
            self.keycloak_openid.logout(refresh_token)
            return True
        except Exception as e:
            logger.error("Logout error: %s", e)
            return False

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        try:
            token_data = self.keycloak_openid.refresh_token(refresh_token)
            return token_data
        except Exception as e:
            logger.error("Refresh token error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

    async def get_user_info(self, token: str) -> Dict[str, Any]:
        try:
            return self.keycloak_openid.userinfo(token)
        except KeycloakError as e:
            logger.error("Userinfo failed: %s", e)
            raise HTTPException(status_code=401, detail="Invalid access token")

    async def validate_token(self, token: str) -> bool:
        """
        Интроспекция токена. Для публичного/конфиденциального клиента может работать по-разному.
        Если интроспекция отключена — можно опустить этот метод и полагаться на userinfo().
        """
        try:
            result = self.keycloak_openid.introspect(token)
            return bool(result.get("active", False))
        except Exception as e:
            logger.error("Token validation error: %s", e)
            return False

    async def get_identity_from_token(self, access_token: str) -> Dict[str, Any]:
        """
        Возвращает payload userinfo (включая sub/email/name и т.д.) для access_token.
        """
        try:
            # Можно пропустить validate_token и сразу звать userinfo
            user_info = await self.get_user_info(access_token)
            if not user_info or "sub" not in user_info:
                raise HTTPException(status_code=400, detail="Invalid token payload: no 'sub'")
            return user_info
        except HTTPException:
            raise
        except Exception as e:
            logger.error("get_identity_from_token error: %s", e)
            raise HTTPException(status_code=500, detail="Failed to parse access token")
