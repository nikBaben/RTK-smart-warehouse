from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field,conint


RobotStatus = Literal["idle", "low battery", "charging", "active","scanning"] 


class RobotBase(BaseModel):
    status: RobotStatus = "idle"
    battery_level: conint(ge=0) = Field(100, description="Всего товаров") # type: ignore
    current_zone: str = Field(..., min_length=1)
    current_row: int = 0
    current_shelf: int = 0


class RobotCreate(BaseModel):
    #id: Optional[str] = Field(None, description="Если не передашь — сгенерируем UUID")
    warehouse_id: Optional[str] = Field(None, description="ID склада, к которому привязан робот")
  

class RobotRead(RobotBase):
    id: str
    last_update: Optional[datetime] = None
    created_at: datetime
    warehouse_id: Optional[str]

    class Config:
        from_attributes = True  

