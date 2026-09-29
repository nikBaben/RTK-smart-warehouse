from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.models.user import User
from backend.schemas.user import UserCreate


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_kkid(self, kkid: str) -> Optional[User]:
        from backend.models.keycloak_user import KeycloakUser

        result = await self.session.execute(
            select(User)
            .join(KeycloakUser, User.id == KeycloakUser.user_id)
            .where(KeycloakUser.kkid == kkid)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_create: UserCreate) -> User:
        user = User(
            email=user_create.email,
            name=user_create.name,
            role=user_create.role,
            password_hash=user_create.password_hash,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update(self, user_id: int, update_data: dict) -> Optional[User]:
        # Сначала проверяем существование пользователя
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Выполняем обновление
        stmt = update(User).where(User.id == user_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.flush()

        # Получаем обновленного пользователя
        await self.session.refresh(user)
        return user
