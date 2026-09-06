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
        "postgresql://neondb_owner:npg_3snhlV1rYeBA@ep-purple-poetry-axvkyvqd-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"
    )
    
    # Google OAuth2 & Gmail Configuration (HTTPS Port 443)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "345293252389-v8am6fn020elna3jb34spg58jb4mj4e9.apps.googleusercontent.com")
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "345293252389-v8am6fn020elna3jb34spg58jb4mj4e9.apps.googleusercontent.com")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "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")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "1//04jRvGIsvawqcCgYIARAAGAQSNwF-L9IrdEgDdYOC45EPM7K6FgSri5wuMA02QhRFfPJsN2xkQNbpSrKgJW80Zo74Gg8RWz67hik")
    GMAIL_SENDER_EMAIL: str = os.getenv("GMAIL_SENDER_EMAIL", "servease.dev@gmail.com")
    GMAIL_FROM_NAME: str = os.getenv("GMAIL_FROM_NAME", "ServEase")

    # OTP Configuration
    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
    OTP_RESEND_COOLDOWN_SECONDS: int = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    
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
