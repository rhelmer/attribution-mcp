"""Profile discovery for multi-account attribution analytics.

Convention: append __PROFILE_NAME to any env var to create a named profile.

Examples:
    # Default account (no suffix = backward compatible)
    MASTODON_ACCESS_TOKEN=abc
    MASTODON_ACCOUNT_ID=123

    # Named profiles
    MASTODON_ACCESS_TOKEN__STELLARWHISKERS=xyz
    MASTODON_ACCOUNT_ID__STELLARWHISKERS=456
    MASTODON_INSTANCE__STELLARWHISKERS=mastodon.games

    # Bluesky example
    BLUESKY_IDENTIFIER__STELLARWHISKERS=stellarwhiskers.bsky.social
    BLUESKY_PASSWORD__STELLARWHISKERS=hunter2

Discovery functions find all profiles, and `resolve_env` reads the right env var
for a given profile — falling back to the bare key for "default".
"""

import os
import re
from typing import Optional

# Delimiter between base env var name and profile name
_DELIMITER = "__"


def resolve_env(base_key: str, profile: str = "default") -> Optional[str]:
    """Read an env var for a specific profile.

    For the "default" profile, reads `base_key` directly (backward compatible).
    For named profiles, tries `{base_key}__{PROFILE}` (double underscore) first,
    then `{base_key}_{PROFILE}` (single underscore) as fallback.
    Returns None if neither is set.
    """
    if profile == "default":
        return os.environ.get(base_key)
    upper_profile = profile.upper()
    # Try double-underscore convention first, then single-underscore
    val = os.environ.get(f"{base_key}{_DELIMITER}{upper_profile}")
    if val is not None:
        return val
    return os.environ.get(f"{base_key}_{upper_profile}")


def discover_profiles(base_key: str) -> list[str]:
    """Discover all configured profile names for a given base env var.

    Scans env vars matching `{base_key}__{NAME}` and `{base_key}_{NAME}`,
    returning sorted unique names. Always returns "default" first if the
    base key itself is set.

    Example:
        >>> os.environ['MASTODON_ACCESS_TOKEN'] = 'abc'
        >>> os.environ['MASTODON_ACCESS_TOKEN__STELLARWHISKERS'] = 'xyz'
        >>> discover_profiles('MASTODON_ACCESS_TOKEN')
        ['default', 'STELLARWHISKERS']
    """
    profiles = set()

    # Scan double-underscore convention
    double_prefix = f"{base_key}{_DELIMITER}"
    for key in os.environ:
        if key.startswith(double_prefix):
            profile_name = key[len(double_prefix):]
            if profile_name:
                profiles.add(profile_name)

    # Also scan single-underscore convention
    single_prefix = f"{base_key}_"
    # Only scan for single underscore variations that aren't the double-underscore ones
    for key in os.environ:
        if key.startswith(single_prefix) and not key.startswith(double_prefix):
            profile_name = key[len(single_prefix):]
            if profile_name:  # skip empty (would be bare key itself)
                profiles.add(profile_name)

    # If the base key itself is set, default is available
    if os.environ.get(base_key):
        return ["default"] + sorted(profiles)
    return sorted(profiles)


def discover_platform_profiles() -> dict[str, list[str]]:
    """Discover all platform profiles from environment variables.

    Scans env vars for known platform prefixes and returns a dict mapping
    platform name to available profiles.

    Returns:
        {
            "mastodon": ["default", "STELLARWHISKERS"],
            "bluesky": ["default"],
            ...
        }
    """
    platform_keys = {
        "mastodon": "MASTODON_ACCESS_TOKEN",
        "bluesky": "BLUESKY_IDENTIFIER",
        "linkedin": "LINKEDIN_ACCESS_TOKEN",
        "instagram": "INSTAGRAM_ACCESS_TOKEN",
        "youtube": "YOUTUBE_API_KEY",
        "gsc": "GSC_SITE_URL",
        "umami": "UMAMI_URL",
    }

    result = {}
    for platform, base_key in platform_keys.items():
        profiles = discover_profiles(base_key)
        if profiles:
            result[platform] = profiles
    return result


def all_platform_profiles() -> dict[str, list[dict[str, Optional[str]]]]:
    """Get fully resolved credential dicts per platform per profile.

    Useful for the multi-platform server to instantiate connectors.
    Returns a dict like:
    {
        "mastodon": [
            {"profile": "default", "access_token": "abc", "account_id": "123"},
            {"profile": "STELLARWHISKERS", "access_token": "xyz", "account_id": "456"},
        ],
        ...
    }
    """
    platform_env_vars = {
        "mastodon": {
            "instance": "MASTODON_INSTANCE",
            "client_id": "MASTODON_CLIENT_ID",
            "client_secret": "MASTODON_CLIENT_SECRET",
            "access_token": "MASTODON_ACCESS_TOKEN",
            "account_id": "MASTODON_ACCOUNT_ID",
        },
        "bluesky": {
            "identifier": "BLUESKY_IDENTIFIER",
            "password": "BLUESKY_PASSWORD",
        },
        "linkedin": {
            "client_id": "LINKEDIN_CLIENT_ID",
            "client_secret": "LINKEDIN_CLIENT_SECRET",
            "access_token": "LINKEDIN_ACCESS_TOKEN",
            "organization_id": "LINKEDIN_ORGANIZATION_ID",
        },
        "instagram": {
            "access_token": "INSTAGRAM_ACCESS_TOKEN",
            "business_account_id": "INSTAGRAM_BUSINESS_ACCOUNT_ID",
        },
        "youtube": {
            "api_key": "YOUTUBE_API_KEY",
            "channel_id": "YOUTUBE_CHANNEL_ID",
        },
        "gsc": {
            "site_url": "GSC_SITE_URL",
            "service_account_file": "GSC_SERVICE_ACCOUNT_FILE",
            "token_file": "GSC_TOKEN_FILE",
        },
        "umami": {
            "url": "UMAMI_URL",
            "api_key": "UMAMI_API_KEY",
            "username": "UMAMI_USERNAME",
            "password": "UMAMI_PASSWORD",
            "team_id": "UMAMI_TEAM_ID",
        },
    }

    result = {}
    for platform, var_map in platform_env_vars.items():
        # Use the first env var as the "canary" to discover profiles
        canary_keys = [k for k in var_map.values()]
        if not canary_keys:
            continue

        profiles = set()
        for canary in canary_keys:
            profiles.update(discover_profiles(canary))

        if not profiles:
            continue

        profile_configs = []
        for profile in profiles:
            config = {"profile": profile}
            for field, env_key in var_map.items():
                val = resolve_env(env_key, profile)
                if val is not None:
                    # Use lowercase, matching-keys for readability
                    config[field] = val
            profile_configs.append(config)

        result[platform] = profile_configs

    return result
