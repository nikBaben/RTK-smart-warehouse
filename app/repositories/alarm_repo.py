from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func,update, delete
from sqlalchemy.exc import IntegrityError

from app.models.alarm import Alarm


class AlarmRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    #Создание уведомления
    async def create(self,*,id: str,user_id: int,message: str,) -> Alarm:
        alarm = Alarm(
            id=id,
            user_id=user_id,
            message=message,
        )

        self.session.add(alarm)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
        await self.session.refresh(alarm)
        return alarm

    #Получение всех уведомлений
    async def get(self,user_id: int) -> list[Alarm]:
        result = await self.session.execute(select(Alarm).where(Alarm.user_id == user_id))
        return result.scalars().all()

    #Удаление всех уведомлений
    async def delete(self, user_id: int):
        stmt = delete(Alarm).where(Alarm.user_id == user_id)
        await self.session.execute(stmt)
        await self.session.commit()
       