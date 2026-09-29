from uuid import uuid4
from backend.ports import AlarmRepository, Transaction
from backend.schemas.alarm import AlarmCreate


class AlarmService:
    def __init__(self, repo: AlarmRepository, transaction: Transaction):
        self.repo = repo
        self.transaction = transaction

    async def create_alarm(self, data: AlarmCreate):
        async with self.transaction:
            alarm = await self.repo.create(
                id=str(uuid4()), user_id=data.user_id, message=data.message
            )
            await self.transaction.commit()
            return alarm

    async def delete_alarms(self, user_id: int) -> dict:
        async with self.transaction:
            await self.repo.delete(user_id)
            await self.transaction.commit()
        return {"detail": "Уведомления удалены."}

    async def get_alarms(self, user_id: int):
        return await self.repo.get(user_id)
