"""SQLite database operations for sync history tracking."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import SyncRecord, SyncStatus, PolarActivity

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for sync history."""
    
    def __init__(self, db_path: Path) -> None:
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._ensure_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self) -> None:
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    polar_activity_id TEXT UNIQUE NOT NULL,
                    garmin_activity_id TEXT,
                    polar_activity_type TEXT,
                    garmin_activity_type TEXT,
                    activity_date TEXT,
                    sync_status TEXT NOT NULL DEFAULT 'pending',
                    sync_timestamp TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    file_path TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_polar_activity_id 
                ON sync_history(polar_activity_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_status 
                ON sync_history(sync_status)
            """)
            
            conn.commit()
            logger.debug("Database tables initialized")
    
    def is_activity_synced(self, polar_activity_id: str) -> bool:
        """
        Check if an activity has already been successfully synced.
        
        Args:
            polar_activity_id: The Polar activity ID to check.
        
        Returns:
            True if the activity has been synced successfully.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT sync_status FROM sync_history WHERE polar_activity_id = ?",
                (polar_activity_id,)
            )
            row = cursor.fetchone()
            # Pydantic models or Enum usage check
            return row is not None and row["sync_status"] == SyncStatus.SUCCESS.value
    
    def get_sync_record(self, polar_activity_id: str) -> Optional[SyncRecord]:
        """
        Get the sync record for an activity.
        
        Args:
            polar_activity_id: The Polar activity ID.
        
        Returns:
            SyncRecord if found, None otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sync_history WHERE polar_activity_id = ?",
                (polar_activity_id,)
            )
            row = cursor.fetchone()
            if row:
                return SyncRecord.from_dict(dict(row))
            return None
    
    def save_sync_record(self, record: SyncRecord) -> SyncRecord:
        """
        Save or update a sync record.
        
        Args:
            record: The SyncRecord to save.
        
        Returns:
            The saved SyncRecord with updated ID.
        """
        with self._get_connection() as conn:
            if record.id:
                conn.execute("""
                    UPDATE sync_history SET
                        garmin_activity_id = ?,
                        polar_activity_type = ?,
                        garmin_activity_type = ?,
                        activity_date = ?,
                        sync_status = ?,
                        sync_timestamp = ?,
                        retry_count = ?,
                        last_error = ?,
                        file_path = ?
                    WHERE id = ?
                """, (
                    record.garmin_activity_id,
                    record.polar_activity_type,
                    record.garmin_activity_type,
                    request_iso := (record.activity_date.isoformat() if record.activity_date else None),
                    record.sync_status,
                    record.sync_timestamp.isoformat(),
                    record.retry_count,
                    record.last_error,
                    record.file_path,
                    record.id,
                ))
            else:
                cursor = conn.execute("""
                    INSERT OR REPLACE INTO sync_history (
                        polar_activity_id, garmin_activity_id, polar_activity_type,
                        garmin_activity_type, activity_date, sync_status,
                        sync_timestamp, retry_count, last_error, file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.polar_activity_id,
                    record.garmin_activity_id,
                    record.polar_activity_type,
                    record.garmin_activity_type,
                    record.activity_date.isoformat() if record.activity_date else None,
                    record.sync_status,
                    record.sync_timestamp.isoformat(),
                    record.retry_count,
                    record.last_error,
                    record.file_path,
                ))
                record.id = cursor.lastrowid
            
            conn.commit()
        
        return record
    
    def get_failed_syncs(self, max_retries: int = 3) -> list[SyncRecord]:
        """
        Get all failed sync records that haven't exceeded max retries.
        
        Args:
            max_retries: Maximum number of retry attempts.
        
        Returns:
            List of failed SyncRecords.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sync_history 
                WHERE sync_status = ? AND retry_count < ?
                ORDER BY sync_timestamp ASC
                """,
                (SyncStatus.FAILED.value, max_retries)
            )
            return [SyncRecord.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_pending_syncs(self) -> list[SyncRecord]:
        """
        Get all pending sync records.
        
        Returns:
            List of pending SyncRecords.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sync_history WHERE sync_status = ?",
                (SyncStatus.PENDING.value,)
            )
            return [SyncRecord.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_sync_stats(self) -> dict:
        """
        Get sync statistics.
        
        Returns:
            Dictionary with sync statistics.
        """
        with self._get_connection() as conn:
            stats = {"total": 0, "success": 0, "failed": 0, "pending": 0, "skipped": 0}
            
            cursor = conn.execute(
                "SELECT sync_status, COUNT(*) as count FROM sync_history GROUP BY sync_status"
            )
            
            for row in cursor.fetchall():
                status = row["sync_status"]
                count = row["count"]
                stats["total"] += count
                if status in stats:
                    stats[status] = count
            
            return stats
    
    def clear_history(self) -> int:
        """
        Clear all sync history.
        
        Returns:
            Number of records deleted.
        """
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM sync_history")
            conn.commit()
            return cursor.rowcount
