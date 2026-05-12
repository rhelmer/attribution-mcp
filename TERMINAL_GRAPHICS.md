# Terminal Graphics with Kitty Graphics Protocol

This project implements comprehensive terminal-based data visualization using the kitty graphics protocol, designed for Ghostty, kitty, and WezTerm terminals.

## 🎯 Features

### 1. **Kitty Graphics Protocol Support** (`libs/kitty_graphics.py`)

Enhanced terminal graphics with:
- **Image Management**: Automatic ID allocation and lifecycle management
- **Terminal Detection**: Automatic capability detection with fallback
- **Cursor Control**: Precise positioning for inline images
- **Chunked Transfer**: Support for large images with automatic chunking
- **Image Updates**: Update displayed images in-place without scrolling

**Key Functions:**
```python
# Send an image to the terminal
send_image_data(image_bytes, format="png", width_cells=50, height_cells=25)

# Update an existing image
update_image(image_id, new_image_bytes)

# Unicode sparklines for inline mini-charts
sparkline = get_unicode_sparkline([1,2,3,4,5], width=30)

# Text-based progress bars
bar = render_progress_bar(75, 100, width=40)
```

### 2. **Chart Types** (`libs/dashboard_charts.py`)

12+ chart types for analytics visualization:

| Chart Type | Function | Use Case |
|------------|----------|----------|
| Line Chart | `generate_line_chart()` | Trends over time |
| Area Chart | `generate_area_chart()` | Volume trends |
| Bar Chart | `generate_bar_chart()` | Category comparison |
| Horizontal Bar | `generate_horizontal_bar_chart()` | Long labels |
| Stacked Bar | `generate_stacked_bar_chart()` | Part-to-whole |
| Pie Chart | `generate_pie_chart()` | Distribution |
| Time Series | `generate_time_series_chart()` | Date-based data |
| Scatter Plot | `generate_scatter_plot()` | Correlations |
| Heatmap | `generate_heatmap()` | 2D patterns |
| Gauge | `generate_gauge()` | Metrics/KPIs |
| Sparkline | `generate_sparkline()` | Mini inline charts |
| Table | `generate_table_image()` | Structured data |
| Metrics Card | `generate_metrics_card()` | KPI dashboards |

### 3. **Analytics Renderer** (`libs/analytics_renderer.py`)

Bridges real MCP analytics data with terminal graphics:

```python
renderer = AnalyticsRenderer()

# Render dashboard with real data
await renderer.render_from_mcp(
    mcp_data,
    website_domain="example.com",
    date_range="2025-01-01 to 2025-12-31"
)

# Or demo mode
renderer.render_standalone_charts()
```

## 🚀 Usage

### Quick Start

```bash
# Demo mode (sample data)
uv run python run_dashboard.py

# Specific demo types
uv run python run_dashboard.py --demo minimal
uv run python run_dashboard.py --demo sparklines

# Real analytics data
uv run python run_dashboard.py \
  --start-date 2025-01-01 \
  --end-date 2025-12-31 \
  --website example.com
```

### Test Suite

```bash
# Run comprehensive test suite
uv run python test_enhanced_graphics.py

# Basic test (legacy)
uv run python test_graphics.py
```

### In Your Own Code

```python
from libs.kitty_graphics import send_image_data, get_unicode_sparkline
from libs.dashboard_charts import generate_line_chart

# Generate a chart
chart_bytes = generate_line_chart(
    data=[10, 20, 15, 25, 30],
    labels=["Mon", "Tue", "Wed", "Thu", "Fri"],
    title="Weekly Traffic"
)

# Send to terminal
send_image_data(chart_bytes, format="png", width_cells=60, height_cells=30)

# Or use unicode sparklines (works everywhere!)
sparkline = get_unicode_sparkline([10, 20, 15, 25, 30], width=30)
print(f"Traffic: {sparkline}")
```

## 📊 Terminal Compatibility

### Supported Terminals
- ✅ **Ghostty** - Full support
- ✅ **kitty** - Full support  
- ✅ **WezTerm** - Full support

### Fallback Behavior

For terminals without graphics support:
- Unicode sparklines still work (text-based)
- Progress bars render with Unicode block characters
- Text-only dashboard mode activates automatically
- Set `KITTY_GRAPHICS_FORCE=1` to override detection

