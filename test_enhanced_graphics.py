#!/usr/bin/env python3
"""
Enhanced Test for Kitty Graphics Features

Tests all the new kitty graphics functionality including:
- Image management
- Unicode sparklines
- Terminal detection
- New chart types
- Real data integration

Usage:
    python test_enhanced_graphics.py
"""

import base64
import sys
import time
from io import BytesIO
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

from PIL import Image, ImageDraw
from dashboard_charts import (
    generate_area_chart,
    generate_bar_chart,
    generate_gauge,
    generate_heatmap,
    generate_horizontal_bar_chart,
    generate_line_chart,
    generate_metrics_card,
    generate_pie_chart,
    generate_scatter_plot,
    generate_sparkline,
    generate_stacked_bar_chart,
    generate_table_image,
    generate_time_series_chart,
)
from kitty_graphics import (
    ImageManager,
    calculate_chart_dimensions,
    clear_display,
    delete_image,
    get_terminal_size,
    get_unicode_sparkline,
    move_cursor_down,
    move_cursor_to,
    probe_support,
    render_progress_bar,
    restore_cursor_position,
    save_cursor_position,
    send_image_data,
    update_image,
)


def create_gradient_image(width=400, height=200):
    """Create a gradient test image."""
    img = Image.new("RGB", (width, height), "#1a1a2e")
    draw = ImageDraw.Draw(img)

    # Draw gradient
    for x in range(width):
        r = int(255 * x / width)
        g = int(100 * (1 - x / width))
        b = 150
        draw.line([(x, 0), (x, height)], fill=(r, g, b))

    # Draw text
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        font = ImageFont.load_default()

    draw.text((50, height // 2 - 10), "KITTY GRAPHICS TEST", fill="#ffffff", font=font)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def test_terminal_detection():
    """Test terminal capability detection."""
    print("\n" + "=" * 60)
    print(" TEST 1: Terminal Detection")
    print("=" * 60)

    cols, rows = get_terminal_size()
    has_support = probe_support()

    print(f"  Terminal size: {cols}x{rows} cells")
    print(f"  Graphics support: {'✅ Yes' if has_support else '⚠️  Not detected'}")
    print(f"  (Set KITTY_GRAPHICS_FORCE=1 to override)")
    print()


def test_unicode_sparklines():
    """Test unicode sparkline generation."""
    print("\n" + "=" * 60)
    print(" TEST 2: Unicode Sparklines")
    print("=" * 60)

    # Simple sparkline
    print("\n  Simple trend:")
    data1 = [10, 20, 15, 25, 30, 28, 35]
    sparkline1 = get_unicode_sparkline(data1, width=30)
    print(f"  {sparkline1}")

    # Multiple sparklines
    print("\n  Multiple metrics:")
    metrics = [
        ("Pageviews", [1200, 1350, 1100, 1450, 1600, 1400, 1847]),
        ("Visitors", [400, 450, 380, 520, 580, 490, 621]),
        ("Conversions", [12, 15, 11, 18, 22, 19, 25]),
    ]

    for name, data in metrics:
        sparkline = get_unicode_sparkline(data, width=35)
        print(f"  {name:15s} {sparkline}")

    # Realistic data with more points
    print("\n  Longer dataset (40 points):")
    data3 = [50 + 30 * (i % 7) / 7 + 10 * (i % 3) for i in range(40)]
    sparkline3 = get_unicode_sparkline(data3, width=40)
    print(f"  {sparkline3}")
    print()


def test_progress_bars():
    """Test progress bar rendering."""
    print("\n" + "=" * 60)
    print(" TEST 3: Progress Bars")
    print("=" * 60)

    print()
    bars = [
        ("CPU Usage", 67, 100),
        ("Memory", 78, 100),
        ("Disk I/O", 45, 100),
        ("Network", 92, 100),
        ("Monthly Goal", 7847, 10000),
        ("Weekly Target", 6590, 8000),
    ]

    for label, value, max_val in bars:
        bar = render_progress_bar(value, max_val, width=40)
        print(f"  {label:20s} {bar}")

    print()


def test_image_management():
    """Test image ID management."""
    print("\n" + "=" * 60)
    print(" TEST 4: Image Management")
    print("=" * 60)

    manager = ImageManager()

    # Allocate IDs
    id1 = manager.allocate_id()
    id2 = manager.allocate_id()
    id3 = manager.allocate_id()

    print(f"  Allocated IDs: {id1}, {id2}, {id3}")

    # Register images
    manager.register(id1, {"type": "line_chart", "title": "Revenue"})
    manager.register(id2, {"type": "bar_chart", "title": "Traffic"})
    manager.register(id3, {"type": "gauge", "title": "CPU"})

    print(f"  Active images: {manager.active_count}")

    # Unregister one
    manager.unregister(id2)
    print(f"  After unregister: {manager.active_count} active")
    print()


def test_basic_image_rendering():
    """Test basic image rendering."""
    print("\n" + "=" * 60)
    print(" TEST 5: Basic Image Rendering")
    print("=" * 60)
    print()

    img_data = create_gradient_image(400, 200)

    print("\033[1mSending test image...\033[0m")
    move_cursor_down(1)

    send_image_data(
        img_data,
        format="png",
        width_cells=50,
        height_cells=25,
    )

    move_cursor_down(2)
    print("✅ Image sent!")
    print()
    input("  Press Enter to continue...")


def test_new_chart_types():
    """Test all new chart types."""
    print("\n" + "=" * 60)
    print(" TEST 6: New Chart Types")
    print("=" * 60)

    cols, rows = get_terminal_size()
    chart_width, chart_height = calculate_chart_dimensions(cols, rows, 0.8, 0.25)

    # 6a. Area chart
    print("\033[1m\n📈 Area Chart\033[0m\n")
    move_cursor_down(1)

    area_data = [8.2, 9.1, 7.8, 10.5, 11.2, 9.8, 12.4, 13.1, 14.2]
    area_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon", "Tue"]

    area_chart = generate_area_chart(
        data=area_data,
        labels=area_labels,
        title="Revenue Trend (Area)",
        width=chart_width,
        height=int(chart_height * 0.6),
        color="#2196F3",
    )
    send_image_data(area_chart, format="png")
    move_cursor_down(2)
    input("  Press Enter to continue...")

    # 6b. Horizontal bar chart
    print("\033[1m\n📊 Horizontal Bar Chart\033[0m\n")
    move_cursor_down(1)

    hbar_data = [450, 320, 280, 190, 150]
    hbar_labels = ["Organic Search", "Direct", "Social Media", "Email", "Referral"]

    hbar_chart = generate_horizontal_bar_chart(
        data=hbar_data,
        labels=hbar_labels,
        title="Traffic Sources",
        width=chart_width,
        height=int(chart_height * 0.7),
    )
    send_image_data(hbar_chart, format="png")
    move_cursor_down(2)
    input("  Press Enter to continue...")

    # 6c. Scatter plot
    print("\033[1m\n⚡ Scatter Plot\033[0m\n")
    move_cursor_down(1)

    scatter_x = [10, 20, 30, 40, 50, 60, 70, 80]
    scatter_y = [15, 25, 35, 45, 55, 65, 75, 85]
    scatter_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]

    scatter_chart = generate_scatter_plot(
        x_data=scatter_x,
        y_data=scatter_y,
        labels=scatter_labels,
        title="Correlation Analysis",
        width=chart_width,
        height=int(chart_height * 0.6),
        color="#E91E63",
    )
    send_image_data(scatter_chart, format="png")
    move_cursor_down(2)
    input("  Press Enter to continue...")

    # 6d. Time series
    print("\033[1m\n📉 Time Series Chart\033[0m\n")
    move_cursor_down(1)

    ts_data = [1200, 1350, 1100, 1450, 1600, 1400, 1847, 1920, 2100, 1950]
    ts_timestamps = [f"2025-04-{i+1:02d}" for i in range(10)]

    ts_chart = generate_time_series_chart(
        timestamps=ts_timestamps,
        data=ts_data,
        title="Daily Pageviews",
        width=chart_width,
        height=int(chart_height * 0.6),
        color="#4CAF50",
    )
    send_image_data(ts_chart, format="png")
    move_cursor_down(2)
    input("  Press Enter to continue...")


def test_heatmap():
    """Test heatmap chart."""
    print("\n" + "=" * 60)
    print(" TEST 7: Heatmap")
    print("=" * 60)
    print()
    print("\033[1m🔥 Activity Heatmap\033[0m\n")
    move_cursor_down(1)

    # Website traffic by day and hour
    heatmap_data = [
        [10, 15, 20, 25, 30, 35, 40, 35, 30, 25, 20, 15],
        [12, 18, 22, 28, 32, 38, 42, 38, 32, 28, 22, 18],
        [8, 12, 18, 22, 28, 32, 38, 32, 28, 22, 18, 12],
        [15, 20, 25, 30, 35, 40, 45, 40, 35, 30, 25, 20],
        [18, 22, 28, 32, 38, 42, 48, 42, 38, 32, 28, 22],
        [25, 30, 35, 40, 45, 50, 55, 50, 45, 40, 35, 30],
        [20, 25, 30, 35, 40, 45, 50, 45, 40, 35, 30, 25],
    ]

    row_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    col_labels = ["8am", "9am", "10am", "11am", "12pm", "1pm", "2pm", "3pm", "4pm", "5pm", "6pm", "7pm"]

    cols, rows = get_terminal_size()
    chart_width, chart_height = calculate_chart_dimensions(cols, rows, 0.8, 0.3)

    heatmap = generate_heatmap(
        data=heatmap_data,
        row_labels=row_labels,
        col_labels=col_labels,
        title="Website Traffic by Day & Hour",
        width=chart_width,
        height=int(chart_height * 0.8),
        cmap="YlOrRd",
    )
    send_image_data(heatmap, format="png")
    move_cursor_down(2)
    input("  Press Enter to continue...")


def test_stacked_bar():
    """Test stacked bar chart."""
    print("\n" + "=" * 60)
    print(" TEST 8: Stacked Bar Chart")
    print("=" * 60)
    print()
    print("\033[1m📊 Stacked Bar Chart\033[0m\n")
    move_cursor_down(1)

    # Traffic by source over weeks
    organic = [200, 220, 250, 280, 300, 320, 350]
    direct = [100, 110, 105, 120, 115, 130, 125]
    social = [50, 60, 70, 65, 80, 85, 90]
    email = [30, 35, 40, 45, 50, 55, 60]

    stacked_data = [organic, direct, social, email]
    stack_labels = ["Organic", "Direct", "Social", "Email"]
    week_labels = [f"Week {i+1}" for i in range(7)]

    cols, rows = get_terminal_size()
    chart_width, chart_height = calculate_chart_dimensions(cols, rows, 0.8, 0.25)

    stacked_chart = generate_stacked_bar_chart(
        data=stacked_data,
        labels=week_labels,
        stack_labels=stack_labels,
        title="Traffic by Source (Weekly)",
        width=chart_width,
        height=int(chart_height * 0.7),
    )
    send_image_data(stacked_chart, format="png")
    move_cursor_down(2)
    input("  Press Enter to continue...")


def test_table():
    """Test table image generation."""
    print("\n" + "=" * 60)
    print(" TEST 9: Table Image")
    print("=" * 60)
    print()
    print("\033[1m📋 Top Pages Table\033[0m\n")
    move_cursor_down(1)

    headers = ["Page", "Views", "Visitors", "Bounce Rate"]
    rows = [
        ["/home", "4,521", "3,241", "35%"],
        ["/blog/ai-trends", "2,105", "1,823", "42%"],
        ["/products", "1,847", "1,456", "38%"],
        ["/about", "1,234", "987", "55%"],
        ["/contact", "892", "756", "48%"],
    ]

    cols, rows = get_terminal_size()
    chart_width = int(cols * 0.7 * 8)
    chart_height = 250

    table = generate_table_image(
        headers=headers,
        rows=rows,
        title="Top Pages This Month",
        width=chart_width,
        height=chart_height,
    )
    send_image_data(table, format="png")
    move_cursor_down(2)
    input("  Press Enter to continue...")


def test_cursor_control():
    """Test cursor positioning."""
    print("\n" + "=" * 60)
    print(" TEST 10: Cursor Control")
    print("=" * 60)
    print()

    print("\033[1mTesting cursor save/restore...\033[0m")
    save_cursor_position()
    print("  Saved position")

    move_cursor_down(2)
    print("  Moved down 2 lines")

    restore_cursor_position()
    print("  Restored position")

    move_cursor_down(3)
    print()


def test_image_update():
    """Test updating images in place."""
    print("\n" + "=" * 60)
    print(" TEST 11: Image Update")
    print("=" * 60)
    print()

    img_id = 999

    print("\033[1mSending initial image...\033[0m")
    move_cursor_down(1)

    # Send first image
    img1 = create_gradient_image(300, 150)
    send_image_data(
        img1,
        format="png",
        image_id=img_id,
        width_cells=40,
        height_cells=20,
    )
    move_cursor_down(1)
    input("  Press Enter to update image...")

    # Update with different image
    print("\033[1mUpdating image...\033[0m")
    img2 = create_gradient_image(300, 150)
    # Modify the image slightly
    img_pil = Image.open(BytesIO(img2))
    draw = ImageDraw.Draw(img_pil)
    draw.rectangle([50, 50, 250, 100], fill="#4CAF50")
    buf = BytesIO()
    img_pil.save(buf, format="PNG")
    buf.seek(0)
    img2_updated = buf.read()

    update_image(img_id, img2_updated, format="png")
    move_cursor_down(2)
    print("✅ Image updated!")
    print()
    input("  Press Enter to continue...")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print(" 🎨 ENHANCED KITTY GRAPHICS TEST SUITE")
    print("=" * 60)
    print(f"\n Terminal: {'Interactive' if sys.stdin.isatty() else 'Not interactive'}")
    print(" Make sure you're running this in Ghostty/kitty/WezTerm")
    print()

    tests = [
        ("Terminal Detection", test_terminal_detection),
        ("Unicode Sparklines", test_unicode_sparklines),
        ("Progress Bars", test_progress_bars),
        ("Image Management", test_image_management),
        ("Basic Image Rendering", test_basic_image_rendering),
        ("New Chart Types", test_new_chart_types),
        ("Heatmap", test_heatmap),
        ("Stacked Bar", test_stacked_bar),
        ("Table", test_table),
        ("Cursor Control", test_cursor_control),
        ("Image Update", test_image_update),
    ]

    for name, test_func in tests:
        try:
            test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error in '{name}': {e}")
            import traceback
            traceback.print_exc()
            input("  Press Enter to continue...")

    print("\n" + "=" * 60)
    print(" ✅ All tests completed!")
    print("=" * 60)
    print()
    print("  💡 Tip: This works in Ghostty, kitty, and WezTerm terminals")
    print("  💡 Tip: Charts are PNG images sent via kitty graphics protocol")
    print("  💡 Tip: Sparklines work in ANY terminal with Unicode support")
    print()


if __name__ == "__main__":
    main()
