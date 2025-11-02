from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с Keycloak
    keycloak_user = relationship("KeycloakUser", back_populates="user", uselist=False)
    alarm_user = relationship(
        "Alarm",
        back_populates="user",
        cascade="all, delete-orphan",
        # uselist=True по умолчанию (у одного User — много Alarm)
    )