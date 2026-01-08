"""Tests for database operations."""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Generator

from src.database import Database
from src.models import SyncRecord, SyncStatus


@pytest.fixture
def db() -> Generator[Database, None, None]:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    database = Database(db_path)
    yield database
    
    # Cleanup - close connections before deleting on Windows
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass  # File still locked on Windows, will be cleaned up later


class TestDatabase:
    """Tests for Database class."""
    
    def test_save_and_retrieve_record(self, db: Database) -> None:
        """Test saving and retrieving a sync record."""
        record = SyncRecord(
            polar_activity_id="test123",
            polar_activity_type="RUNNING",
            garmin_activity_type="running",
            activity_date=datetime.now(),
            sync_status=SyncStatus.SUCCESS,
        )
        
        saved = db.save_sync_record(record)
        assert saved.id is not None
        
        retrieved = db.get_sync_record("test123")
        assert retrieved is not None
        assert retrieved.polar_activity_id == "test123"
        assert retrieved.sync_status == SyncStatus.SUCCESS
    
    def test_is_activity_synced(self, db: Database) -> None:
        """Test checking if activity is synced."""
        # Not synced initially
        assert db.is_activity_synced("test456") is False
        
        # Add successful sync
        record = SyncRecord(
            polar_activity_id="test456",
            sync_status=SyncStatus.SUCCESS,
        )
        db.save_sync_record(record)
        
        assert db.is_activity_synced("test456") is True
    
    def test_is_activity_synced_failed(self, db: Database) -> None:
        """Test that failed syncs don't count as synced."""
        record = SyncRecord(
            polar_activity_id="test789",
            sync_status=SyncStatus.FAILED,
        )
        db.save_sync_record(record)
        
        assert db.is_activity_synced("test789") is False
    
    def test_get_failed_syncs(self, db: Database) -> None:
        """Test retrieving failed sync records."""
        # Add some records
        for i in range(3):
            db.save_sync_record(SyncRecord(
                polar_activity_id=f"success_{i}",
                sync_status=SyncStatus.SUCCESS,
            ))
        
        for i in range(2):
            db.save_sync_record(SyncRecord(
                polar_activity_id=f"failed_{i}",
                sync_status=SyncStatus.FAILED,
                retry_count=i,
            ))
        
        failed = db.get_failed_syncs(max_retries=3)
        assert len(failed) == 2
    
    def test_get_failed_syncs_respects_max_retries(self, db: Database) -> None:
        """Test that max retries limit is respected."""
        db.save_sync_record(SyncRecord(
            polar_activity_id="exceeded",
            sync_status=SyncStatus.FAILED,
            retry_count=5,
        ))
        
        failed = db.get_failed_syncs(max_retries=3)
        assert len(failed) == 0
    
    def test_update_existing_record(self, db: Database) -> None:
        """Test updating an existing record."""
        record = SyncRecord(
            polar_activity_id="update_test",
            sync_status=SyncStatus.PENDING,
        )
        saved = db.save_sync_record(record)
        
        # Update the record
        saved.sync_status = SyncStatus.SUCCESS
        saved.garmin_activity_id = "garmin123"
        db.save_sync_record(saved)
        
        retrieved = db.get_sync_record("update_test")
        assert retrieved is not None
        assert retrieved.sync_status == SyncStatus.SUCCESS
        assert retrieved.garmin_activity_id == "garmin123"
    
    def test_get_sync_stats(self, db: Database) -> None:
        """Test retrieving sync statistics."""
        db.save_sync_record(SyncRecord(
            polar_activity_id="s1", sync_status=SyncStatus.SUCCESS
        ))
        db.save_sync_record(SyncRecord(
            polar_activity_id="s2", sync_status=SyncStatus.SUCCESS
        ))
        db.save_sync_record(SyncRecord(
            polar_activity_id="f1", sync_status=SyncStatus.FAILED
        ))
        db.save_sync_record(SyncRecord(
            polar_activity_id="p1", sync_status=SyncStatus.PENDING
        ))
        
        stats = db.get_sync_stats()
        assert stats["total"] == 4
        assert stats["success"] == 2
        assert stats["failed"] == 1
        assert stats["pending"] == 1
    
    def test_clear_history(self, db: Database) -> None:
        """Test clearing sync history."""
        for i in range(5):
            db.save_sync_record(SyncRecord(
                polar_activity_id=f"clear_{i}",
                sync_status=SyncStatus.SUCCESS,
            ))
        
        deleted = db.clear_history()
        assert deleted == 5
        
        stats = db.get_sync_stats()
        assert stats["total"] == 0
