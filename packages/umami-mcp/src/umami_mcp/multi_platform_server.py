"""
Unified Multi-Platform Analytics MCP Server with multi-account support.

Aggregates data from multiple analytics platforms, each with multiple
named profiles (accounts):

    - Umami (web analytics)
    - Google Search Console (search performance)
    - YouTube (video analytics)
    - Mastodon (social engagement)
    - Bluesky (social engagement)
    - LinkedIn (professional social)
    - Instagram/Threads (social engagement)

Each connector can be instantiated per-profile. Profile names are discovered
automatically from env vars using the ``__PROFILE`` suffix convention.
"""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type
from importlib import import_module

from attribution_profiles import all_platform_profiles, resolve_env


class MultiPlatformServer:
    """MCP Server that aggregates multiple analytics platforms with multi-account."""

    def __init__(self):
        # Key: "{platform}:{profile}"  —  e.g. "mastodon:default", "mastodon:STELLARWHISKERS"
        self.connectors: Dict[str, Any] = {}
        self.platform_profiles: Dict[str, list[str]] = {}
        self.initialized = False
        self._load_connectors()

    def _log(self, message: str) -> None:
        sys.stderr.write(f"[multi-platform-mcp] {message}\n")
        sys.stderr.flush()

    def _send_response(self, response: Dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def _success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _load_connectors(self) -> None:
        """Dynamically load connectors for each discovered (platform, profile) pair."""
        # Map of platform names to their module paths and connector class names
        platform_modules = {
            "umami": {
                "module": "umami_mcp.server",
                "connector": "UmamiClient",
                "needs_profile_init": True,
            },
            "gsc": {
                "module": "gsc_mcp.server",
                "connector": "GSCConnector",
                "needs_profile_init": False,
            },
            "youtube": {
                "module": "youtube_mcp.server",
                "connector": "YouTubeConnector",
                "needs_profile_init": False,
            },
            "mastodon": {
                "module": "mastodon_mcp.server",
                "connector": "MastodonConnector",
                "needs_profile_init": True,
            },
            "bluesky": {
                "module": "bluesky_mcp.server",
                "connector": "BlueskyConnector",
                "needs_profile_init": True,
            },
            "linkedin": {
                "module": "linkedin_mcp.server",
                "connector": "LinkedInConnector",
                "needs_profile_init": False,
            },
            "instagram": {
                "module": "instagram_mcp.server",
                "connector": "InstagramConnector",
                "needs_profile_init": False,
            },
        }

        # Discover all profiles for all platforms
        all_configs = all_platform_profiles()
        self._log(f"Discovered platform profiles: {all_configs}")

        for platform, info in platform_modules.items():
            platform_configs = all_configs.get(platform, [])

            if not platform_configs:
                self._log(f"Skipping {platform}: no profiles configured")
                continue

            try:
                module = import_module(info["module"])
                connector_class = getattr(module, info["connector"], None)
                if not connector_class:
                    self._log(f"Could not find {info['connector']} in {info['module']}")
                    continue

                for config in platform_configs:
                    profile = config["profile"]
                    key = f"{platform}:{profile}"

                    try:
                        if info["needs_profile_init"]:
                            # Connector accepts a `profile` kwarg
                            conn = connector_class(profile=profile)
                        elif platform == "umami":
                            # UmamiClient takes explicit args
                            conn = connector_class(
                                base_url=config.get("url", ""),
                                api_key=config.get("api_key"),
                                username=config.get("username"),
                                password=config.get("password"),
                                team_id=config.get("team_id"),
                            )
                        else:
                            # Falls back to env-var-based init (single-account)
                            if profile != "default":
                                # Connector doesn't support profiles yet — skip non-default
                                self._log(
                                    f"  {platform}:{profile} — connector doesn't support "
                                    f"multi-account, skipped"
                                )
                                continue
                            conn = connector_class()

                        self.connectors[key] = conn
                        self._log(f"  Loaded connector: {key}")

                    except Exception as e:
                        self._log(f"  Error loading {key}: {e}")

            except ImportError as e:
                self._log(f"Could not load {platform} module: {e}")
            except Exception as e:
                self._log(f"Error loading {platform}: {e}")

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize each connector."""
        for key, connector in self.connectors.items():
            try:
                if hasattr(connector, "authenticate"):
                    connector.authenticate()
                self._log(f"Initialized: {key}")
            except Exception as e:
                self._log(f"Failed to initialize {key}: {e}")

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
                    "version": "2.0.0",
                    "connectors": list(self.connectors.keys()),
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = [
            {
                "name": "get_all_metrics",
                "description": "Get metrics from all configured platforms and profiles",
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
                "description": "Get connection status for all configured connector profiles",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_cross_platform_summary",
                "description": "Get unified summary metrics across all platforms and profiles",
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
            # Per-profile platform tools
            *self._get_platform_tools()
        ]

        return self._success_response(request.get("id"), {"tools": tools})

    def _get_platform_tools(self) -> List[Dict[str, Any]]:
        """Generate per-profile tools for each configured platform."""
        platform_tools = []

        platform_descriptions = {
            "umami": {
                "metrics": "Get Umami web analytics (pageviews, visitors, bounces)",
                "websites": "List all websites tracked by Umami",
            },
            "gsc": {
                "metrics": "Get Google Search Console metrics (impressions, clicks, CTR)",
                "queries": "Get top search queries from GSC",
            },
            "youtube": {
                "metrics": "Get YouTube video metrics (views, watch time)",
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

        # Group connectors by platform
        by_platform: Dict[str, list[str]] = {}
        for key in self.connectors.keys():
            platform, profile = key.split(":", 1)
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(profile)

        for platform, profiles in by_platform.items():
            desc = platform_descriptions.get(platform, {})

            for profile in profiles:
                account_label = profile if profile != "default" else "personal"
                profile_tag = f"_{profile}" if profile != "default" else ""

                platform_tools.append({
                    "name": f"get_{platform}{profile_tag}_metrics",
                    "description": (
                        f"{desc.get('metrics', f'Get metrics from {platform}')} "
                        f"[profile: {account_label}]"
                    ),
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

                # Add profile-specific content/get tools if they exist
                if desc.get("posts"):
                    platform_tools.append({
                        "name": f"get_{platform}{profile_tag}_posts",
                        "description": (
                            f"{desc.get('posts', f'Get {platform} content')} "
                            f"[profile: {account_label}]"
                        ),
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

                if desc.get("followers"):
                    platform_tools.append({
                        "name": f"get_{platform}{profile_tag}_followers",
                        "description": (
                            f"{desc.get('followers', f'Get {platform} followers')} "
                            f"[profile: {account_label}]"
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                        },
                    })

        return platform_tools

    def _call_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
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
        """Execute a tool and return results."""

        # Global tools
        if tool_name == "get_platform_status":
            return self._get_platform_status()

        elif tool_name == "get_all_metrics":
            return self._get_all_metrics(args)

        elif tool_name == "get_cross_platform_summary":
            return self._get_cross_platform_summary(args)

        # Per-profile per-platform tools
        # Parse pattern: get_{platform}_{PROFILE}_{action} or get_{platform}_{action}
        # Remove 'get_' prefix
        rest = tool_name[len("get_"):]  # e.g. "mastodon_STELLARWHISKERS_metrics"

        # Split into platform_and_profile and action
        # Find the last 'metrics'/'posts'/'followers' to determine action
        action_suffixes = ["_metrics", "_posts", "_followers"]
        action = None
        for suffix in action_suffixes:
            if rest.endswith(suffix):
                action = suffix[1:]  # remove leading underscore
                rest = rest[:-len(suffix)]
                break

        if not action:
            raise ValueError(f"Unknown tool: {tool_name}")

        # rest is now like "mastodon_STELLARWHISKERS" or just "mastodon"
        parts = rest.split("_", 1)
        platform = parts[0]
        profile = "default"

        if len(parts) > 1:
            # Could be "mastodon" + "STELLARWHISKERS" but if platform name
            # has underscores (unlikely for known platforms), this gets hairy.
            # For known platforms, we know the platform name is first.
            potential_profile = parts[1].upper()
            test_key = f"{platform}:{potential_profile}"
            if test_key in self.connectors:
                profile = potential_profile
            else:
                # Try with original casing
                test_key = f"{platform}:{parts[1]}"
                if test_key in self.connectors:
                    profile = parts[1]

        connector_key = f"{platform}:{profile}"
        connector = self.connectors.get(connector_key)
        if not connector:
            raise ValueError(f"No connector found for {connector_key}")

        if action == "metrics":
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

        elif action == "posts":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            content = connector.get_content(start_date, end_date)
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
                }
                for c in content
            ]

        elif action == "followers":
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
            raise ValueError(f"Unknown action '{action}' for tool {tool_name}")

    def _get_platform_status(self) -> Dict[str, Any]:
        """Get connection status for all connector profiles."""
        status = {}

        for key, connector in self.connectors.items():
            try:
                if hasattr(connector, "test_connection"):
                    result = connector.test_connection()
                    status[key] = result.get("status", "unknown")
                else:
                    status[key] = "configured"
            except Exception as e:
                status[key] = f"error: {str(e)}"

        return {
            "connectors": status,
            "total_configured": len(self.connectors),
            "message": f"{len(self.connectors)} connectors configured"
        }

    def _get_all_metrics(self, args: Dict[str, Any]) -> Dict[str, list]:
        """Get metrics from all configured connectors."""
        start_date = date.fromisoformat(args["start_date"])
        end_date = date.fromisoformat(args["end_date"])

        all_metrics: Dict[str, list] = {}

        for key, connector in self.connectors.items():
            try:
                if hasattr(connector, "get_metrics"):
                    metrics = connector.get_metrics(start_date, end_date)
                    all_metrics[key] = [
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
                all_metrics[key] = {"error": str(e)}

        return all_metrics

    def _get_cross_platform_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get unified summary across all connectors."""
        start_date = date.fromisoformat(args["start_date"])
        end_date = date.fromisoformat(args["end_date"])

        summary = {
            "date_range": {
                "start": str(start_date),
                "end": str(end_date),
            },
            "connectors": {},
            "totals": {},
        }

        for key, connector in self.connectors.items():
            try:
                if hasattr(connector, "get_metrics"):
                    metrics = connector.get_metrics(start_date, end_date)

                    connector_totals: Dict[str, float] = {}
                    for m in metrics:
                        metric_type = m.metric_type
                        if metric_type not in connector_totals:
                            connector_totals[metric_type] = 0
                        connector_totals[metric_type] += m.value

                    summary["connectors"][key] = connector_totals

                    for metric_type, value in connector_totals.items():
                        if metric_type not in summary["totals"]:
                            summary["totals"][metric_type] = 0
                        summary["totals"][metric_type] += value

            except Exception as e:
                summary["connectors"][key] = {"error": str(e)}

        return summary

    def _handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming JSON-RPC message."""
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
        """Main server loop - read from stdin, write to stdout."""
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
            pass
        except Exception as e:
            raise


def main():
    """Entry point"""
    server = MultiPlatformServer()
    server.run()


if __name__ == "__main__":
    main()
