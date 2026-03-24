"""Bluesky MCP Server."""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from atproto import Client, client_utils
from atproto_client.exceptions import LoginRequiredError, BadRequestError
from attribution_schema.schema import Metric, Content, Audience
from attribution_cache.cache import Cache


class BlueskyConnector:
    """Bluesky connector using the AT Protocol."""

    name = "bluesky"

    def __init__(self):
        self.client = None
        self.identifier = os.environ.get("BLUESKY_IDENTIFIER")
        self.password = os.environ.get("BLUESKY_PASSWORD")
        self.cache = Cache()

    def authenticate(self) -> bool:
        """Authenticate with Bluesky using app password."""
        if not self.identifier or not self.password:
            raise ValueError("BLUESKY_IDENTIFIER and BLUESKY_PASSWORD must be set")

        try:
            self.client = Client()
            self.client.login(self.identifier, self.password)
            return True
        except LoginRequiredError as e:
            raise ValueError(f"Bluesky authentication failed: {e}")
        except Exception as e:
            raise ValueError(f"Failed to connect to Bluesky: {e}")

    def get_metrics(
        self,
        start_date: date,
        end_date: date,
        dimensions: Optional[List[str]] = None
    ) -> List[Metric]:
        """
        Fetch post engagement data from Bluesky.

        Metrics: likes, reposts, replies, quote_posts
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
            # Get user's feed
            feed = self.client.app.bsky.feed.get_author_feed({
                "actor": self.identifier,
                "limit": 100,
            })

            metrics = []
            for post in feed.feed:
                record = post.post.record
                uri = post.post.uri

                # Parse creation date
                created_at = record.created_at
                if isinstance(created_at, datetime):
                    post_date = created_at.date()
                else:
                    try:
                        post_date = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        ).date()
                    except:
                        post_date = date.today()

                # Filter by date range
                if post_date < start_date or post_date > end_date:
                    continue

                # Get engagement counts
                likes = post.post.like_count or 0
                reposts = post.post.repost_count or 0
                replies = post.post.reply_count or 0
                quote_posts = getattr(post.post, 'quote_count', 0) or 0

                # Create metrics for each engagement type
                metrics.append(Metric(
                    source=self.name,
                    date=post_date,
                    metric_type="likes",
                    value=likes,
                    dimensions={"post_uri": str(uri)}
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=post_date,
                    metric_type="reposts",
                    value=reposts,
                    dimensions={"post_uri": str(uri)}
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=post_date,
                    metric_type="replies",
                    value=replies,
                    dimensions={"post_uri": str(uri)}
                ))

                if quote_posts > 0:
                    metrics.append(Metric(
                        source=self.name,
                        date=post_date,
                        metric_type="quote_posts",
                        value=quote_posts,
                        dimensions={"post_uri": str(uri)}
                    ))

            # Cache the results
            self.cache.set_metrics(metrics)
            return metrics

        except BadRequestError as e:
            raise ValueError(f"Bluesky API error: {e}")

    def get_content(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Content]:
        """Get posts from Bluesky."""
        if not self.client:
            self.authenticate()

        try:
            feed = self.client.app.bsky.feed.get_author_feed({
                "actor": self.identifier,
                "limit": 100,
            })

            content_list = []
            for post in feed.feed:
                record = post.post.record
                uri = post.post.uri

                # Parse creation date
                created_at = record.created_at
                if isinstance(created_at, datetime):
                    post_date = created_at
                else:
                    try:
                        post_date = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    except:
                        post_date = datetime.now()

                # Filter by date range
                if post_date.date() < start_date or post_date.date() > end_date:
                    continue

                # Extract text content
                text = record.text or ""

                # Build URL from URI
                # URI format: at://did:plc:.../app.bsky.feed.post/...
                post_url = f"https://bsky.app/profile/{self.identifier}/post/{uri.split('/')[-1]}"

                # Get engagement counts
                likes = post.post.like_count or 0
                reposts = post.post.repost_count or 0
                replies = post.post.reply_count or 0

                content = Content(
                    source=self.name,
                    content_id=str(uri),
                    content_type="post",
                    url=post_url,
                    title=text[:100] + "..." if len(text) > 100 else text,
                    created_at=post_date,
                    author=self.identifier,
                    metrics=[
                        Metric(
                            source=self.name,
                            date=post_date.date(),
                            metric_type="likes",
                            value=likes,
                            dimensions={"post_uri": str(uri)}
                        ),
                        Metric(
                            source=self.name,
                            date=post_date.date(),
                            metric_type="reposts",
                            value=reposts,
                            dimensions={"post_uri": str(uri)}
                        ),
                        Metric(
                            source=self.name,
                            date=post_date.date(),
                            metric_type="replies",
                            value=replies,
                            dimensions={"post_uri": str(uri)}
                        ),
                    ]
                )
                content_list.append(content)

            return content_list

        except BadRequestError as e:
            raise ValueError(f"Bluesky API error: {e}")

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
            # Get profile
            profile = self.client.app.bsky.actor.get_profile({
                "actor": self.identifier
            })

            followers_count = profile.followers_count or 0

            return [Audience(
                source=self.name,
                date=date.today(),
                segment="followers",
                count=followers_count,
            )]

        except BadRequestError as e:
            raise ValueError(f"Bluesky API error: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Test Bluesky connection and return status."""
        try:
            if not self.client:
                self.authenticate()

            # Get profile
            profile = self.client.app.bsky.actor.get_profile({
                "actor": self.identifier
            })

            return {
                "status": "connected",
                "identifier": self.identifier,
                "display_name": profile.display_name,
                "followers": profile.followers_count or 0,
                "follows": profile.follows_count or 0,
                "message": "Successfully connected to Bluesky"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


# MCP Server implementation
class MCPServer:
    """MCP Server for Bluesky"""

    def __init__(self):
        self.connector: Optional[BlueskyConnector] = None
        self.initialized = False

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[bluesky-mcp] {message}\n")
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
            self.connector = BlueskyConnector()
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
                    "name": "bluesky-mcp",
                    "version": "1.0.0",
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "get_bluesky_metrics",
                "description": "Get Bluesky post engagement metrics (likes, reposts, replies)",
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
                "name": "get_bluesky_posts",
                "description": "Get posts from Bluesky with engagement data",
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
                            "description": "Maximum number of posts to return (default: 100)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "name": "get_bluesky_followers",
                "description": "Get current follower count",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "test_bluesky_connection",
                "description": "Test the Bluesky connection",
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

        if tool_name == "test_bluesky_connection":
            return self.connector.test_connection()

        elif tool_name == "get_bluesky_metrics":
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

        elif tool_name == "get_bluesky_posts":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            limit = args.get("limit", 100)
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

        elif tool_name == "get_bluesky_followers":
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
