"""
Analytics Renderer for Terminal Graphics

Integrates real analytics data from MCP servers with kitty graphics
protocol to render live dashboards in Ghostty/kitty terminals.

Usage:
    from analytics_renderer import AnalyticsRenderer

    renderer = AnalyticsRenderer()
    await renderer.render_dashboard(start_date, end_date)
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent))

from dashboard_charts import (
    generate_bar_chart,
    generate_line_chart,
    generate_pie_chart,
    generate_gauge,
    generate_sparkline,
    generate_horizontal_bar_chart,
    generate_stacked_bar_chart,
    generate_time_series_chart,
    generate_metrics_card,
    generate_table_image,
)
from kitty_graphics import (
    get_terminal_size,
    send_image_data,
    move_cursor_down,
    calculate_chart_dimensions,
    get_unicode_sparkline,
    render_progress_bar,
    probe_support,
)


class AnalyticsRenderer:
    """Render analytics data as terminal graphics using kitty protocol."""

    def __init__(self):
        self.terminal_cols, self.terminal_rows = get_terminal_size()
        self.has_graphics = probe_support()

        if not self.has_graphics:
            print("⚠️  Terminal may not support kitty graphics protocol")
            print("   Try setting KITTY_GRAPHICS_FORCE=1 to override\n")

    def _print_header(self, text: str, level: int = 1) -> None:
        """Print a styled header."""
        colors = {1: "36", 2: "32", 3: "33"}
        color = colors.get(level, "36")
        width = min(60, self.terminal_cols)

        print()
        print(f"\033[1;{color}m{'=' * width}\033[0m")
        print(f"\033[1;{color}m {text}\033[0m")
        print(f"\033[1;{color}m{'=' * width}\033[0m")
        print()

    def _print_metric(self, label: str, value: str, color_code: str = "32") -> None:
        """Print a metric with styling."""
        print(f"  \033[{color_code}m{value}\033[0m  {label}")

    def _print_sparkline(self, data: list[float], label: str = "") -> None:
        """Print an inline unicode sparkline."""
        sparkline = get_unicode_sparkline(data, width=30)
        if label:
            print(f"  {label:20s} {sparkline}")
        else:
            print(f"  {sparkline}")

    def _calculate_chart_size(self, width_pct: float = 0.8, height_pct: float = 0.25):
        """Calculate chart dimensions based on terminal size."""
        return calculate_chart_dimensions(
            self.terminal_cols,
            self.terminal_rows,
            width_pct=width_pct,
            height_pct=height_pct,
        )

    async def render_from_mcp(
        self,
        mcp_data: Dict[str, Any],
        website_domain: str,
        date_range: str,
    ) -> None:
        """
        Render a complete dashboard from MCP data.

        Args:
            mcp_data: Data retrieved from MCP servers
            website_domain: Website domain being analyzed
            date_range: Date range string
        """
        if not self.has_graphics:
            print("⚠️  Graphics not supported, showing text-only mode\n")
            self._render_text_dashboard(mcp_data, website_domain, date_range)
            return

        self._print_header(f"📊 ANALYTICS DASHBOARD - {website_domain}")
        print(f"  📅 Period: {date_range}")
        print(f"  💻 Terminal: {self.terminal_cols}x{self.terminal_rows} cells")
        print()

        # Extract and render different data types
        self._render_metrics_section(mcp_data)
        move_cursor_down(1)

        self._render_time_series(mcp_data)
        move_cursor_down(1)

        self._render_breakdowns(mcp_data)
        move_cursor_down(1)

        self._render_social_platforms(mcp_data)
        move_cursor_down(1)

        self._print_footer()

    def _render_metrics_section(self, data: Dict[str, Any]) -> None:
        """Render key metrics section."""
        print("\033[1m📈 Key Performance Indicators\033[0m\n")

        # Try to extract website stats
        stats = data.get("website_stats", {})
        if isinstance(stats, list) and len(stats) > 0:
            stats_content = stats[0]
            if hasattr(stats_content, "text"):
                stats_data = json.loads(stats_content.text)

                # Extract metrics
                pageviews = stats_data.get("pageviews", 0)
                visitors = stats_data.get("visitors", 0)
                visits = stats_data.get("visits", 0)
                bounce_rate = stats_data.get("bounce_rate", 0)

                metrics = [
                    ("Pageviews", f"{pageviews:,}", "#4CAF50"),
                    ("Visitors", f"{visitors:,}", "#2196F3"),
                    ("Visits", f"{visits:,}", "#FF9800"),
                    ("Bounce Rate", f"{bounce_rate:.1f}%", "#E91E63"),
                ]

                for label, value, color in metrics:
                    self._print_metric(label, value, "32")
        else:
            # Fallback to sample metrics
            print("  ⚠️  No stats data available")
            metrics = [
                ("Pageviews", "N/A", "#808080"),
                ("Visitors", "N/A", "#808080"),
            ]

        move_cursor_down(1)

    def _render_time_series(self, data: Dict[str, Any]) -> None:
        """Render time series charts."""
        print("\033[1m📉 Traffic Trends\033[0m\n")
        move_cursor_down(1)

        # Try to get pageview series
        pageview_data = data.get("pageview_series", [])
        if isinstance(pageview_data, list) and len(pageview_data) > 0:
            try:
                pageview_json = json.loads(pageview_data[0].text)

                if "data" in pageview_json:
                    # Extract values and timestamps
                    values = [point.get("y", 0) for point in pageview_json["data"]]
                    timestamps = [point.get("x", "") for point in pageview_json["data"]]

                    if values:
                        chart_width, chart_height = self._calculate_chart_size(0.8, 0.25)

                        # Format timestamps for labels
                        labels = []
                        for ts in timestamps[:15]:  # Limit labels
                            try:
                                dt = datetime.fromisoformat(ts)
                                labels.append(dt.strftime("%m/%d"))
                            except:
                                labels.append(ts)

                        chart = generate_time_series_chart(
                            timestamps=labels,
                            data=values,
                            title="Pageviews Over Time",
                            width=chart_width,
                            height=chart_height,
                            color="#4CAF50",
                        )
                        send_image_data(chart, format="png")
                        move_cursor_down(2)
                        return
            except Exception as e:
                print(f"  ⚠️  Could not render pageview chart: {e}")

        print("  ⚠️  No time series data available")
        move_cursor_down(1)

    def _render_breakdowns(self, data: Dict[str, Any]) -> None:
        """Render breakdown charts (pages, referrers, etc.)."""
        print("\033[1m📊 Traffic Breakdown\033[0m\n")
        move_cursor_down(1)

        # Top pages
        url_metrics = data.get("metrics_url", [])
        if isinstance(url_metrics, list) and len(url_metrics) > 0:
            try:
                urls_data = json.loads(url_metrics[0].text)
                if "data" in urls_data and len(urls_data["data"]) > 0:
                    # Get top 10 pages
                    top_pages = urls_data["data"][:10]
                    page_names = [p.get("x", "Unknown") for p in top_pages]
                    page_views = [p.get("y", 0) for p in top_pages]

                    # Shorten long URLs
                    page_names = [name[:30] + "..." if len(name) > 30 else name
                                 for name in page_names]

                    chart_width, chart_height = self._calculate_chart_size(0.8, 0.25)
                    chart = generate_horizontal_bar_chart(
                        data=page_views,
                        labels=page_names,
                        title="Top Pages",
                        width=chart_width,
                        height=chart_height,
                    )
                    send_image_data(chart, format="png")
                    move_cursor_down(2)
            except Exception as e:
                print(f"  ⚠️  Could not render pages chart: {e}")

        # Top referrers
        referrer_metrics = data.get("metrics_referrer", [])
        if isinstance(referrer_metrics, list) and len(referrer_metrics) > 0:
            try:
                ref_data = json.loads(referrer_metrics[0].text)
                if "data" in ref_data and len(ref_data["data"]) > 0:
                    top_refs = ref_data["data"][:8]
                    ref_names = [r.get("x", "Unknown") for r in top_refs]
                    ref_values = [r.get("y", 0) for r in top_refs]

                    chart_width, chart_height = self._calculate_chart_size(0.8, 0.2)
                    chart = generate_bar_chart(
                        data=ref_values,
                        labels=ref_names,
                        title="Top Referrers",
                        width=chart_width,
                        height=chart_height,
                    )
                    send_image_data(chart, format="png")
                    move_cursor_down(2)
            except Exception as e:
                print(f"  ⚠️  Could not render referrers chart: {e}")

    def _render_social_platforms(self, data: Dict[str, Any]) -> None:
        """Render social platform metrics."""
        print("\033[1m🌐 Social Platform Status\033[0m\n")

        # Check which platforms are configured
        platforms = [
            ("Umami", "websites" in data or "website_stats" in data),
            ("GSC", "gsc_data" in data),
            ("YouTube", "youtube_data" in data),
            ("Mastodon", "mastodon_data" in data),
            ("Bluesky", "bluesky_data" in data),
            ("LinkedIn", "linkedin_data" in data),
            ("Instagram", "instagram_data" in data),
        ]

        for platform, is_configured in platforms:
            status = "✅" if is_configured else "⚪"
            print(f"  {status} {platform}")

        move_cursor_down(1)

    def _render_text_dashboard(
        self,
        data: Dict[str, Any],
        website_domain: str,
        date_range: str,
    ) -> None:
        """Render a text-only dashboard for terminals without graphics."""
        print(f"Website: {website_domain}")
        print(f"Period: {date_range}")
        print()

        # Show available tools
        tools = data.get("available_tools", [])
        print(f"Available MCP tools: {', '.join(tools[:10])}")
        print()

        # Show any stats
        if "website_stats" in data:
            print("Website Stats:")
            print(json.dumps(data["website_stats"], indent=2, default=str)[:500])
            print()

    def _print_footer(self) -> None:
        """Print dashboard footer."""
        print()
        print("\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36m ✅ Dashboard rendered successfully!\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m")
        print()
        print("  💡 Tip: Works in Ghostty, kitty, and WezTerm terminals")
        print("  💡 Tip: Charts generated as PNG via kitty graphics protocol")
        print()

    def render_standalone_charts(self) -> None:
        """Render standalone demo charts (fallback mode)."""
        self._print_header("📊 TERMINAL DASHBOARD DEMO")

        chart_width, chart_height = self._calculate_chart_size()

        # 1. Metrics
        print("\033[1m📈 Sample Metrics\033[0m\n")
        metrics = [
            ("Revenue", "$12.4K", "#4CAF50"),
            ("Users", "1,247", "#2196F3"),
            ("Conv.", "3.2%", "#FF9800"),
        ]
        for label, value, _ in metrics:
            self._print_metric(label, value)

        move_cursor_down(1)

        # 2. Line chart
        print("\033[1m📉 Revenue Trend\033[0m\n")
        move_cursor_down(1)

        revenue = [8.2, 9.1, 7.8, 10.5, 11.2, 9.8, 12.4]
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        chart = generate_line_chart(
            data=revenue,
            labels=days,
            title="Daily Revenue ($K)",
            width=chart_width,
            height=int(chart_height * 0.6),
        )
        send_image_data(chart, format="png")
        move_cursor_down(2)

        # 3. Bar chart with sparkline
        print("\033[1m📊 Traffic Sources\033[0m\n")
        move_cursor_down(1)

        channels = [450, 320, 280, 190, 150]
        channel_names = ["Organic", "Direct", "Social", "Email", "Referral"]

        # Print sparklines for each channel
        for name, value in zip(channel_names, channels):
            spark_data = [value * (0.8 + i * 0.05) for i in range(10)]
            self._print_sparkline(spark_data, f"{name}: {value}")

        move_cursor_down(1)

        chart = generate_bar_chart(
            data=channels,
            labels=channel_names,
            title="Traffic by Channel",
            width=chart_width,
            height=int(chart_height * 0.6),
        )
        send_image_data(chart, format="png")
        move_cursor_down(2)

        # 4. Gauge
        print("\033[1m🎯 Performance Metrics\033[0m\n")
        move_cursor_down(1)

        # Text-based progress bars
        print(f"  {'CPU Usage':20s} {render_progress_bar(67, 100)}")
        print(f"  {'Memory':20s} {render_progress_bar(78, 100)}")
        print(f"  {'Disk I/O':20s} {render_progress_bar(45, 100)}")

        move_cursor_down(1)

        gauge = generate_gauge(
            value=67,
            max_value=100,
            title="System Load",
            width=int(chart_width * 0.6),
            height=int(chart_height * 0.3),
        )
        send_image_data(gauge, format="png")
        move_cursor_down(2)

        self._print_footer()
