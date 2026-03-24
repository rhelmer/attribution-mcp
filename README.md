# Multi-Platform Analytics MCP

A unified analytics platform that aggregates data from multiple sources using the Model Context Protocol (MCP) with Ollama, Cloudflare Workers, or Google Gemini to generate intelligent cross-platform insights.

Blog post: https://www.rhelmer.org/blog/simplifying-ai-analytics-zero-dependency-umami-reports/

## Overview

This project combines multiple analytics platforms into a unified interface for AI-powered analysis:

- **MCP Client**: Direct use of the Model Context Protocol for orchestrating AI interactions
- **Ollama/Cloudflare Workers/Google Gemini**: LLM inference backends
- **Multi-Platform Connectors**: Unified data access from 7+ platforms
- **Automated Reporting**: Generates comprehensive cross-platform analytics reports using AI

## Features

- 🤖 **AI-Powered Analysis**: Uses large language models to analyze multi-platform analytics data
- 📊 **Unified Dashboard**: Aggregate data from web analytics, search, social media, and video
- 🔌 **Multi-Platform Support**: Connect to Umami, GSC, YouTube, Mastodon, Bluesky, LinkedIn, Instagram
- 🔄 **Flexible Backends**: Choose between local Ollama, Cloudflare Workers, or Google Gemini
- 💬 **Interactive Mode**: Chat interface for exploring your analytics data
- 🚀 **Easy Setup**: Simple installation and configuration process
- 🔒 **Secure**: All credentials stored locally, OAuth support
- 📈 **Cross-Platform Insights**: Compare performance across all your platforms
- 🎯 **Content Analysis**: Track which content performs best on each platform

## Prerequisites

- Python 3.8+
- Access to analytics platforms (see Supported Platforms below)
- An AI provider:
  - Ollama installed locally with a Llama model, OR
  - A Cloudflare Workers account with AI access, OR
  - A Google AI Studio API key for Gemini

## Supported Platforms

| Platform | Data Type | Auth Method | Status |
|----------|-----------|-------------|--------|
| **Umami** | Web Analytics | API Key / OAuth | ✅ Complete |
| **Google Search Console** | Search Performance | Service Account | ✅ Complete |
| **YouTube** | Video Analytics | API Key / OAuth | ✅ Complete |
| **Mastodon** | Social Engagement | OAuth | ✅ Complete |
| **Bluesky** | Social Engagement | App Password | ✅ Complete |
| **LinkedIn** | Professional Social | OAuth | ✅ Complete |
| **Instagram/Threads** | Social Engagement | OAuth | ✅ Complete |

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>
   ```

2. **Install dependencies**
   ```bash
   pip install uv
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration (see Platform Setup below):
   ```env
   # Umami (required)
   UMAMI_URL=https://api.umami.is
   UMAMI_API_KEY=your_api_key_here

   # Google Search Console (optional)
   # GSC_SERVICE_ACCOUNT_FILE=/path/to/service-account-key.json
   # GSC_SITE_URL=https://your-domain.com/

   # YouTube (optional)
   # YOUTUBE_API_KEY=your_youtube_api_key
   # YOUTUBE_CHANNEL_ID=your_channel_id

   # ... and more
   ```

## Configuration

### Platform Setup

Configure each platform by adding credentials to your `.env` file. Only configure platforms you want to use.

#### Umami (Web Analytics)

**For Umami Cloud:**
1. Go to **Settings → API Keys** in your Umami Cloud dashboard
2. Create an API key
3. Add to your `.env` file:
   ```env
   UMAMI_URL=https://api.umami.is
   UMAMI_API_KEY=your_api_key_here
   ```

**For Self-hosted Umami:**
1. Use your login credentials
2. Add to your `.env` file:
   ```env
   UMAMI_URL=https://your-umami-instance.com
   UMAMI_USERNAME=admin
   UMAMI_PASSWORD=your_password
   UMAMI_TEAM_ID=your-team-id  # Optional: for team-based access
   ```

#### Google Search Console (Search Performance)

