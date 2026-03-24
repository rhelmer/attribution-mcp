"""
Umami MCP Server - Main entry point
Implements Model Context Protocol over stdio
"""

import os
import sys
import json
from typing import Any, Dict, List, Optional
from .umami_client import UmamiClient, UmamiAPIError


class MCPServer:
    """MCP Server for Umami Analytics"""

    def __init__(self):
        self.client: Optional[UmamiClient] = None
        self.initialized = False

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[umami-mcp] {message}\n")
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
        # Initialize Umami client
        base_url = os.environ.get("UMAMI_URL", "https://api.umami.is")
        api_key = os.environ.get("UMAMI_API_KEY")
        username = os.environ.get("UMAMI_USERNAME")
        password = os.environ.get("UMAMI_PASSWORD")
        team_id = os.environ.get("UMAMI_TEAM_ID")

        try:
            self.client = UmamiClient(
                base_url=base_url,
                api_key=api_key,
                username=username,
                password=password,
                team_id=team_id,
            )
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
                    "name": "umami-mcp",
                    "version": "1.0.0",
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "get_websites",
                "description": "List all websites being tracked by Umami",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_stats",
                "description": "Get summary statistics for a website (pageviews, visitors, bounces, avg. visit duration)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "website_id": {
                            "type": "string",
                            "description": "The website ID to get stats for",
                        },
                        "start_at": {
                            "type": "string",
                            "description": "Start date in ISO format (YYYY-MM-DD or ISO8601)",
                        },
                        "end_at": {
                            "type": "string",
                            "description": "End date in ISO format (YYYY-MM-DD or ISO8601)",
                        },
                        "unit": {
                            "type": "string",
                            "description": "Time unit for aggregation: minute, hour, day, month, year",
                            "enum": ["minute", "hour", "day", "month", "year"],
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone for the query",
                        },
                    },
                    "required": ["website_id", "start_at", "end_at"],
                },
            },
            {
                "name": "get_pageviews",
                "description": "Get pageview data with optional filters for URL or referrer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "website_id": {
                            "type": "string",
                            "description": "The website ID to get pageviews for",
                        },
                        "start_at": {
                            "type": "string",
                            "description": "Start date in ISO format",
                        },
                        "end_at": {
                            "type": "string",
                            "description": "End date in ISO format",
                        },
                        "unit": {
                            "type": "string",
                            "description": "Time unit for aggregation",
                            "enum": ["minute", "hour", "day", "month", "year"],
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone for the query",
                        },
                        "url": {
                            "type": "string",
                            "description": "Filter by specific URL path",
                        },
                        "referrer": {
                            "type": "string",
                            "description": "Filter by specific referrer",
                        },
                    },
                    "required": ["website_id", "start_at", "end_at"],
                },
            },
            {
                "name": "get_metrics",
                "description": "Get metrics breakdown by type (url, referrer, browser, os, device, country, language, event)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "website_id": {
                            "type": "string",
                            "description": "The website ID to get metrics for",
                        },
                        "start_at": {
                            "type": "string",
                            "description": "Start date in ISO format",
                        },
                        "end_at": {
                            "type": "string",
                            "description": "End date in ISO format",
                        },
                        "metric_type": {
                            "type": "string",
                            "description": "Type of metric: url, referrer, browser, os, device, country, language, event",
                            "enum": [
                                "url",
                                "referrer",
                                "browser",
                                "os",
                                "device",
                                "country",
                                "language",
                                "event",
                            ],
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone for the query",
                        },
                    },
                    "required": ["website_id", "start_at", "end_at", "metric_type"],
                },
            },
            {
                "name": "get_utm_metrics",
                "description": "Get UTM parameter metrics (utm_source, utm_medium, utm_campaign, utm_content, utm_term)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "website_id": {
                            "type": "string",
                            "description": "The website ID to get UTM metrics for",
                        },
                        "start_at": {
                            "type": "string",
                            "description": "Start date in ISO format",
                        },
                        "end_at": {
                            "type": "string",
                            "description": "End date in ISO format",
                        },
                        "utm_type": {
                            "type": "string",
                            "description": "UTM parameter type: utm_source, utm_medium, utm_campaign, utm_content, utm_term",
                            "enum": [
                                "utm_source",
                                "utm_medium",
                                "utm_campaign",
                                "utm_content",
                                "utm_term",
                            ],
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone for the query",
                        },
                    },
                    "required": ["website_id", "start_at", "end_at", "utm_type"],
                },
            },
            {
                "name": "get_active_visitors",
                "description": "Get the number of currently active visitors (last 5 minutes)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "website_id": {
                            "type": "string",
                            "description": "The website ID to check",
                        },
                    },
                    "required": ["website_id"],
                },
            },
            {
                "name": "get_realtime_data",
                "description": "Get realtime analytics data for the specified duration",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "website_id": {
                            "type": "string",
                            "description": "The website ID to get data for",
                        },
                        "duration": {
                            "type": "integer",
                            "description": "Duration in seconds (default: 30)",
                        },
                    },
                    "required": ["website_id"],
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
        except UmamiAPIError as e:
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
    ) -> Dict[str, Any]:
        """Execute a tool and return results"""

        if tool_name == "get_websites":
            return self.client.get_websites()

        elif tool_name == "get_stats":
            return self.client.get_stats(
                website_id=args["website_id"],
                start_at=args["start_at"],
                end_at=args["end_at"],
                unit=args.get("unit", "day"),
                timezone=args.get("timezone", "UTC"),
            )

        elif tool_name == "get_pageviews":
            return self.client.get_pageviews(
                website_id=args["website_id"],
                start_at=args["start_at"],
                end_at=args["end_at"],
                unit=args.get("unit", "day"),
                timezone=args.get("timezone", "UTC"),
                url=args.get("url"),
                referrer=args.get("referrer"),
            )

        elif tool_name == "get_metrics":
            return self.client.get_metrics(
                website_id=args["website_id"],
                start_at=args["start_at"],
                end_at=args["end_at"],
                metric_type=args["metric_type"],
                timezone=args.get("timezone", "UTC"),
            )

        elif tool_name == "get_utm_metrics":
            return self.client.get_utm_metrics(
                website_id=args["website_id"],
                start_at=args["start_at"],
                end_at=args["end_at"],
                utm_type=args["utm_type"],
                timezone=args.get("timezone", "UTC"),
            )

        elif tool_name == "get_active_visitors":
            return self.client.get_active_visitors(website_id=args["website_id"])

        elif tool_name == "get_realtime_data":
            return self.client.get_realtime_data(
                website_id=args["website_id"],
                duration=args.get("duration", 30),
            )

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
