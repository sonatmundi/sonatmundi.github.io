#!/usr/bin/env python3
"""
SEO Optimizer — AI-powered title, description, and tag optimization.

Uses Claude API to generate YouTube-optimized metadata for Sonat Mundi videos.
Can audit existing videos or generate metadata for new uploads.

Usage:
    python -m growth.seo_optimizer                      # audit all videos
    python -m growth.seo_optimizer --video VIDEO_ID     # audit one video
    python -m growth.seo_optimizer --generate album.json  # generate for new album
"""

import argparse
import json
import os
import sys
from datetime import datetime

import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from growth import config, auth

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
CHANNEL_ID = config.channel_id()

BRAND_CONTEXT = """\
Channel: Sonat Mundi — United Colours of Sound
Tagline: Omnia Resonant (All things resonate)
Content pillars:
  1. Sounds of World — authentic world music from 195 nations
  2. Sounds of Moods — instrumental journeys through human emotions
  3. Sounds of Concepts — study, sleep, meditation, focus music
  4. Sounds of Frequencies — 432 Hz, 528 Hz, Solfeggio, Binaural healing

Title format: "Series Vol.X ✶ Subtitle ✶ Genre Description | Sonat Mundi"
Title max: 100 characters (YouTube limit)
Tags max: 500 characters total
Description must include: tracklist with timestamps, instrument list, about section, links.
All content must be YouTube monetization-compliant.
Target audience: meditation, healing, world music, ambient music listeners."""


def _get_client():
    return anthropic.Anthropic(api_key=config.anthropic_api_key())


def fetch_video_metadata(youtube, video_ids=None):
    """Fetch current metadata for channel videos."""
    if video_ids:
        ids_str = ",".join(video_ids)
        resp = youtube.videos().list(part="snippet,statistics", id=ids_str).execute()
    else:
        # Get all uploads
        ch = youtube.channels().list(part="contentDetails", id=CHANNEL_ID).execute()
        uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        resp_pl = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_id, maxResults=50
        ).execute()
        ids = [item["contentDetails"]["videoId"] for item in resp_pl["items"]]
        resp = youtube.videos().list(
            part="snippet,statistics", id=",".join(ids)
        ).execute()
    return resp.get("items", [])


def audit_seo(videos):
    """Use Claude to audit SEO for existing videos and suggest improvements."""
    client = _get_client()

    video_data = []
    for v in videos:
        s = v["snippet"]
        st = v.get("statistics", {})
        video_data.append({
            "id": v["id"],
            "title": s["title"],
            "description": s["description"][:500],
            "tags": s.get("tags", []),
            "views": st.get("viewCount", "0"),
            "likes": st.get("likeCount", "0"),
        })

    prompt = f"""{BRAND_CONTEXT}

Analyze these YouTube videos and provide SEO optimization suggestions.
For EACH video, evaluate:
1. Title: keyword density, search appeal, length, special characters
2. Tags: missing high-volume keywords, competitor analysis suggestions
3. Description: first 2 lines (shown in search), keyword placement, CTA

Return a JSON array with this structure for each video:
[{{
  "video_id": "...",
  "current_title": "...",
  "suggested_title": "...",
  "title_score": 1-10,
  "missing_tags": ["tag1", "tag2"],
  "suggested_tags": ["tag1", "tag2", ...],
  "description_tips": ["tip1", "tip2"],
  "overall_score": 1-10,
  "priority": "high/medium/low"
}}]

Videos to audit:
{json.dumps(video_data, indent=2, ensure_ascii=False)}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def generate_metadata(album_info):
    """Generate SEO-optimized metadata for a new album upload."""
    client = _get_client()

    prompt = f"""{BRAND_CONTEXT}

Generate YouTube-optimized metadata for this NEW album:
{json.dumps(album_info, indent=2, ensure_ascii=False)}

Return a JSON object:
{{
  "title": "optimized title (max 100 chars)",
  "description": "full description with tracklist, timestamps, instruments, about section",
  "tags": ["tag1", "tag2", ...],
  "category": "10",
  "thumbnail_text_suggestions": ["text overlay 1", "text overlay 2"]
}}

Rules:
- Title must follow format: "Series Vol.X ✶ Subtitle ✶ Genre | Sonat Mundi"
- First 2 lines of description are most critical (shown in YouTube search)
- Include ALL relevant long-tail keywords in tags
- Tags total must be under 500 characters
- Description must end with the standard Sonat Mundi about section and links"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def save_report(content, report_type="seo_audit"):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(REPORTS_DIR, f"{report_type}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Report saved: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="Sonat Mundi SEO Optimizer")
    parser.add_argument("--video", help="Audit specific video ID")
    parser.add_argument("--generate", help="Path to album info JSON for new metadata")
    parser.add_argument("--all", action="store_true", help="Audit all channel videos")
    args = parser.parse_args()

    if args.generate:
        with open(args.generate, encoding="utf-8") as f:
            album_info = json.load(f)
        result = generate_metadata(album_info)
        save_report(result, "seo_generated")
        print(result)
        return

    youtube = auth.youtube_service()
    video_ids = [args.video] if args.video else None
    videos = fetch_video_metadata(youtube, video_ids)

    if not videos:
        print("No videos found.")
        return

    print(f"Auditing {len(videos)} videos...")
    result = audit_seo(videos)
    save_report(result)
    print(result)


if __name__ == "__main__":
    main()
