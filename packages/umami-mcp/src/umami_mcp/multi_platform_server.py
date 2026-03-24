"""
Unified Multi-Platform Analytics MCP Server

Aggregates data from multiple analytics platforms:
- Umami (web analytics)
- Google Search Console (search performance)
- YouTube (video analytics)
- Mastodon (social engagement)
- Bluesky (social engagement)
- LinkedIn (professional social)
- Instagram/Threads (social engagement)
"""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type
from importlib import import_module


class MultiPlatformServer:
    """MCP Server that aggregates multiple analytics platforms."""

    def __init__(self):
        self.connectors: Dict[str, Any] = {}
        self.initialized = False
        self._load_connectors()

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[multi-platform-mcp] {message}\n")
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

    def _load_connectors(self) -> None:
        """Dynamically load available connectors."""

        # Map of platform names to their module paths
        platform_modules = {
            "umami": "umami_mcp.server",
            "gsc": "gsc_mcp.server",
            "youtube": "youtube_mcp.server",
            "mastodon": "mastodon_mcp.server",
            "bluesky": "bluesky_mcp.server",
            "linkedin": "linkedin_mcp.server",
            "instagram": "instagram_mcp.server",
        }

        for platform, module_path in platform_modules.items():
            try:
                # Check if environment variables are set for this platform
                if not self._platform_configured(platform):
                    self._log(f"Skipping {platform}: credentials not configured")
                    continue

                # Import the module
                module = import_module(module_path)

                # Get the connector class (naming convention: {Platform}Connector)
                connector_class_name = f"{platform.capitalize()}Connector"
                if platform == "gsc":
                    connector_class_name = "GSCConnector"
                elif platform == "umami":
                    connector_class_name = "UmamiClient"

                connector_class = getattr(module, connector_class_name, None)
                if connector_class:
                    self.connectors[platform] = connector_class()
                    self._log(f"Loaded connector: {platform}")

            except ImportError as e:
                self._log(f"Could not load {platform} connector: {e}")
            except Exception as e:
                self._log(f"Error loading {platform} connector: {e}")

    def _platform_configured(self, platform: str) -> bool:
        """Check if a platform has required environment variables set."""

        env_requirements = {
            "umami": ["UMAMI_API_KEY"],
            "gsc": ["GSC_SERVICE_ACCOUNT_FILE", "GSC_SITE_URL"],
            "youtube": ["YOUTUBE_API_KEY", "YOUTUBE_CHANNEL_ID"],
            "mastodon": ["MASTODON_ACCESS_TOKEN", "MASTODON_ACCOUNT_ID"],
            "bluesky": ["BLUESKY_IDENTIFIER", "BLUESKY_PASSWORD"],
            "linkedin": ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_ORGANIZATION_ID"],
            "instagram": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID"],
        }

        required = env_requirements.get(platform, [])
        return all(os.environ.get(var) for var in required)

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        # Initialize each connector
        for platform, connector in self.connectors.items():
            try:
                if hasattr(connector, "authenticate"):
                    connector.authenticate()
                self._log(f"Initialized connector: {platform}")
            except Exception as e:
                self._log(f"Failed to initialize {platform}: {e}")

        self.initialized = True

        return self._success_response(
            request.get("id"),
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "multi-platform-analytics-mcp",
                    "version": "1.0.0",
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "get_all_metrics",
                "description": "Get metrics from all configured platforms for a date range",
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
                        "platforms": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(self.connectors.keys())
                            },
                            "description": "Specific platforms to query (default: all)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "name": "get_cross_platform_summary",
                "description": "Get unified summary metrics across all platforms",
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
                "name": "get_platform_status",
                "description": "Get connection status for all platforms",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            # Add platform-specific tools
            *self._get_platform_tools()
        ]

        return self._success_response(request.get("id"), {"tools": tools})

    def _get_platform_tools(self) -> List[Dict[str, Any]]:
        """Get tools for each configured platform."""
        platform_tools = []

        platform_descriptions = {
            "umami": {
                "metrics": "Get Umami web analytics (pageviews, visitors, bounces)",
                "websites": "List all websites tracked by Umami",
            },
            "gsc": {
                "metrics": "Get Google Search Console metrics (impressions, clicks, CTR, position)",
                "queries": "Get top search queries from GSC",
                "pages": "Get pages with search performance",
            },
            "youtube": {
                "metrics": "Get YouTube video metrics (views, watch time, impressions)",
                "videos": "Get videos with statistics",
                "subscribers": "Get subscriber count",
            },
            "mastodon": {
                "metrics": "Get Mastodon post engagement (reblogs, favourites, replies)",
                "posts": "Get posts with engagement data",
                "followers": "Get follower count",
            },
            "bluesky": {
                "metrics": "Get Bluesky post engagement (likes, reposts, replies)",
                "posts": "Get posts with engagement data",
                "followers": "Get follower count",
            },
            "linkedin": {
                "metrics": "Get LinkedIn organization metrics (impressions, clicks, engagements)",
                "posts": "Get organization posts",
                "followers": "Get follower count",
            },
            "instagram": {
                "metrics": "Get Instagram insights (impressions, reach, engagement)",
                "posts": "Get posts with engagement data",
                "followers": "Get follower count",
            },
        }

        for platform in self.connectors.keys():
            desc = platform_descriptions.get(platform, {})

            # Metrics tool
            platform_tools.append({
                "name": f"get_{platform}_metrics",
                "description": desc.get("metrics", f"Get metrics from {platform}"),
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

        return platform_tools

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

        # Multi-platform tools
        if tool_name == "get_platform_status":
            return self._get_platform_status()

        elif tool_name == "get_all_metrics":
            return self._get_all_metrics(args)

        elif tool_name == "get_cross_platform_summary":
            return self._get_cross_platform_summary(args)

        # Platform-specific tools - delegate to connectors
        elif tool_name.startswith("get_") and tool_name.endswith("_metrics"):
            platform = tool_name.replace("get_", "").replace("_metrics", "")
            if platform in self.connectors:
                return self._get_platform_metrics(platform, args)
            else:
                raise ValueError(f"Unknown platform: {platform}")

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _get_platform_status(self) -> Dict[str, Any]:
        """Get connection status for all platforms."""
        status = {}

        for platform, connector in self.connectors.items():
            try:
                if hasattr(connector, "test_connection"):
                    result = connector.test_connection()
                    status[platform] = result.get("status", "unknown")
                else:
                    status[platform] = "configured"
            except Exception as e:
                status[platform] = f"error: {str(e)}"

        return {
            "platforms": status,
            "total_configured": len(self.connectors),
            "message": f"{len(self.connectors)} platforms configured"
        }

    def _get_all_metrics(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get metrics from all configured platforms."""
        start_date = date.fromisoformat(args["start_date"])
        end_date = date.fromisoformat(args["end_date"])
        platforms = args.get("platforms", list(self.connectors.keys()))

        all_metrics = []

        for platform in platforms:
            if platform not in self.connectors:
                continue

            try:
                connector = self.connectors[platform]
                if hasattr(connector, "get_metrics"):
                    metrics = connector.get_metrics(start_date, end_date)
                    all_metrics.extend([
                        {
                            "source": m.source,
                            "date": str(m.date),
                            "metric_type": m.metric_type,
                            "value": m.value,
                            "dimensions": m.dimensions,
                        }
                        for m in metrics
                    ])
            except Exception as e:
                self._log(f"Error getting metrics from {platform}: {e}")

        return all_metrics

    def _get_cross_platform_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get unified summary across all platforms."""
        start_date = date.fromisoformat(args["start_date"])
        end_date = date.fromisoformat(args["end_date"])

        summary = {
            "date_range": {
                "start": str(start_date),
                "end": str(end_date),
            },
            "platforms": {},
            "totals": {},
        }

        for platform, connector in self.connectors.items():
            try:
                if hasattr(connector, "get_metrics"):
                    metrics = connector.get_metrics(start_date, end_date)

                    # Aggregate by metric type
                    platform_totals: Dict[str, float] = {}
                    for m in metrics:
                        metric_type = m.metric_type
                        if metric_type not in platform_totals:
                            platform_totals[metric_type] = 0
                        platform_totals[metric_type] += m.value

                    summary["platforms"][platform] = platform_totals

                    # Add to global totals
                    for metric_type, value in platform_totals.items():
                        if metric_type not in summary["totals"]:
                            summary["totals"][metric_type] = 0
                        summary["totals"][metric_type] += value

            except Exception as e:
                self._log(f"Error summarizing {platform}: {e}")
                summary["platforms"][platform] = {"error": str(e)}

        return summary

    def _get_platform_metrics(
        self,
        platform: str,
        args: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get metrics from a specific platform."""
        start_date = date.fromisoformat(args["start_date"])
        end_date = date.fromisoformat(args["end_date"])

        if platform not in self.connectors:
            raise ValueError(f"Unknown platform: {platform}")

        connector = self.connectors[platform]

        if not hasattr(connector, "get_metrics"):
            raise ValueError(f"Platform {platform} does not support metrics")

        metrics = connector.get_metrics(start_date, end_date)

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
    server = MultiPlatformServer()
    server.run()


if __name__ == "__main__":
    main()
