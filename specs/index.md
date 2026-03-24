# Multi-Platform Analytics Specs

This directory contains specifications for extending the analytics platform to support multiple data sources.

## Specifications

| Spec | Status | Priority |
|------|--------|----------|
| [001-multi-platform-connectors](./001-multi-platform-connectors.md) | 📝 Draft | 🔴 High |

## Roadmap

### Phase 1: Core Infrastructure
- [ ] Base connector interface
- [ ] Unified data schema
- [ ] Credential management
- [ ] Data caching layer

### Phase 2: High-Value Connectors
- [ ] Google Search Console
- [ ] YouTube
- [ ] Mastodon
- [ ] Bluesky

### Phase 3: Social Platforms
- [ ] LinkedIn
- [ ] Instagram/Threads
- [ ] TikTok (or manual import)

### Phase 4: UI/UX
- [ ] Web dashboard
- [ ] Cross-platform queries
- [ ] Automated insights

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Sources                                  │
│  ┌────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────┐ │
│  │ Umami  │ │ GSC  │ │LinkedIn │ │Mastodon  │ │Bluesky │ │Threads│ │
│  └───┬────┘ └──┬───┘ └────┬────┘ └────┬─────┘ └───┬────┘ └───┬───┘ │
│      │         │          │           │           │           │     │
│      │         │          │      ┌────┴───────────┴────┐      │     │
│      │         │          │      │   Instagram/FB     │      │     │
│      │         │          │      └────────┬───────────┘      │     │
│      │         │          │               │                  │     │
│  ┌───┴────┐ ┌──┴───┐ ┌────┴────┐ ┌────────┴──────────┐ ┌────┴───┐ │
│  │        │ │      │ │         │ │                   │ │        │ │
│  └───┬────┘ └──┬───┘ └────┬────┘ └────────┬──────────┘ └────┬───┘ │
│      │         │          │               │                  │     │
│      └─────────┴──────────┴───────────────┴──────────────────┘     │
│                           │                                         │
│                    ┌──────▼──────┐                                  │
│                    │  Connector  │                                  │
│                    │   Layer     │                                  │
│                    └──────┬──────┘                                  │
│                           │                                         │
│                    ┌──────▼──────┐                                  │
│                    │   Unified   │                                  │
│                    │ Data Schema │                                  │
│                    └──────┬──────┘                                  │
│                           │                                         │
│         ┌─────────────────┼─────────────────┐                       │
│         │                 │                 │                       │
│    ┌────▼────┐      ┌─────▼─────┐     ┌────▼────┐                  │
│    │   CLI   │      │   Web UI  │     │  API    │                  │
│    │  Chat   │      │ Dashboard │     │ Export  │                  │
│    └─────────┘      └───────────┘     └─────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Platform Summary

| Platform | API Type | Auth | Cost | Rate Limit | Priority |
|----------|----------|------|------|------------|----------|
| **Umami** | REST | Token | Free (self-hosted) | None | ✅ Done |
| **GSC** | Google REST | Service Account | Free | 2,000/day | 🔴 High |
| **YouTube** | REST | OAuth/API Key | Free | 10,000 units/day | 🔴 High |
| **Mastodon** | REST | OAuth | Free | 300/hour | 🟡 Medium |
| **Bluesky** | AT Protocol | App Password | Free | 5,000/hour | 🟡 Medium |
| **LinkedIn** | REST | OAuth | Free | 500/day | 🟢 Low |
| **Instagram/Threads** | Graph API | OAuth | Free | 200/hour | 🟢 Low |
| **TikTok** | REST | OAuth | Limited | 100/hour | ⚪ Optional |

## Getting Started

1. Read [001-multi-platform-connectors.md](./001-multi-platform-connectors.md) for the full proposal
2. Set up development environment (see Phase 1 in the spec)
3. Start with GSC connector (highest ROI)

## Related Documentation

- [Umami MCP Server](../umami_mcp_server/README.md)
- [Main README](../README.md)
