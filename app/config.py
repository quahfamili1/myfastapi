# config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from dotenv import load_dotenv
import logging

# Load environment variables explicitly
load_dotenv()

class Settings(BaseSettings):
    # OpenMetadata API URL
    OPENMETADATA_API_URL: str = Field(..., env="OPENMETADATA_API_URL")
    OPENMETADATA_TOKEN: str = Field(..., env="OPENMETADATA_TOKEN")

    # Database Configuration
    DATABASE_HOST: str = Field(..., env="DATABASE_HOST")
    DATABASE_PORT: int = Field(..., env="DATABASE_PORT")
    DATABASE_NAME: str = Field(..., env="DATABASE_NAME")
    DATABASE_USER: str = Field(..., env="DATABASE_USER")
    DATABASE_PASSWORD: str = Field(..., env="DATABASE_PASSWORD")

    # JWT Secret Key
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")

    # Token Expiration
    TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="TOKEN_EXPIRE_MINUTES")

    # CORS
    CORS_ORIGINS: str = Field(default="*", env="CORS_ORIGINS")

    # Debug Mode
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    def get_cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS environment variable into a list."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS

settings = Settings()
# Add logging to confirm settings loaded properly
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.debug(f"Loaded OpenMetadata API URL: {settings.OPENMETADATA_API_URL}")