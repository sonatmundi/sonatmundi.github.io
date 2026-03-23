#!/usr/bin/env python3
"""
Trending Analyzer — Discovers trending topics in the meditation/world music niche.

Uses YouTube Data API to find trending videos in relevant categories,
then uses Claude to analyze patterns and suggest content opportunities.

Usage:
    python -m growth.trending_analyzer                # full analysis
    python -m growth.trending_analyzer --competitors  # competitor analysis
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

# Competitor channels and search queries for niche analysis
NICHE_QUERIES = [
    "meditation music 2026",
    "healing frequencies",
    "world music ambient",
    "solfeggio frequencies",
    "binaural beats sleep",
    "528 hz music",
    "432 hz music",
    "study music lofi",
    "ancient music ambient",
    "tibetan singing bowls",
    "sufi music meditation",
    "indian raga ambient",
]

COMPETITOR_CHANNELS = [
    "Meditative Mind",
    "Yellow Brick Cinema",
    "Healing Vibrations",
    "PowerThoughts Meditation Club",
    "Nu Meditation Music",
]


def search_trending(youtube, query, max_results=10):
    """Search YouTube for recent trending videos matching a query."""
    resp = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        order="viewCount",
        publishedAfter=(
            datetime(datetime.now().year, datetime.now().month, 1).isoformat() + "Z"
        ),
        maxResults=max_results,
        relevanceLanguage="en",
    ).execute()

    video_ids = [item["id"]["videoId"] for item in resp.get("items", [])]
    if not video_ids:
        return []

    # Get detailed stats
    details = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids),
    ).execute()

    results = []
    for item in details.get("items", []):
        s = item["snippet"]
        st = item.get("statistics", {})
        results.append({
            "id": item["id"],
            "title": s["title"],
            "channel": s["channelTitle"],
            "published": s["publishedAt"],
            "views": int(st.get("viewCount", 0)),
            "likes": int(st.get("likeCount", 0)),
            "comments": int(st.get("commentCount", 0)),
            "tags": s.get("tags", [])[:15],
            "duration": item["contentDetails"]["duration"],
        })

    return sorted(results, key=lambda x: x["views"], reverse=True)


def analyze_competitors(youtube):
    """Search for competitor channels and analyze their recent uploads."""
    all_results = []
    for ch_name in COMPETITOR_CHANNELS:
        resp = youtube.search().list(
            part="snippet",
            q=ch_name,
            type="channel",
            maxResults=1,
        ).execute()

        if not resp.get("items"):
            continue

        ch_id = resp["items"][0]["snippet"]["channelId"]

        # Get their recent videos
        videos = youtube.search().list(
            part="snippet",
            channelId=ch_id,
            type="video",
            order="date",
            maxResults=5,
        ).execute()

        video_ids = [v["id"]["videoId"] for v in videos.get("items", [])]
        if video_ids:
            details = youtube.videos().list(
                part="snippet,statistics",
                id=",".join(video_ids),
            ).execute()

            for item in details.get("items", []):
                s = item["snippet"]
                st = item.get("statistics", {})
                all_results.append({
                    "channel": ch_name,
                    "title": s["title"],
                    "views": int(st.get("viewCount", 0)),
                    "tags": s.get("tags", [])[:10],
                })

    return all_results


def ai_analysis(trending_data, competitor_data=None):
    """Use Claude to analyze trends and suggest content opportunities."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    data_summary = {
        "trending_by_query": trending_data,
        "competitors": competitor_data or [],
    }

    prompt = f"""You are a YouTube growth strategist for Sonat Mundi, a meditation/world music channel.

Channel pillars:
1. Sounds of World — authentic world music (195 nations)
2. Sounds of Moods — instrumental emotional journeys
3. Sounds of Concepts — study, sleep, focus music
4. Sounds of Frequencies — 432Hz, 528Hz, Solfeggio, Binaural

Analyze this trending data and provide:

1. **TOP 5 CONTENT OPPORTUNITIES** — specific album/video ideas that match current trends
   and fit our brand. Include suggested title, series, and why it would work.

2. **TRENDING KEYWORDS** — top 20 keywords we should target in our next uploads.

3. **COMPETITOR GAPS** — what competitors are doing that we're not, and vice versa.

4. **UPLOAD TIMING** — based on competitor publishing patterns, when should we upload?

5. **THUMBNAIL PATTERNS** — common visual elements in high-performing thumbnails.

Return as structured JSON:
{{
  "opportunities": [...],
  "keywords": [...],
  "competitor_gaps": [...],
  "timing_advice": "...",
  "thumbnail_patterns": [...]
}}

Data:
{json.dumps(data_summary, indent=2, ensure_ascii=False)[:8000]}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Sonat Mundi Trending Analyzer")
    parser.add_argument("--competitors", action="store_true", help="Include competitor analysis")
    args = parser.parse_args()

    youtube = auth.youtube_service()

    # Gather trending data
    print("Searching trending videos in our niche...")
    trending_data = {}
    for query in NICHE_QUERIES:
        print(f"  Searching: {query}")
        results = search_trending(youtube, query, max_results=5)
        trending_data[query] = results

    competitor_data = None
    if args.competitors:
        print("\nAnalyzing competitors...")
        competitor_data = analyze_competitors(youtube)

    # AI analysis
    print("\nRunning AI analysis...")
    report = ai_analysis(trending_data, competitor_data)

    # Save
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(REPORTS_DIR, f"trending_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved: {path}")
    print(report)


if __name__ == "__main__":
    main()
