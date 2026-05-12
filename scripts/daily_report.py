#!/usr/bin/env python3
"""Daily analytics report generator. Uses attribution-mcp libs to get real data."""

import os, sys, json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/src/attribution-mcp/packages/umami-mcp/src"))

from umami_mcp.umami_client import UmamiClient
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/src/attribution-mcp/.env"))

def get_ummami():
    url = os.environ.get("UMAMI_URL", "")
    api_key = os.environ.get("UMAMI_API_KEY")
    username = os.environ.get("UMAMI_USERNAME")
    password = os.environ.get("UMAMI_PASSWORD")
    team_id = os.environ.get("UMAMI_TEAM_ID")
    
    if api_key:
        return UmamiClient(base_url=url, api_key=api_key)
    elif username and password:
        return UmamiClient(base_url=url, username=username, password=password, team_id=team_id)
    return None

def main():
    client = get_ummami()
    if not client:
        print("ERROR: No Umami credentials configured")
        sys.exit(1)
    
    # Get websites to find the right one
    websites = client.get_websites()
    if not websites or len(websites) == 0:
        print("ERROR: No websites found in Umami")
        sys.exit(1)
    
    # Try to find rhelmer.org by domain or name
    target = None
    for w in websites:
        if w.get("domain") == "rhelmer.org" or w.get("name") == "rhelmer.org":
            target = w
            break
    if not target and len(websites) > 0:
        target = websites[0]
    
    ws_id = target.get("id")
    ws_domain = target.get("domain", target.get("name", "unknown"))
    print(f"Using website: {ws_domain} (id={ws_id})")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get pageviews/stats
    stats = client.get_website_stats(ws_id, start=start_date, end=end_date)
    print(f"Stats: {json.dumps(stats, default=str)[:500]}")
    
    # Get pageviews
    pageviews = client.get_website_pageviews(ws_id, start=start_date, end=end_date)
    print(f"Pageviews: {json.dumps(pageviews, default=str)[:500]}")
    
    # Get events (could include custom events)
    try:
        events = client.get_website_events(ws_id, start=start_date, end=end_date)
        print(f"Events: {json.dumps(events, default=str)[:500]}")
    except:
        pass

if __name__ == "__main__":
    main()
