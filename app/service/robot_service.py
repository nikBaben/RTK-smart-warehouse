import time
import random
import string

from uuid import uuid4
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.schemas.robot import RobotCreate
from app.schemas.alarm import AlarmCreate
from app.repositories.robot_repo import RobotRepository
from app.service.alarm_service import AlarmService
from app.models.robot import Robot



class RobotService:
    def __init__(self, repo: RobotRepository,alarm_service:AlarmService):
        self.repo = repo
        self.alarm_service = alarm_service

    async def create_id(self) -> str:
        alphabet = string.digits + string.ascii_uppercase  # 0-9 + A-Z

        def base36(num):
            return ''.join(
                alphabet[num // 36 ** i % 36] for i in reversed(range(2))
            )

        ts = int(time.time()) % 100000
        rnd = random.randint(0, 1295)
        return base36(ts % 1296) + base36(rnd)

    async def create_robot(self, data: RobotCreate)->Robot:#, user_id: int) -> Robot:

        robot_id = await self.create_id()

        if data.warehouse_id is None or data.warehouse_id == "":
            raise HTTPException(status_code=400, detail="warehouse_id is required")
        
        try:
            robot = await self.repo.create(
                id=robot_id,
                status="idle",
                battery_level=100,
                current_zone="A",
                current_row=0,
                current_shelf=0,
                warehouse_id=data.warehouse_id, 
                check_warehouse_exists=True
            )
            #await self.alarm_service.create_alarm(
            #    AlarmCreate(user_id=user_id, message="Робот создан")
            #)
            return robot
        
        

    


        except IntegrityError as e:
            code = getattr(getattr(e, "orig", None), "pgcode", None) or getattr(getattr(e, "orig", None), "sqlstate", None)
            detail = str(getattr(getattr(e, "orig", None), "diag", None) or e.orig or e)

            if code == "23505":  
                raise HTTPException(status_code=409, detail="Robot with this id already exists")
            if code == "23502": 
                raise HTTPException(status_code=400, detail="Missing required field (NOT NULL violation)")
            if code == "23503":  
                raise HTTPException(status_code=422, detail="Related entity not found (FK violation)")
            raise HTTPException(status_code=500, detail=f"Integrity error: {detail}")
    
    async def delete_robot(self, robot_id: str) -> dict:
        try:
            await self.repo.delete(robot_id)
            return {"detail": f"Робот с id '{robot_id}' успешно удалён."}

        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        except IntegrityError as e:
            code = getattr(getattr(e, "orig", None), "pgcode", None) or getattr(getattr(e, "orig", None), "sqlstate", None)
            detail = str(getattr(getattr(e, "orig", None), "diag", None) or e.orig or e)

            if code == "23503":  # FK violation
                raise HTTPException(
                    status_code=422,
                    detail="Невозможно удалить робота: на него ссылаются другие сущности (FK violation)."
                )
            raise HTTPException(status_code=500, detail=f"Integrity error: {detail}")
        
    async def get_robots_by_warehouse_id(self, warehouse_id: str):
        robots = await self.repo.get_all_by_warehouse_id(warehouse_id)
        return robots
    
    async def get_robot(self, robot_id:str): 
        robot = await self.repo.get(robot_id)
        if not robot:
            raise ValueError(f"Роботы на скалде id '{robot_id}' не найдены.")
        return robot
    
    