### Detection Logic

```python
from libs.kitty_graphics import probe_support

if probe_support():
    # Use full graphics
    send_image_data(chart, format="png")
else:
    # Use text-based fallback
    print(get_unicode_sparkline(data))
```

## 🎨 Examples

### Unicode Sparklines

```python
from libs.kitty_graphics import get_unicode_sparkline

# Simple trend
data = [10, 20, 15, 25, 30, 28, 35]
sparkline = get_unicode_sparkline(data, width=30)
print(f"Revenue: {sparkline}")
# Output: Revenue:  ▁▂▄▃▅▄█

# Multiple metrics
metrics = [
    ("Pageviews", [1200, 1350, 1100, 1450, 1600]),
    ("Visitors", [400, 450, 380, 520, 580]),
]
for name, data in metrics:
    print(f"{name:15s} {get_unicode_sparkline(data, width=35)}")
```

### Progress Bars

```python
from libs.kitty_graphics import render_progress_bar

print(render_progress_bar(67, 100, width=40))
# Output: [██████████████████████████░░░░░░░░░░░░░░] 67%

print(render_progress_bar(7847, 10000, width=40))
# Output: [███████████████████████████████░░░░░░░░░] 78%
```

### Full Dashboard

```python
from libs.analytics_renderer import AnalyticsRenderer

renderer = AnalyticsRenderer()
renderer.render_standalone_charts()
```

This renders:
1. Key metrics with colored text
2. Line chart (PNG via kitty protocol)
3. Bar chart with sparklines
4. Gauges for system metrics
5. Unicode progress bars

### Real Analytics Data

```python
from run import AnalyticsDashboard
from libs.analytics_renderer import AnalyticsRenderer

# Get real data
dashboard = AnalyticsDashboard("packages/umami-mcp/src/umami_mcp")

async with stdio_client(dashboard.server_params) as (read, write):
    async with ClientSession(read, write) as session:
        data = await dashboard.get_real_data_from_mcp(
            session, "example.com", "2025-01-01", "2025-12-31"
        )
        
        # Render dashboard
        renderer = AnalyticsRenderer()
        await renderer.render_from_mcp(data, "example.com", "Jan-Dec 2025")
```

## 🔧 Architecture

```
┌─────────────────────────────────────────────────────┐
│              Terminal Dashboard                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐    ┌──────────────────────┐      │
│  │ run_dashboard│───▶│ AnalyticsRenderer    │      │
│  │   .py        │    │                      │      │
│  └──────────────┘    └──────────┬───────────┘      │
│                                 │                   │
│              ┌──────────────────┼──────────────┐   │
│              │                  │               │   │
│              ▼                  ▼               ▼   │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────┐│
│  │dashboard_charts  │  │kitty_graphics│  │ MCP    ││
│  │  .py             │  │  .py         │  │ Data   ││
│  │                  │  │              │  │        ││
│  │ • Line charts    │  │ • send_image │  │ Umami  ││
│  │ • Bar charts     │  │ • sparklines │  │ GSC    ││
│  │ • Heatmaps       │  │ • progress   │  │ YouTube││
│  │ • Tables         │  │ • cursor ctrl│  │ Social ││
│  └──────────────────┘  └──────────────┘  └────────┘│
│                                                      │
└─────────────────────────────────────────────────────┘
```

## 📝 API Reference

### kitty_graphics.py

| Function | Description | Parameters |
|----------|-------------|------------|
| `send_image_data()` | Send image to terminal | image_data, format, width_cells, height_cells, image_id |
| `update_image()` | Update existing image | image_id, image_data, format |
| `delete_image()` | Remove image | image_id, all |
| `get_unicode_sparkline()` | Text sparkline | data, width |
| `render_progress_bar()` | Text progress bar | value, max_value, width |
| `probe_support()` | Detect terminal support | - |
| `get_terminal_size()` | Get terminal dimensions | - |
| `calculate_chart_dimensions()` | Auto-size charts | terminal_cols, terminal_rows, width_pct, height_pct |
| `move_cursor_down()` | Move cursor | lines |
| `move_cursor_to()` | Position cursor | row, col |
| `save_cursor_position()` | Save cursor | - |
| `restore_cursor_position()` | Restore cursor | - |

### dashboard_charts.py

