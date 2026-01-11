"""Data models for the sync application."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SyncStatus(Enum):
    """Status of a sync operation."""
    
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PolarActivity(BaseModel):
    """Represents an activity from Polar."""
    
    id: str
    polar_user_id: str = Field(alias="polar-user")
    transaction_id: Optional[str] = None
    date: datetime = Field(alias="start-time")
    duration: int
    calories: int
    distance: float
    activity_type: str
    heart_rate_avg: Optional[int] = None
    heart_rate_max: Optional[int] = None
    training_load: Optional[float] = None
    detailed_sport_info: Optional[str] = None
    has_route: bool = False
    tcx_url: Optional[str] = None
    gpx_url: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict, transaction_id: Optional[str] = None) -> "PolarActivity":
        """Create a PolarActivity from Polar API response data."""
        
        # Helper to get value with hyphen or underscore key
        def get_val(d, key_hyphen: str):
            key_under = key_hyphen.replace("-", "_")
            return d.get(key_hyphen, d.get(key_under))

        # Parse duration from ISO format "PT1H2M3S" to seconds
        # The API might verify "PT2H44M" or "PT3600S"
        duration_str = get_val(data, "duration") or "PT0S"
        duration_seconds = 0
        
        try:
            import re
            # Regex to parse ISO duration: PT#H#M#S
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(\.\d+)?)S)?', duration_str)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = float(match.group(3) or 0)
                duration_seconds = int(hours * 3600 + minutes * 60 + seconds)
            else:
                duration_seconds = 0
        except Exception:
            duration_seconds = 0

        # Mapping logical fields
        flat_data = data.copy()
        
        # Normalize keys for Pydantic (it expects aliases like 'start-time' or field name 'date')
        # We will populate the fields directly in flat_data using Pydantic field names where possible
        
        # Handle start-time/date
        start_time = get_val(data, "start-time")
        if start_time:
             flat_data["start-time"] = start_time.replace("Z", "+00:00")
        
        # Handle polar-user
        flat_data["polar-user"] = get_val(data, "polar-user")

        # Handle nested heart-rate
        hr_data = get_val(data, "heart-rate")
        if hr_data:
            flat_data["heart_rate_avg"] = hr_data.get("average")
            flat_data["heart_rate_max"] = hr_data.get("maximum")
        
        # Handle activity type
        flat_data["activity_type"] = get_val(data, "detailed-sport-info") or get_val(data, "sport") or "OTHER"
        
        flat_data["duration"] = duration_seconds
        flat_data["transaction_id"] = transaction_id
        
        # Determine TCX/GPX URLs if not present (for List Exercises API)
        # If 'tcx' key is missing but we have 'id', we can construct it?
        # The calling client might set this, but we can also be smart here if we passed the base URL context.
        # For now, we leave them None if missing, and client handles it.
        flat_data["tcx_url"] = get_val(data, "tcx")
        flat_data["gpx_url"] = get_val(data, "gpx")

        return cls(**flat_data)


class SyncRecord(BaseModel):
    """Record of a synced activity."""
    
    id: Optional[int] = None
    polar_activity_id: str = ""
    garmin_activity_id: Optional[str] = None
    polar_activity_type: str = ""
    garmin_activity_type: str = ""
    activity_date: Optional[datetime] = None
    sync_status: SyncStatus = SyncStatus.PENDING
    sync_timestamp: datetime = Field(default_factory=datetime.now)
    retry_count: int = 0
    last_error: Optional[str] = None
    file_path: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True, validate_default=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        data = self.model_dump(mode='json')
        # Ensure enums are values (handled by use_enum_values but double check if needed for sqlite)
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "SyncRecord":
        """Create from dictionary (database row)."""
        # Pydantic handles coercion
        return cls(**data)


class SyncResult(BaseModel):
    """Result of a sync operation."""
    
    success: bool
    message: str
    activities_synced: int = 0
    activities_skipped: int = 0
    activities_failed: int = 0
    errors: list[str] = Field(default_factory=list)
    
    def __str__(self) -> str:
        return (
            f"Sync {'completed' if self.success else 'failed'}: "
            f"{self.activities_synced} synced, "
            f"{self.activities_skipped} skipped, "
            f"{self.activities_failed} failed"
        )
