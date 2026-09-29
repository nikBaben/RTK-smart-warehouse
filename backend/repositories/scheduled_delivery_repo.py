from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.delivery import ScheduledDelivery


class ScheduledDeliveryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: str) -> ScheduledDelivery | None:
        return await self.session.get(ScheduledDelivery, id)

    async def create(self, **values) -> ScheduledDelivery:
        delivery = ScheduledDelivery(**values, status="scheduled")
        self.session.add(delivery)
        await self.session.flush()
        return delivery
