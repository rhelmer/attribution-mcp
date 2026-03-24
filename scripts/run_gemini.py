#!/usr/bin/env python3
"""
Configure and run Gemini CLI with multi-platform analytics MCP servers.

This script configures Gemini CLI to use the analytics MCP servers
and launches Gemini. Configuration is stored globally in ~/.gemini/

Usage:
    uv run scripts/run_gemini.py                 # Configure and start Gemini
    uv run scripts/run_gemini.py --configure-only  # Just configure

Credentials are read from .env file.
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent


def run_gemini_mcp(*args):
    """Run gemini mcp command."""
    cmd = ["gemini", "mcp"] + list(args)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def configure_mcp_servers():
    """Configure MCP servers using gemini mcp add commands."""

    print("🔧 Configuring MCP servers for Gemini CLI...")
    print("   (Configuration stored in ~/.gemini/settings.json)")
    print()

    # Remove existing servers (clean slate)
    print("Removing existing MCP servers...")
    run_gemini_mcp("remove", "umami")
    run_gemini_mcp("remove", "gsc")
    run_gemini_mcp("remove", "youtube")
    run_gemini_mcp("remove", "mastodon")
    run_gemini_mcp("remove", "bluesky")
    run_gemini_mcp("remove", "linkedin")
    run_gemini_mcp("remove", "instagram")
    print("✅ Cleaned up old configurations")
    print()

    # Add Umami if configured
    umami_api_key = os.environ.get("UMAMI_API_KEY")
    umami_username = os.environ.get("UMAMI_USERNAME")
    umami_password = os.environ.get("UMAMI_PASSWORD")

    if umami_api_key or (umami_username and umami_password):
        umami_url = os.environ.get("UMAMI_URL", "https://api.umami.is")

        # Build environment string
        env_args = []
        if umami_api_key:
            env_args.extend(["--env", f"UMAMI_API_KEY={umami_api_key}"])
        if umami_username:
            env_args.extend(["--env", f"UMAMI_USERNAME={umami_username}"])
        if umami_password:
            env_args.extend(["--env", f"UMAMI_PASSWORD={umami_password}"])
        if os.environ.get("UMAMI_TEAM_ID"):
            env_args.extend(["--env", f"UMAMI_TEAM_ID={os.environ.get('UMAMI_TEAM_ID')}"])

        cmd = [
            "gemini", "mcp", "add", "umami",
            "uv", "run", "umami-mcp",
            "--cwd", str(PROJECT_ROOT),
        ] + env_args

        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Umami MCP server added")
        else:
            print(f"⚠️  Umami config failed: {result.stderr}")
    else:
        print("⚠️  Umami credentials not set. Skipping Umami.")

    # Add GSC if OAuth token exists
    gsc_token = PROJECT_ROOT / ".gsc_token.json"
    if gsc_token.exists():
        gsc_site_url = os.environ.get("GSC_SITE_URL")

        cmd = [
            "gemini", "mcp", "add", "gsc",
            "uv", "run", "gsc-mcp",
            "--cwd", str(PROJECT_ROOT),
        ]
        if gsc_site_url:
            cmd.extend(["--env", f"GSC_SITE_URL={gsc_site_url}"])

        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ GSC MCP server added{' for ' + gsc_site_url if gsc_site_url else ''}")
        else:
            print(f"⚠️  GSC config failed: {result.stderr}")
    else:
        print("⚠️  .gsc_token.json not found. Skipping GSC.")
        print("   Run: uv run scripts/gsc_oauth.py")

    # Add YouTube if configured
    youtube_key = os.environ.get("YOUTUBE_API_KEY")
    youtube_channel = os.environ.get("YOUTUBE_CHANNEL_ID")
    if youtube_key and youtube_channel:
        cmd = [
            "gemini", "mcp", "add", "youtube",
            "uv", "run", "youtube-mcp",
            "--cwd", str(PROJECT_ROOT),
            "--env", f"YOUTUBE_API_KEY={youtube_key}",
            "--env", f"YOUTUBE_CHANNEL_ID={youtube_channel}",
        ]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ YouTube MCP server added")
        else:
            print(f"⚠️  YouTube config failed: {result.stderr}")
    else:
        print("⚠️  YouTube credentials not set. Skipping YouTube.")

    # Add Mastodon if configured
    mastodon_token = os.environ.get("MASTODON_ACCESS_TOKEN")
    mastodon_account = os.environ.get("MASTODON_ACCOUNT_ID")
    if mastodon_token and mastodon_account:
        cmd = [
            "gemini", "mcp", "add", "mastodon",
            "uv", "run", "mastodon-mcp",
            "--cwd", str(PROJECT_ROOT),
            "--env", f"MASTODON_ACCESS_TOKEN={mastodon_token}",
            "--env", f"MASTODON_ACCOUNT_ID={mastodon_account}",
        ]
        if os.environ.get("MASTODON_INSTANCE"):
            cmd.extend(["--env", f"MASTODON_INSTANCE={os.environ.get('MASTODON_INSTANCE')}"])

        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Mastodon MCP server added")
        else:
            print(f"⚠️  Mastodon config failed: {result.stderr}")
    else:
        print("⚠️  Mastodon credentials not set. Skipping Mastodon.")

    # Add Bluesky if configured
    bluesky_id = os.environ.get("BLUESKY_IDENTIFIER")
    bluesky_pass = os.environ.get("BLUESKY_PASSWORD")
    if bluesky_id and bluesky_pass:
        cmd = [
            "gemini", "mcp", "add", "bluesky",
            "uv", "run", "bluesky-mcp",
            "--cwd", str(PROJECT_ROOT),
            "--env", f"BLUESKY_IDENTIFIER={bluesky_id}",
            "--env", f"BLUESKY_PASSWORD={bluesky_pass}",
        ]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Bluesky MCP server added")
        else:
            print(f"⚠️  Bluesky config failed: {result.stderr}")
    else:
        print("⚠️  Bluesky credentials not set. Skipping Bluesky.")

    # Add LinkedIn if configured
    linkedin_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    linkedin_org = os.environ.get("LINKEDIN_ORGANIZATION_ID")
    if linkedin_token and linkedin_org:
        cmd = [
            "gemini", "mcp", "add", "linkedin",
            "uv", "run", "linkedin-mcp",
            "--cwd", str(PROJECT_ROOT),
            "--env", f"LINKEDIN_ACCESS_TOKEN={linkedin_token}",
            "--env", f"LINKEDIN_ORGANIZATION_ID={linkedin_org}",
        ]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ LinkedIn MCP server added")
        else:
            print(f"⚠️  LinkedIn config failed: {result.stderr}")
    else:
        print("⚠️  LinkedIn credentials not set. Skipping LinkedIn.")

    # Add Instagram if configured
    insta_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    insta_account = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    if insta_token and insta_account:
        cmd = [
            "gemini", "mcp", "add", "instagram",
            "uv", "run", "instagram-mcp",
            "--cwd", str(PROJECT_ROOT),
            "--env", f"INSTAGRAM_ACCESS_TOKEN={insta_token}",
            "--env", f"INSTAGRAM_BUSINESS_ACCOUNT_ID={insta_account}",
        ]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Instagram MCP server added")
        else:
            print(f"⚠️  Instagram config failed: {result.stderr}")
    else:
        print("⚠️  Instagram credentials not set. Skipping Instagram.")

    print()

    # List configured servers
    print("📊 Configured MCP servers:")
    result = subprocess.run(["gemini", "mcp", "list"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    print(result.stdout)

    return True


def main():
    configure_only = "--configure-only" in sys.argv

    if not configure_mcp_servers():
        sys.exit(1)

    if configure_only:
        print("\n✅ Configuration complete!")
        print("To start Gemini, run: uv run scripts/run_gemini.py")
        return

    print("Starting Gemini CLI...")
    print("Use 'Ctrl+C' to exit.")
    print("-" * 50)

    # Run Gemini CLI
    subprocess.run(["gemini"], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    main()
