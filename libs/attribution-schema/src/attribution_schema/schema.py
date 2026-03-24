"""Unified data models for multi-platform analytics."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any


@dataclass
class Metric:
    """A single metric value with dimensions."""
    source: str                    # "umami", "gsc", "youtube", etc.
    date: date
    metric_type: str               # "pageviews", "impressions", "clicks"
    value: float
    dimensions: Dict[str, str] = field(default_factory=dict)
    # Common dimensions: url, title, query, country, device, platform


@dataclass
class Content:
    """A piece of content (page, post, video)."""
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
    """Audience/follower metrics."""
    source: str
    date: date
    segment: str                   # "followers", "subscribers"
    count: int
    demographics: Dict[str, Any] = field(default_factory=dict)
    # demographics: {"countries": {...}, "age": {...}, "gender": {...}}
