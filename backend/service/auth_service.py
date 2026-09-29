from backend.domain.errors import InvalidOperation, NotFound
from backend.ports import IdentityProvider
from backend.schemas.auth import AuthResponse, UserResponse
from backend.service.user_service import UserService


class AuthService:
    def __init__(self, keycloak_service: IdentityProvider, user_service: UserService):
        self.keycloak_service = keycloak_service
        self.user_service = user_service

    @staticmethod
    def _response(token, user):
        return AuthResponse(
            token=token,
            user={
                "id": user.id,
                "name": user.name,
                "role": user.role,
                "email": user.email,
            },
        )

    async def login(self, email: str, password: str) -> AuthResponse:
        auth_data = await self.keycloak_service.login(email, password)
        user_info = await self.keycloak_service.get_user_info(auth_data["access_token"])
        kkid = user_info.get("sub")
        if not kkid:
            raise InvalidOperation("Invalid user info from Keycloak")
        user = await self.user_service.get_or_create_user_from_keycloak(
            kkid, email, user_info, password
        )
        return self._response(auth_data["access_token"], user)

    async def refresh_token(self, refresh_token: str) -> AuthResponse:
        auth_data = await self.keycloak_service.refresh_token(refresh_token)
        user_info = await self.keycloak_service.get_user_info(auth_data["access_token"])
        user = await self.user_service.get_user_by_kkid(user_info.get("sub"))
        if user is None:
            raise NotFound("User not found")
        return self._response(auth_data["access_token"], user)

    async def logout(self, refresh_token: str) -> dict:
        success = await self.keycloak_service.logout(refresh_token)
        return {"success": success, "message": "Logged out successfully"}

    async def get_current_user(self, access_token: str) -> UserResponse:
        info = await self.keycloak_service.get_identity_from_token(access_token)
        user = await self.user_service.get_user_by_kkid(info["sub"])
        if user is None:
            raise NotFound("User not found")
        return UserResponse(
            id=user.id, name=user.name, role=user.role, email=user.email
        )
