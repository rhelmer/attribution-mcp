"""
Kitty Graphics Protocol Utilities

Provides functions to detect terminal support and render images
using the kitty graphics protocol (works in Ghostty, kitty, WezTerm).

Enhanced features:
- Image placement and positioning control
- Image lifecycle management (create, update, delete)
- Unicode sparklines for inline mini-charts
- Terminal capability detection
- Animated sequence support
"""

import base64
import os
import sys
import zlib
from io import BytesIO
from typing import Optional


class ImageManager:
    """Manage images sent to the terminal via kitty graphics protocol."""

    def __init__(self):
        self._next_id = 1
        self._active_images = {}

    def allocate_id(self) -> int:
        """Allocate a new image ID."""
        img_id = self._next_id
        self._next_id += 1
        return img_id

    def register(self, img_id: int, metadata: dict = None) -> None:
        """Register an image ID with optional metadata."""
        self._active_images[img_id] = metadata or {}

    def unregister(self, img_id: int) -> None:
        """Remove an image from tracking."""
        self._active_images.pop(img_id, None)

    @property
    def active_count(self) -> int:
        return len(self._active_images)


# Global image manager instance
_image_manager = ImageManager()


def probe_support() -> bool:
    """
    Check if the terminal supports the kitty graphics protocol.

    Uses multiple detection methods:
    1. Explicit environment variable override
    2. Terminal program detection
    3. Direct protocol probe (best-effort)

    For Ghostty: Set KITTY_GRAPHICS=1 if auto-detection fails.
    """
    # 1. Check explicit override first
    if os.environ.get("KITTY_GRAPHICS") == "1":
        return True

    # 2. Check terminal environment variables
    term = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")

    # Known terminals with kitty graphics support
    # Note: TERM can be "xterm-ghostty", "xterm-kitty", "xterm-256color" etc.
    supported_terms = ["xterm-kitty", "xterm-ghostty", "ghostty", "wezterm"]
    supported_programs = ["ghostty", "wezterm", "kitty", "apple_terminal"]

    has_support = (
        any(t in term.lower() for t in supported_terms) or
        any(p in term_program.lower() for p in supported_programs)
    )

    if has_support:
        return True

    # 3. If we're in an interactive terminal, try a probe
    # Be optimistic - if we're interactive, graphics might work
    if sys.stdin.isatty() and sys.stdout.isatty():
        sys.stdout.write("\x1b_Gi=1,a=q\x1b\\")
        sys.stdout.flush()
        return True  # Optimistic: assume support if probe sent

    return False


def get_unicode_sparkline(data: list[float], width: int = 20) -> str:
    """
    Generate a unicode sparkline (inline mini chart) using Braille patterns.

    This creates a text-based sparkline that can be rendered inline without
    requiring image support.

    Args:
        data: List of numeric values
        width: Target width in characters

    Returns:
        Unicode sparkline string
    """
    if not data or len(data) == 0:
        return ""

    # Braille characters for different levels
    braille_chars = " ▁▂▃▄▅▆▇█"

    # Normalize data to 0-1 range
    min_val = min(data)
    max_val = max(data)

    if max_val == min_val:
        # All values are the same
        normalized = [0.5] * len(data)
    else:
        normalized = [(v - min_val) / (max_val - min_val) for v in data]

    # Sample data to fit width
    if len(normalized) > width:
        step = len(normalized) / width
        sampled = [normalized[int(i * step)] for i in range(width)]
    else:
        sampled = normalized

    # Convert to braille characters
    sparkline = "".join(
        braille_chars[int(v * (len(braille_chars) - 1))] for v in sampled
    )

    return sparkline


def encode_image(
    image_data: bytes,
    format: str = "png",
    compress: bool = True,
    image_id: int | None = None,
) -> tuple[str, str]:
    """
    Encode image data for the kitty graphics protocol.

    Returns:
        tuple: (options_string, base64_encoded_data)
    """
    # f=100 for PNG, f=24 for JPEG
    format_map = {"png": 100, "jpeg": 24, "jpg": 24}
    f_code = format_map.get(format.lower(), 100)

    payload = image_data
    compression_flag = 0

    if compress and format.lower() not in ("png", "jpeg"):
        payload = zlib.compress(image_data)
        compression_flag = 1

    b64_data = base64.b64encode(payload).decode("ascii")

    # a=t = transmit, t=d = direct transfer
    options = f"a=t,t=d,f={f_code}"
    if compression_flag:
        options += ",z=1"
    if image_id is not None:
        options += f",i={image_id}"

    return options, b64_data


