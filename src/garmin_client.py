"""Garmin Connect client using garth library."""

import logging
from pathlib import Path
from typing import Optional

import garth
from garth.exc import GarthHTTPError

from .config.settings import GarminConfig

logger = logging.getLogger(__name__)


class GarminClient:
    """Client for interacting with Garmin Connect."""
    
    def __init__(self, config: GarminConfig, session_path: Path) -> None:
        """
        Initialize the Garmin client.
        
        Args:
            config: Garmin configuration.
            session_path: Path to store session data.
        """
        self.config = config
        self.session_path = session_path
        self._authenticated = False
    
    @property
    def is_authenticated(self) -> bool:
        """Check if we have an active session."""
        return self._authenticated
    
    def authenticate(self) -> bool:
        """
        Authenticate with Garmin Connect.
        
        Returns:
            True if authentication was successful.
        """
        # Try to resume existing session
        if self._try_resume_session():
            return True
        
        # Login with credentials
        return self._login()
    
    def _try_resume_session(self) -> bool:
        """Try to resume an existing session."""
        if self.session_path.exists():
            try:
                garth.resume(str(self.session_path))
                # Test the session
                garth.client.username
                self._authenticated = True
                logger.info("Resumed existing Garmin session")
                return True
            except Exception as e:
                logger.debug(f"Could not resume session: {e}")
        return False
    
    def _login(self) -> bool:
        """Login with email and password."""
        try:
            logger.info("Logging into Garmin Connect...")
            garth.login(self.config.email, self.config.password)
            
            # Save session for future use
            self.session_path.parent.mkdir(parents=True, exist_ok=True)
            garth.save(str(self.session_path))
            
            self._authenticated = True
            logger.info("Successfully logged into Garmin Connect")
            return True
            
        except GarthHTTPError as e:
            logger.error(f"Garmin login failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Garmin login error: {e}")
            return False
    
    def upload_activity(
        self,
        file_content: bytes,
        file_name: str,
        activity_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload an activity file to Garmin Connect.
        
        Args:
            file_content: The TCX/FIT/GPX file content.
            file_name: Name of the file (used to determine format).
            activity_type: Optional Garmin activity type.
        
        Returns:
            Garmin activity ID if successful, None otherwise.
        """
        if not self._authenticated:
            logger.error("Not authenticated with Garmin")
            return None
        
        try:
            # Determine file format from extension
            file_format = file_name.split(".")[-1].lower()
            
            logger.debug(f"Uploading activity: {file_name}")
            
            # Upload using garth
            result = garth.client.upload(file_content)
            
            if result and hasattr(result, "get"):
                activity_id = result.get("detailedImportResult", {}).get(
                    "successes", [{}]
                )[0].get("internalId")
                
                if activity_id:
                    logger.info(f"Activity uploaded successfully: {activity_id}")
                    return str(activity_id)
            
            # Try alternative response format
            if result:
                logger.info("Activity uploaded successfully")
                return str(result) if not isinstance(result, dict) else None
            
            logger.warning("Upload returned no activity ID")
            return None
            
        except GarthHTTPError as e:
            if "duplicate" in str(e).lower() or "409" in str(e):
                logger.warning(f"Activity already exists in Garmin: {e}")
                return "duplicate"
            logger.error(f"Garmin upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Garmin upload error: {e}")
            return None
    
    def get_activities(self, limit: int = 20) -> list[dict]:
        """
        Get recent activities from Garmin Connect.
        
        Args:
            limit: Maximum number of activities to retrieve.
        
        Returns:
            List of activity dictionaries.
        """
        if not self._authenticated:
            logger.error("Not authenticated with Garmin")
            return []
        
        try:
            activities = garth.client.get(
                "activitylist-service",
                f"activities?limit={limit}&start=0",
            )
            return activities if isinstance(activities, list) else []
            
        except Exception as e:
            logger.error(f"Failed to get Garmin activities: {e}")
            return []
    
    def set_activity_type(self, activity_id: str, activity_type: str) -> bool:
        """
        Update the activity type for an uploaded activity.
        
        Args:
            activity_id: Garmin activity ID.
            activity_type: New activity type.
        
        Returns:
            True if update was successful.
        """
        if not self._authenticated:
            logger.error("Not authenticated with Garmin")
            return False
        
        try:
            garth.client.put(
                "activity-service",
                f"activity/{activity_id}",
                json={"activityTypeDTO": {"typeKey": activity_type}},
            )
            logger.debug(f"Updated activity {activity_id} type to {activity_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update activity type: {e}")
            return False
