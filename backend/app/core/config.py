"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from urllib.parse import urlparse


IS_VERCEL_ENV = os.getenv("VERCEL", "").lower() in {"1", "true", "yes"}


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "Network Monitoring System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    IS_VERCEL: bool = IS_VERCEL_ENV

    # Database - PostgreSQL / Supabase
    DATABASE_URL: Optional[str] = None
    DB_PASSWORD: Optional[str] = None  # Override password in DATABASE_URL (avoids URL-encoding issues)
    POSTGRES_USER: str = "nms"
    POSTGRES_PASSWORD: str = "nms_secret_password"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "nms_db"

    DB_USE_NULL_POOL: bool = IS_VERCEL_ENV
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 3600

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            # If DB_PASSWORD is set separately, replace the password in DATABASE_URL
            if self.DB_PASSWORD:
                from urllib.parse import urlparse, quote_plus, urlunparse
                parsed = urlparse(self.DATABASE_URL)
                encoded_pw = quote_plus(self.DB_PASSWORD)
                netloc = f"{parsed.username}:{encoded_pw}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                return urlunparse((parsed.scheme, netloc, parsed.path,
                                   parsed.params, parsed.query, parsed.fragment))
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # InfluxDB
    INFLUXDB_ENABLED: bool = True
    INFLUXDB_URL: str = "http://influxdb:8086"
    INFLUXDB_TOKEN: str = "nms_secret_password"
    INFLUXDB_ORG: str = "nms_org"
    INFLUXDB_BUCKET: str = "metrics"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "change-me-redis-password"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    ENABLE_CELERY: bool = not IS_VERCEL_ENV

    @property
    def resolved_celery_broker_url(self) -> str:
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def resolved_celery_result_backend(self) -> str:
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # Startup behavior
    AUTO_CREATE_TABLES: bool = not IS_VERCEL_ENV
    SEED_DEFAULT_ADMIN: bool = not IS_VERCEL_ENV
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@nms.local"
    ADMIN_FULL_NAME: str = "Administrator"
    ADMIN_PASSWORD: str = "admin123"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SNMP
    SNMP_TIMEOUT: int = 5  # seconds
    SNMP_RETRIES: int = 2

    # Polling intervals (seconds)
    POLLING_INTERVAL_HEALTH: int = 60  # Device health (CPU, Memory)
    POLLING_INTERVAL_INTERFACE: int = 60  # Interface stats
    POLLING_INTERVAL_ROUTING: int = 300  # Routing protocols
    POLLING_INTERVAL_VPN: int = 300  # VPN tunnels

    # Backup
    BACKUP_DIR: str = "/app/backups"
    BACKUP_RETENTION_DAYS: int = 90
    BACKUP_GIT_ENABLED: bool = False
    BACKUP_GIT_REPO: str = ""

    # Cloud backup (S3)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: Optional[str] = "us-east-1"

    # Alerting
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    ALERT_EMAIL_ENABLED: bool = False

    SLACK_WEBHOOK_URL: Optional[str] = None
    ALERT_SLACK_ENABLED: bool = False

    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    ALERT_TELEGRAM_ENABLED: bool = False

    # Frontend URL (for CORS)
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = ""

    @staticmethod
    def _normalize_origin(origin: str) -> str:
        """Normalize origin values from env vars for CORS matching."""
        clean = origin.strip()
        if not clean:
            return ""

        if clean == "*":
            return clean

        parsed = urlparse(clean)
        if parsed.scheme and parsed.netloc:
            # FastAPI CORS expects origin format: scheme://host[:port]
            return f"{parsed.scheme}://{parsed.netloc}"

        # Fallback for already-normalized values without trailing slash
        return clean.rstrip("/")

    @property
    def parsed_cors_origins(self) -> List[str]:
        origins = {
            self._normalize_origin(self.FRONTEND_URL),
            "http://localhost:3000",
            "http://localhost:5173",
        }
        if self.CORS_ORIGINS:
            for origin in self.CORS_ORIGINS.split(","):
                clean_origin = self._normalize_origin(origin)
                if clean_origin:
                    origins.add(clean_origin)
        return sorted(origin for origin in origins if origin)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