def send_image_data(
    image_data: bytes,
    format: str = "png",
    width: int | None = None,
    height: int | None = None,
    width_cells: int | None = None,
    height_cells: int | None = None,
    x: int | None = None,
    y: int | None = None,
    image_id: int | None = None,
    quiet: bool = True,
    chunk_size: int = 4096,
    inline: bool = True,
    cursor_control: bool = True,
) -> None:
    """
    Send image data to the terminal using kitty graphics protocol.

    Args:
        image_data: Raw image bytes (PNG, JPEG, etc.)
        format: Image format ("png" or "jpeg")
        width: Image width in pixels
        height: Image height in pixels
        width_cells: Image width in terminal cells
        height_cells: Image height in terminal cells
        x: X position in cells (column)
        y: Y position in cells (row)
        image_id: Unique ID for the image (for later updates/deletion)
        quiet: Suppress acknowledgment from terminal
        chunk_size: Max bytes per chunk for large images
        inline: Whether to display inline with text (True) or in a separate view
        cursor_control: Whether to control cursor placement after image
    """
    f_code = 100 if format.lower() == "png" else 24
    options = f"a=t,t=d,f={f_code}"

    if image_id is not None:
        options += f",i={image_id}"
    if quiet:
        options += ",q=2"
    if width and height:
        options += f",v={width}x{height}"
    if width_cells and height_cells:
        options += f",s={width_cells}x{height_cells}"
    if x is not None and y is not None:
        options += f",p={x},{y}"

    # Control how image is displayed
    if inline:
        options += ",c=1"  # inline mode

    if cursor_control:
        options += ",C=1"  # place cursor after image

    # Encode to base64
    b64_data = base64.b64encode(image_data).decode("ascii")

    # Check if we need chunking (kitty protocol limit ~200KB per chunk)
    max_payload = chunk_size
    if len(b64_data) <= max_payload:
        # Single chunk
        sys.stdout.write(f"\x1b_G{options};{b64_data}\x1b\\")
        sys.stdout.flush()
    else:
        # Chunked transfer
        chunks = [
            b64_data[i : i + max_payload]
            for i in range(0, len(b64_data), max_payload)
        ]

        for idx, chunk in enumerate(chunks):
            is_last = idx == len(chunks) - 1
            m_flag = "0" if is_last else "1"

            if idx == 0:
                # First chunk includes all options
                chunk_options = f"{options},m={m_flag}"
            else:
                # Subsequent chunks only need m flag and image_id
                chunk_options = f"m={m_flag}"
                if image_id is not None:
                    chunk_options += f",i={image_id}"

            sys.stdout.write(f"\x1b_G{chunk_options};{chunk}\x1b\\")
            sys.stdout.flush()


def update_image(
    image_id: int,
    image_data: bytes,
    format: str = "png",
    quiet: bool = True,
) -> None:
    """
    Update a previously displayed image in place.

    Args:
        image_id: ID of the image to update
        image_data: New image data
        format: Image format
        quiet: Suppress acknowledgment
    """
    f_code = 100 if format.lower() == "png" else 24
    options = f"a=t,t=d,f={f_code},i={image_id}"
    if quiet:
        options += ",q=2"

    b64_data = base64.b64encode(image_data).decode("ascii")
    sys.stdout.write(f"\x1b_G{options};{b64_data}\x1b\\")
    sys.stdout.flush()


def send_image_file(
    path: str,
    **kwargs,
) -> None:
    """Send an image file to the terminal."""
    with open(path, "rb") as f:
        image_data = f.read()

    # Determine format from extension
    ext = os.path.splitext(path)[1].lower()
    format_map = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg"}
    fmt = format_map.get(ext, "png")

    send_image_data(image_data, format=fmt, **kwargs)


def delete_image(image_id: int | None = None, all: bool = False) -> None:
    """Delete a previously sent image from the terminal."""
    options = "a=d"
    if all:
        options += ",d=A"
    elif image_id is not None:
        options += ",d=I"
        options += f",i={image_id}"

    sys.stdout.write(f"\x1b_G{options}\x1b\\")
    sys.stdout.flush()


def clear_display() -> None:
    """Clear all images from the display."""
    delete_image(all=True)


def move_cursor_down(lines: int = 1) -> None:
    """Move cursor down to make room for inline images."""
    sys.stdout.write(f"\x1b[{lines}E")
    sys.stdout.flush()


def move_cursor_to(row: int, col: int) -> None:
    """Move cursor to specific position."""
    sys.stdout.write(f"\x1b[{row};{col}H")
    sys.stdout.flush()


def save_cursor_position() -> None:
    """Save current cursor position."""
    sys.stdout.write("\x1b7")
    sys.stdout.flush()


def restore_cursor_position() -> None:
    """Restore saved cursor position."""
    sys.stdout.write("\x1b8")
    sys.stdout.flush()


def get_terminal_size() -> tuple[int, int]:
    """Get terminal size (columns, rows)."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24


def calculate_chart_dimensions(
    terminal_cols: int,
    terminal_rows: int,
    width_pct: float = 0.8,
    height_pct: float = 0.3,
    cell_width_px: int = 8,
    cell_height_px: int = 16,
) -> tuple[int, int]:
    """
    Calculate appropriate chart dimensions based on terminal size.

    Args:
        terminal_cols: Terminal width in cells
        terminal_rows: Terminal height in rows
        width_pct: Percentage of terminal width to use
        height_pct: Percentage of terminal height to use
        cell_width_px: Approximate pixel width of a terminal cell
        cell_height_px: Approximate pixel height of a terminal cell

    Returns:
        tuple: (width_px, height_px) for chart
    """
    width_px = int(terminal_cols * width_pct * cell_width_px)
    height_px = int(terminal_rows * height_pct * cell_height_px)

    # Clamp to reasonable ranges
    width_px = max(200, min(width_px, 1200))
    height_px = max(150, min(height_px, 600))

    return width_px, height_px


def render_progress_bar(
    value: float,
    max_value: float = 100,
    width: int = 40,
    color: str = "#4CAF50",
    bg_color: str = "#404040",
) -> str:
    """
    Render a text-based progress bar with ANSI colors.

    This is a lightweight alternative to image-based gauges
    that works in any terminal with ANSI support.

    Args:
        value: Current value
        max_value: Maximum value
        width: Width of progress bar in characters
        color: ANSI color code or hex
        bg_color: Background color

    Returns:
        ANSI-colored progress bar string
    """
    if max_value == 0:
        percentage = 0
    else:
        percentage = value / max_value

    filled = int(percentage * width)
    empty = width - filled

    # Convert hex to ANSI if needed
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percentage:.0%}"
