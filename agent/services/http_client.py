"""
HTTP Client for InfraMind AI Windows Agent.

Responsibilities:
  - Login to the backend and obtain a JWT access token.
  - Auto-refresh the token when a 401 is received.
  - POST device registration and metric ingestion payloads.
  - Retry failed requests with exponential backoff.
  - Raise clear exceptions so the uploader can decide to queue offline.

Design decisions:
  - Uses `httpx` (synchronous client) — the agent is single-threaded and
    runs metric collection + upload on a simple time-based loop.
  - The token is stored in memory only — each agent restart triggers a
    fresh login, which is correct behaviour for a long-running process.
  - `_with_retry` wraps every outbound call with configurable retry count
    and exponential backoff to handle transient network failures.
"""

import time
import logging
from typing import Any, Dict, Optional

import httpx

from agent.config.settings import get_settings, AgentSettings
from agent.utils.logger import get_logger
from agent.utils.credentials import load_credentials, save_credentials, clear_credentials


class BackendHTTPClient:
    """
    Synchronous HTTP client that handles auth and communicates with the
    InfraMind AI FastAPI backend.
    """

    def __init__(self, settings: AgentSettings = get_settings):
        self.settings = settings
        self.logger = get_logger("services.http_client", settings=settings)
        self.base_url = settings.backend_api_url.rstrip("/")
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        
        # Attempt to load saved encrypted credentials on startup
        creds = load_credentials()
        if creds and creds.get("access_token"):
            self._access_token = creds.get("access_token")
            self._refresh_token = creds.get("refresh_token")
            self.logger.info(f"Loaded saved credentials for account: {creds.get('email')}")

        self._client = httpx.Client(
            timeout=settings.upload_timeout_sec,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    # ── Authentication ────────────────────────────────────────────────────────
    def refresh_token(self) -> bool:
        """Attempts to exchange saved refresh_token for new access token."""
        if not self._refresh_token:
            return False
        url = f"{self.base_url}/auth/refresh"
        try:
            resp = self._client.post(url, json={"refresh_token": self._refresh_token})
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data["access_token"]
                self._refresh_token = data.get("refresh_token", self._refresh_token)
                creds = load_credentials() or {}
                save_credentials(
                    creds.get("email", self.settings.backend_email),
                    self._access_token,
                    self._refresh_token,
                )
                self.logger.info("Successfully refreshed JWT access token.")
                return True
        except Exception as e:
            self.logger.warning(f"Token refresh attempt failed: {e}")
        return False

    def login(self) -> bool:
        """
        Authenticates with the backend using stored or configured email/password.
        Stores the JWT access token for subsequent requests.

        Returns True on success, False on failure.
        """
        # Try refresh first if we have a refresh token
        if self._refresh_token and self.refresh_token():
            return True

        url = f"{self.base_url}/auth/login"
        payload = {
            "email": self.settings.backend_email,
            "password": self.settings.backend_password,
        }
        try:
            resp = self._client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data["access_token"]
                self._refresh_token = data.get("refresh_token")
                save_credentials(self.settings.backend_email, self._access_token, self._refresh_token or "")
                self.logger.info("Successfully authenticated with backend.")
                return True
            elif resp.status_code == 401:
                # Agent account may not exist yet on fresh DB instance — attempt auto-registration
                self.logger.info("Agent account not found. Attempting auto-registration...")
                reg_resp = self._client.post(
                    f"{self.base_url}/auth/register",
                    json={
                        "email": self.settings.backend_email,
                        "password": self.settings.backend_password,
                        "full_name": "InfraMind Monitoring Agent",
                    },
                )
                if reg_resp.status_code in (200, 201):
                    self.logger.info("Agent account auto-registered successfully. Retrying login...")
                    retry_login = self._client.post(url, json=payload)
                    if retry_login.status_code == 200:
                        self._access_token = retry_login.json()["access_token"]
                        self.logger.info("Successfully authenticated with backend after auto-registration.")
                        return True
                self.logger.error(
                    f"Login failed: HTTP {resp.status_code} — {resp.text[:200]}"
                )
                return False
            else:
                self.logger.error(
                    f"Login failed: HTTP {resp.status_code} — {resp.text[:200]}"
                )
                return False
        except httpx.RequestError as e:
            self.logger.error(f"Login request failed (backend unreachable?): {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        """Returns True if we have a token, attempts login if we don't."""
        if self._access_token:
            return True
        return self.login()

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    # ── Retry wrapper ─────────────────────────────────────────────────────────
    def _post_with_retry(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Optional[httpx.Response]:
        """
        POST to endpoint with exponential backoff retry.
        Automatically re-authenticates once on 401.

        Returns the Response on success, None if all retries fail.
        """
        if not self._ensure_authenticated():
            return None

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        max_retries = self.settings.upload_max_retries

        for attempt in range(1, max_retries + 1):
            try:
                resp = self._client.post(url, json=payload, headers=self._auth_headers())

                if resp.status_code in (200, 201):
                    return resp

                # Token expired — re-auth once and retry immediately
                if resp.status_code == 401 and attempt == 1:
                    self.logger.warning("Access token expired. Re-authenticating...")
                    self._access_token = None
                    if not self.login():
                        return None
                    continue

                self.logger.warning(
                    f"POST {endpoint} attempt {attempt}/{max_retries}: "
                    f"HTTP {resp.status_code} — {resp.text[:200]}"
                )

            except httpx.RequestError as e:
                self.logger.warning(
                    f"POST {endpoint} attempt {attempt}/{max_retries} failed: {e}"
                )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < max_retries:
                backoff = 2 ** (attempt - 1)
                self.logger.debug(f"Retrying in {backoff}s...")
                time.sleep(backoff)

        self.logger.error(
            f"All {max_retries} attempts failed for POST {endpoint}."
        )
        return None

    # ── Public API methods ────────────────────────────────────────────────────
    def register_device(self, device_payload: Dict[str, Any]) -> bool:
        """
        Calls POST /devices/register with the agent's device metadata.
        Returns True on success.
        """
        resp = self._post_with_retry("/devices/register", device_payload)
        if resp:
            self.logger.info(
                f"Device registered/updated: {device_payload.get('device_uuid')}"
            )
            return True
        return False

    def send_heartbeat(self, device_uuid: str) -> bool:
        """Calls POST /devices/{device_uuid}/heartbeat."""
        resp = self._post_with_retry(f"/devices/{device_uuid}/heartbeat", {})
        return resp is not None

    def ingest_metric(self, metric_payload: Dict[str, Any]) -> bool:
        """
        Calls POST /metrics/ingest with the telemetry payload.
        Returns True on success.
        """
        resp = self._post_with_retry("/metrics/ingest", metric_payload)
        if resp:
            self.logger.debug("Telemetry ingested successfully.")
            return True
        return False

    def close(self) -> None:
        """Close the underlying httpx client and release connections."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