1. Create a Google Cloud project
2. Enable the Search Console API
3. Create a service account and download the JSON key
4. Share your GSC property with the service account email
5. Add to `.env`:
   ```env
   GSC_SERVICE_ACCOUNT_FILE=/path/to/service-account-key.json
   GSC_SITE_URL=https://your-domain.com/
   ```

#### YouTube (Video Analytics)

1. Create a Google Cloud project
2. Enable YouTube Data API v3
3. Create an API key
4. Get your channel ID from YouTube Studio
5. Add to `.env`:
   ```env
   YOUTUBE_API_KEY=your_api_key
   YOUTUBE_CHANNEL_ID=your_channel_id
   ```

#### Mastodon (Social Engagement)

1. Register an application on your Mastodon instance
2. Get your access token from settings
3. Get your account ID from your profile
4. Add to `.env`:
   ```env
   MASTODON_INSTANCE=mastodon.social
   MASTODON_CLIENT_ID=your_client_id
   MASTODON_CLIENT_SECRET=your_client_secret
   MASTODON_ACCESS_TOKEN=your_access_token
   MASTODON_ACCOUNT_ID=your_account_id
   ```

#### Bluesky (Social Engagement)

1. Go to Settings → App Passwords in Bluesky
2. Create a new app password
3. Add to `.env`:
   ```env
   BLUESKY_IDENTIFIER=your-handle.bsky.social
   BLUESKY_PASSWORD=your_app_password
   ```

#### LinkedIn (Professional Social)

1. Create a LinkedIn app in the Developer Portal
2. Get organization admin authorization
3. Complete OAuth 2.0 flow to get access token
4. Add to `.env`:
   ```env
   LINKEDIN_CLIENT_ID=your_client_id
   LINKEDIN_CLIENT_SECRET=your_client_secret
   LINKEDIN_ACCESS_TOKEN=your_access_token
   LINKEDIN_ORGANIZATION_ID=your_organization_id
   ```

#### Instagram/Threads (Social Engagement)

1. Create a Facebook Developer account
2. Convert your Instagram to a Business account
3. Link your Facebook Page
4. Create an app and get access token
5. Add to `.env`:
   ```env
   INSTAGRAM_ACCESS_TOKEN=your_access_token
   INSTAGRAM_BUSINESS_ACCOUNT_ID=your_business_account_id
   ```

## Usage

You have two options for using the analytics platform:

### Option 1: run.py with Chat Mode (Recommended for Focused Analysis)

The `run.py` script provides an intelligent chat experience with automatic data injection:

```bash
# Generate dashboard with interactive chat mode (cross-platform!)
uv run run.py --start-date 2025-01-01 --end-date 2025-12-31 --website example.com --chat

# Generate dashboard without chat
uv run run.py --start-date 2025-01-01 --end-date 2025-12-31 --website example.com
```

**Chat Mode Features:**
- ✅ **Cross-platform** (Umami, GSC, YouTube, Mastodon, Bluesky, LinkedIn, Instagram)
- ✅ Automatic data injection (prevents AI hallucination)
- ✅ Hallucination detection (scans for fake numbers)
- ✅ Multiline input support (use Ctrl+D to end input)
- ✅ Focused analytics conversation

**Example Questions:**
- "Compare my Umami traffic with GSC impressions"
- "Which YouTube videos drove the most website traffic?"
- "Show engagement across all social platforms"

### Option 2: Gemini CLI (General-Purpose Assistant)

For broader questions beyond analytics:

```bash
# Configure and start Gemini with MCP servers
uv run scripts/run_gemini.py

# Or directly (if already configured)
gemini
```

**Gemini CLI Features:**
- ✅ Multi-platform (same 7 platforms)
- ✅ Full multiline input and command history
- ✅ Tool discovery and automatic documentation
- ✅ General-purpose AI assistant (not just analytics)

**Limitations:**
- ⚠️ Manual data injection required (may hallucinate)
- ⚠️ Need to specify which tools to call

### Interactive Chat Mode

Start an interactive session to explore your analytics data across all platforms:

```bash
# Using Gemini (recommended)
uv run --with-requirements requirements.txt run.py \
  --start-date 2025-01-01 --end-date 2025-12-31 \
  --website example.com --chat --ai-provider gemini-cli

# Using Ollama
uv run --with-requirements requirements.txt run.py \
  --start-date 2025-01-01 --end-date 2025-12-31 \
  --website example.com --chat --ai-provider ollama

# Using Cloudflare
uv run --with-requirements requirements.txt run.py \
  --start-date 2025-01-01 --end-date 2025-12-31 \
  --website example.com --chat --ai-provider cloudflare
```

### Example Queries

Once connected to multiple platforms, you can ask cross-platform questions:

**Single Platform:**
- "Show my top search queries from GSC last month"
- "Which YouTube videos got the most views this quarter?"
- "What are my top pages on Umami this week?"

**Cross-Platform:**
- "Compare engagement rates across Mastodon, Bluesky, and LinkedIn"
- "Did my LinkedIn posts drive more traffic than Mastodon?"
- "Show me content that performed well on both YouTube AND search"
- "Which platform has the best engagement rate for tutorial content?"

**Insights:**
- "My GSC impressions are up but clicks are down - what's happening?"
- "What type of content should I create more of based on all platforms?"
- "Correlate my social media campaigns with Umami traffic spikes"

### Running Individual Platform Servers

Each platform has its own MCP server that can be run independently:

```bash
# Run only the GSC server
uv run gsc-mcp

# Run only the YouTube server
uv run youtube-mcp

# Run only the Mastodon server
uv run mastodon-mcp

# Run the unified multi-platform server (all configured platforms)
uv run multi-platform-mcp
```

### Command Line Reports

Generate specific reports directly:

```bash
# Custom date range with Gemini
uv run --with-requirements requirements.txt run.py \
  --start-date 2025-01-01 --end-date 2025-12-31 \
  --website example.com --ai-provider gemini-cli

# Using Ollama
uv run --with-requirements requirements.txt run.py \
  --start-date 2025-01-01 --end-date 2025-12-31 \
  --website example.com --ai-provider ollama
```

### Automated Scheduling

Set up automated report generation using cron:

```bash
# Add to crontab for weekly reports every Monday at 9 AM
0 9 * * 1 cd /path/to/project && uv run --with-requirements requirements.txt run.py --start-date 2025-01-01 --end-date 2025-12-31 --website example.com --ai-provider gemini-cli
```

## Report Types

- **Traffic Summary**: Page views, unique visitors, sessions, bounce rate (Umami)
- **Search Performance**: Impressions, clicks, CTR, position (GSC)
- **Video Analytics**: Views, watch time, subscribers (YouTube)
- **Social Engagement**: Likes, reposts, replies, followers (Mastodon, Bluesky, LinkedIn, Instagram)
- **Top Content**: Most popular pages, posts, and videos by platform
- **Geographic Analysis**: Visitor locations and demographics (Umami, GSC)
- **Device & Browser**: Technology usage patterns (Umami)
- **UTM Campaign Tracking**: Performance by source, medium, campaign (Umami)
- **Cross-Platform Comparison**: Compare metrics across all connected platforms
- **Content Performance**: Which content types work best on each platform
- **Growth Trends**: Follower/subscriber growth over time

## Project Structure

```
attribution-mcp/
├── run.py                          # Main application entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── specs/
│   └── 001-multi-platform-connectors.md  # Technical specification
├── libs/
│   ├── attribution-schema/         # Unified data models
│   ├── attribution-cache/          # SQLite caching layer
│   └── attribution-auth/           # Authentication utilities
├── packages/
│   ├── umami-mcp/                  # Umami connector
│   ├── gsc-mcp/                    # Google Search Console connector
│   ├── youtube-mcp/                # YouTube connector
│   ├── mastodon-mcp/               # Mastodon connector
│   ├── bluesky-mcp/                # Bluesky connector
│   ├── linkedin-mcp/               # LinkedIn connector
│   └── instagram-mcp/              # Instagram/Threads connector
└── packages/umami-mcp/src/umami_mcp/
    ├── server.py                   # Umami MCP server
    ├── umami_client.py             # Umami API client
    └── multi_platform_server.py    # Unified multi-platform server
```

## Troubleshooting

### Common Issues

