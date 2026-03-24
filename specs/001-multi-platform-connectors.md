# Spec 001: Multi-Platform Analytics Connectors

**Status:** 📝 Draft  
**Created:** 2026-03-22  
**Author:** AI Assistant  
**Priority:** 🔴 High

## Overview

Extend the analytics platform to pull data from multiple sources beyond Umami, enabling unified cross-platform analytics and AI-powered insights.

## Target Platforms

| Platform | API | Auth | Data Quality | Implementation Effort |
|----------|-----|------|--------------|----------------------|
| **Umami** | REST | Token | ⭐⭐⭐⭐⭐ | ✅ Done |
| **Google Search Console** | Google API | Service Account | ⭐⭐⭐⭐⭐ | 🟢 Easy |
| **YouTube** | Data API v3 | OAuth/API Key | ⭐⭐⭐⭐⭐ | 🟢 Easy |
| **Mastodon** | REST | OAuth | ⭐⭐⭐⭐ | 🟢 Easy |
| **Bluesky** | AT Protocol | App Password | ⭐⭐⭐⭐ | 🟢 Easy |
| **LinkedIn** | REST | OAuth | ⭐⭐⭐ | 🟡 Medium |
| **Instagram/Threads** | Graph API | OAuth | ⭐⭐⭐⭐ | 🟡 Medium |
| **TikTok** | REST | OAuth | ⭐⭐ | 🔴 Hard |

## Architecture

### Connector Interface

All data sources implement a common interface:

```python
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List, Dict, Any

class Connector(ABC):
    """Base class for all analytics data connectors"""
    
    name: str  # e.g., "umami", "gsc", "youtube"
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the service. Returns True if successful."""
        pass
    
    @abstractmethod
    async def get_metrics(
        self,
        start_date: date,
        end_date: date,
        dimensions: Optional[List[str]] = None,
        **kwargs
    ) -> List[Metric]:
        """Fetch metrics for the given date range"""
        pass
    
    @abstractmethod
    async def get_content(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Content]:
        """Fetch content items (pages, posts, videos)"""
        pass
    
    @abstractmethod
    async def get_audience(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> List[Audience]:
        """Fetch audience/follower data"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test the connection and return status info"""
        pass
```

### Unified Data Schema

```python
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any

@dataclass
class Metric:
    """A single metric value with dimensions"""
    source: str                    # "umami", "gsc", "youtube", etc.
    date: date
    metric_type: str               # "pageviews", "impressions", "clicks"
    value: float
    dimensions: Dict[str, str] = field(default_factory=dict)
    # Common dimensions: url, title, query, country, device, platform
    
@dataclass
class Content:
    """A piece of content (page, post, video)"""
    source: str
    content_id: str
    content_type: str              # "page", "post", "video", "article"
    url: str
    title: str
    created_at: datetime
    author: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metrics: List[Metric] = field(default_factory=list)
    
@dataclass
class Audience:
    """Audience/follower metrics"""
    source: str
    date: date
    segment: str                   # "followers", "subscribers"
    count: int
    demographics: Dict[str, Any] = field(default_factory=dict)
    # demographics: {"countries": {...}, "age": {...}, "gender": {...}}
```

### Data Caching

```python
import sqlite3
from datetime import timedelta

class Cache:
    """SQLite-based cache for API responses"""
    
    def __init__(self, db_path: str = ".analytics_cache.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                date DATE NOT NULL,
                metric_type TEXT NOT NULL,
                dimensions_hash TEXT NOT NULL,
                value REAL NOT NULL,
                dimensions_json TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, date, metric_type, dimensions_hash)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                content_id TEXT NOT NULL,
                content_type TEXT NOT NULL,
                url TEXT,
                title TEXT,
                created_at TIMESTAMP,
                data_json TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, content_id)
            )
        """)
        conn.commit()
        conn.close()
    
    def get_metrics(
        self,
        source: str,
        start_date: date,
        end_date: date,
        max_age: timedelta = timedelta(hours=1)
    ) -> List[Metric]:
        """Fetch cached metrics if fresh enough"""
        pass
    
    def set_metrics(self, metrics: List[Metric]):
        """Store metrics in cache"""
        pass
```

## Platform Specifications

### 1. Google Search Console

**Setup:**
1. Create Google Cloud project
2. Enable Search Console API
3. Create service account
4. Share GSC property with service account email

**Environment:**
```env
GSC_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
GSC_SITE_URL=sc-domain:example.com
```

