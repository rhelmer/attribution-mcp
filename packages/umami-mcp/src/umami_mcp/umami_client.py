"""
Umami API Client - Zero dependencies
Handles authentication and API calls to Umami Analytics
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from datetime import datetime


class UmamiClient:
    """Client for interacting with Umami Analytics API"""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        team_id: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self.team_id = team_id
        self._auth_token: Optional[str] = None
        self.user_id: Optional[str] = None

        # Auto-detect mode and authenticate
        if self.api_key:
            self.mode = "cloud"
        elif self.username and self.password:
            self.mode = "self-hosted"
            self._authenticate()
        else:
            raise ValueError(
                "Either UMAMI_API_KEY (cloud) or UMAMI_USERNAME + UMAMI_PASSWORD (self-hosted) must be provided"
            )

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[umami-client] {message}\n")
        sys.stderr.flush()

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        use_auth: bool = True,
    ) -> Dict[str, Any]:
        """Make HTTP request to Umami API"""
        # Handle base_url that may or may not include /api
        base = self.base_url.rstrip("/")

        # Endpoint should start with /api, but handle both cases
        if not endpoint.startswith("/api"):
            endpoint = f"/api{endpoint}"

        # Don't double up /api if base already ends with it
        if base.endswith("/api"):
            url = f"{base}{endpoint}"
        else:
            url = f"{base}{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "umami-mcp/1.0",
        }

        if use_auth:
            if self.mode == "cloud" and self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.mode == "self-hosted" and self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"

        body = None
        if data:
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise UmamiAPIError(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise UmamiAPIError(f"Connection error: {e.reason}")
        except json.JSONDecodeError as e:
            raise UmamiAPIError(f"Invalid JSON response: {e}")

    def _authenticate(self) -> None:
        """Authenticate with self-hosted Umami instance"""
        result = self._make_request(
            "/auth/login",
            method="POST",
            data={"username": self.username, "password": self.password},
            use_auth=False,
        )
        self._auth_token = result.get("token")
        self.user_id = result.get("user", {}).get("id")
        if not self._auth_token:
            raise UmamiAPIError("Failed to authenticate: no token received")

    def get_websites(self) -> Dict[str, Any]:
        """Get list of all websites accessible to the user/team"""
        # Try different endpoints based on Umami version and permissions

        # Option 1: Team websites with bearer token (works for team members)
        if self.team_id and self._auth_token:
            try:
                result = self._make_request(f"/teams/{self.team_id}/websites")
                if isinstance(result, dict) and result.get("data"):
                    return result
            except UmamiAPIError as e:
                pass

        # Option 2: Try user-specific websites endpoint (Umami v2+)
        if self.user_id:
            try:
                result = self._make_request(f"/users/{self.user_id}/websites")
                if isinstance(result, dict) and result.get("data"):
                    return result
            except UmamiAPIError as e:
                pass

        # Option 3: Try general websites endpoint
        result = self._make_request("/websites")
        if isinstance(result, dict) and "data" in result:
            return result

        # Return empty result if nothing worked
        return {"data": [], "count": 0}

    def _parse_date(self, date_str: str) -> int:
        """Convert ISO date string to Unix timestamp (milliseconds)"""
        # Handle both YYYY-MM-DD and ISO8601 formats
        try:
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            return int(dt.timestamp() * 1000)
        except Exception as e:
            self._log(f"Error parsing date '{date_str}': {e}")
            # Return current time as fallback
            return int(datetime.now().timestamp() * 1000)

    def get_website(self, website_id: str) -> Dict[str, Any]:
        """Get specific website details"""
        return self._make_request(f"/api/websites/{website_id}")

    def get_stats(
        self,
        website_id: str,
        start_at: str,
        end_at: str,
        unit: str = "day",
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """Get website statistics summary"""
        params = {
            "websiteId": website_id,
            "startAt": self._parse_date(start_at),
            "endAt": self._parse_date(end_at),
            "unit": unit,
            "timezone": timezone,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self._make_request(f"/api/websites/{website_id}/stats?{query}")

    def get_pageviews(
        self,
        website_id: str,
        start_at: str,
        end_at: str,
        unit: str = "day",
        timezone: str = "UTC",
        url: Optional[str] = None,
        referrer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get pageview data with optional filters"""
        params = {
            "websiteId": website_id,
            "startAt": self._parse_date(start_at),
            "endAt": self._parse_date(end_at),
            "unit": unit,
            "timezone": timezone,
        }
        if url:
            params["url"] = url
        if referrer:
            params["referrer"] = referrer

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self._make_request(f"/api/websites/{website_id}/pageviews?{query}")

    def get_metrics(
        self,
        website_id: str,
        start_at: str,
        end_at: str,
        metric_type: str,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Get metrics breakdown by type.
        metric_type: url, referrer, browser, os, device, country, language, event
        """
        valid_types = [
            "url",
            "referrer",
            "browser",
            "os",
            "device",
            "country",
            "language",
            "event",
        ]
        if metric_type not in valid_types:
            raise ValueError(
                f"Invalid metric type: {metric_type}. Must be one of: {valid_types}"
            )

        params = {
            "websiteId": website_id,
            "startAt": self._parse_date(start_at),
            "endAt": self._parse_date(end_at),
            "type": metric_type,
            "timezone": timezone,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self._make_request(f"/api/websites/{website_id}/metrics?{query}")

    def get_utm_metrics(
        self,
        website_id: str,
        start_at: str,
        end_at: str,
        utm_type: str,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Get UTM parameter metrics.
        utm_type: utm_source, utm_medium, utm_campaign, utm_content, utm_term
        """
        valid_types = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]
        if utm_type not in valid_types:
            raise ValueError(
                f"Invalid UTM type: {utm_type}. Must be one of: {valid_types}"
            )

        params = {
            "websiteId": website_id,
            "startAt": self._parse_date(start_at),
            "endAt": self._parse_date(end_at),
            "type": utm_type,
            "timezone": timezone,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self._make_request(f"/api/websites/{website_id}/metrics?{query}")

    def get_active_visitors(self, website_id: str) -> Dict[str, Any]:
        """Get number of active visitors in the last 5 minutes"""
        return self._make_request(f"/api/websites/{website_id}/active")

    def get_realtime_data(
        self, website_id: str, duration: int = 30
    ) -> Dict[str, Any]:
        """Get realtime data for the specified duration (in seconds, default 30)"""
        params = {"duration": duration}
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self._make_request(
            f"/api/websites/{website_id}/realtime/data?{query}"
        )


class UmamiAPIError(Exception):
    """Exception raised for Umami API errors"""

    pass
