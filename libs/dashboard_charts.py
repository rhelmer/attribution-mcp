"""
Dashboard Chart Generator

Generates dashboard-style charts and gauges as PNG images
using matplotlib and Pillow, ready for terminal rendering.
"""

import io
from datetime import datetime, timedelta

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont

# Use non-interactive backend for headless rendering
matplotlib.use("Agg")


def _fig_to_png_bytes(fig, dpi: int = 100, transparent: bool = False) -> bytes:
    """Convert a matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        transparent=transparent,
    )
    buf.seek(0)
    png_bytes = buf.read()
    plt.close(fig)
    return png_bytes


def generate_line_chart(
    data: list[float],
    labels: list[str] | None = None,
    title: str = "Trend",
    width: int = 600,
    height: int = 300,
    color: str = "#4CAF50",
    fill: bool = True,
) -> bytes:
    """Generate a line chart image."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    x = range(len(data))
    ax.plot(x, data, color=color, linewidth=2, marker="o", markersize=4)

    if fill:
        ax.fill_between(x, data, alpha=0.2, color=color)

    if labels:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_bar_chart(
    data: list[float],
    labels: list[str] | None = None,
    title: str = "Comparison",
    width: int = 600,
    height: int = 300,
    colors: list[str] | None = None,
) -> bytes:
    """Generate a bar chart image."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    if colors is None:
        colors = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0"]
        colors = (colors * (len(data) // len(colors) + 1))[: len(data)]

    x = range(len(data))
    bars = ax.bar(x, data, color=colors, edgecolor="white", linewidth=0.5)

    # Add value labels on bars
    for bar, value in zip(bars, data):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(data) * 0.02,
            f"{value:.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    if labels:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    else:
        ax.set_xticks(x)
        ax.set_xticklabels([f"Item {i+1}" for i in x])

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_axisbelow(True)
    ax.grid(True, axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_pie_chart(
    data: list[float],
    labels: list[str] | None = None,
    title: str = "Distribution",
    width: int = 500,
    height: int = 300,
    colors: list[str] | None = None,
) -> bytes:
    """Generate a pie/donut chart image."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    if colors is None:
        colors = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4"]

    if labels is None:
        labels = [f"Item {i+1}" for i in range(len(data))]

    wedges, texts, autotexts = ax.pie(
        data,
        labels=labels,
        colors=colors[: len(data)],
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 10},
    )

    # Make percentage text bold and white
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_gauge(
    value: float,
    max_value: float = 100,
    title: str = "Gauge",
    width: int = 300,
    height: int = 200,
    color: str = "#4CAF50",
    warning_threshold: float = 0.7,
    danger_threshold: float = 0.9,
) -> bytes:
    """Generate a gauge/meter image."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    percentage = value / max_value

    # Determine color based on thresholds
    if percentage >= danger_threshold:
        bar_color = "#E91E63"
    elif percentage >= warning_threshold:
        bar_color = "#FF9800"
    else:
        bar_color = color

    # Create horizontal bar gauge
    ax.barh(
        [0],
        [max_value],
        height=0.3,
        color="#E0E0E0",
        edgecolor="none",
    )
    ax.barh([0], [value], height=0.3, color=bar_color, edgecolor="none")

    # Add value text
    ax.text(
        max_value * 0.5,
        0,
        f"{value:.0f}/{max_value:.0f} ({percentage:.0%})",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlim(0, max_value)
    ax.set_axis_off()

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_metrics_card(
    metrics: list[tuple[str, str, str]],
    title: str = "Key Metrics",
    width: int = 600,
    height: int = 200,
) -> bytes:
    """
    Generate a metrics card image using Pillow.

    metrics: list of (label, value, color) tuples
    """
    img = Image.new("RGB", (width, height), "#1E1E1E")
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fallback to default if not available
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        font_value = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except (IOError, OSError):
        font_title = ImageFont.load_default()
        font_label = font_title
        font_value = font_title

    # Title
    draw.text((20, 15), title, fill="#FFFFFF", font=font_title)

    # Divider line
    draw.line([(20, 45), (width - 20, 45)], fill="#404040", width=2)

    # Metrics
    num_metrics = len(metrics)
    spacing = width // num_metrics

    for i, (label, value, color) in enumerate(metrics):
        x = spacing * i + spacing // 2

        # Value
        draw.text(
            (x, 65),
            value,
            fill=color,
            font=font_value,
            anchor="mt",
        )

        # Label
        draw.text(
            (x, 110),
            label,
            fill="#B0B0B0",
            font=font_label,
            anchor="mt",
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def generate_sparkline(
    data: list[float],
    width: int = 200,
    height: int = 60,
    color: str = "#4CAF50",
) -> bytes:
    """Generate a mini sparkline image."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    ax.plot(data, color=color, linewidth=2)
    ax.fill_between(range(len(data)), data, alpha=0.3, color=color)

    # Hide everything except the line
    ax.set_axis_off()
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    plt.tight_layout(pad=0)
    return _fig_to_png_bytes(fig, transparent=True)