**Key Methods:**
```python
class GSCConnector(Connector):
    name = "gsc"
    
    async def get_metrics(self, start_date, end_date, dimensions=None):
        """
        Fetch search performance data.
        
        Dimensions: ["query", "page", "country", "device"]
        Metrics: impressions, clicks, CTR, position
        """
        request = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dimensions or [],
            "rowLimit": 25000,
        }
        response = self.service.searchanalytics().query(
            siteUrl=self.site_url, body=request
        ).execute()
        return self._parse_response(response)
```

**Rate Limits:** 2,000 requests/day

---

### 2. YouTube

**Setup:**
1. Create Google Cloud project
2. Enable YouTube Data API v3 + YouTube Analytics API
3. Create OAuth credentials or API key

**Environment:**
```env
YOUTUBE_API_KEY=your-api-key
YOUTUBE_CHANNEL_ID=your-channel-id
# Or for OAuth:
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
```

**Key Methods:**
```python
class YouTubeConnector(Connector):
    name = "youtube"
    
    async def get_metrics(self, start_date, end_date, dimensions=None):
        """
        Fetch video analytics.
        
        Dimensions: ["video", "trafficSource", "subscribedStatus"]
        Metrics: views, watchTime, impressions, impressionCTR
        """
        response = self.youtube_analytics.reports().query(
            ids=f"channel=={self.channel_id}",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics="views,watchTimeMinutes,impressions,impressionClickThroughRate",
            dimensions="day,video",
        ).execute()
        return self._parse_response(response)
    
    async def get_content(self, start_date, end_date):
        """Fetch video details"""
        response = self.youtube.videos().list(
            part="snippet,statistics",
            myRating="mine",
            maxResults=50,
        ).execute()
        return self._parse_videos(response)
```

**Rate Limits:** 10,000 units/day (free tier)

---

### 3. Mastodon

**Setup:**
1. Register app on your instance
2. Get access token

**Environment:**
```env
MASTODON_INSTANCE=mastodon.social
MASTODON_CLIENT_ID=...
MASTODON_CLIENT_SECRET=...
MASTODON_ACCESS_TOKEN=...
MASTODON_ACCOUNT_ID=...
```

**Key Methods:**
```python
class MastodonConnector(Connector):
    name = "mastodon"
    
    async def get_metrics(self, start_date, end_date, **kwargs):
        """
        Fetch post engagement data.
        
        Metrics: reblogs, favourites, replies
        """
        statuses = self.mastodon.account_statuses(self.account_id)
        return self._parse_statuses(statuses, start_date, end_date)
    
    async def get_audience(self, start_date, end_date, **kwargs):
        """Fetch follower count"""
        account = self.mastodon.account(self.account_id)
        return [Audience(
            source="mastodon",
            date=date.today(),
            segment="followers",
            count=account["followers_count"],
        )]
```

**Rate Limits:** ~300 requests/hour (instance-dependent)

---

### 4. Bluesky

**Setup:**
1. Create app password in settings

**Environment:**
```env
BLUESKY_IDENTIFIER=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password
```

**Key Methods:**
```python
class BlueskyConnector(Connector):
    name = "bluesky"
    
    async def get_metrics(self, start_date, end_date, **kwargs):
        """
        Fetch post engagement data.
        
        Metrics: likes, reposts, replies
        """
        feed = await self.atproto.app.bsky.feed.get_author_feed({
            "actor": self.identifier,
            "limit": 100,
        })
        return self._parse_feed(feed, start_date, end_date)
```

**Rate Limits:** 5,000 requests/hour

---

### 5. LinkedIn

**Setup:**
1. Create LinkedIn app
2. Get organization admin authorization
3. OAuth 2.0 flow

**Environment:**
```env
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_ORGANIZATION_ID=...
```

**Key Methods:**
```python
class LinkedInConnector(Connector):
    name = "linkedin"
    
    async def get_metrics(self, start_date, end_date, **kwargs):
        """
        Fetch organization page analytics.
        
        Metrics: impressions, clicks, engagements, followers
        """
        # Company statistics
        response = await self._request(
            f"/v2/organizations/{self.org_id}/statistics",
            params={"timeIntervals": ...}
        )
        return self._parse_response(response)
```

**Rate Limits:** 500 requests/day

---

### 6. Instagram/Threads

**Setup:**
1. Facebook Developer account
2. Instagram Business account
3. Link Facebook Page
4. App review (for some permissions)

**Environment:**
```env
INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_BUSINESS_ACCOUNT_ID=...
```

**Key Methods:**
```python
class InstagramConnector(Connector):
    name = "instagram"
    
    async def get_metrics(self, start_date, end_date, **kwargs):
        """
        Fetch Instagram + Threads insights.
        
        Metrics: impressions, reach, engagement, profile_views
        """
        insights = await self._request(
            f"/{self.account_id}/insights",
            params={
                "metric": "impressions,reach,engagement,profile_views",
                "period": "day",
            }
        )
        return self._parse_insights(insights)
```

