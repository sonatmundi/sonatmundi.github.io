"""
Central configuration loader for Sonat Mundi growth automation.

Reads config.json (local) or environment variables (GitHub Actions).
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

_config_cache = None


def _load():
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    # Try local config.json first, fall back to env vars
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _config_cache = json.load(f)
    else:
        _config_cache = {}

    return _config_cache


def get(key, default=None):
    """Get a config value. Env vars override config.json."""
    env_key = key.upper()
    env_val = os.environ.get(env_key)
    if env_val is not None:
        return env_val
    return _load().get(key, default)


# Convenience accessors
def anthropic_api_key():
    return get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")


def channel_id():
    return get("channel_id", "UCVFOpInPEdxJQF_FmnoKSMQ")


def default_privacy():
    return get("default_privacy", "public")


def best_upload_hours():
    return get("best_upload_hours", [])