**Platform Not Connecting**
- Check that all required environment variables are set in `.env`
- Verify credentials are correct (API keys, tokens, etc.)
- Check the server logs for specific error messages

**Umami Connection Errors**
```bash
# Check Umami API connectivity
curl -u user:pass https://your-umami-instance.com/api/auth/login
```

**GSC API Errors**
- Ensure the service account email has been added to your GSC property
- Check that the service account JSON file path is correct
- Verify the GSC_SITE_URL matches your property exactly

**YouTube API Quota Exceeded**
- YouTube has a daily quota of 10,000 units (free tier)
- Reduce the frequency of API calls or request quota increase

**Social Platform Rate Limits**
- Each platform has different rate limits
- The connectors cache responses to minimize API calls
- Wait a few minutes and retry if you hit rate limits

**Missing Data**
- Ensure the account/user has access to the data in each platform
- For LinkedIn, ensure you have organization admin access
- For Instagram, ensure you have a Business account

### Checking Platform Status

You can check the connection status of all platforms:

```bash
# In chat mode, ask:
"What platforms are connected?"
"Show platform status"
```

## Development

### Project Structure
```
├── run.py                          # Main application entry point
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # MCP server package config
├── specs/
│   └── 001-multi-platform-connectors.md  # Technical specification
├── libs/                           # Shared libraries
│   ├── attribution-schema/         # Unified data models
│   ├── attribution-cache/          # SQLite caching
│   └── attribution-auth/           # Auth utilities
├── packages/                       # Platform-specific MCP servers
│   ├── umami-mcp/
│   ├── gsc-mcp/
│   ├── youtube-mcp/
│   ├── mastodon-mcp/
│   ├── bluesky-mcp/
│   ├── linkedin-mcp/
│   └── instagram-mcp/
└── packages/umami-mcp/src/umami_mcp/
    ├── server.py                   # Umami MCP server
    ├── umami_client.py             # Umami API client
    └── multi_platform_server.py    # Unified multi-platform server
```

### Adding a New Connector

To add a new platform connector:

1. Create a new package in `packages/your-platform-mcp/`
2. Implement the connector following the pattern in `specs/001-multi-platform-connectors.md`
3. Use the unified schema from `libs/attribution-schema/`
4. Add caching with `libs/attribution-cache/`
5. Add environment variables to `.env.example`
6. Update the README with setup instructions

### Running Tests

```bash
# Run unit tests for a specific connector
cd packages/gsc-mcp && uv run pytest

# Run integration tests (requires API credentials)
uv run pytest tests/integration/
```

## Dependencies

### Core Dependencies
- `mcp`: Model Context Protocol SDK
- `python-dotenv`: Environment variable management
- `aiohttp`: Async HTTP client

### Platform Dependencies (installed per-package)
- `google-api-python-client`: Google Search Console and YouTube
- `mastodon.py`: Mastodon API client
- `atproto`: Bluesky AT Protocol client
- `requests`, `requests-oauthlib`: LinkedIn API
- `facebook-sdk`: Instagram Graph API
- `pydantic`: Data validation
- `sqlite3`: Built-in caching

## Support

For issues and questions:
- Create an issue in this repository
- Review [MCP Python SDK documentation](https://github.com/modelcontextprotocol/python-sdk)
- Check platform-specific API documentation:
  - [Umami API](https://umami.is/docs/api)
  - [Google Search Console API](https://developers.google.com/webmaster-tools/search-console-api-original)
  - [YouTube API](https://developers.google.com/youtube/v3)
  - [Mastodon API](https://docs.joinmastodon.org/api/)
  - [Bluesky AT Protocol](https://atproto.com/)
  - [LinkedIn API](https://learn.microsoft.com/en-us/linkedin/)
  - [Instagram Graph API](https://developers.facebook.com/docs/instagram-api)

## Acknowledgments

- [Umami](https://umami.is/) for the analytics platform
- [Ollama](https://ollama.ai/) for local LLM inference
- [Cloudflare](https://workers.cloudflare.com/) for cloud AI services
- [Google Gemini](https://ai.google.dev/) for the Gemini API
- [Model Context Protocol](https://modelcontextprotocol.io/) for the MCP specification
- All platform providers for their public APIs
