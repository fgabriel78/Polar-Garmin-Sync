"""Application settings and configuration."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class PolarConfig(BaseModel):
    """Polar API configuration."""
    
    client_id: str = Field(default_factory=lambda: os.getenv("POLAR_CLIENT_ID", ""))
    client_secret: str = Field(default_factory=lambda: os.getenv("POLAR_CLIENT_SECRET", ""))
    redirect_uri: str = "http://localhost:8080/callback"
    authorization_url: str = "https://flow.polar.com/oauth2/authorization"
    token_url: str = "https://polarremote.com/v2/oauth2/token"
    api_base_url: str = "https://www.polaraccesslink.com/v3"


class GarminConfig(BaseModel):
    """Garmin Connect configuration."""
    
    email: str = Field(default_factory=lambda: os.getenv("GARMIN_EMAIL", ""))
    password: str = Field(default_factory=lambda: os.getenv("GARMIN_PASSWORD", ""))


class SyncConfig(BaseModel):
    """Sync operation configuration."""
    
    retry_attempts: int = Field(default_factory=lambda: int(os.getenv("SYNC_RETRY_ATTEMPTS", "3")))
    retry_delay_seconds: int = Field(default_factory=lambda: int(os.getenv("SYNC_RETRY_DELAY_SECONDS", "30")))
    default_activity_type: str = Field(default_factory=lambda: os.getenv("DEFAULT_ACTIVITY_TYPE", "other"))
    database_path: Path = DATA_DIR / "sync_history.db"
    token_path: Path = DATA_DIR / "polar_token.json"
    garmin_session_path: Path = DATA_DIR / "garmin_session"


class Settings(BaseModel):
    """Application settings container."""
    
    polar: PolarConfig = Field(default_factory=PolarConfig)
    garmin: GarminConfig = Field(default_factory=GarminConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    
    def validate_settings(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.polar.client_id:
            errors.append("POLAR_CLIENT_ID is not set")
        if not self.polar.client_secret:
            errors.append("POLAR_CLIENT_SECRET is not set")
        if not self.garmin.email:
            errors.append("GARMIN_EMAIL is not set")
        if not self.garmin.password:
            errors.append("GARMIN_PASSWORD is not set")
        
        return errors
    
    # helper for compatibility with previous validate() call
    def validate(self) -> list[str]:
        return self.validate_settings()


# Global settings instance
settings = Settings()
