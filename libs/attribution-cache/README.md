# Attribution Cache

SQLite-based caching for analytics API responses.

## Usage

```python
from attribution_cache import Cache
from attribution_schema import Metric

cache = Cache()

# Store metrics
cache.set_metrics([metric1, metric2])

# Retrieve cached metrics
metrics = cache.get_metrics(
    source="gsc",
    start_date=start_date,
    end_date=end_date,
    max_age_hours=1
)
```
