"""
Unified YouTube authentication for growth automation.

Supports two modes:
  1. Local: reads token.json + credentials.json from disk
  2. CI/CD: decodes base64 secrets from environment variables
"""

import base64
import json
import os
import tempfile

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
CREDS_PATH = os.path.join(BASE_DIR, "credentials.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube",                 # full management (playlists, titles, thumbnails)
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",          # video/thumbnail upload
    "https://www.googleapis.com/auth/youtube.force-ssl",       # comments
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


def _decode_env_secret(env_var, fallback_path):
    """Decode a base64 env var to a temp file, or return the local path."""
    b64 = os.environ.get(env_var)
    if b64:
        data = base64.b64decode(b64)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp.write(data.decode("utf-8"))
        tmp.close()
        return tmp.name
    if os.path.exists(fallback_path):
        return fallback_path
    return None


def get_credentials():
    """Return valid OAuth2 credentials, refreshing if needed."""
    token_path = _decode_env_secret("YOUTUBE_TOKEN", TOKEN_PATH)
    creds_path = _decode_env_secret("YOUTUBE_CREDENTIALS", CREDS_PATH)

    creds = None
    if token_path and os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[auth] Token refresh failed: {e}")
                creds = None

        if not creds:
            if os.environ.get("CI"):
                raise RuntimeError(
                    "Token expired in CI and cannot re-authorize interactively. "
                    "Please refresh token.json locally and update YOUTUBE_TOKEN secret."
                )
            from google_auth_oauthlib.flow import InstalledAppFlow
            print("[auth] Opening browser for OAuth2...")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save refreshed token locally
        if not os.environ.get("CI"):
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

    return creds


def youtube_service():
    """Return an authenticated YouTube Data API v3 service."""
    return build("youtube", "v3", credentials=get_credentials())


def analytics_service():
    """Return an authenticated YouTube Analytics API v2 service."""
    return build("youtubeAnalytics", "v2", credentials=get_credentials())


def youtube_and_analytics():
    """Return both services sharing one set of credentials."""
    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds)
    ya = build("youtubeAnalytics", "v2", credentials=creds)
    return yt, ya
