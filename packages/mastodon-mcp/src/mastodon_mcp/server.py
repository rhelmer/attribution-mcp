"""Mastodon MCP Server."""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from mastodon import Mastodon as MastodonClient
from mastodon.Mastodon import MastodonAPIError, MastodonUnauthorizedError
from attribution_schema.schema import Metric, Content, Audience
from attribution_cache.cache import Cache


class MastodonConnector:
    """Mastodon connector using the REST API."""

    name = "mastodon"

    def __init__(self):
        self.client = None
        self.instance = os.environ.get("MASTODON_INSTANCE", "mastodon.social")
        self.client_id = os.environ.get("MASTODON_CLIENT_ID")
        self.client_secret = os.environ.get("MASTODON_CLIENT_SECRET")
        self.access_token = os.environ.get("MASTODON_ACCESS_TOKEN")
        self.account_id = os.environ.get("MASTODON_ACCOUNT_ID")
        self.cache = Cache()

    def authenticate(self) -> bool:
        """Authenticate with Mastodon."""
        if not self.access_token:
            raise ValueError("MASTODON_ACCESS_TOKEN must be set")

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
        # Try cache first
        cached = self.cache.get_metrics(
            source=self.name,
            start_date=start_date,
            end_date=end_date,
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

                # Create metrics for each engagement type
                metrics.append(Metric(
                    source=self.name,
                    date=status_date,
                    metric_type="reblogs",
                    value=status.get("reblogs_count", 0),
                    dimensions={
                        "status_id": status_id,
                        "url": status.get("url", "")
                    }
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=status_date,
                    metric_type="favourites",
                    value=status.get("favourites_count", 0),
                    dimensions={
                        "status_id": status_id,
                        "url": status.get("url", "")
                    }
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=status_date,
                    metric_type="replies",
                    value=status.get("replies_count", 0),
                    dimensions={
                        "status_id": status_id,
                        "url": status.get("url", "")
                    }
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
                # Simple HTML stripping
                import re
                content_text = re.sub(r"<[^>]+>", "", content_text)

                content = Content(
                    source=self.name,
                    content_id=str(status["id"]),
                    content_type="post",
                    url=status.get("url", ""),
                    title=content_text[:100] + "..." if len(content_text) > 100 else content_text,
                    created_at=status_date,
                    author=status.get("account", {}).get("username", ""),
                    metrics=[
                        Metric(
                            source=self.name,
                            date=status_date.date(),
                            metric_type="reblogs",
                            value=status.get("reblogs_count", 0),
                            dimensions={"status_id": str(status["id"])}
                        ),
                        Metric(
                            source=self.name,
                            date=status_date.date(),
                            metric_type="favourites",
                            value=status.get("favourites_count", 0),
                            dimensions={"status_id": str(status["id"])}
                        ),
                        Metric(
                            source=self.name,
                            date=status_date.date(),
                            metric_type="replies",
                            value=status.get("replies_count", 0),
                            dimensions={"status_id": str(status["id"])}
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
                "instance": self.instance,
                "username": account.get("username"),
                "followers": account.get("followers_count", 0),
                "message": "Successfully connected to Mastodon"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


# MCP Server implementation
class MCPServer:
    """MCP Server for Mastodon"""

    def __init__(self):
        self.connector: Optional[MastodonConnector] = None
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
        """Handle initialize request"""
        try:
            self.connector = MastodonConnector()
            self.connector.authenticate()
        except Exception as e:
            return self._error_response(
                request.get("id"), -32000, f"Failed to initialize: {e}"
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
                    "version": "1.0.0",
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "get_mastodon_metrics",
                "description": "Get Mastodon post engagement metrics (reblogs, favourites, replies)",
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
                "name": "get_mastodon_posts",
                "description": "Get posts (statuses) from Mastodon with engagement data",
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
                "name": "get_mastodon_followers",
                "description": "Get current follower count",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "test_mastodon_connection",
                "description": "Test the Mastodon connection",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

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

        if tool_name == "test_mastodon_connection":
            return self.connector.test_connection()

        elif tool_name == "get_mastodon_metrics":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            metrics = self.connector.get_metrics(start_date, end_date)
            return [
                {
                    "source": m.source,
                    "date": str(m.date),
                    "metric_type": m.metric_type,
                    "value": m.value,
                    "dimensions": m.dimensions,
                }
                for m in metrics
            ]

        elif tool_name == "get_mastodon_posts":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            limit = args.get("limit", 40)
            content = self.connector.get_content(start_date, end_date)

            # Sort by creation date and limit
            sorted_content = sorted(
                content,
                key=lambda c: c.created_at,
                reverse=True
            )[:limit]

            return [
                {
                    "source": c.source,
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
                        }
                        for m in c.metrics
                    ],
                }
                for c in sorted_content
            ]

        elif tool_name == "get_mastodon_followers":
            start_date = date.fromisoformat(args.get("start_date", date.today().isoformat()))
            end_date = date.fromisoformat(args.get("end_date", date.today().isoformat()))
            audience = self.connector.get_audience(start_date, end_date)
            return [
                {
                    "source": a.source,
                    "date": str(a.date),
                    "segment": a.segment,
                    "count": a.count,
                }
                for a in audience
            ]

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming JSON-RPC message"""
        method = message.get("method")

        if method == "initialize":
            return self._initialize(message)
        elif method == "notifications/initialized":
            self._log("Client notified initialization complete")
            return None
        elif method == "tools/list":
            return self._list_tools(message)
        elif method == "tools/call":
            return self._call_tool(message)
        else:
            self._log(f"Unknown method: {method}")
            return self._error_response(
                message.get("id"), -32601, f"Method not found: {method}"
            )

    def run(self) -> None:
        """Main server loop - read from stdin, write to stdout"""
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    response = self._handle_message(message)
                    if response:
                        self._send_response(response)

                except json.JSONDecodeError as e:
                    error_response = self._error_response(
                        None, -32700, f"Parse error: {e}"
                    )
                    self._send_response(error_response)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            raise


def main():
    """Entry point"""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
