from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.keycloak_user import KeycloakUser
from app.models.user import User
from typing import Optional

async def get_user_by_kkid(session: AsyncSession, kkid: str) -> Optional[User]:
    result = await session.execute(
        select(KeycloakUser)
        .options(selectinload(KeycloakUser.user))
        .where(KeycloakUser.kkid == kkid)
    )
    kk_user = result.scalar_one_or_none()
    return kk_user.user if kk_user else None

async def create_kkid_user(session: AsyncSession, kkid: str, user_id: int) -> KeycloakUser:
    kk_user = KeycloakUser(kkid=kkid, user_id=user_id)
    session.add(kk_user)
    await session.commit()
    await session.refresh(kk_user)
    return kk_user

async def get_kkid_by_user_id(session: AsyncSession, user_id: int) -> Optional[str]:
    result = await session.execute(
        select(KeycloakUser.kkid).where(KeycloakUser.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def delete_kkid_user(session: AsyncSession, kkid: str) -> bool:
    result = await session.execute(
        select(KeycloakUser).where(KeycloakUser.kkid == kkid)
    )
    kk_user = result.scalar_one_or_none()
    if kk_user:
        await session.delete(kk_user)
        await session.commit()
        return True
    return False