from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MonthlyReportRequest(BaseModel):
    year: int
    warehouse_id: str
    months: Optional[list[int]] = None