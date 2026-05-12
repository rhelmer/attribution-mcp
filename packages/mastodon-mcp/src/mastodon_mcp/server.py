"""Mastodon MCP Server with multi-account support.

Usage:
    # Default profile (backward compatible)
    conn = MastodonConnector()
    conn.authenticate()

    # Named profile — reads MASTODON_ACCESS_TOKEN__STELLARWHISKERS etc.
    conn = MastodonConnector(profile="STELLARWHISKERS")
    conn.authenticate()
"""

import os
import sys
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from mastodon import Mastodon as MastodonClient
from mastodon.Mastodon import MastodonAPIError, MastodonUnauthorizedError
from attribution_schema.schema import Metric, Content, Audience
from attribution_cache.cache import Cache
from attribution_profiles import resolve_env


class MastodonConnector:
    """Mastodon connector using the REST API.

    Supports multiple accounts via the `profile` parameter. Each profile
    reads its own env vars (e.g. ``MASTODON_ACCESS_TOKEN__STELLARWHISKERS``).
    """

    name = "mastodon"

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.account = profile.lower()  # canonical account identifier
        self.client = None
        self.instance = resolve_env("MASTODON_INSTANCE", profile) or "mastodon.social"
        self.client_id = resolve_env("MASTODON_CLIENT_ID", profile)
        self.client_secret = resolve_env("MASTODON_CLIENT_SECRET", profile)
        self.access_token = resolve_env("MASTODON_ACCESS_TOKEN", profile)
        self.account_id = resolve_env("MASTODON_ACCOUNT_ID", profile)
        self.cache = Cache()

    def authenticate(self) -> bool:
        """Authenticate with Mastodon."""
        if not self.access_token:
            profile_suffix = f"__{self.profile.upper()}" if self.profile != "default" else ""
            raise ValueError(f"MASTODON_ACCESS_TOKEN{profile_suffix} must be set")

        try:
            self.client = MastodonClient(
                client_id=self.client_id,
                client_secret=self.client_secret,
                access_token=self.access_token,
                api_base_url=f"https://{self.instance}",
            )
            # Verify connection by getting account info
            self.client.account_verify_credentials()
            return True
        except MastodonUnauthorizedError as e:
            raise ValueError(f"Mastodon authentication failed: {e}")
        except Exception as e:
            raise ValueError(f"Failed to connect to Mastodon: {e}")

    def get_metrics(
        self,
        start_date: date,
        end_date: date,
        dimensions: Optional[List[str]] = None
    ) -> List[Metric]:
        """
        Fetch post engagement data from Mastodon.

        Metrics: reblogs, favourites, replies, impressions
        """
        # Try cache first (now account-aware)
        cached = self.cache.get_metrics(
            source=self.name,
            start_date=start_date,
            end_date=end_date,
            account=self.account,
            max_age_hours=1
        )
        if cached:
            return cached

        if not self.client:
            self.authenticate()

        try:
            # Get user's statuses
            statuses = self.client.account_statuses(
                self.account_id,
                limit=40,
                exclude_replies=False,
                exclude_reblogs=False
            )

            metrics = []
            for status in statuses:
                # Parse creation date
                created_at = status["created_at"]
                if isinstance(created_at, datetime):
                    status_date = created_at.date()
                else:
                    try:
                        status_date = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        ).date()
                    except:
                        status_date = date.today()

                # Filter by date range
                if status_date < start_date or status_date > end_date:
                    continue

                status_id = str(status["id"])

                base_dimensions = {
                    "status_id": status_id,
                    "url": status.get("url", ""),
                    "account": self.account,
                }

                # Create metrics for each engagement type
                metrics.append(Metric(
                    source=self.name,
                    date=status_date,
                    metric_type="reblogs",
                    value=status.get("reblogs_count", 0),
                    account=self.account,
                    dimensions=base_dimensions
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=status_date,
                    metric_type="favourites",
                    value=status.get("favourites_count", 0),
                    account=self.account,
                    dimensions=base_dimensions
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=status_date,
                    metric_type="replies",
                    value=status.get("replies_count", 0),
                    account=self.account,
                    dimensions=base_dimensions
                ))

                # Impressions (if available - requires extended token permissions)
                if "pleroma" in self.instance.lower() or hasattr(status, "pleroma"):
                    # Pleroma/Friendica may have different field names
                    pass

            # Cache the results
            self.cache.set_metrics(metrics)
            return metrics

        except MastodonAPIError as e:
            raise ValueError(f"Mastodon API error: {e}")

    def get_content(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Content]:
        """Get posts (statuses) from Mastodon."""
        if not self.client:
            self.authenticate()

        try:
            statuses = self.client.account_statuses(
                self.account_id,
                limit=40,
                exclude_replies=False,
                exclude_reblogs=False
            )

            content_list = []
            for status in statuses:
                created_at = status["created_at"]
                if isinstance(created_at, datetime):
                    status_date = created_at
                else:
                    try:
                        status_date = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    except:
                        status_date = datetime.now()

                # Filter by date range
                if status_date.date() < start_date or status_date.date() > end_date:
                    continue

                # Extract plain text content (strip HTML)
                content_text = status.get("content", "")
                content_text = re.sub(r"<[^>]+>", "", content_text)

                content = Content(
                    source=self.name,
                    content_id=str(status["id"]),
                    content_type="post",
                    url=status.get("url", ""),
                    title=content_text[:100] + "..." if len(content_text) > 100 else content_text,
                    created_at=status_date,
                    account=self.account,
                    author=status.get("account", {}).get("username", ""),
                    metrics=[
                        Metric(
                            source=self.name,
                            date=status_date.date(),
                            metric_type="reblogs",
                            value=status.get("reblogs_count", 0),
                            account=self.account,
                            dimensions={"status_id": str(status["id"]), "account": self.account}
                        ),
                        Metric(
                            source=self.name,
                            date=status_date.date(),
                            metric_type="favourites",
                            value=status.get("favourites_count", 0),
                            account=self.account,
                            dimensions={"status_id": str(status["id"]), "account": self.account}
                        ),
                        Metric(
                            source=self.name,
                            date=status_date.date(),
                            metric_type="replies",
                            value=status.get("replies_count", 0),
                            account=self.account,
                            dimensions={"status_id": str(status["id"]), "account": self.account}
                        ),
                    ]
                )
                content_list.append(content)

            return content_list

        except MastodonAPIError as e:
            raise ValueError(f"Mastodon API error: {e}")

    def get_audience(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Audience]:
        """Get follower count."""
        if not self.client:
            self.authenticate()

        try:
            account = self.client.account(self.account_id)
            followers_count = account.get("followers_count", 0)

            return [Audience(
                source=self.name,
                date=date.today(),
                segment="followers",
                count=followers_count,
                account=self.account,
            )]

        except MastodonAPIError as e:
            raise ValueError(f"Mastodon API error: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Test Mastodon connection and return status."""
        try:
            if not self.client:
                self.authenticate()

            # Get account info
            account = self.client.account_verify_credentials()

            return {
                "status": "connected",
                "account": self.account,
                "instance": self.instance,
                "username": account.get("username"),
                "followers": account.get("followers_count", 0),
                "message": f"Successfully connected to Mastodon [profile: {self.profile}]"
            }

        except Exception as e:
            return {
                "status": "error",
                "account": self.account,
                "message": str(e)
            }


# MCP Server implementation
class MCPServer:
    """MCP Server for Mastodon with multi-account support.

    Discovers all Mastodon profiles and exposes one tool set per profile.
    """

    def __init__(self):
        self.connectors: Dict[str, MastodonConnector] = {}
        self.initialized = False

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[mastodon-mcp] {message}\n")
        sys.stderr.flush()

    def _send_response(self, response: Dict[str, Any]) -> None:
        """Send JSON-RPC response to stdout"""
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> Dict[str, Any]:
        """Create error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def _success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Create success response"""
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize connectors for all discovered profiles."""
        from attribution_profiles import discover_profiles

        profiles = discover_profiles("MASTODON_ACCESS_TOKEN")
        if not profiles:
            return self._error_response(
                request.get("id"), -32000,
                "No Mastodon profiles configured. Set MASTODON_ACCESS_TOKEN in .env"
            )

        errors = []
        for profile in profiles:
            try:
                conn = MastodonConnector(profile=profile)
                conn.authenticate()
                self.connectors[profile] = conn
                self._log(f"Initialized Mastodon profile: {profile}")
            except Exception as e:
                errors.append(f"{profile}: {e}")
                self._log(f"Failed to initialize Mastodon profile {profile}: {e}")

        if not self.connectors:
            return self._error_response(
                request.get("id"), -32000,
                f"Failed to initialize any Mastodon profiles: {'; '.join(errors)}"
            )

        self.initialized = True

        return self._success_response(
            request.get("id"),
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "mastodon-mcp",
                    "version": "2.0.0",
                    "profiles": list(self.connectors.keys()),
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request — show per-profile tools."""
        tools = []

        for profile in self.connectors.keys():
            account_label = profile if profile != "default" else "personal"
            profile_tag = f"_{profile}" if profile != "default" else ""

            tools.extend([
                {
                    "name": f"get_mastodon{profile_tag}_metrics",
                    "description": f"Get Mastodon post engagement metrics (profile: {account_label})",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date in YYYY-MM-DD format",
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": "End date in YYYY-MM-DD format",
                            },
                        },
                        "required": ["start_date", "end_date"],
                    },
                },
                {
                    "name": f"get_mastodon{profile_tag}_posts",
                    "description": f"Get Mastodon posts with engagement data (profile: {account_label})",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date in YYYY-MM-DD format",
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": "End date in YYYY-MM-DD format",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of posts to return (default: 40)",
                            },
                        },
                        "required": ["start_date", "end_date"],
                    },
                },
                {
                    "name": f"get_mastodon{profile_tag}_followers",
                    "description": f"Get follower count (profile: {account_label})",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                },
                {
                    "name": f"test_mastodon{profile_tag}_connection",
                    "description": f"Test the Mastodon connection (profile: {account_label})",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                },
            ])

        # Also expose a "catch-all" tool that accepts an account param
        tools.append({
            "name": "get_mastodon_all",
            "description": "Get metrics from all configured Mastodon profiles",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "End date in YYYY-MM-DD format",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        })

        return self._success_response(request.get("id"), {"tools": tools})

    def _call_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        if not self.initialized:
            return self._error_response(
                request.get("id"), -32000, "Server not initialized"
            )

        params = request.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        try:
            result = self._execute_tool(tool_name, tool_args)
            return self._success_response(
                request.get("id"),
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, default=str),
                        }
                    ]
                },
            )
        except ValueError as e:
            return self._success_response(
                request.get("id"),
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"error": str(e)}, indent=2),
                        }
                    ]
                },
            )
        except Exception as e:
            return self._error_response(request.get("id"), -32000, str(e))

    def _execute_tool(
        self, tool_name: str, args: Dict[str, Any]
    ) -> Any:
        """Execute a tool and return results"""
        # Handle per-profile tools: extract profile from tool name
        # Pattern: get_mastodon_{profile}_{action}
        # Pattern: get_mastodon_{action} (default profile — no suffix)

        # Parse the tool name to extract profile and action
        profile = "default"
        action = None

        if tool_name.startswith("get_mastodon_all"):
            # Aggregate all profiles
            all_results = {}
            for p, conn in self.connectors.items():
                try:
                    sd = date.fromisoformat(args.get("start_date", date.today().isoformat()))
                    ed = date.fromisoformat(args.get("end_date", date.today().isoformat()))
                    metrics = conn.get_metrics(sd, ed)
                    all_results[p] = [
                        {
                            "source": m.source,
                            "account": m.account,
                            "date": str(m.date),
                            "metric_type": m.metric_type,
                            "value": m.value,
                            "dimensions": m.dimensions,
                        }
                        for m in metrics
                    ]
                except Exception as e:
                    all_results[p] = {"error": str(e)}
            return all_results

        # Parse: get_mastodon_STELLARWHISKERS_metrics or get_mastodon_metrics
        parts = tool_name.replace("get_mastodon_", "", 1).split("_", 1)
        if len(parts) == 1:
            # No profile suffix → default profile
            action = parts[0]
            profile = "default"
        else:
            # Has a profile suffix
            potential_profile = parts[0].upper()
            action = parts[1]
            if potential_profile in self.connectors:
                profile = potential_profile
            else:
                profile = "default"

        connector = self.connectors.get(profile)
        if not connector:
            raise ValueError(f"No connector for profile: {profile}")

        if tool_name.startswith("test_mastodon"):
            return connector.test_connection()

        elif tool_name.endswith("_metrics"):
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            metrics = connector.get_metrics(start_date, end_date)
            return [
                {
                    "source": m.source,
                    "account": m.account,
                    "date": str(m.date),
                    "metric_type": m.metric_type,
                    "value": m.value,
                    "dimensions": m.dimensions,
                }
                for m in metrics
            ]

        elif tool_name.endswith("_posts"):
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            limit = args.get("limit", 40)
            content = connector.get_content(start_date, end_date)

            # Sort by creation date and limit
            sorted_content = sorted(
                content,
                key=lambda c: c.created_at,
                reverse=True
            )[:limit]

            return [
                {
                    "source": c.source,
                    "account": c.account,
                    "content_id": c.content_id,
                    "content_type": c.content_type,
                    "url": c.url,
                    "title": c.title,
                    "created_at": str(c.created_at),
                    "author": c.author,
                    "metrics": [
                        {
                            "metric_type": m.metric_type,
                            "value": m.value,
                            "account": m.account,
                        }
                        for m in c.metrics
                    ],
                }
                for c in sorted_content
            ]

        elif tool_name.endswith("_followers"):
            sd = date.fromisoformat(args.get("start_date", date.today().isoformat()))
            ed = date.fromisoformat(args.get("end_date", date.today().isoformat()))
            audience = connector.get_audience(sd, ed)
            return [
                {
                    "source": a.source,
                    "account": a.account,
                    "date": str(a.date),
                    "segment": a.segment,
                    "count": a.count,
                }
                for a in audience
            ]

        else:
            raise ValueError(f"Unknown tool: {tool_name}")


def main():
    """Run the Mastodon MCP server."""
    server = MCPServer()
    server.run()


# Re-export run method for compatibility
MCPServer.run = lambda self: self._run()

def _run_impl(self):
    """Main server loop - read from stdin, write to stdout"""
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                self._log(f"Invalid JSON: {e}")
                self._send_response(
                    self._error_response(None, -32700, f"Parse error: {e}")
                )
                continue

            try:
                response = self._handle_message(message)
                if response:
                    self._send_response(response)
            except Exception as e:
                self._log(f"Error handling message: {e}")
                self._send_response(
                    self._error_response(
                        message.get("id"), -32603, f"Internal error: {e}"
                    )
                )

    except KeyboardInterrupt:
        self._log("Server shutting down")
    except Exception as e:
        self._log(f"Fatal error: {e}")
        sys.exit(1)

MCPServer._run = _run_impl

# Also keep the main entry point
setattr(MCPServer, "run", lambda self: self._run())
