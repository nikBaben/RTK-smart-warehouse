from sqlalchemy.ext.asyncio import AsyncSession
from app.models.keycloak_user import KeycloakUser

class KkidUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, kkid: str, user_id: int) -> KeycloakUser:
        kkid_user = KeycloakUser(kkid=kkid, user_id=user_id)
        self.session.add(kkid_user)
        await self.session.commit()
        await self.session.refresh(kkid_user)
        return kkid_user