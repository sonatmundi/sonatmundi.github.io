#!/usr/bin/env python3
"""Fetch YouTube channel data and write data/channel.json for the website."""

import json
import os
import sys
import base64
import pickle
import re
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
]

CHANNEL_ID = "UCVFOpInPEdxJQF_FmnoKSMQ"

# Playlists (known)
PLAYLISTS = {
    "PLFwHyBcRUIvWB-zuYabHpeA1I5SanQfEt": "Sounds of Sleep",
    "PLFwHyBcRUIvVYjQahdDJ1zvPaNd1ZC_OT": "Sounds of Frequencies",
    "PLFwHyBcRUIvUaegQrL-bSgB1IwjV4990v": "Sounds of World",
    "PLFwHyBcRUIvX9wvqnl3b5d1qexRG3s9Zg": "Sounds of Concepts",
    "PLFwHyBcRUIvXGtW_B_sYFEAOz91CCBoKS": "Sounds of Moods",
}


def get_credentials():
    """Get YouTube API credentials from env (GitHub Actions) or local file."""
    # GitHub Actions: credentials from secrets
    token_b64 = os.environ.get("YOUTUBE_TOKEN")
    if token_b64:
        token_data = base64.b64decode(token_b64)
        creds = pickle.loads(token_data)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds

    # Local: use token file
    token_paths = [
        "D:/Yedekler/UCS/Sounds/yt_token_analysis.pickle",
        "D:/Yedekler/UCS/Sounds/Sounds of Concepts Vol.1 Study Music/yt_token.pickle",
    ]
    for path in token_paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                creds = pickle.load(f)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(path, "wb") as f:
                    pickle.dump(creds, f)
            return creds

    raise RuntimeError("No YouTube credentials found")


def parse_duration(iso_dur):
    """Convert ISO 8601 duration (PT1H32M5S) to seconds."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_dur or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def format_duration(seconds):
    """Format seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m"


def fetch_channel_data(youtube):
    """Fetch channel statistics."""
    resp = youtube.channels().list(
        part="statistics,snippet,brandingSettings",
        id=CHANNEL_ID,
    ).execute()
    item = resp["items"][0]
    stats = item["statistics"]
    return {
        "name": item["snippet"]["title"],
        "description": item["snippet"].get("description", ""),
        "subscriberCount": int(stats.get("subscriberCount", 0)),
        "viewCount": int(stats.get("viewCount", 0)),
        "videoCount": int(stats.get("videoCount", 0)),
        "customUrl": item["snippet"].get("customUrl", ""),
    }


def fetch_all_videos(youtube):
    """Fetch all videos with details using uploads playlist (catches Shorts too)."""
    # Uploads playlist ID = channel ID with "UC" replaced by "UU"
    uploads_playlist = CHANNEL_ID.replace("UC", "UU", 1)

    video_ids = []
    next_page = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist,
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for item in resp["items"]:
            video_ids.append(item["contentDetails"]["videoId"])
        next_page = resp.get("nextPageToken")
        if not next_page:
            break

    if not video_ids:
        return []

    # Step 2: Get detailed info for all videos (batch of 50)
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(batch),
        ).execute()
        for item in resp["items"]:
            duration_sec = parse_duration(item["contentDetails"]["duration"])
            stats = item.get("statistics", {})
            vid = {
                "id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"].get("description", "")[:200],
                "publishedAt": item["snippet"]["publishedAt"],
                "thumbnail": f"https://img.youtube.com/vi/{item['id']}/mqdefault.jpg",
                "thumbnailHQ": f"https://img.youtube.com/vi/{item['id']}/maxresdefault.jpg",
                "duration": duration_sec,
                "durationFormatted": format_duration(duration_sec),
                "viewCount": int(stats.get("viewCount", 0)),
                "likeCount": int(stats.get("likeCount", 0)),
                "isShort": duration_sec <= 62,
            }
            videos.append(vid)

    # Sort by publish date (newest first)
    videos.sort(key=lambda v: v["publishedAt"], reverse=True)
    return videos


def fetch_playlists(youtube):
    """Fetch playlist data."""
    playlists = []
    for pl_id, pl_name in PLAYLISTS.items():
        try:
            resp = youtube.playlists().list(
                part="snippet,contentDetails",
                id=pl_id,
            ).execute()
            if resp["items"]:
                item = resp["items"][0]
                playlists.append({
                    "id": pl_id,
                    "title": item["snippet"]["title"],
                    "seriesName": pl_name,
                    "itemCount": item["contentDetails"]["itemCount"],
                    "thumbnail": item["snippet"]["thumbnails"].get(
                        "high", item["snippet"]["thumbnails"].get("default", {})
                    ).get("url", ""),
                })
        except Exception as e:
            print(f"  Warning: Could not fetch playlist {pl_name}: {e}")
            playlists.append({
                "id": pl_id,
                "title": pl_name,
                "seriesName": pl_name,
                "itemCount": 0,
                "thumbnail": "",
            })
    return playlists


def main():
    print("Fetching YouTube channel data...")
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    # Fetch all data
    channel = fetch_channel_data(youtube)
    print(f"  Channel: {channel['name']} — {channel['subscriberCount']} subs, {channel['viewCount']} views")

    videos = fetch_all_videos(youtube)
    long_form = [v for v in videos if not v["isShort"]]
    shorts = [v for v in videos if v["isShort"]]
    print(f"  Videos: {len(long_form)} long-form, {len(shorts)} shorts")

    playlists = fetch_playlists(youtube)
    print(f"  Playlists: {len(playlists)}")

    # Build data object
    data = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel": channel,
        "videos": long_form,
        "shorts": shorts,
        "playlists": playlists,
        "stats": {
            "totalTracks": 80,  # Known from DistroKid
            "totalAlbums": 6,
            "totalNations": 195,
        },
    }

    # Write JSON
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "channel.json")
    out_path = os.path.normpath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  Written to {out_path}")
    print("Done!")


if __name__ == "__main__":
    main()
