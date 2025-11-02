from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_kkid(self, kkid: str) -> Optional[User]:
        from app.models.keycloak_user import KeycloakUser
        result = await self.session.execute(
            select(User)
            .join(KeycloakUser, User.id == KeycloakUser.user_id)
            .where(KeycloakUser.kkid == kkid)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_create: UserCreate) -> User:
        user = User(
            email=user_create.email,
            name=user_create.name,
            role=user_create.role,
            password_hash=user_create.password_hash
        )
        self.session.add(user) 
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        # Сначала проверяем существование пользователя
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Подготавливаем данные для обновления
        update_data = user_update.dict(exclude_unset=True)
        
        # Если в обновлении есть пароль, хэшируем его
        if 'password' in update_data:
            update_data['password_hash'] = get_password_hash(update_data.pop('password'))
        
        # Выполняем обновление
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        
        # Получаем обновленного пользователя
        await self.session.refresh(user)
        return user