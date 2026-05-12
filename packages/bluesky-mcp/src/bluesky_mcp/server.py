"""Bluesky MCP Server with multi-account support.

Usage:
    # Default profile (backward compatible)
    conn = BlueskyConnector()
    conn.authenticate()

    # Named profile — reads BLUESKY_IDENTIFIER__STELLARWHISKERS etc.
    conn = BlueskyConnector(profile="STELLARWHISKERS")
    conn.authenticate()
"""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from atproto import Client, client_utils
from atproto_client.exceptions import LoginRequiredError, BadRequestError
from attribution_schema.schema import Metric, Content, Audience
from attribution_cache.cache import Cache
from attribution_profiles import resolve_env, discover_profiles


class BlueskyConnector:
    """Bluesky connector using the AT Protocol.

    Supports multiple accounts via the `profile` parameter. Each profile
    reads its own env vars (e.g. ``BLUESKY_IDENTIFIER__STELLARWHISKERS``).
    """

    name = "bluesky"

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.account = profile.lower()  # canonical account identifier
        self.client = None
        self.identifier = resolve_env("BLUESKY_IDENTIFIER", profile)
        self.password = resolve_env("BLUESKY_PASSWORD", profile)
        self.did = None  # set during authenticate(); used to filter out reposts
        self.cache = Cache()

    def authenticate(self) -> bool:
        """Authenticate with Bluesky using app password."""
        if not self.identifier or not self.password:
            profile_suffix = f"__{self.profile.upper()}" if self.profile != "default" else ""
            raise ValueError(
                f"BLUESKY_IDENTIFIER{profile_suffix} and "
                f"BLUESKY_PASSWORD{profile_suffix} must be set"
            )

        try:
            self.client = Client()
            self.client.login(self.identifier, self.password)
            # Store DID for repost filtering — compare author DID rather than handle
            profile = self.client.app.bsky.actor.get_profile({
                "actor": self.identifier
            })
            self.did = profile.did
            return True
        except LoginRequiredError as e:
            raise ValueError(f"Bluesky authentication failed: {e}")
        except Exception as e:
            raise ValueError(f"Failed to connect to Bluesky: {e}")

    def _is_original_post(self, post_item) -> bool:
        """Check if a feed item is the user's own original post (not a repost)."""
        return post_item.post.author.did == self.did

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

                # Skip reposts — only count engagement on original posts
                if not self._is_original_post(post):
                    continue

                # Get engagement counts
                likes = post.post.like_count or 0
                reposts = post.post.repost_count or 0
                replies = post.post.reply_count or 0
                quote_posts = getattr(post.post, 'quote_count', 0) or 0

                # Create metrics for each engagement type
                base_dims = {"post_uri": str(uri), "account": self.account}

                metrics.append(Metric(
                    source=self.name,
                    date=post_date,
                    metric_type="likes",
                    value=likes,
                    account=self.account,
                    dimensions=base_dims
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=post_date,
                    metric_type="reposts",
                    value=reposts,
                    account=self.account,
                    dimensions=base_dims
                ))

                metrics.append(Metric(
                    source=self.name,
                    date=post_date,
                    metric_type="replies",
                    value=replies,
                    account=self.account,
                    dimensions=base_dims
                ))

                if quote_posts > 0:
                    metrics.append(Metric(
                        source=self.name,
                        date=post_date,
                        metric_type="quote_posts",
                        value=quote_posts,
                        account=self.account,
                        dimensions=base_dims
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

                # Skip reposts — only return original content
                if not self._is_original_post(post):
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
                    account=self.account,
                    author=self.identifier,
                    metrics=[
                        Metric(
                            source=self.name,
                            date=post_date.date(),
                            metric_type="likes",
                            value=likes,
                            account=self.account,
                            dimensions={"post_uri": str(uri), "account": self.account}
                        ),
                        Metric(
                            source=self.name,
                            date=post_date.date(),
                            metric_type="reposts",
                            value=reposts,
                            account=self.account,
                            dimensions={"post_uri": str(uri), "account": self.account}
                        ),
                        Metric(
                            source=self.name,
                            date=post_date.date(),
                            metric_type="replies",
                            value=replies,
                            account=self.account,
                            dimensions={"post_uri": str(uri), "account": self.account}
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
                account=self.account,
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
                "account": self.account,
                "identifier": self.identifier,
                "display_name": profile.display_name,
                "followers": profile.followers_count or 0,
                "follows": profile.follows_count or 0,
                "message": f"Successfully connected to Bluesky [profile: {self.profile}]"
            }

        except Exception as e:
            return {
                "status": "error",
                "account": self.account,
                "message": str(e)
            }


# MCP Server implementation
class MCPServer:
    """MCP Server for Bluesky with multi-account support."""

    def __init__(self):
        self.connectors: Dict[str, BlueskyConnector] = {}
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
        """Initialize connectors for all discovered profiles."""
        profiles = discover_profiles("BLUESKY_IDENTIFIER")
        if not profiles:
            return self._error_response(
                request.get("id"), -32000,
                "No Bluesky profiles configured. Set BLUESKY_IDENTIFIER in .env"
            )

        errors = []
        for profile in profiles:
            try:
                conn = BlueskyConnector(profile=profile)
                conn.authenticate()
                self.connectors[profile] = conn
                self._log(f"Initialized Bluesky profile: {profile}")
            except Exception as e:
                errors.append(f"{profile}: {e}")

        if not self.connectors:
            return self._error_response(
                request.get("id"), -32000,
                f"Failed to initialize any Bluesky profiles: {'; '.join(errors)}"
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
                    "name": f"get_bluesky{profile_tag}_metrics",
                    "description": f"Get Bluesky post engagement metrics (profile: {account_label})",
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
                    "name": f"get_bluesky{profile_tag}_posts",
                    "description": f"Get Bluesky posts with engagement data (profile: {account_label})",
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
                    "name": f"get_bluesky{profile_tag}_followers",
                    "description": f"Get follower count (profile: {account_label})",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                },
                {
                    "name": f"test_bluesky{profile_tag}_connection",
                    "description": f"Test the Bluesky connection (profile: {account_label})",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                },
            ])

        # Aggregate tool
        tools.append({
            "name": "get_bluesky_all",
            "description": "Get metrics from all configured Bluesky profiles",
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
        profile = "default"
        action = None

        # Handle aggregate tool
        if tool_name.startswith("get_bluesky_all"):
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

        # Parse: get_bluesky_STELLARWHISKERS_metrics or get_bluesky_metrics
        parts = tool_name.replace("get_bluesky_", "", 1).split("_", 1)
        if len(parts) == 1:
            action = parts[0]
            profile = "default"
        else:
            potential_profile = parts[0].upper()
            action = parts[1]
            if potential_profile in self.connectors:
                profile = potential_profile
            else:
                profile = "default"

        connector = self.connectors.get(profile)
        if not connector:
            raise ValueError(f"No connector for profile: {profile}")

        if tool_name.startswith("test_bluesky"):
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
            limit = args.get("limit", 100)
            content = connector.get_content(start_date, end_date)

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
    """Run the Bluesky MCP server."""
    server = MCPServer()
    server.run()


# Re-export run method
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
setattr(MCPServer, "run", lambda self: self._run())