**Rate Limits:** 200 calls/hour per user

---

### 7. TikTok

**Status:** ⚠️ Limited API access

**Options:**
1. Apply for Research API access (requires approval)
2. Manual data export (download CSV from TikTok)
3. Skip and focus on other platforms

**Environment:**
```env
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
TIKTOK_ACCESS_TOKEN=...
```

---

## MCP Tools

Expose connectors as MCP tools:

```python
# In umami_mcp_server/server.py

TOOLS = [
    {
        "name": "get_analytics_metrics",
        "description": "Get metrics from any connected analytics source",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["umami", "gsc", "youtube", "mastodon", "bluesky", "linkedin", "instagram"]
                },
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
                "metric_types": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["source", "start_date", "end_date"]
        }
    },
    {
        "name": "get_cross_platform_summary",
        "description": "Get unified metrics across all platforms for a date range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
            },
            "required": ["start_date", "end_date"]
        }
    },
    # ... more tools for content, audience, etc.
]
```

## Example Queries

Once implemented, the LLM can answer:

**Single Platform:**
- "Show my top search queries from GSC last month"
- "Which YouTube videos got the most views this quarter?"

**Cross-Platform:**
- "Did my LinkedIn posts drive more traffic than Mastodon?"
- "Show me content that performed well on both YouTube AND search"
- "Correlate my Twitter campaigns with Umami traffic spikes"
- "Which platform has the best engagement rate for tutorial content?"

**Insights:**
- "My GSC impressions are up but clicks are down - what's happening?"
- "What type of content should I create more of based on all platforms?"

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `connectors/` package
- [ ] Implement base `Connector` class
- [ ] Define data schema (`Metric`, `Content`, `Audience`)
- [ ] Add SQLite caching layer
- [ ] Add credential management utilities

### Phase 2: High-Value Connectors (Week 2-3)
- [ ] GSC connector (free, stable, high ROI)
- [ ] YouTube connector (free, well-documented)
- [ ] Mastodon connector (simple API)
- [ ] Bluesky connector (modern API)

### Phase 3: Social Platforms (Week 4-5)
- [ ] LinkedIn connector (OAuth complexity)
- [ ] Instagram/Threads connector (Meta app review)
- [ ] TikTok (or manual import fallback)

### Phase 4: Integration (Week 6)
- [ ] Expose connectors as MCP tools
- [ ] Update `run.py` to fetch from all sources
- [ ] Add cross-platform analysis prompts
- [ ] Update documentation

### Phase 5: Web UI (Future)
- [ ] Next.js dashboard
- [ ] Interactive charts
- [ ] Platform comparison views
- [ ] Automated insight generation

## Dependencies

```txt
# Existing
mcp
python-dotenv
aiohttp

# New
google-api-python-client>=2.0.0    # GSC + YouTube
google-auth-httplib2>=0.1.0        # Google auth
mastodon.py>=1.5.0                 # Mastodon
atproto>=0.0.0                     # Bluesky
facebook-sdk>=3.0.0                # Instagram/Threads
requests-oauthlib>=1.3.0           # OAuth
sqlite-utils>=3.0.0                # Data caching
pydantic>=2.0.0                    # Data validation
```

## Testing Strategy

1. **Unit tests** for each connector's parsing logic
2. **Integration tests** with mock API responses
3. **E2E tests** with real API calls (CI with stored credentials)
4. **Data validation** - ensure schema consistency across connectors

## Security Considerations

- Store all credentials in `.env` (gitignored)
- Use service accounts where possible (no user OAuth)
- Cache tokens securely
- Never log API responses containing PII
- Rate limit locally to respect API limits

## Open Questions

1. **TikTok**: Skip or provide manual CSV import?
2. **Historical data**: How far back to fetch on first run?
3. **Timezones**: Normalize all dates to UTC or preserve source timezone?
4. **Missing data**: How to handle platforms with different data availability?

## Success Metrics

- [ ] All 8 platforms connected and returning data
- [ ] Cross-platform queries working in chat mode
- [ ] API rate limits respected (no 429 errors)
- [ ] Cache hit rate > 80% for repeated queries
- [ ] Documentation complete for each connector

## References

- [GSC API Docs](https://developers.google.com/webmaster-tools/search-console-api-original)
- [YouTube API Docs](https://developers.google.com/youtube/v3)
- [Mastodon API Docs](https://docs.joinmastodon.org/api/)
- [Bluesky AT Protocol](https://atproto.com/)
- [LinkedIn API](https://learn.microsoft.com/en-us/linkedin/)
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api)
