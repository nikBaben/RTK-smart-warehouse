from sqlalchemy import Column, Integer, String, DateTime,ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Alarm(Base):
    __tablename__ = "alarms"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message =  Column(String)
    message1 =  Column(String)
    message2 =  Column(String)
    message3 =  Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="alarm_user")