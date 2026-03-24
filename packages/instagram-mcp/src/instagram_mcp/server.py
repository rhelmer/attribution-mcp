"""Instagram/Threads MCP Server."""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import requests
from attribution_schema.schema import Metric, Content, Audience
from attribution_cache.cache import Cache


class InstagramConnector:
    """Instagram/Threads connector using the Graph API."""

    name = "instagram"

    def __init__(self):
        self.access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self.business_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.cache = Cache()

        self._base_url = "https://graph.facebook.com/v18.0"

    def authenticate(self) -> bool:
        """Authenticate with Instagram using access token."""
        if not self.access_token or not self.business_account_id:
            raise ValueError(
                "INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID must be set"
            )

        try:
            # Test connection by getting account info
            response = requests.get(
                f"{self._base_url}/{self.business_account_id}",
                params={
                    "fields": "id,username",
                    "access_token": self.access_token
                }
            )
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Instagram authentication failed: {e}")
        except Exception as e:
            raise ValueError(f"Failed to connect to Instagram: {e}")

    def get_metrics(
        self,
        start_date: date,
        end_date: date,
        dimensions: Optional[List[str]] = None
    ) -> List[Metric]:
        """
        Fetch Instagram insights data.

        Metrics: impressions, reach, engagement, profile_views, follower_count
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

        if not self.access_token:
            self.authenticate()

        try:
            metrics = []

            # Get insights for the date range
            # Note: Instagram Insights returns aggregated data, not per-day breakdowns
            # for all metrics without pagination

            insight_metrics = [
                "impressions",
                "reach",
                "engagement",
                "profile_views",
                "follower_count"
            ]

            for metric_name in insight_metrics:
                try:
                    response = requests.get(
                        f"{self._base_url}/{self.business_account_id}/insights",
                        params={
                            "metric": metric_name,
                            "period": "day",
                            "since": int(start_date.timestamp()),
                            "until": int(end_date.timestamp()),
                            "access_token": self.access_token
                        }
                    )

                    if response.status_code != 200:
                        continue

                    data = response.json()
                    insight_data = data.get("data", [])

                    if not insight_data:
                        continue

                    # Instagram returns data points with values
                    for insight in insight_data:
                        values = insight.get("values", [])
                        for value_point in values:
                            value = value_point.get("value", 0)
                            end_time = value_point.get("end_time", "")

                            if end_time:
                                try:
                                    metric_date = datetime.fromisoformat(
                                        end_time.replace("Z", "+00:00")
                                    ).date()
                                except:
                                    metric_date = start_date
                            else:
                                metric_date = start_date

                            metrics.append(Metric(
                                source=self.name,
                                date=metric_date,
                                metric_type=metric_name,
                                value=value if isinstance(value, (int, float)) else 0,
                                dimensions={
                                    "account_id": self.business_account_id
                                }
                            ))

                except Exception:
                    # Continue even if individual metric requests fail
                    continue

            # Cache the results
            self.cache.set_metrics(metrics)
            return metrics

        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Instagram API error: {e}")

    def get_content(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Content]:
        """Get Instagram media posts with insights."""
        if not self.access_token:
            self.authenticate()

        try:
            content_list = []

            # Get media posts
            response = requests.get(
                f"{self._base_url}/{self.business_account_id}/media",
                params={
                    "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
                    "limit": 50,
                    "access_token": self.access_token
                }
            )

            if response.status_code != 200:
                return content_list

            data = response.json()
            media_items = data.get("data", [])

            for media in media_items:
                # Parse timestamp
                timestamp = media.get("timestamp", "")
                if timestamp:
                    try:
                        created_at = datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        )
                    except:
                        created_at = datetime.now()
                else:
                    created_at = datetime.now()

                # Filter by date range
                if created_at.date() < start_date or created_at.date() > end_date:
                    continue

                # Get insights for this media
                media_id = media.get("id", "")
                media_insights = self._get_media_insights(media_id)

                content = Content(
                    source=self.name,
                    content_id=media_id,
                    content_type="post",
                    url=media.get("permalink", ""),
                    title=media.get("caption", "")[:100] + "..." if media.get("caption") and len(media.get("caption", "")) > 100 else (media.get("caption") or "Instagram Post"),
                    created_at=created_at,
                    thumbnail_url=media.get("media_url") if media.get("media_type") == "IMAGE" else None,
                    metrics=[
                        Metric(
                            source=self.name,
                            date=created_at.date(),
                            metric_type="likes",
                            value=media.get("like_count", 0),
                            dimensions={"media_id": media_id}
                        ),
                        Metric(
                            source=self.name,
                            date=created_at.date(),
                            metric_type="comments",
                            value=media.get("comments_count", 0),
                            dimensions={"media_id": media_id}
                        ),
                    ] + media_insights
                )
                content_list.append(content)

            return content_list

        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Instagram API error: {e}")

    def _get_media_insights(self, media_id: str) -> List[Metric]:
        """Get insights for a specific media post."""
        insights = []

        try:
            response = requests.get(
                f"{self._base_url}/{media_id}/insights",
                params={
                    "metric": "impressions,reach,engagement,saved",
                    "access_token": self.access_token
                }
            )

            if response.status_code != 200:
                return insights

            data = response.json()
            insight_data = data.get("data", [])

            for insight in insight_data:
                metric_name = insight.get("name", "")
                values = insight.get("values", [])

                if values:
                    value = values[0].get("value", 0)
                    insights.append(Metric(
                        source=self.name,
                        date=date.today(),
                        metric_type=metric_name,
                        value=value if isinstance(value, (int, float)) else 0,
                        dimensions={"media_id": media_id}
                    ))

        except Exception:
            pass

        return insights

    def get_audience(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Audience]:
        """Get follower count."""
        if not self.access_token:
            self.authenticate()

        try:
            # Get follower count
            response = requests.get(
                f"{self._base_url}/{self.business_account_id}/insights",
                params={
                    "metric": "follower_count",
                    "access_token": self.access_token
                }
            )

            followers_count = 0
            if response.status_code == 200:
                data = response.json()
                insight_data = data.get("data", [])
                if insight_data:
                    values = insight_data[0].get("values", [])
                    if values:
                        followers_count = values[-1].get("value", 0)

            return [Audience(
                source=self.name,
                date=date.today(),
                segment="followers",
                count=int(followers_count),
            )]

        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Instagram API error: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Test Instagram connection and return status."""
        try:
            if not self.access_token:
                self.authenticate()

            # Get account info
            response = requests.get(
                f"{self._base_url}/{self.business_account_id}",
                params={
                    "fields": "id,username,name",
                    "access_token": self.access_token
                }
            )
            response.raise_for_status()

            account_data = response.json()

            return {
                "status": "connected",
                "account_id": self.business_account_id,
                "username": account_data.get("username", ""),
                "name": account_data.get("name", ""),
                "message": "Successfully connected to Instagram"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


# MCP Server implementation
class MCPServer:
    """MCP Server for Instagram/Threads"""

    def __init__(self):
        self.connector: Optional[InstagramConnector] = None
        self.initialized = False

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[instagram-mcp] {message}\n")
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
            self.connector = InstagramConnector()
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
                    "name": "instagram-mcp",
                    "version": "1.0.0",
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "get_instagram_metrics",
                "description": "Get Instagram insights (impressions, reach, engagement, profile views)",
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
                "name": "get_instagram_posts",
                "description": "Get Instagram posts with engagement data",
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
                            "description": "Maximum number of posts to return (default: 50)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "name": "get_instagram_followers",
                "description": "Get current follower count",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "test_instagram_connection",
                "description": "Test the Instagram connection",
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

        if tool_name == "test_instagram_connection":
            return self.connector.test_connection()

        elif tool_name == "get_instagram_metrics":
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

        elif tool_name == "get_instagram_posts":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            limit = args.get("limit", 50)
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
                    "thumbnail_url": c.thumbnail_url,
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

        elif tool_name == "get_instagram_followers":
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
