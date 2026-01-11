"""Tests for data models."""

import pytest
from datetime import datetime

from src.models import SyncRecord, SyncStatus, SyncResult


class TestSyncRecord:
    """Tests for SyncRecord model."""
    
    def test_to_dict(self) -> None:
        """Test converting SyncRecord to dictionary."""
        record = SyncRecord(
            id=1,
            polar_activity_id="test123",
            garmin_activity_id="garmin456",
            polar_activity_type="RUNNING",
            garmin_activity_type="running",
            activity_date=datetime(2024, 1, 15, 10, 30),
            sync_status=SyncStatus.SUCCESS,
            sync_timestamp=datetime(2024, 1, 15, 11, 0),
            retry_count=0,
        )
        
        data = record.to_dict()
        
        assert data["id"] == 1
        assert data["polar_activity_id"] == "test123"
        assert data["garmin_activity_id"] == "garmin456"
        # Pydantic with use_enum_values=True stores the value string
        assert data["sync_status"] == "success"
    
    def test_from_dict(self) -> None:
        """Test creating SyncRecord from dictionary."""
        data = {
            "id": 1,
            "polar_activity_id": "test123",
            "garmin_activity_id": "garmin456",
            "polar_activity_type": "RUNNING",
            "garmin_activity_type": "running",
            "activity_date": "2024-01-15T10:30:00",
            "sync_status": "success",
            "sync_timestamp": "2024-01-15T11:00:00",
            "retry_count": 0,
        }
        
        record = SyncRecord.from_dict(data)
        
        assert record.id == 1
        assert record.polar_activity_id == "test123"
        # Pydantic model field will be the Enum member if queried via .sync_status access?
        # Wait, if use_enum_values=True, the field itself on the instance becomes the value (str).
        # Let's check the defined model config.
        # "model_config = ConfigDict(use_enum_values=True)"
        # So record.sync_status will be 'success' (str), not SyncStatus.SUCCESS.
        assert record.sync_status == "success" 
    
    def test_default_values(self) -> None:
        """Test default values for SyncRecord."""
        record = SyncRecord()
        
        assert record.id is None
        assert record.polar_activity_id == ""
        # Default is SyncStatus.PENDING, which becomes "pending" with use_enum_values=True
        assert record.sync_status == "pending"
        assert record.retry_count == 0


class TestSyncResult:
    """Tests for SyncResult model."""
    
    def test_str_representation(self) -> None:
        """Test string representation of SyncResult."""
        result = SyncResult(
            success=True,
            message="Sync completed",
            activities_synced=5,
            activities_skipped=2,
            activities_failed=1,
        )
        
        result_str = str(result)
        assert "5 synced" in result_str
        assert "2 skipped" in result_str
        assert "1 failed" in result_str
    
    def test_failed_result(self) -> None:
        """Test failed SyncResult."""
        result = SyncResult(
            success=False,
            message="Sync failed",
            errors=["Error 1", "Error 2"],
        )
        
        assert result.success is False
        assert len(result.errors) == 2


class TestSyncStatus:
    """Tests for SyncStatus enum."""
    
    def test_status_values(self) -> None:
        """Test SyncStatus enum values."""
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.SUCCESS.value == "success"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.SKIPPED.value == "skipped"

from src.models import SyncRecord, SyncStatus, SyncResult, PolarActivity

class TestPolarActivity:
    """Tests for PolarActivity model."""
    
    def test_from_api_response(self) -> None:
        """Test parsing PolarActivity from API response."""
        data = {
            "id": "123",
            "polar-user": "user1",
            "start-time": "2023-01-01T10:00:00Z",
            "duration": "PT1H30M10S",
            "calories": 500,
            "distance": 1000.0,
            "detailed-sport-info": "RUNNING",
             "heart-rate": {"average": 140, "maximum": 170}
        }
        
        activity = PolarActivity.from_api_response(data)
        
        # Duration: 1h 30m 10s = 3600 + 1800 + 10 = 5410
        assert activity.duration == 5410
        assert activity.activity_type == "RUNNING"
        assert activity.calories == 500
        assert activity.heart_rate_avg == 140

    def test_underscore_keys(self) -> None:
        """Test parsing with underscore keys (List Exercises format compatibility)."""
        data = {
            "id": "456",
            "polar_user": "user2",
            "start_time": "2023-01-02T10:00:00Z",
            "duration": "PT45M",
            "calories": 300,
            "distance": 5000.0,
            "sport": "CYCLING"
        }
        
        activity = PolarActivity.from_api_response(data)
        
        assert activity.duration == 2700  # 45 * 60
        assert activity.activity_type == "CYCLING"
        assert activity.polar_user_id == "user2"
