from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class KeycloakUser(Base):
    __tablename__ = "kkid_userid"
    
    kkid = Column(String, primary_key=True, index=True)                 # Keycloak ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="keycloak_user")