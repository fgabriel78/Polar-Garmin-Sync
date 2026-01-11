"""Sync manager for coordinating Polar to Garmin activity sync."""

import logging
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config.activity_mapping import get_garmin_activity_type
from .config.settings import Settings
from .database import Database
from .garmin_client import GarminClient
from .models import PolarActivity, SyncRecord, SyncResult, SyncStatus
from .polar_client import PolarClient

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages synchronization of activities from Polar to Garmin."""
    
    def __init__(
        self,
        settings: Settings,
        polar_client: Optional[PolarClient] = None,
        garmin_client: Optional[GarminClient] = None,
        database: Optional[Database] = None,
    ) -> None:
        """
        Initialize the sync manager.
        
        Args:
            settings: Application settings.
            polar_client: Optional PolarClient instance.
            garmin_client: Optional GarminClient instance.
            database: Optional Database instance.
        """
        self.settings = settings
        
        self.polar = polar_client or PolarClient(
            settings.polar,
            settings.sync.token_path,
        )
        
        self.garmin = garmin_client or GarminClient(
            settings.garmin,
            settings.sync.garmin_session_path,
        )
        
        self.db = database or Database(settings.sync.database_path)
        
        self._temp_dir = Path(tempfile.gettempdir()) / "polar_garmin_sync"
        self._temp_dir.mkdir(exist_ok=True)
    
    async def sync_all(self, dry_run: bool = False) -> SyncResult:
        """
        Sync all new activities from Polar to Garmin.
        
        Args:
            dry_run: If True, don't actually sync, just preview.
        
        Returns:
            SyncResult with operation summary.
        """
        result = SyncResult(success=True, message="Sync completed")
        
        # Ensure we're authenticated
        if not await self._ensure_authenticated():
            return SyncResult(
                success=False,
                message="Authentication failed",
                errors=["Could not authenticate with Polar or Garmin"],
            )
        
        # Get new activities from Polar
        logger.info("Fetching new activities from Polar...")
        activities = await self.polar.get_new_activities()
        
        if not activities:
            logger.info("No new activities to sync")
            result.message = "No new activities found"
            return result
        
        logger.info(f"Found {len(activities)} new activities")
        
        # Process activities in parallel using TaskGroup (Python 3.11+)
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self._safe_sync_activity(activity, dry_run))
                for activity in activities
            ]
        
        # Collect results
        for task in tasks:
            sync_result = task.result()
            
            # Use match/case (Python 3.10+)
            match sync_result:
                case SyncStatus.SUCCESS:
                    result.activities_synced += 1
                case SyncStatus.SKIPPED:
                    result.activities_skipped += 1
                case _:
                     result.activities_failed += 1
        
        if result.activities_failed > 0:
            result.success = False
            result.message = f"Sync completed with {result.activities_failed} failures"
        
        return result

    async def _safe_sync_activity(self, activity: PolarActivity, dry_run: bool) -> SyncStatus:
        """Wrapper to handle exceptions during parallel execution."""
        try:
            return await self._sync_activity(activity, dry_run)
        except Exception as e:
            logger.error(f"Failed to sync activity {activity.id}: {e}")
            return SyncStatus.FAILED
    
    async def _sync_activity(
        self,
        activity: PolarActivity,
        dry_run: bool = False
    ) -> SyncStatus:
        """
        Sync a single activity.
        
        Args:
            activity: The PolarActivity to sync.
            dry_run: If True, don't actually sync.
        
        Returns:
            SyncStatus indicating the result.
        """
        # Check if already synced
        # DB is synchronous, run in thread if we really want to be pure async, but for SQLite it's fast enough usually.
        # However, to be strict about async, we could use to_thread for DB calls too, 
        # but the contention on SQLite might be the bottleneck then.
        # For this exercise, I'll keep DB calls sync as they are fast local reads/writes, 
        # mixing sync IO in async function is not ideal but acceptable for SQLite CLI tools often.
        if self.db.is_activity_synced(activity.id):
            logger.info(f"Activity {activity.id} already synced, skipping")
            return SyncStatus.SKIPPED
        
        # Get or create sync record
        record = self.db.get_sync_record(activity.id) or SyncRecord(
            polar_activity_id=activity.id,
            polar_activity_type=activity.activity_type,
            activity_date=activity.date,
        )
        
        # Map activity type
        garmin_type = get_garmin_activity_type(
            activity.activity_type,
            self.settings.sync.default_activity_type,
        )
        record.garmin_activity_type = garmin_type
        
        logger.info(
            f"Syncing activity {activity.id}: {activity.activity_type} -> {garmin_type}"
        )
        
        if dry_run:
            logger.info(f"[DRY RUN] Would sync activity {activity.id}")
            return SyncStatus.SKIPPED
        
        # Download TCX file
        if not activity.tcx_url:
            logger.warning(f"Activity {activity.id} has no TCX URL")
            record.sync_status = SyncStatus.FAILED
            record.last_error = "No TCX URL available"
            self.db.save_sync_record(record)
            return SyncStatus.FAILED
        
        tcx_content = await self.polar.download_tcx(activity.tcx_url)
        
        if not tcx_content:
            logger.error(f"Failed to download TCX for activity {activity.id}")
            record.sync_status = SyncStatus.FAILED
            record.last_error = "TCX download failed"
            record.retry_count += 1
            self.db.save_sync_record(record)
            return SyncStatus.FAILED
        
        # Save TCX temporarily
        tcx_path = self._temp_dir / f"{activity.id}.tcx"
        # File IO should be async or threaded in strict async app, but purely local temp file write is fast.
        # Let's use to_thread for correctness in optimization.
        await asyncio.to_thread(tcx_path.write_bytes, tcx_content)
        record.file_path = str(tcx_path)
        
        # Upload to Garmin with retry
        garmin_id = await self._upload_with_retry(
            tcx_content,
            f"{activity.id}.tcx",
            garmin_type,
            record,
        )
        
        if garmin_id:
            if garmin_id == "duplicate":
                record.sync_status = SyncStatus.SKIPPED
                record.last_error = "Already exists in Garmin"
                logger.info(f"Activity {activity.id} already exists in Garmin")
            else:
                record.garmin_activity_id = garmin_id
                record.sync_status = SyncStatus.SUCCESS
                record.last_error = None
                logger.info(f"Activity {activity.id} synced to Garmin as {garmin_id}")
        else:
            record.sync_status = SyncStatus.FAILED
            record.retry_count += 1
        
        record.sync_timestamp = datetime.now()
        self.db.save_sync_record(record)
        
        return record.sync_status
    
    async def _upload_with_retry(
        self,
        content: bytes,
        filename: str,
        activity_type: str,
        record: SyncRecord,
    ) -> Optional[str]:
        """
        Upload activity to Garmin with retry logic.
        
        Args:
            content: File content to upload.
            filename: Name of the file.
            activity_type: Garmin activity type.
            record: SyncRecord for tracking retries.
        
        Returns:
            Garmin activity ID or None.
        """
        max_retries = self.settings.sync.retry_attempts
        delay = self.settings.sync.retry_delay_seconds
        
        for attempt in range(max_retries):
            try:
                garmin_id = await self.garmin.upload_activity(
                    content,
                    filename,
                    activity_type,
                )
                
                if garmin_id:
                    return garmin_id
                
            except Exception as e:
                record.last_error = str(e)
                logger.warning(
                    f"Upload attempt {attempt + 1}/{max_retries} failed: {e}"
                )
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        return None
    
    async def retry_failed(self) -> SyncResult:
        """
        Retry all previously failed sync operations.
        
        Returns:
            SyncResult with operation summary.
        """
        result = SyncResult(success=True, message="Retry completed")
        
        # Ensure we're authenticated
        if not await self._ensure_authenticated():
            return SyncResult(
                success=False,
                message="Authentication failed",
                errors=["Could not authenticate with Polar or Garmin"],
            )
        
        # Get failed records
        failed_records = self.db.get_failed_syncs(self.settings.sync.retry_attempts)
        
        if not failed_records:
            logger.info("No failed syncs to retry")
            result.message = "No failed syncs to retry"
            return result
        
        logger.info(f"Retrying {len(failed_records)} failed syncs")
        
        # Process retries in parallel
        async with asyncio.TaskGroup() as tg:
             tasks = [
                 tg.create_task(self._process_retry(record, result))
                 for record in failed_records
             ]
        
        if result.activities_failed > 0:
            result.success = False
            result.message = f"Retry completed with {result.activities_failed} failures"
        
        return result

    async def _process_retry(self, record: SyncRecord, result: SyncResult):
         """Helper to process a single retry item."""
         try:
            # Try to read the cached TCX file
            tcx_path = Path(record.file_path) if record.file_path else None
            
            if tcx_path and tcx_path.exists():
                tcx_content = await asyncio.to_thread(tcx_path.read_bytes)
            else:
                logger.warning(f"No cached file for {record.polar_activity_id}")
                result.activities_failed += 1
                return
            
            garmin_id = await self._upload_with_retry(
                tcx_content,
                f"{record.polar_activity_id}.tcx",
                record.garmin_activity_type,
                record,
            )
            
            if garmin_id and garmin_id != "duplicate":
                record.garmin_activity_id = garmin_id
                record.sync_status = SyncStatus.SUCCESS
                record.last_error = None
                result.activities_synced += 1
            elif garmin_id == "duplicate":
                record.sync_status = SyncStatus.SKIPPED
                result.activities_skipped += 1
            else:
                record.retry_count += 1
                result.activities_failed += 1
            
            record.sync_timestamp = datetime.now()
            # DB writes should be careful if parallel, but SQLite handles concurrency reasonable well for this scale
            self.db.save_sync_record(record)
            
         except Exception as e:
            logger.error(f"Retry failed for {record.polar_activity_id}: {e}")
            result.activities_failed += 1
            result.errors.append(f"{record.polar_activity_id}: {str(e)}")

    async def _ensure_authenticated(self) -> bool:
        """Ensure both Polar and Garmin are authenticated."""
        if not self.polar.is_authenticated:
            logger.error("Polar is not authenticated. Run --authorize first.")
            return False
        
        if not self.garmin.is_authenticated:
            if not await self.garmin.authenticate():
                logger.error("Failed to authenticate with Garmin")
                return False
        
        return True
    
    def get_stats(self) -> dict:
        """
        Get sync statistics.
        
        Returns:
            Dictionary with sync statistics.
        """
        return self.db.get_sync_stats()
