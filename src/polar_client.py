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
        self._load_token()
    
    def _load_token(self) -> None:
        """Load OAuth token from file."""
        if self.token_path.exists():
            try:
                with open(self.token_path, "r") as f:
                    self._token = json.load(f)
                logger.debug("Loaded existing OAuth token")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load token: {e}")
                self._token = None
    
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
    
    
    def authorize(self) -> bool:
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
            
            # Register user with AccessLink (sync call as this is CLI setup flow)
            # functionality usually ok to be sync here or we run async wrapper
            asyncio.run(self._register_user())
            
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
        
        Returns:
            List of new PolarActivity objects.
        """
        activities = []
        
        try:
            async with await self._get_client() as client:
                # Create a transaction for exercises
                response = await client.post(
                    f"{self.config.api_base_url}/users/this/exercise-transactions",
                )
                
                if response.status_code == 201:
                    transaction = response.json()
                    transaction_id = str(transaction.get("transaction-id", ""))
                    resource_uri = transaction.get("resource-uri", "")
                    
                    logger.info(f"Created transaction {transaction_id}")
                    
                    # Get list of exercises in transaction
                    list_response = await client.get(resource_uri)
                    
                    if list_response.status_code == 200:
                        exercises_data = list_response.json()
                        exercise_urls = exercises_data.get("exercises", [])
                        
                        # Fetch all exercises in parallel
                        async with asyncio.TaskGroup() as tg:
                             tasks = [tg.create_task(self._fetch_activity(client, url, transaction_id)) for url in exercise_urls]
                        
                        for task in tasks:
                             res = task.result()
                             if res:
                                 activities.append(res)
                    
                elif response.status_code == 204:
                    logger.info("No new activities available")
                else:
                    logger.warning(f"Transaction creation failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to get activities: {e}")
        
        return activities

    async def _fetch_activity(self, client: httpx.AsyncClient, url: str, transaction_id: str) -> Optional[PolarActivity]:
        """Fetch a single activity."""
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                 data = resp.json()
                 activity = PolarActivity.from_api_response(data, transaction_id)
                 activity.tcx_url = data.get("tcx")
                 activity.gpx_url = data.get("gpx")
                 logger.debug(f"Retrieved activity {activity.id}")
                 return activity
        except Exception as e:
            logger.error(f"Failed to get exercise from {url}: {e}")
        return None
    
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
                response = await client.put(
                    f"{self.config.api_base_url}/users/this/exercise-transactions/{transaction_id}",
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
