"""Polar AccessLink API client."""

import json
import logging
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse
import asyncio

import httpx
from requests_oauthlib import OAuth2Session  # Still useful for constructing auth URLs

from .config.settings import PolarConfig
from .models import PolarActivity

logger = logging.getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    def do_GET(self) -> None:
        """Handle GET request with OAuth callback."""
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        
        if "code" in query_params:
            self.server.auth_code = query_params["code"][0]  # type: ignore
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization successful!</h1>"
                b"<p>You can close this window.</p></body></html>"
            )
        else:
            self.server.auth_code = None  # type: ignore
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization failed!</h1></body></html>"
            )
    
    def log_message(self, format: str, *args) -> None:
        """Suppress HTTP server logs."""
        pass


class PolarClient:
    """Client for interacting with Polar AccessLink API."""
    
    def __init__(self, config: PolarConfig, token_path: Path) -> None:
        """
        Initialize the Polar client.
        
        Args:
            config: Polar API configuration.
            token_path: Path to store OAuth tokens.
        """
        self.config = config
        self.token_path = token_path
        self._token: Optional[dict] = None
        self.user_id: Optional[int] = None
        self._load_token()
    
    def _load_token(self) -> None:
        """Load OAuth token from file."""
        if self.token_path.exists():
            try:
                with open(self.token_path, "r") as f:
                    self._token = json.load(f)
                    self.user_id = self._token.get("x_user_id")
                logger.debug("Loaded existing OAuth token")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load token: {e}")
                self._token = None
                self.user_id = None
    
    def _save_token(self, token: dict) -> None:
        """Save OAuth token to file."""
        self._token = token
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as f:
            json.dump(token, f)
        logger.debug("Saved OAuth token")
    
    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid token."""
        return self._token is not None and "access_token" in self._token
    
    
    async def authorize(self) -> bool:
        """
        Run OAuth authorization flow.
        
        Returns:
            True if authorization was successful.
        """
        logger.info("Starting OAuth authorization flow...")
        
        # Use requests-oauthlib just for convenient URL generation
        oauth = OAuth2Session(
            client_id=self.config.client_id,
            redirect_uri=self.config.redirect_uri,
        )
        
        authorization_url, state = oauth.authorization_url(
            self.config.authorization_url
        )
        
        print(f"\nOpening browser for authorization...")
        print(f"If browser doesn't open, visit: {authorization_url}\n")
        webbrowser.open(authorization_url)
        
        # Start local server to receive callback
        server_address = ("localhost", 8080)
        httpd = HTTPServer(server_address, OAuthCallbackHandler)
        httpd.auth_code = None  # type: ignore
        
        print("Waiting for authorization...")
        httpd.handle_request()
        
        auth_code = httpd.auth_code  # type: ignore
        
        if not auth_code:
            logger.error("Authorization failed - no code received")
            return False
        
        # Exchange code for token
        try:
            token = oauth.fetch_token(
                self.config.token_url,
                code=auth_code,
                client_secret=self.config.client_secret,
            )
            self._save_token(token)
            
            # Register user with AccessLink
            await self._register_user()
            
            logger.info("Authorization successful!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to get token: {e}")
            return False
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get an authenticated AsyncClient."""
        if not self.is_authenticated or not self._token:
            raise RuntimeError("Not authenticated. Please run authorization first.")
            
        headers = {
            "Authorization": f"Bearer {self._token['access_token']}",
            "Accept": "application/json"
        }
        
        return httpx.AsyncClient(headers=headers, timeout=30.0)

    async def _register_user(self) -> None:
        """Register user with Polar AccessLink."""
        try:
            async with await self._get_client() as client:
                response = await client.post(
                    f"{self.config.api_base_url}/users",
                    json={"member-id": f"user_{datetime.now().timestamp()}"},
                )
                
                if response.status_code == 200:
                    logger.info("User registered with AccessLink")
                elif response.status_code == 409:
                    logger.debug("User already registered")
                else:
                    logger.warning(f"User registration status: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"User registration failed: {e}")
    
    async def get_new_activities(self) -> list[PolarActivity]:
        """
        Get new activities from Polar.
        Uses the 'List exercises' endpoint which returns exercises from the last 30 days.
        Local deduplication in SyncManager will handle skipping already synced ones.
        
        Returns:
            List of new PolarActivity objects.
        """
        activities = []
        
        try:
            if not self.user_id:
                logger.error("No user ID found in token. Please re-authorize.")
                return []

            async with await self._get_client() as client:
                # Use the List Exercises API
                # https://www.polar.com/accesslink-api/#list-exercises
                url = f"{self.config.api_base_url}/exercises"
                
                logger.info(f"Fetching exercises from {url}")
                response = await client.get(url)
                
                if response.status_code == 401:
                     logger.error("Authentication failed (401). Token may be expired.")
                     return []
                
                if response.status_code == 200:
                    exercises_data = response.json()
                    # exercises_data should be a list of exercise objects
                    
                    if isinstance(exercises_data, list):
                        logger.info(f"Found {len(exercises_data)} exercises from Polar (last 30 days)")
                        
                        for item in exercises_data:
                            try:
                                # Create activity object
                                activity = PolarActivity.from_api_response(item, transaction_id=None)
                                
                                # Manually construct the TCX/GPX URLs properly since they are standard
                                # Docs: GET /v3/exercises/{exerciseId}/tcx
                                if not activity.tcx_url:
                                     activity.tcx_url = f"{self.config.api_base_url}/exercises/{activity.id}/tcx"
                                if not activity.gpx_url:
                                     activity.gpx_url = f"{self.config.api_base_url}/exercises/{activity.id}/gpx"
                                
                                activities.append(activity)
                            except Exception as e:
                                logger.warning(f"Failed to parse activity item: {e}")
                    else:
                        logger.warning(f"Unexpected response format: {type(exercises_data)}")
                        
                else:
                    logger.warning(f"Failed to list exercises: {response.status_code} - {response.text}")
                    # If 404, standard logic might suggest user not registered, but let's just log for now
                    if response.status_code == 404:
                         logger.warning("Received 404. User might not be registered or API endpoint changed.")
                         # Optional: try self._register_user() if we firmly believe it's needed,
                         # but usually Authorize flow handles it.
                
        except Exception as e:
            logger.error(f"Failed to get activities: {e}")
        
        return activities

    # _fetch_activity is no longer needed with the List Exercises API 
    # as the list endpoint returns full objects (or sufficient summaries).
    
    async def download_tcx(self, tcx_url: str) -> Optional[bytes]:
        """
        Download TCX file for an activity.
        
        Args:
            tcx_url: URL to download TCX from.
        
        Returns:
            TCX file content as bytes, or None if download failed.
        """
        try:
            async with await self._get_client() as client:
                # Override headers specifically for this request
                # AccessLink requires specific accept for TCX
                response = await client.get(
                    tcx_url,
                    headers={
                        "Authorization": f"Bearer {self._token['access_token']}",
                        "Accept": "application/vnd.garmin.tcx+xml"
                    }
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"TCX download failed: {response.status_code}")
                    return None
                
        except Exception as e:
            logger.error(f"TCX download error: {e}")
            return None
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit a transaction to mark activities as retrieved.
        
        Args:
            transaction_id: The transaction ID to commit.
        
        Returns:
            True if commit was successful.
        """
        try:
            async with await self._get_client() as client:
                if not self.user_id:
                     logger.error("No user ID found")
                     return False

                response = await client.put(
                    f"{self.config.api_base_url}/users/{self.user_id}/exercise-transactions/{transaction_id}",
                )
                
                if response.status_code == 200:
                    logger.info(f"Transaction {transaction_id} committed")
                    return True
                else:
                    logger.error(f"Transaction commit failed: {response.status_code}")
                    return False
                
        except Exception as e:
            logger.error(f"Transaction commit error: {e}")
            return False