def generate_area_chart(
    data: list[float],
    labels: list[str] | None = None,
    title: str = "Area Trend",
    width: int = 600,
    height: int = 300,
    color: str = "#4CAF50",
    alpha: float = 0.3,
) -> bytes:
    """Generate an area chart (filled line chart)."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    x = range(len(data))
    ax.fill_between(x, data, alpha=alpha, color=color)
    ax.plot(x, data, color=color, linewidth=2, marker="o", markersize=4)

    if labels:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_heatmap(
    data: list[list[float]],
    row_labels: list[str] | None = None,
    col_labels: list[str] | None = None,
    title: str = "Heatmap",
    width: int = 600,
    height: int = 400,
    cmap: str = "YlOrRd",
) -> bytes:
    """
    Generate a heatmap image.

    Args:
        data: 2D array of values
        row_labels: Labels for rows
        col_labels: Labels for columns
        title: Chart title
        width: Image width in pixels
        height: Image height in pixels
        cmap: Colormap name
    """
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    im = ax.imshow(data, cmap=cmap, aspect="auto")

    # Add labels
    if col_labels:
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=45, ha="right")

    if row_labels:
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)

    # Add text annotations
    for i in range(len(data)):
        for j in range(len(data[i])):
            text_color = "white" if data[i][j] > max(max(row) for row in data) * 0.6 else "black"
            ax.text(j, i, f"{data[i][j]:.0f}", ha="center", va="center",
                   color=text_color, fontsize=8, fontweight="bold")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    fig.colorbar(im, ax=ax)
    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_scatter_plot(
    x_data: list[float],
    y_data: list[float],
    labels: list[str] | None = None,
    title: str = "Scatter Plot",
    width: int = 600,
    height: int = 400,
    color: str = "#4CAF50",
    size: float = 50,
) -> bytes:
    """
    Generate a scatter plot.

    Args:
        x_data: X coordinates
        y_data: Y coordinates
        labels: Optional labels for points
        title: Chart title
        width: Image width
        height: Image height
        color: Point color
        size: Point size
    """
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    scatter = ax.scatter(x_data, y_data, c=color, s=size, alpha=0.6, edgecolors="white")

    # Add labels if provided
    if labels:
        for i, label in enumerate(labels):
            ax.annotate(label, (x_data[i], y_data[i]),
                       textcoords="offset points", xytext=(0, 10),
                       ha="center", fontsize=8)

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_horizontal_bar_chart(
    data: list[float],
    labels: list[str] | None = None,
    title: str = "Horizontal Bar Chart",
    width: int = 600,
    height: int = 300,
    color: str = "#4CAF50",
) -> bytes:
    """Generate a horizontal bar chart."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    if labels is None:
        labels = [f"Item {i+1}" for i in range(len(data))]

    y_pos = range(len(data))
    bars = ax.barh(y_pos, data, color=color, edgecolor="white")

    # Add value labels
    for bar, value in zip(bars, data):
        ax.text(
            bar.get_width() + max(data) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.0f}",
            ha="left",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_axisbelow(True)
    ax.grid(True, axis="x", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_stacked_bar_chart(
    data: list[list[float]],
    labels: list[str] | None = None,
    stack_labels: list[str] | None = None,
    title: str = "Stacked Bar Chart",
    width: int = 600,
    height: int = 350,
    colors: list[str] | None = None,
) -> bytes:
    """
    Generate a stacked bar chart.

    Args:
        data: List of lists, where each inner list is a stack
        labels: X-axis labels
        stack_labels: Legend labels for stacks
        title: Chart title
        width: Image width
        height: Image height
        colors: Colors for each stack
    """
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    if colors is None:
        colors = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0"]

    num_stacks = len(data)
    num_bars = len(data[0])
    x = range(num_bars)

    bottom = [0] * num_bars
    for i, (stack_data, color) in enumerate(zip(data, colors)):
        bars = ax.bar(x, stack_data, bottom=bottom, color=color,
                     edgecolor="white", linewidth=0.5,
                     label=stack_labels[i] if stack_labels else f"Stack {i+1}")
        bottom = [b + s for b, s in zip(bottom, stack_data)]

    if labels:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_time_series_chart(
    timestamps: list[str],
    data: list[float],
    title: str = "Time Series",
    width: int = 600,
    height: int = 300,
    color: str = "#2196F3",
    fill: bool = True,
) -> bytes:
    """
    Generate a time series chart with formatted date labels.

    Args:
        timestamps: List of date strings (YYYY-MM-DD)
        data: Values for each timestamp
        title: Chart title
        width: Image width
        height: Image height
        color: Line color
        fill: Whether to fill under the line
    """
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)

    x = range(len(data))
    ax.plot(x, data, color=color, linewidth=2, marker="o", markersize=4)

    if fill:
        ax.fill_between(x, data, alpha=0.2, color=color)

    # Format timestamps - show fewer labels if there are many
    if len(timestamps) > 15:
        step = len(timestamps) // 15
        tick_positions = x[::step]
        tick_labels = timestamps[::step]
    else:
        tick_positions = x
        tick_labels = timestamps

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_table_image(
    headers: list[str],
    rows: list[list[str]],
    title: str = "Table",
    width: int = 600,
    height: int = 300,
    col_widths: list[float] | None = None,
) -> bytes:
    """
    Generate a styled table image.

    Args:
        headers: Column headers
        rows: Table rows
        title: Table title
        width: Image width
        height: Image height
        col_widths: Relative column widths
    """
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    ax.set_axis_off()

    # Create table
    table_data = [headers] + rows
    table = ax.table(
        cellText=table_data,
        loc="center",
        cellLoc="center",
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    # Style header row
    for col, header in enumerate(headers):
        cell = table[0, col]
        cell.set_facecolor("#4CAF50")
        cell.set_text_props(color="white", fontweight="bold")

    # Style data rows with alternating colors
    for row_idx in range(1, len(table_data)):
        for col_idx in range(len(headers)):
            cell = table[row_idx, col_idx]
            if row_idx % 2 == 0:
                cell.set_facecolor("#F5F5F5")
            else:
                cell.set_facecolor("white")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=20)
    plt.tight_layout()
    return _fig_to_png_bytes(fig)


def generate_dashboard_layout(
    charts: list[tuple[bytes, int, int]],
    terminal_cols: int,
    terminal_rows: int,
) -> bytes:
    """
    Generate a full dashboard layout combining multiple chart images.

    charts: list of (image_bytes, width_cells, height_cells)
    """
    # For now, this is a placeholder - in a full implementation
    # you'd composite images together using Pillow
    # For the prototype, we'll render charts sequentially
    return charts[0][0] if charts else b""
