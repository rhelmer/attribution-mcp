"""YouTube MCP Server."""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from attribution_schema.schema import Metric, Content, Audience
from attribution_cache.cache import Cache


class YouTubeConnector:
    """YouTube connector using Data API v3 and YouTube Analytics API."""

    name = "youtube"

    def __init__(self):
        self.youtube = None
        self.youtube_analytics = None
        self.channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")
        self.api_key = os.environ.get("YOUTUBE_API_KEY")
        self.cache = Cache()

    def authenticate(self) -> bool:
        """Authenticate with YouTube using API key."""
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY must be set")

        try:
            # YouTube Data API
            self.youtube = build("youtube", "v3", developerKey=self.api_key)

            # YouTube Analytics API (requires OAuth for full access, but API key works for some endpoints)
            self.youtube_analytics = build("youtubeAnalytics", "v2", developerKey=self.api_key)
            return True
        except Exception as e:
            raise ValueError(f"Failed to authenticate with YouTube: {e}")

    def get_metrics(
        self,
        start_date: date,
        end_date: date,
        dimensions: Optional[List[str]] = None
    ) -> List[Metric]:
        """
        Fetch video analytics from YouTube.

        Dimensions: ["video", "trafficSource", "subscribedStatus", "day"]
        Metrics: views, watchTime, impressions, impressionCTR
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

        if not self.youtube_analytics:
            self.authenticate()

        if not self.channel_id:
            raise ValueError("YOUTUBE_CHANNEL_ID must be set")

        try:
            # Use YouTube Analytics API
            response = self.youtube_analytics.reports().query(
                ids=f"channel=={self.channel_id}",
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics="views,watchTimeMinutes,impressions,impressionClickThroughRate",
                dimensions="day",
            ).execute()

            metrics = []
            rows = response.get("rows", [])
            column_headers = [h["name"] for h in response.get("columnHeaders", [])]

            for row in rows:
                row_dict = dict(zip(column_headers, row))

                # Parse date
                date_str = row_dict.get("day", "")
                try:
                    metric_date = date.fromisoformat(date_str)
                except:
                    metric_date = start_date

                # Create metrics
                if "views" in row_dict:
                    metrics.append(Metric(
                        source=self.name,
                        date=metric_date,
                        metric_type="views",
                        value=row_dict["views"],
                        dimensions={}
                    ))

                if "watchTimeMinutes" in row_dict:
                    metrics.append(Metric(
                        source=self.name,
                        date=metric_date,
                        metric_type="watchTimeMinutes",
                        value=row_dict["watchTimeMinutes"],
                        dimensions={}
                    ))

                if "impressions" in row_dict:
                    metrics.append(Metric(
                        source=self.name,
                        date=metric_date,
                        metric_type="impressions",
                        value=row_dict["impressions"],
                        dimensions={}
                    ))

                if "impressionClickThroughRate" in row_dict:
                    metrics.append(Metric(
                        source=self.name,
                        date=metric_date,
                        metric_type="impressionCtr",
                        value=row_dict["impressionClickThroughRate"],
                        dimensions={}
                    ))

            # Cache the results
            self.cache.set_metrics(metrics)
            return metrics

        except HttpError as e:
            # If analytics API fails (common with API key), fall back to video statistics
            self._log(f"Analytics API error, falling back to video stats: {e}")
            return self._get_video_stats(start_date, end_date)

    def _get_video_stats(
        self,
        start_date: date,
        end_date: date
    ) -> List[Metric]:
        """Fallback: Get video statistics from Data API."""
        if not self.youtube:
            self.authenticate()

        metrics = []

        try:
            # Get channel's videos
            request = self.youtube.search().list(
                part="id",
                channelId=self.channel_id,
                maxResults=50,
                order="date",
                type="video"
            )

            while request:
                response = request.execute()

                video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

                if video_ids:
                    # Get statistics for these videos
                    stats_response = self.youtube.videos().list(
                        part="statistics",
                        id=",".join(video_ids)
                    ).execute()

                    for video in stats_response.get("items", []):
                        video_id = video["id"]
                        stats = video.get("statistics", {})

                        # Add metrics (note: these are lifetime stats, not date-range specific)
                        if "viewCount" in stats:
                            metrics.append(Metric(
                                source=self.name,
                                date=start_date,
                                metric_type="views",
                                value=int(stats["viewCount"]),
                                dimensions={"video_id": video_id}
                            ))

                        if "likeCount" in stats:
                            metrics.append(Metric(
                                source=self.name,
                                date=start_date,
                                metric_type="likes",
                                value=int(stats["likeCount"]),
                                dimensions={"video_id": video_id}
                            ))

                        if "commentCount" in stats:
                            metrics.append(Metric(
                                source=self.name,
                                date=start_date,
                                metric_type="comments",
                                value=int(stats["commentCount"]),
                                dimensions={"video_id": video_id}
                            ))

                # Next page
                request = self.youtube.search().list_next(request, response)
                if not request:
                    break

        except HttpError as e:
            raise ValueError(f"YouTube API error: {e}")

        return metrics

    def get_content(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Content]:
        """Fetch video details from YouTube."""
        if not self.youtube:
            self.authenticate()

        content_list = []

        try:
            # Get channel's videos
            request = self.youtube.search().list(
                part="id,snippet",
                channelId=self.channel_id,
                maxResults=50,
                order="date",
                type="video"
            )

            while request:
                response = request.execute()

                video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

                if video_ids:
                    # Get detailed info including statistics
                    stats_response = self.youtube.videos().list(
                        part="snippet,statistics,contentDetails",
                        id=",".join(video_ids)
                    ).execute()

                    for video in stats_response.get("items", []):
                        snippet = video.get("snippet", {})
                        stats = video.get("statistics", {})
                        content_details = video.get("contentDetails", {})

                        published_at = snippet.get("publishedAt", "")
                        try:
                            created_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        except:
                            created_at = datetime.now()

                        content = Content(
                            source=self.name,
                            content_id=video["id"],
                            content_type="video",
                            url=f"https://www.youtube.com/watch?v={video['id']}",
                            title=snippet.get("title", ""),
                            created_at=created_at,
                            author=snippet.get("channelTitle"),
                            thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url"),
                            metrics=[
                                Metric(
                                    source=self.name,
                                    date=created_at.date(),
                                    metric_type="views",
                                    value=int(stats.get("viewCount", 0)),
                                    dimensions={"video_id": video["id"]}
                                ),
                                Metric(
                                    source=self.name,
                                    date=created_at.date(),
                                    metric_type="likes",
                                    value=int(stats.get("likeCount", 0)),
                                    dimensions={"video_id": video["id"]}
                                ),
                                Metric(
                                    source=self.name,
                                    date=created_at.date(),
                                    metric_type="comments",
                                    value=int(stats.get("commentCount", 0)),
                                    dimensions={"video_id": video["id"]}
                                ),
                            ]
                        )
                        content_list.append(content)

                # Next page
                request = self.youtube.search().list_next(request, response)
                if not request:
                    break

        except HttpError as e:
            raise ValueError(f"YouTube API error: {e}")

        return content_list

    def get_audience(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Audience]:
        """Get subscriber count."""
        if not self.youtube:
            self.authenticate()

        try:
            # Get channel details
            response = self.youtube.channels().list(
                part="statistics",
                id=self.channel_id
            ).execute()

            if not response.get("items"):
                return []

            channel = response["items"][0]
            stats = channel.get("statistics", {})
            subscriber_count = int(stats.get("subscriberCount", 0))

            return [Audience(
                source=self.name,
                date=date.today(),
                segment="subscribers",
                count=subscriber_count,
            )]

        except HttpError as e:
            raise ValueError(f"YouTube API error: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Test YouTube connection and return status."""
        try:
            if not self.youtube:
                self.authenticate()

            # Try to get channel info
            response = self.youtube.channels().list(
                part="snippet",
                id=self.channel_id
            ).execute()

            if not response.get("items"):
                return {
                    "status": "error",
                    "message": "Channel not found"
                }

            channel = response["items"][0]
            return {
                "status": "connected",
                "channel_id": self.channel_id,
                "channel_title": channel["snippet"]["title"],
                "message": "Successfully connected to YouTube"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def _log(self, message: str) -> None:
        """Log debug message."""
        sys.stderr.write(f"[youtube-connector] {message}\n")


# MCP Server implementation
class MCPServer:
    """MCP Server for YouTube Analytics"""

    def __init__(self):
        self.connector: Optional[YouTubeConnector] = None
        self.initialized = False

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[youtube-mcp] {message}\n")
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
            self.connector = YouTubeConnector()
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
                    "name": "youtube-mcp",
                    "version": "1.0.0",
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "get_youtube_metrics",
                "description": "Get YouTube video metrics (views, watch time, impressions, CTR)",
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
                "name": "get_youtube_videos",
                "description": "Get videos with their statistics from YouTube",
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
                            "description": "Maximum number of videos to return (default: 50)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "name": "get_youtube_subscribers",
                "description": "Get current subscriber count",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "test_youtube_connection",
                "description": "Test the YouTube connection",
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

        if tool_name == "test_youtube_connection":
            return self.connector.test_connection()

        elif tool_name == "get_youtube_metrics":
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

        elif tool_name == "get_youtube_videos":
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
                    "author": c.author,
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

        elif tool_name == "get_youtube_subscribers":
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
