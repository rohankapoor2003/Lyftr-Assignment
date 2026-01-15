"""Configuration management using environment variables."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    webhook_secret: str
    database_url: str = "sqlite:////data/app.db"
    log_level: str = "INFO"
    enable_metrics: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_db_path(database_url: str) -> Path:
    """Extract SQLite database file path from database URL."""
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        return Path(db_path)
    raise ValueError(f"Unsupported database URL format: {database_url}")


settings = Settings()