| Function | Description | Key Parameters |
|----------|-------------|----------------|
| `generate_line_chart()` | Line chart | data, labels, title, width, height, color |
| `generate_area_chart()` | Filled area chart | data, labels, title, color, alpha |
| `generate_bar_chart()` | Vertical bars | data, labels, title, colors |
| `generate_horizontal_bar_chart()` | Horizontal bars | data, labels, title, color |
| `generate_stacked_bar_chart()` | Stacked bars | data, labels, stack_labels, colors |
| `generate_pie_chart()` | Pie/donut chart | data, labels, title, colors |
| `generate_time_series_chart()` | Time-based line | timestamps, data, title, color |
| `generate_scatter_plot()` | Scatter plot | x_data, y_data, labels, title, color, size |
| `generate_heatmap()` | 2D heatmap | data, row_labels, col_labels, title, cmap |
| `generate_gauge()` | Progress gauge | value, max_value, title, color |
| `generate_sparkline()` | Mini sparkline | data, width, height, color |
| `generate_metrics_card()` | KPI card | metrics, title, width, height |
| `generate_table_image()` | Styled table | headers, rows, title, width, height |

## 🎯 Best Practices

### 1. Always Detect Terminal First

```python
from libs.kitty_graphics import probe_support

has_graphics = probe_support()
if has_graphics:
    send_image_data(chart, format="png")
else:
    print(get_unicode_sparkline(data))
```

### 2. Size Charts Appropriately

```python
cols, rows = get_terminal_size()
chart_width, chart_height = calculate_chart_dimensions(
    cols, rows,
    width_pct=0.8,  # 80% of terminal width
    height_pct=0.25  # 25% of terminal height
)
```

### 3. Use Image IDs for Updates

```python
from libs.kitty_graphics import ImageManager

manager = ImageManager()
img_id = manager.allocate_id()

# Send initial image
send_image_data(chart1, format="png", image_id=img_id)

# Update in place (no scrolling)
update_image(img_id, chart2, format="png")
```

### 4. Provide Fallbacks

```python
try:
    chart = generate_line_chart(data, labels, title)
    send_image_data(chart, format="png")
except Exception as e:
    # Fallback to text
    sparkline = get_unicode_sparkline(data, width=30)
    print(f"{title}: {sparkline}")
```

## 🐛 Troubleshooting

### Charts Not Showing

**Problem**: Images not rendering in terminal

**Solutions**:
1. Verify terminal support: `echo $TERM` (should contain "kitty", "ghostty", or "wezterm")
2. Force graphics: `KITTY_GRAPHICS_FORCE=1 uv run python run_dashboard.py`
3. Check image size - too large may fail: use `calculate_chart_dimensions()`
4. Ensure PNG data is valid: `len(image_bytes) > 0`

### Sparklines Not Aligned

**Problem**: Unicode sparklines appear jagged

**Solutions**:
1. Use monospace font in terminal
2. Ensure consistent width: `get_unicode_sparkline(data, width=30)`
3. Pad labels to same length

### Real Data Not Loading

**Problem**: MCP server connection fails

**Solutions**:
1. Check `.env` file has required credentials
2. Test MCP server independently: `uv run packages/umami-mcp/src/umami_mcp/multi_platform_server.py`
3. Verify website domain exists in your analytics
4. Check date format: YYYY-MM-DD

## 📚 Resources

- [Kitty Graphics Protocol Spec](https://sw.kovidgoyal.net/kitty/graphics-protocol/)
- [Ghostty Documentation](https://ghostty.org/docs)
- [WezTerm Graphics](https://wezfurlong.org/wezterm/graphics.html)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 🚀 Future Enhancements

- [ ] Animated charts (gif sequences)
- [ ] Interactive chart selection
- [ ] Real-time data streaming
- [ ] Custom color themes
- [ ] Export charts to files
- [ ] More chart types (radar, polar, etc.)
- [ ] Automatic dashboard layout optimization

## 💡 Tips

1. **Unicode sparklines work everywhere** - great for inline text
2. **Use progress bars for text-only mode** - no graphics needed
3. **Auto-size charts** - `calculate_chart_dimensions()` adapts to terminal
4. **Image IDs enable updates** - avoid scrolling with `update_image()`
5. **Chunked transfer** - large images sent automatically in chunks

---

**Happy charting! 📊✨**
