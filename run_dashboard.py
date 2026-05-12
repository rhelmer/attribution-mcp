#!/usr/bin/env python3
"""
Terminal Dashboard with Kitty Graphics

Renders analytics dashboards directly in your terminal using the kitty graphics protocol.
Works with Ghostty, kitty, and WezTerm terminals.

Features:
- Real analytics data from MCP servers (Umami, GSC, YouTube, social platforms)
- Beautiful charts and visualizations rendered inline
- Unicode sparklines for inline mini-charts
- Automatic terminal size detection
- Fallback to text-only mode for unsupported terminals

Usage:
    # Demo mode with sample data
    python run_dashboard.py

    # Real data from MCP servers
    python run_dashboard.py --start-date 2025-01-01 --end-date 2025-12-31 --website example.com

    # Force graphics even if not detected
    KITTY_GRAPHICS_FORCE=1 python run_dashboard.py
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

from analytics_renderer import AnalyticsRenderer
from dashboard_charts import (
    generate_bar_chart,
    generate_gauge,
    generate_line_chart,
    generate_metrics_card,
    generate_pie_chart,
    generate_sparkline,
)
from kitty_graphics import (
    get_terminal_size,
    move_cursor_down,
    send_image_data,
    probe_support,
    get_unicode_sparkline,
    render_progress_bar,
)


def print_header(text: str) -> None:
    """Print a styled header using rich text formatting."""
    width = 60
    print()
    print(f"\033[1;36m{'=' * width}\033[0m")
    print(f"\033[1;36m {text}\033[0m")
    print(f"\033[1;36m{'=' * width}\033[0m")
    print()


def print_metric(label: str, value: str, color_code: str = "32") -> None:
    """Print a text metric alongside graphics."""
    print(f"  \033[{color_code}m{value}\033[0m  {label}")


async def run_real_dashboard(args: argparse.Namespace) -> None:
    """Render dashboard with real data from MCP servers."""
    from run import AnalyticsDashboard

    print("🔄 Connecting to analytics platforms...")
    print()

    # Create analytics dashboard instance
    dashboard = AnalyticsDashboard(
        mcp_server_dir="packages/umami-mcp/src/umami_mcp",
        ai_provider="cloudflare",  # Not used for data retrieval
    )

    # Create renderer
    renderer = AnalyticsRenderer()

    try:
        # Get real data from MCP
        import os
        from mcp.client.stdio import stdio_client
        from mcp.client.session import ClientSession

        async with stdio_client(dashboard.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ Connected to MCP server")

                try:
                    await session.initialize()
                except Exception as init_error:
                    print(f"⚠️  Initialization warning: {init_error}")

                # Fetch real data
                print(f"📊 Fetching data for {args.website}...")
                real_data = await dashboard.get_real_data_from_mcp(
                    session,
                    args.website,
                    args.start_date,
                    args.end_date,
                    args.timezone,
                )

                date_range = f"{args.start_date} to {args.end_date}"

                # Render dashboard with real data
                await renderer.render_from_mcp(
                    real_data,
                    args.website,
                    date_range,
                )

    except Exception as e:
        print(f"\n❌ Error fetching analytics data: {e}")
        print("\n💡 Tip: Make sure your .env file has the required credentials")
        print("💡 Tip: Try demo mode first: python run_dashboard.py")
        sys.exit(1)


async def run_demo_dashboard(args: argparse.Namespace) -> None:
    """Render demo dashboard with sample data."""
    renderer = AnalyticsRenderer()

    if args.demo_type == "full":
        renderer.render_standalone_charts()
    elif args.demo_type == "minimal":
        await run_minimal_demo()
    elif args.demo_type == "sparklines":
        await run_sparklines_demo()
    else:
        renderer.render_standalone_charts()


async def run_minimal_demo() -> None:
    """Run a minimal text-heavy demo."""
    print_header("📊 MINIMAL DASHBOARD DEMO")

    cols, rows = get_terminal_size()
    print(f"  Terminal: {cols}x{rows} cells")
    print(f"  Graphics: {'✅ Yes' if probe_support() else '⚠️  Limited'}")
    print()

    # Key metrics
    print("\033[1m📈 Key Metrics\033[0m\n")
    metrics = [
        ("Pageviews", "12,847", "32"),
        ("Visitors", "3,241", "34"),
        ("Bounce Rate", "42.3%", "33"),
        ("Avg. Duration", "3m 24s", "35"),
    ]

    for label, value, color in metrics:
        print_metric(label, value, color)

    print()

    # Sparklines
    print("\033[1m📉 Trends (Last 7 Days)\033[0m\n")

    pageviews = [1200, 1350, 1100, 1450, 1600, 1400, 1847]
    visitors = [400, 450, 380, 520, 580, 490, 621]

    print(f"  {'Pageviews':15s} {get_unicode_sparkline(pageviews, width=30)}")
    print(f"  {'Visitors':15s} {get_unicode_sparkline(visitors, width=30)}")
    print()

    # Progress bars
    print("\033[1m🎯 Goals Progress\033[0m\n")
    print(f"  {'Monthly Target':20s} {render_progress_bar(7847, 10000, width=40)}")
    print(f"  {'Weekly Target':20s} {render_progress_bar(6590, 8000, width=40)}")
    print(f"  {'Daily Avg':20s} {render_progress_bar(1436, 1500, width=40)}")
    print()

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print("\033[1;36m ✅ Minimal demo complete!\033[0m")
    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print()


async def run_sparklines_demo() -> None:
    """Run a sparkline-focused demo."""
    print_header("⚡ SPARKLINES DEMO")

    # Revenue trend
    print("\033[1m💰 Revenue Trend (12 months)\033[0m\n")
    revenue = [8.2, 9.1, 7.8, 10.5, 11.2, 9.8, 12.4, 13.1, 14.2, 13.8, 15.1, 16.4]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    sparkline = get_unicode_sparkline(revenue, width=40)
    print(f"  Revenue: {sparkline}")
    print(f"           {'$8.2K':<6}                              {'$16.4K':>6}")
    print()

    # Multiple metrics with sparklines
    print("\033[1m📊 Multiple Metrics\033[0m\n")

    metrics_data = [
        ("Pageviews", [1200, 1350, 1100, 1450, 1600, 1400, 1847, 1920]),
        ("Visitors", [400, 450, 380, 520, 580, 490, 621, 680]),
        ("Conversions", [12, 15, 11, 18, 22, 19, 25, 28]),
        ("Revenue", [820, 910, 780, 1050, 1120, 980, 1240, 1310]),
    ]

    for name, data in metrics_data:
        sparkline = get_unicode_sparkline(data, width=35)
        current = data[-1]
        print(f"  {name:15s} {sparkline} {current:,}")

    print()

    # Social engagement
    print("\033[1m🌐 Social Engagement (7 days)\033[0m\n")

    social_data = [
        ("Mastodon", [45, 52, 38, 61, 55, 70, 68]),
        ("Bluesky", [23, 28, 35, 42, 38, 51, 47]),
        ("LinkedIn", [120, 135, 142, 158, 165, 178, 185]),
    ]

    for platform, data in social_data:
        sparkline = get_unicode_sparkline(data, width=30)
        total = sum(data)
        avg = sum(data) / len(data)
        print(f"  {platform:15s} {sparkline}")
        print(f"  {'':15s} Total: {total:,} | Avg: {avg:.0f}/day")
        print()

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print("\033[1;36m ⚡ Sparklines demo complete!\033[0m")
    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Terminal dashboard with kitty graphics protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo mode
  python run_dashboard.py

  # Demo with specific type
  python run_dashboard.py --demo minimal
  python run_dashboard.py --demo sparklines

  # Real data from analytics platforms
  python run_dashboard.py --start-date 2025-01-01 --end-date 2025-12-31 --website example.com

Environment:
  KITTY_GRAPHICS_FORCE=1    Force graphics even if not detected
        """,
    )

    # Mode selection
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for analytics (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date for analytics (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--website",
        type=str,
        help="Website domain to analyze",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="UTC",
        help="Timezone for date interpretation (default: UTC)",
    )

    # Demo options
    parser.add_argument(
        "--demo",
        type=str,
        choices=["full", "minimal", "sparklines"],
        default="full",
        help="Demo type when not using real data (default: full)",
    )

    args = parser.parse_args()

    # Determine if we're using real data or demo
    use_real_data = all([
        args.start_date,
        args.end_date,
        args.website,
    ])

    if use_real_data:
        # Run with real data
        asyncio.run(run_real_dashboard(args))
    else:
        # Run demo
        args.demo_type = args.demo
        asyncio.run(run_demo_dashboard(args))


if __name__ == "__main__":
    main()
