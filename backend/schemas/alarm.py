from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class AlarmBase(BaseModel):
    user_id: int
    message: str


class AlarmCreate(AlarmBase):
    pass


class AlarmResponse(AlarmBase):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}
