import logging
import httpx
from typing import Dict, Any, Optional
from keycloak import KeycloakOpenID, KeycloakAdmin
from keycloak.exceptions import KeycloakError
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

class KeycloakService:
    def __init__(self):
        logger.info(
            f"Initializing Keycloak: URL={settings.KEYCLOAK_URL}, "
            f"Realm={settings.KEYCLOAK_REALM}, "
            f"Client={settings.KEYCLOAK_CLIENT_ID}"
        )

        self.keycloak_openid = KeycloakOpenID(
            server_url=settings.KEYCLOAK_URL,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            realm_name=settings.KEYCLOAK_REALM,
            client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
            verify=True
        )

        #Инициализация KeycloakAdmin для управления пользователями
        self.keycloak_admin = KeycloakAdmin(
            server_url=settings.KEYCLOAK_URL,
            username=settings.KEYCLOAK_ADMIN_USERNAME,
            password=settings.KEYCLOAK_ADMIN_PASSWORD,
            realm_name=settings.KEYCLOAK_REALM,
            verify=True
        )

    async def create_user(self, email: str, password: str, first_name: str, last_name: str = "", username: str = None) -> str:
        try:
            if username is None:
                username = email

            logger.info(f"Creating user in Keycloak: {email}")

            user_data = {
                "email": email,
                "username": username,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": True,
                "credentials": [{
                    "type": "password",
                    "value": password,
                    "temporary": False
                }]
            }

            # Создаем пользователя в Keycloak
            user_id = self.keycloak_admin.create_user(user_data)
            
            logger.info(f"✅ User created in Keycloak: {user_id}, email: {email}")
            return user_id

        except KeycloakError as e:
            logger.error(f"❌ Keycloak error creating user {email}: {e}")
            if "User exists with same username" in str(e) or "User exists with same email" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User with email {email} already exists in Keycloak"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create user in Keycloak: {str(e)}"
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error creating user in Keycloak: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )

    async def delete_user(self, user_id: str) -> bool:
        try:
            logger.info(f"Deleting user from Keycloak: {user_id}")
            self.keycloak_admin.delete_user(user_id)
            logger.info(f"✅ User deleted from Keycloak: {user_id}")
            return True
        except KeycloakError as e:
            logger.error(f"❌ Keycloak error deleting user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to delete user from Keycloak: {str(e)}"
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting user from Keycloak: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}"
            )

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            users = self.keycloak_admin.get_users({"email": email})
            if users:
                return users[0]
            return None
        except Exception as e:
            logger.error(f"Error searching user by email {email}: {e}")
            return None

    # Существующие методы остаются без изменений
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        try:
            logger.info(f"Attempting login for: {email}")

            token = self.keycloak_openid.token(
                username=email,
                password=password,
                grant_type="password"
            )

            logger.info("Login successful")

            return {
                "user_id": token.get('sub'),
                "email": email,
                "access_token": token['access_token'],
                "refresh_token": token['refresh_token'],
                "expires_in": token['expires_in'],
                "refresh_expires_in": token['refresh_expires_in'],
                "token_type": token['token_type'],
            }

        except KeycloakError as e:
            logger.error(f"Login error: {e}")
            if "Invalid user credentials" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            elif "Account is not fully set up" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is not fully set up"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
        except Exception as e:
            logger.error(f"Unexpected login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during authentication"
            )

    async def logout(self, refresh_token: str) -> bool:
        try:
            self.keycloak_openid.logout(refresh_token)
            logger.info("Logout successful")
            return True
        except KeycloakError as e:
            logger.error(f"Logout error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected logout error: {e}")
            return False

    async def get_user_info(self, token: str) -> Dict[str, Any]:
        try:
            user_info = self.keycloak_openid.userinfo(token)
            logger.debug(f"User info retrieved: {user_info.get('sub')}")
            return user_info
        except KeycloakError as e:
            logger.warning(f"Direct userinfo failed: {e}, attempting token exchange")
            exchanged = await self._exchange_token(token)
            exchanged_token = exchanged['access_token']
            user_info = self.keycloak_openid.userinfo(exchanged_token)
            return user_info
        except Exception as e:
            logger.error(f"Unexpected error in get_user_info: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user information"
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        try:
            token_data = self.keycloak_openid.refresh_token(refresh_token)
            logger.info("Token refreshed successfully")
            return token_data
        except KeycloakError as e:
            logger.error(f"Refresh token error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        except Exception as e:
            logger.error(f"Unexpected refresh token error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh token"
            )

    async def validate_token(self, token: str) -> bool:
        try:
            result = self.keycloak_openid.introspect(token)
            is_active = result.get('active', False)

            if is_active:
                logger.debug("Token is active")
                return True
            else:
                logger.warning("Token is not active, attempting token exchange")
                exchanged = await self._exchange_token(token)
                exchanged_token = exchanged['access_token']
                result = self.keycloak_openid.introspect(exchanged_token)
                return result.get('active', False)

        except KeycloakError as e:
            logger.error(f"Token validation error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected token validation error: {e}")
            return False

    async def _exchange_token(self, subject_token: str) -> Dict[str, Any]:
        logger.info("Attempting token exchange")

        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                "scope": "openid"
            }

            url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
            logger.info(f"Exchanging token at: {url}")

            try:
                response = await client.post(url, data=data, timeout=10.0)

                if response.status_code == 200:
                    token_data = response.json()
                    logger.info("Token exchange successful")
                    return token_data
                else:
                    logger.error(f"Token exchange failed with status {response.status_code}: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Token exchange failed: {response.text}"
                    )

            except httpx.TimeoutException:
                logger.error("Token exchange timeout")
                raise HTTPException(status_code=408, detail="Token exchange timeout")
            except Exception as e:
                logger.error(f"Token exchange request failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Token exchange request failed: {str(e)}"
                )

    async def get_identity_from_token(self, access_token: str) -> Dict[str, Any]:
        try:
            is_valid = await self.validate_token(access_token)
            if not is_valid:
                raise HTTPException(status_code=401, detail="Invalid or expired access token")

            # userinfo даст sub/email/name и т.п.
            user_info = await self.get_user_info(access_token)
            if not user_info or "sub" not in user_info:
                raise HTTPException(status_code=400, detail="Invalid token payload: no 'sub'")

            return user_info

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"get_identity_from_token error: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse access token")
