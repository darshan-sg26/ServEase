import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file explicitly
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "ServEase API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "servease_super_secret_jwt_key_2026_vtu_aiml")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    USE_LOCAL_SQLITE: bool = os.getenv("USE_LOCAL_SQLITE", "true").lower() in ("true", "1", "yes")
    
    # Database URL configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        ""
    )
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.USE_LOCAL_SQLITE:
            db_file_path = Path(__file__).resolve().parent.parent.parent / "servease.db"
            return f"sqlite+aiosqlite:///{db_file_path}"

        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        if "channel_binding=" in url:
            import re
            url = re.sub(r'[&?]channel_binding=[^&]+', '', url)
        return url

    class Config:
        env_file = str(env_path)
        extra = "ignore"

settings = Settings()
