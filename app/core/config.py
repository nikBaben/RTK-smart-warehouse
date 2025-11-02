from __future__ import annotations
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",        
        case_sensitive=False,  
    )

    #базовые
    APP_NAME: str = "rtk-smart-warehouse"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["*"]  

    #БД
    DB_URL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DB_URL", "DATABASE_URL", "SQLALCHEMY_DATABASE_URI", "DB_DSN"),
    )

    #совместимость
    @property
    def DATABASE_URL(self) -> Optional[str]:
        return self.DB_URL

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> Optional[str]:
        return self.DB_URL

    @property
    def DB_DSN(self) -> Optional[str]:
        return self.DB_URL

    #Redis
    USE_REDIS: bool = True
    REDIS_DSN: str = "redis://redis:6379/0"

    #Keycloak (делаем опциональными, чтобы не валиться, если чего-то нет) ---
    KEYCLOAK_URL: Optional[str] = None
    KEYCLOAK_REALM: Optional[str] = None
    KEYCLOAK_CLIENT_ID: Optional[str] = None
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None
    KEYCLOAK_ADMIN_USERNAME: Optional[str] = None
    KEYCLOAK_ADMIN_PASSWORD: Optional[str] = None

settings = Settings()
