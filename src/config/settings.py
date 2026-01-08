"""Application settings and configuration."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class PolarConfig:
    """Polar API configuration."""
    
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/callback"
    authorization_url: str = "https://flow.polar.com/oauth2/authorization"
    token_url: str = "https://polarremote.com/v2/oauth2/token"
    api_base_url: str = "https://www.polaraccesslink.com/v3"
    
    @classmethod
    def from_env(cls) -> "PolarConfig":
        """Create configuration from environment variables."""
        return cls(
            client_id=os.getenv("POLAR_CLIENT_ID", ""),
            client_secret=os.getenv("POLAR_CLIENT_SECRET", ""),
        )


@dataclass
class GarminConfig:
    """Garmin Connect configuration."""
    
    email: str
    password: str
    
    @classmethod
    def from_env(cls) -> "GarminConfig":
        """Create configuration from environment variables."""
        return cls(
            email=os.getenv("GARMIN_EMAIL", ""),
            password=os.getenv("GARMIN_PASSWORD", ""),
        )


@dataclass
class SyncConfig:
    """Sync operation configuration."""
    
    retry_attempts: int = 3
    retry_delay_seconds: int = 30
    default_activity_type: str = "other"
    database_path: Path = DATA_DIR / "sync_history.db"
    token_path: Path = DATA_DIR / "polar_token.json"
    garmin_session_path: Path = DATA_DIR / "garmin_session"
    
    @classmethod
    def from_env(cls) -> "SyncConfig":
        """Create configuration from environment variables."""
        return cls(
            retry_attempts=int(os.getenv("SYNC_RETRY_ATTEMPTS", "3")),
            retry_delay_seconds=int(os.getenv("SYNC_RETRY_DELAY_SECONDS", "30")),
            default_activity_type=os.getenv("DEFAULT_ACTIVITY_TYPE", "other"),
        )


class Settings:
    """Application settings container."""
    
    def __init__(self) -> None:
        self.polar = PolarConfig.from_env()
        self.garmin = GarminConfig.from_env()
        self.sync = SyncConfig.from_env()
    
    def validate(self) -> list[str]:
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


# Global settings instance
settings = Settings()
