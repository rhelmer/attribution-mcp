# Attribution Schema

Unified data models for multi-platform analytics.

## Usage

```python
from attribution_schema import Metric, Content, Audience

# Create a metric
metric = Metric(
    source="gsc",
    date=date.today(),
    metric_type="clicks",
    value=100,
    dimensions={"query": "python tutorial"}
)
```

## Models

- `Metric`: A single metric value with dimensions
- `Content`: A piece of content (page, post, video)
- `Audience`: Audience/follower metrics
