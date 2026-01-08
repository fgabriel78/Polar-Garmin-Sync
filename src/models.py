"""Data models for the sync application."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SyncStatus(Enum):
    """Status of a sync operation."""
    
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PolarActivity:
    """Represents an activity from Polar."""
    
    id: str
    polar_user_id: str
    transaction_id: Optional[str]
    date: datetime
    duration: int  # Duration in seconds
    calories: int
    distance: float  # Distance in meters
    activity_type: str
    heart_rate_avg: Optional[int] = None
    heart_rate_max: Optional[int] = None
    training_load: Optional[float] = None
    detailed_sport_info: Optional[str] = None
    has_route: bool = False
    tcx_url: Optional[str] = None
    gpx_url: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: dict, transaction_id: Optional[str] = None) -> "PolarActivity":
        """Create a PolarActivity from Polar API response data."""
        return cls(
            id=str(data.get("id", "")),
            polar_user_id=str(data.get("polar-user", "")),
            transaction_id=transaction_id,
            date=datetime.fromisoformat(data.get("start-time", "").replace("Z", "+00:00")),
            duration=int(data.get("duration", "PT0S").replace("PT", "").replace("S", "").split("H")[0].split("M")[0] or 0),
            calories=int(data.get("calories", 0)),
            distance=float(data.get("distance", 0)),
            activity_type=data.get("detailed-sport-info", data.get("sport", "OTHER")),
            heart_rate_avg=data.get("heart-rate", {}).get("average"),
            heart_rate_max=data.get("heart-rate", {}).get("maximum"),
            training_load=data.get("training-load"),
            detailed_sport_info=data.get("detailed-sport-info"),
            has_route=data.get("has-route", False),
        )


@dataclass
class SyncRecord:
    """Record of a synced activity."""
    
    id: Optional[int] = None
    polar_activity_id: str = ""
    garmin_activity_id: Optional[str] = None
    polar_activity_type: str = ""
    garmin_activity_type: str = ""
    activity_date: Optional[datetime] = None
    sync_status: SyncStatus = SyncStatus.PENDING
    sync_timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    last_error: Optional[str] = None
    file_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "polar_activity_id": self.polar_activity_id,
            "garmin_activity_id": self.garmin_activity_id,
            "polar_activity_type": self.polar_activity_type,
            "garmin_activity_type": self.garmin_activity_type,
            "activity_date": self.activity_date.isoformat() if self.activity_date else None,
            "sync_status": self.sync_status.value,
            "sync_timestamp": self.sync_timestamp.isoformat(),
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "file_path": self.file_path,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SyncRecord":
        """Create from dictionary (database row)."""
        return cls(
            id=data.get("id"),
            polar_activity_id=data.get("polar_activity_id", ""),
            garmin_activity_id=data.get("garmin_activity_id"),
            polar_activity_type=data.get("polar_activity_type", ""),
            garmin_activity_type=data.get("garmin_activity_type", ""),
            activity_date=datetime.fromisoformat(data["activity_date"]) if data.get("activity_date") else None,
            sync_status=SyncStatus(data.get("sync_status", "pending")),
            sync_timestamp=datetime.fromisoformat(data["sync_timestamp"]) if data.get("sync_timestamp") else datetime.now(),
            retry_count=data.get("retry_count", 0),
            last_error=data.get("last_error"),
            file_path=data.get("file_path"),
        )


@dataclass
class SyncResult:
    """Result of a sync operation."""
    
    success: bool
    message: str
    activities_synced: int = 0
    activities_skipped: int = 0
    activities_failed: int = 0
    errors: list[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        return (
            f"Sync {'completed' if self.success else 'failed'}: "
            f"{self.activities_synced} synced, "
            f"{self.activities_skipped} skipped, "
            f"{self.activities_failed} failed"
        )
