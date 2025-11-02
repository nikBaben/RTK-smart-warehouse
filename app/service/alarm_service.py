from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.schemas.alarm import AlarmCreate
from app.repositories.alarm_repo import AlarmRepository
from app.models.alarm import Alarm


class AlarmService:
    def __init__(self, repo: AlarmRepository):
        self.repo = repo

    async def create_alarm(self, data: AlarmCreate) -> Alarm:
        alarm_id = str(uuid4())

        try:
            alarm = await self.repo.create(
                id=alarm_id,
                user_id=data.user_id,
                message=data.message,    
            )
            return alarm

        except IntegrityError as e:
            code = getattr(getattr(e, "orig", None), "pgcode", None) or getattr(getattr(e, "orig", None), "sqlstate", None)
            detail = str(getattr(getattr(e, "orig", None), "diag", None) or getattr(e, "orig", e))

            if code == "23505": 
                raise HTTPException(status_code=409, detail="Product with this id already exists")
            if code == "23502":  
                raise HTTPException(status_code=400, detail="Missing required field (NOT NULL violation)")
            if code == "23503":  
                raise HTTPException(status_code=422, detail="Related entity not found (FK violation)")
            raise HTTPException(status_code=500, detail=f"Integrity error: {detail}")
        
    async def delete_alarms(self, user_id: int) -> dict:
        try:
            await self.repo.delete(user_id)
            return {"detail": f"Уведомления удалены."}

        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        except IntegrityError as e:
            code = getattr(getattr(e, "orig", None), "pgcode", None) or getattr(getattr(e, "orig", None), "sqlstate", None)
            detail = str(getattr(getattr(e, "orig", None), "diag", None) or e.orig or e)

            if code == "23503":  # FK violation
                raise HTTPException(
                    status_code=422,
                    detail="Невозможно удалить товар: на него ссылаются другие сущности (FK violation)."
                )
            raise HTTPException(status_code=500, detail=f"Integrity error: {detail}")
        
    async def get_alarms(self, user_id: int):
        alarms = await self.repo.get(user_id)
        if not alarms:
            raise ValueError(f"Уведомелния у пользователя не найдены")
        return alarms