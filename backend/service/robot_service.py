import secrets
import string
from backend.domain.errors import InvalidOperation, NotFound
from backend.ports import RobotRepository, WarehouseRepository, Transaction
from backend.schemas.robot import RobotCreate


class RobotService:
    def __init__(
        self,
        repo: RobotRepository,
        warehouses: WarehouseRepository,
        transaction: Transaction,
    ):
        self.repo = repo
        self.warehouses = warehouses
        self.transaction = transaction

    async def create_robot(self, data: RobotCreate):
        if not data.warehouse_id:
            raise InvalidOperation("warehouse_id is required")
        async with self.transaction:
            if await self.warehouses.get_by_id(data.warehouse_id) is None:
                raise NotFound(f"Склад '{data.warehouse_id}' не найден.")
            robot = await self.repo.create(
                id="".join(
                    secrets.choice(string.digits + string.ascii_uppercase)
                    for _ in range(4)
                ),
                status="idle",
                battery_level=100,
                current_zone="A",
                current_row=0,
                current_shelf=0,
                warehouse_id=data.warehouse_id,
            )
            await self.transaction.commit()
            return robot

    async def delete_robot(self, robot_id: str) -> dict:
        async with self.transaction:
            await self.repo.delete(robot_id)
            await self.transaction.commit()
        return {"detail": f"Робот с id '{robot_id}' успешно удалён."}

    async def get_robots_by_warehouse_id(self, warehouse_id: str):
        return await self.repo.get_all_by_warehouse_id(warehouse_id)

    async def get_robot(self, robot_id: str):
        robot = await self.repo.get(robot_id)
        if robot is None:
            raise NotFound(f"Робот '{robot_id}' не найден.")
        return robot
