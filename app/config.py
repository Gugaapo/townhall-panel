from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings and configuration"""

    # Application
    APP_NAME: str = "Townhall Document Management API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # MongoDB
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_DATABASE: str = "townhall_db"
    MONGO_USERNAME: str = "admin"
    MONGO_PASSWORD: str = "admin123"

    @property
    def MONGO_URL(self) -> str:
        """Generate MongoDB connection URL"""
        return f"mongodb://{self.MONGO_USERNAME}:{self.MONGO_PASSWORD}@{self.MONGO_HOST}:{self.MONGO_PORT}"

    # Security & Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """Convert CORS origins string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@townhall.com"
    SMTP_FROM_NAME: str = "Townhall System"

    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: str = "pdf,doc,docx,xls,xlsx,jpg,jpeg,png"

    @property
    def ALLOWED_FILE_TYPES_LIST(self) -> List[str]:
        """Convert allowed file types string to list"""
        return [ft.strip() for ft in self.ALLOWED_FILE_TYPES.split(",")]

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """Convert MB to bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


# Create global settings instance
settings = Settings()
