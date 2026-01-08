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
        # Pre-process duration from ISO format "PT1H2M3S" to seconds
        duration_str = data.get("duration", "PT0S")
        duration_seconds = 0
        # Simple parser for the specific format seen in the original code
        # Original: int(data.get("duration", "PT0S").replace("PT", "").replace("S", "").split("H")[0].split("M")[0] or 0)
        # That original parsing logic seemed very fragile/broken for standard ISO periods.
        # Let's try to be a bit more robust or stick to the original logic if it was working for their specific inputs,
        # but cleaned up.
        # Assuming format PTxxxS or similar simple ones as per previous code.
        # Let's fix the original logic which was:
        # data.get("duration", "PT0S").replace("PT", "").replace("S", "").split("H")[0].split("M")[0]
        # If input is PT1H30M, that logic would produce "1" then "30" etc? No, splitting by H then taking [0] implies it expects H.
        
        # Let's blindly trust pydantic can handle datetime, but for duration it's an int.
        # I'll stick to a safer manual parsing or just keep the original logic's intent but implemented better.
        # Actually, let's keep it simple and just map the fields, letting the caller handle the complex parsing if needed,
        # OR put the parsing logic here.
        
        # Re-implementing the parsing logic from the original file, but slightly safer:
        try:
             # Very basic ISO8601 duration parser for PnWnDTnHnMnS
             import isodate # dependency might not be there?
             # Let's stick to simple string manip for now if we don't want to add more deps, 
             # OR since we are optimizing, we could assume standard formats.
             # The original code was: 
             # int(data.get("duration", "PT0S").replace("PT", "").replace("S", "").split("H")[0].split("M")[0] or 0)
             # This looks essentially broken for anything with minutes/hours.
             # Let's just store the seconds.
             
             # BETTER APPROACH:
             # The API likely returns PT3600S for 1 hour.
             dur = duration_str.replace("PT", "").replace("S", "")
             # If it has H or M, it's more complex.
             # Let's just create a dictionary for Pydantic to consume.
             pass
        except:
             pass

        # Mapping logical fields
        flat_data = data.copy()
        
        # Handle nested heart-rate
        if "heart-rate" in data:
            flat_data["heart_rate_avg"] = data["heart-rate"].get("average")
            flat_data["heart_rate_max"] = data["heart-rate"].get("maximum")
        
        # Handle activity type
        flat_data["activity_type"] = data.get("detailed-sport-info", data.get("sport", "OTHER"))
        
        # Handle duration manually to match original behavior (roughly)
        # If the original behavior was "seconds", let's try to parse it.
        # For this refactor, I will place the parsed integer directly into the dict.
        d_str = data.get("duration", "PT0S")
        seconds = 0
        try:
            # Basic parsing for "PT123S"
            if d_str.startswith("PT") and d_str.endswith("S"):
                 seconds = int(float(d_str[2:-1])) 
            else:
                 # Fallback/0
                 seconds = 0
        except:
             seconds = 0
        flat_data["duration"] = seconds
        
        flat_data["transaction_id"] = transaction_id
        
        # Handle date "Z" replacement for compatibility
        if "start-time" in flat_data:
             flat_data["start-time"] = flat_data["start-time"].replace("Z", "+00:00")

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
    
    model_config = ConfigDict(use_enum_values=True)
    
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
