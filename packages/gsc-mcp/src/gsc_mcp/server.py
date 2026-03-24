"""Google Search Console MCP Server."""

import os
import sys
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from attribution_schema.schema import Metric, Content, Audience
from attribution_cache.cache import Cache


class GSCConnector:
    """Google Search Console connector."""

    name = "gsc"

    def __init__(self):
        self.service = None
        self.site_url = os.environ.get("GSC_SITE_URL")  # Optional default
        self.credentials_file = os.environ.get("GSC_SERVICE_ACCOUNT_FILE")
        self.token_file = os.environ.get("GSC_TOKEN_FILE", ".gsc_token.json")
        self.cache = Cache()

    def authenticate(self) -> bool:
        """Authenticate with GSC using OAuth token or service account."""
        # Try OAuth token first
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
                credentials = Credentials.from_authorized_user_info(
                    token_data,
                    scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
                )
                self.service = build("searchconsole", "v1", credentials=credentials)
                return True
            except Exception as e:
                raise ValueError(f"Failed to authenticate with GSC OAuth token: {e}")

        # Fall back to service account
        if not self.credentials_file:
            raise ValueError(
                "GSC_SERVICE_ACCOUNT_FILE must be set, or .gsc_token.json must exist"
            )

        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            )
            self.service = build("searchconsole", "v1", credentials=credentials)
            return True
        except Exception as e:
            raise ValueError(f"Failed to authenticate with GSC: {e}")

    def get_metrics(
        self,
        start_date: date,
        end_date: date,
        dimensions: Optional[List[str]] = None,
        site_url: Optional[str] = None
    ) -> List[Metric]:
        """
        Fetch search performance data from GSC.

        Dimensions: ["query", "page", "country", "device"]
        Metrics: impressions, clicks, CTR, position

        Args:
            site_url: Optional. Override default site_url for this query.
                     If not set, uses GSC_SITE_URL from environment.
        """
        # Use provided site_url or fall back to default
        effective_site_url = site_url or self.site_url

        if not effective_site_url:
            raise ValueError(
                "No GSC property specified. Either set GSC_SITE_URL in environment, "
                "or pass site_url parameter. Use list_gsc_properties to see available properties."
            )

        # Try cache first
        cached = self.cache.get_metrics(
            source=self.name,
            start_date=start_date,
            end_date=end_date,
            max_age_hours=1
        )
        if cached:
            return cached

        if not self.service:
            self.authenticate()

        request = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dimensions or [],
            "rowLimit": 25000,
        }

        try:
            response = self.service.searchanalytics().query(
                siteUrl=effective_site_url, body=request
            ).execute()

            metrics = []
            for row in response.get("rows", []):
                # Parse dimensions from row
                dim_dict = {}
                keys = row.get("keys", [])
                for i, key in enumerate(keys):
                    if dimensions and i < len(dimensions):
                        dim_dict[dimensions[i]] = key

                # Create metrics for clicks and impressions
                if "clicks" in row:
                    metrics.append(Metric(
                        source=self.name,
                        date=start_date,  # GSC returns aggregated data
                        metric_type="clicks",
                        value=row["clicks"],
                        dimensions=dim_dict
                    ))

                if "impressions" in row:
                    metrics.append(Metric(
                        source=self.name,
                        date=start_date,
                        metric_type="impressions",
                        value=row["impressions"],
                        dimensions=dim_dict
                    ))

                if "ctr" in row:
                    metrics.append(Metric(
                        source=self.name,
                        date=start_date,
                        metric_type="ctr",
                        value=row["ctr"],
                        dimensions=dim_dict
                    ))

                if "position" in row:
                    metrics.append(Metric(
                        source=self.name,
                        date=start_date,
                        metric_type="position",
                        value=row["position"],
                        dimensions=dim_dict
                    ))

            # Cache the results
            self.cache.set_metrics(metrics)
            return metrics

        except HttpError as e:
            raise ValueError(f"GSC API error: {e}")

    def get_content(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Content]:
        """Get pages with their search performance."""
        metrics = self.get_metrics(
            start_date=start_date,
            end_date=end_date,
            dimensions=["page"]
        )

        # Group by URL
        content_map: Dict[str, Content] = {}
        for m in metrics:
            url = m.dimensions.get("page", "")
            if not url:
                continue

            if url not in content_map:
                content_map[url] = Content(
                    source=self.name,
                    content_id=url,
                    content_type="page",
                    url=url,
                    title=url,  # GSC doesn't provide titles directly
                    created_at=datetime.now(),
                    metrics=[]
                )

            content_map[url].metrics.append(m)

        return list(content_map.values())

    def get_audience(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Audience]:
        """GSC doesn't provide audience/follower data."""
        return []

    def test_connection(self) -> Dict[str, Any]:
        """Test GSC connection and return status."""
        try:
            if not self.service:
                self.authenticate()

            # Try to get a small sample of data
            test_start = date.today()
            test_end = date.today()

            request = {
                "startDate": test_start.isoformat(),
                "endDate": test_end.isoformat(),
                "rowLimit": 1,
            }

            self.service.searchanalytics().query(
                siteUrl=self.site_url, body=request
            ).execute()

            return {
                "status": "connected",
                "site_url": self.site_url,
                "message": "Successfully connected to GSC"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def list_properties(self) -> List[Dict[str, str]]:
        """List all GSC properties available to the account."""
        if not self.service:
            self.authenticate()

        try:
            # Use webmasters.sites.list to get all properties
            response = self.service.sites().list().execute()

            properties = []
            for site_info in response.get("siteEntry", []):
                properties.append({
                    "site_url": site_info.get("siteUrl", ""),
                    "permission_level": site_info.get("permissionLevel", ""),
                })

            return properties

        except Exception as e:
            return [{"error": str(e)}]


# MCP Server implementation
class MCPServer:
    """MCP Server for Google Search Console"""

    def __init__(self):
        self.connector: Optional[GSCConnector] = None
        self.initialized = False

    def _log(self, message: str) -> None:
        """Log debug message to stderr"""
        sys.stderr.write(f"[gsc-mcp] {message}\n")
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
            self.connector = GSCConnector()
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
                    "name": "gsc-mcp",
                    "version": "1.0.0",
                },
            },
        )

    def _list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "list_gsc_properties",
                "description": "List all GSC properties (sites) available to your account",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_gsc_metrics",
                "description": "Get Google Search Console metrics (impressions, clicks, CTR, position)",
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
                        "dimensions": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["query", "page", "country", "device"]
                            },
                            "description": "Dimensions to break down data by",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "Optional: Override default GSC_SITE_URL for this query",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "name": "get_gsc_pages",
                "description": "Get pages with their search performance from GSC",
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
                "name": "get_gsc_queries",
                "description": "Get top search queries from GSC",
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
                            "description": "Maximum number of queries to return (default: 100)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "name": "test_gsc_connection",
                "description": "Test the GSC connection",
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

        if tool_name == "test_gsc_connection":
            return self.connector.test_connection()

        elif tool_name == "list_gsc_properties":
            return self.connector.list_properties()

        elif tool_name == "get_gsc_metrics":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            dimensions = args.get("dimensions")
            site_url = args.get("site_url")

            metrics = self.connector.get_metrics(start_date, end_date, dimensions, site_url)

            # Add site_url to each metric for clarity
            result = [
                {
                    "source": m.source,
                    "site_url": self.connector.site_url or site_url,  # Show which property
                    "date": str(m.date),
                    "metric_type": m.metric_type,
                    "value": m.value,
                    "dimensions": m.dimensions,
                }
                for m in metrics
            ]
            return result

        elif tool_name == "get_gsc_pages":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            content = self.connector.get_content(start_date, end_date)
            return [
                {
                    "source": c.source,
                    "content_id": c.content_id,
                    "content_type": c.content_type,
                    "url": c.url,
                    "title": c.title,
                    "metrics": [
                        {
                            "metric_type": m.metric_type,
                            "value": m.value,
                            "dimensions": m.dimensions,
                        }
                        for m in c.metrics
                    ],
                }
                for c in content
            ]

        elif tool_name == "get_gsc_queries":
            start_date = date.fromisoformat(args["start_date"])
            end_date = date.fromisoformat(args["end_date"])
            limit = args.get("limit", 100)
            metrics = self.connector.get_metrics(
                start_date, end_date, dimensions=["query"]
            )

            # Group by query and aggregate
            query_data: Dict[str, Dict[str, Any]] = {}
            for m in metrics:
                query = m.dimensions.get("query", "")
                if not query:
                    continue

                if query not in query_data:
                    query_data[query] = {
                        "query": query,
                        "clicks": 0,
                        "impressions": 0,
                        "ctr": 0,
                        "position": 0,
                    }

                if m.metric_type == "clicks":
                    query_data[query]["clicks"] = m.value
                elif m.metric_type == "impressions":
                    query_data[query]["impressions"] = m.value
                elif m.metric_type == "ctr":
                    query_data[query]["ctr"] = m.value
                elif m.metric_type == "position":
                    query_data[query]["position"] = m.value

            # Sort by impressions and limit
            sorted_queries = sorted(
                query_data.values(),
                key=lambda x: x["impressions"],
                reverse=True
            )[:limit]

            return sorted_queries

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
