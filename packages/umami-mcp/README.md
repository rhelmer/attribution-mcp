# Umami MCP Server

A zero-dependency [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for [Umami Analytics](https://umami.is/). Works with both Umami Cloud and self-hosted instances.

## Features

- 🔒 **Zero dependencies** - Uses only Python standard library
- ☁️ **Cloud & Self-hosted** - Supports both Umami Cloud and self-hosted instances
- 🔐 **Flexible auth** - API key authentication for cloud, username/password for self-hosted
- 🛠️ **Full API coverage** - Access all major Umami analytics endpoints
- 🚀 **Easy setup** - Install and run with `uvx`

## Installation

### Prerequisites

Install [`uv`](https://docs.astral.sh/uv/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UMAMI_URL` | Optional | Base URL — defaults to `https://api.umami.is` for cloud mode |
| `UMAMI_API_KEY` | Cloud | API key from Umami Cloud dashboard |
| `UMAMI_USERNAME` | Self-hosted | Login username |
| `UMAMI_PASSWORD` | Self-hosted | Login password |

**Note:** Set either `UMAMI_API_KEY` (cloud) or both `UMAMI_USERNAME` + `UMAMI_PASSWORD` (self-hosted). The server auto-detects which mode to use.

### MCP Client Configuration

#### Claude Desktop / Claude Code

Add to your MCP config (`~/.claude.json` or Claude Desktop settings):

**For Umami Cloud:**
```json
{
  "mcpServers": {
    "umami": {
      "command": "uvx",
      "args": ["umami-mcp", "--from", "git+https://github.com/YOUR_USERNAME/umami-mcp-llm-report@main"],
      "env": {
        "UMAMI_URL": "https://api.umami.is",
        "UMAMI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**For Self-hosted:**
```json
{
  "mcpServers": {
    "umami": {
      "command": "uvx",
      "args": ["umami-mcp", "--from", "git+https://github.com/YOUR_USERNAME/umami-mcp-llm-report@main"],
      "env": {
        "UMAMI_URL": "https://your-umami-instance.com",
        "UMAMI_USERNAME": "admin",
        "UMAMI_PASSWORD": "your_password"
      }
    }
  }
}
```

#### Local Development

When running locally with this project:

```json
{
  "mcpServers": {
    "umami": {
      "command": "uv",
      "args": ["--directory", "/path/to/umami-mcp-llm-report", "run", "umami-mcp"],
      "env": {
        "UMAMI_URL": "https://your-umami-instance.com",
        "UMAMI_USERNAME": "admin",
        "UMAMI_PASSWORD": "your_password"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_websites` | List all websites being tracked |
| `get_stats` | Get summary statistics (pageviews, visitors, bounces, avg. visit duration) |
| `get_pageviews` | Get pageview data with optional filters for URL or referrer |
| `get_metrics` | Get metrics breakdown by type (url, referrer, browser, os, device, country, language, event) |
| `get_active_visitors` | Get number of currently active visitors (last 5 minutes) |
| `get_realtime_data` | Get realtime analytics data for specified duration |

## Usage Examples

Once connected to an MCP client, you can ask:

- "What are my top pages this week?"
- "Show me visitor trends for the last 30 days"
- "Which countries are my visitors from?"
- "How many people are on my site right now?"
- "Compare this month's traffic to last month"
- "What are the top referrers to my site?"

## Getting Your Credentials

### Umami Cloud

1. Go to **Settings → API Keys** in your Umami Cloud dashboard
2. Create a new API key
3. Copy the key to use in your configuration

### Self-hosted

Use the same username and password you use to log in to your Umami instance.

## Development

### Running Locally

```bash
# Set environment variables
export UMAMI_URL=https://your-umami-instance.com
export UMAMI_USERNAME=admin
export UMAMI_PASSWORD=your_password

# Run the server
uv run umami-mcp
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run umami-mcp
```

## How It Works

The server implements the Model Context Protocol over stdio using JSON-RPC (one JSON object per line). When an MCP client starts it:

1. The server reads environment variables for configuration
2. Authenticates with the Umami API (auto-detects cloud vs self-hosted)
3. Handles `initialize`, `tools/list`, and `tools/call` methods
4. Makes authenticated HTTP requests to the Umami API
5. Returns results as JSON text content

No background processes, no polling, no state beyond the auth token.

## License

MIT
