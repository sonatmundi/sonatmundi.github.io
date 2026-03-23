"""
_auth.py — Shared authentication & utilities for Sonat Mundi Analytics.

Handles OAuth token refresh and re-authorization when new scopes are needed.
Import this module from every report script.
"""

import os
import re
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_PATH  = r"D:\Yedekler\UCS\token.json"
CREDS_PATH  = r"D:\Yedekler\UCS\credentials.json"
CHANNEL_ID  = "UCVFOpInPEdxJQF_FmnoKSMQ"
REPORTS_DIR = r"D:\Yedekler\UCS\analytics\reports"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


def get_services():
    """Return authenticated (youtube, youtubeAnalytics) service objects.

    Automatically refreshes the token. If the existing token is missing the
    required Analytics scopes a browser-based re-authorization is triggered.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[_auth] Token refresh failed ({e}). Re-authorizing...")
                creds = None

        if not creds:
            from google_auth_oauthlib.flow import InstalledAppFlow
            print("[_auth] Opening browser for OAuth authorization (analytics scopes)...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as fh:
            fh.write(creds.to_json())

    youtube   = build("youtube",          "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)
    return youtube, analytics


def ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return REPORTS_DIR


# ─── Analytics helpers ────────────────────────────────────────────────────────

def parse_analytics(response):
    """Convert Analytics API resultTable response to list of dicts."""
    if not response or not response.get("rows"):
        return []
    headers = [h["name"] for h in response["columnHeaders"]]
    return [dict(zip(headers, row)) for row in response["rows"]]


def safe_int(v):
    return int(v) if v is not None else 0


def safe_float(v):
    return float(v) if v is not None else 0.0


# ─── Formatting helpers ───────────────────────────────────────────────────────

def format_duration(seconds):
    """Format seconds → 'M:SS' or 'H:MM:SS'."""
    if not seconds:
        return "0:00"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def format_minutes(minutes):
    """Format total minutes → 'Xh Ym' or 'Y min'."""
    if not minutes:
        return "0 min"
    m = int(minutes)
    h, rem = divmod(m, 60)
    return f"{h:,}h {rem}m" if h else f"{m:,} min"


def ascii_bar(value, max_value, width=30):
    """Return a simple ASCII progress bar."""
    if max_value <= 0:
        return " " * width
    filled = int(round(value / max_value * width))
    return "█" * filled + "░" * (width - filled)


# ─── Channel-specific helpers ─────────────────────────────────────────────────

def detect_series(title):
    """Classify a video title into a Sonat Mundi content pillar."""
    t = title.lower()
    if "sounds of world" in t:
        return "Sounds of World"
    if "sounds of emotion" in t or "sounds of mood" in t:
        return "Sounds of Emotions"
    if "sounds of concept" in t:
        return "Sounds of Concepts"
    if ("sounds of frequen" in t or " hz" in t or "binaural" in t
            or "solfeggio" in t or "432" in t or "528" in t
            or "sacred frequen" in t):
        return "Sounds of Frequencies"
    return "Other"


def sanitize_filename(name):
    """Strip characters that are illegal in Windows filenames."""
    safe = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    safe = re.sub(r"\s+", "_", safe)
    return safe[:80]


def get_video_titles_and_tags(youtube, video_ids):
    """Batch-fetch titles and tags for up to N video IDs.

    Returns:
        title_map : {video_id: title}
        tags_map  : {video_id: [tag, ...]}
    """
    title_map = {}
    tags_map  = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp  = youtube.videos().list(
            part="snippet",
            id=",".join(batch)
        ).execute()
        for item in resp.get("items", []):
            vid               = item["id"]
            title_map[vid]    = item["snippet"]["title"]
            tags_map[vid]     = item["snippet"].get("tags", [])
    return title_map, tags_map
