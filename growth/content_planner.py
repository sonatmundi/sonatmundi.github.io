#!/usr/bin/env python3
"""
Content Planner — AI-powered content calendar and album planning.

Combines analytics data, trending analysis, and channel performance
to suggest the optimal content roadmap for Sonat Mundi.

Usage:
    python -m growth.content_planner                  # generate next month plan
    python -m growth.content_planner --weeks 8        # plan for 8 weeks ahead
    python -m growth.content_planner --next-album     # suggest next album details
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


def fetch_channel_stats(youtube):
    """Gather current channel state for planning context."""
    ch = youtube.channels().list(
        part="snippet,statistics,contentDetails", id=CHANNEL_ID
    ).execute()

    channel = ch["items"][0]
    stats = channel["statistics"]

    # Get all video titles
    uploads_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    pl_resp = youtube.playlistItems().list(
        part="snippet", playlistId=uploads_id, maxResults=50
    ).execute()

    videos = []
    for item in pl_resp["items"]:
        s = item["snippet"]
        videos.append({
            "title": s["title"],
            "published": s["publishedAt"],
        })

    return {
        "channel_name": channel["snippet"]["title"],
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "total_videos": int(stats.get("videoCount", 0)),
        "existing_videos": videos,
    }


def fetch_performance_data(youtube, analytics):
    """Get per-video performance for content strategy."""
    ch = youtube.channels().list(part="contentDetails", id=CHANNEL_ID).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl_resp = youtube.playlistItems().list(
        part="contentDetails", playlistId=uploads_id, maxResults=50
    ).execute()
    video_ids = [item["contentDetails"]["videoId"] for item in pl_resp["items"]]

    if not video_ids:
        return []

    details = youtube.videos().list(
        part="snippet,statistics", id=",".join(video_ids)
    ).execute()

    perf = []
    for item in details.get("items", []):
        s = item["snippet"]
        st = item.get("statistics", {})
        perf.append({
            "title": s["title"],
            "views": int(st.get("viewCount", 0)),
            "likes": int(st.get("likeCount", 0)),
            "comments": int(st.get("commentCount", 0)),
            "published": s["publishedAt"],
        })

    return sorted(perf, key=lambda x: x["views"], reverse=True)


def generate_content_plan(channel_stats, performance, weeks=4):
    """Use Claude to create an optimal content plan."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    prompt = f"""You are a YouTube content strategist for Sonat Mundi.

Channel pillars:
1. Sounds of World — authentic world music from 195 nations
2. Sounds of Moods — instrumental journeys (emotions)
3. Sounds of Concepts — study, sleep, meditation, focus
4. Sounds of Frequencies — 432Hz, 528Hz, Solfeggio, Binaural

Current channel state:
{json.dumps(channel_stats, indent=2, ensure_ascii=False)}

Performance data (by views):
{json.dumps(performance[:10], indent=2, ensure_ascii=False)}

Create a {weeks}-week content plan. For each week, suggest:
1. Album title and series
2. Number of tracks (10-15)
3. Track themes/titles
4. Target keywords
5. Best upload day and time
6. Cross-promotion strategy

Also suggest:
- Which series to prioritize based on performance
- Seasonal/trending opportunities
- Collaboration or playlist strategies

Return as JSON:
{{
  "strategy_summary": "overall strategy in 3 sentences",
  "weekly_plan": [
    {{
      "week": 1,
      "upload_date": "YYYY-MM-DD",
      "album_title": "...",
      "series": "Sounds of ...",
      "track_count": 15,
      "tracks": ["Track 1 Title", ...],
      "keywords": ["kw1", "kw2"],
      "notes": "why this week"
    }}
  ],
  "series_priority": ["series ranked by recommended focus"],
  "seasonal_opportunities": ["..."],
  "growth_tactics": ["tactic 1", "tactic 2"]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def suggest_next_album(channel_stats, performance):
    """Generate detailed specs for the next album."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    prompt = f"""You are a creative director for Sonat Mundi, a world music channel.

Existing content:
{json.dumps([v['title'] for v in channel_stats['existing_videos']], indent=2, ensure_ascii=False)}

Performance (top to bottom):
{json.dumps(performance[:10], indent=2, ensure_ascii=False)}

Design the NEXT album in complete detail:

Return JSON:
{{
  "series": "Sounds of ...",
  "volume": "Vol.X",
  "title": "Album Title",
  "subtitle": "Creative Subtitle",
  "concept": "2-3 sentence album concept",
  "track_count": 15,
  "tracks": [
    {{
      "number": 1,
      "title": "Track Title",
      "subtitle": "Description",
      "instruments": ["instrument1", "instrument2"],
      "mood": "mood description",
      "duration_minutes": 5,
      "production_notes": "key sounds and textures"
    }}
  ],
  "youtube_title": "SEO-optimized title (max 100 chars)",
  "youtube_tags": ["tag1", "tag2"],
  "cover_art_direction": "visual concept for 15 cover images",
  "target_audience": "who this album is for"
}}

Base the suggestion on:
- What series is underrepresented
- What's performing best
- Seasonal relevance
- Keyword gaps"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Sonat Mundi Content Planner")
    parser.add_argument("--weeks", type=int, default=4, help="Weeks to plan ahead")
    parser.add_argument("--next-album", action="store_true", help="Design next album")
    args = parser.parse_args()

    youtube, analytics = auth.youtube_and_analytics()

    print("Fetching channel data...")
    channel_stats = fetch_channel_stats(youtube)
    performance = fetch_performance_data(youtube, analytics)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")

    if args.next_album:
        print("Designing next album...")
        result = suggest_next_album(channel_stats, performance)
        path = os.path.join(REPORTS_DIR, f"next_album_{ts}.json")
    else:
        print(f"Generating {args.weeks}-week content plan...")
        result = generate_content_plan(channel_stats, performance, args.weeks)
        path = os.path.join(REPORTS_DIR, f"content_plan_{ts}.json")

    with open(path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"\nSaved: {path}")
    print(result)


if __name__ == "__main__":
    main()
