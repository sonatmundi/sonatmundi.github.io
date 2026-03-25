"""
Trend Scanner — Deep YouTube trend analysis for content opportunities.

Scans trending videos, competitor channels, and search volume
in meditation/ambient/healing music niches.
Uses Claude AI to generate actionable content recommendations.
"""

import json
import os
from datetime import datetime

import anthropic

from . import auth, config

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Competitor channels to monitor
COMPETITOR_CHANNELS = [
    "UCjFl-7N1lKo5AHBnH9MlMdw",  # Meditative Mind
    "UCqbH-KnJ6hOQXxQOr7TQxnA",  # Yellow Brick Cinema
    "UCN1XdPml9NnKjnAKAtKp5Pg",  # Healing Meditation
    "UCUDt4yvREAq5IjrWQMHsMBg",  # PowerThoughts Meditation Club
]

# Search queries to monitor
NICHE_QUERIES = [
    "sleep music 8 hours 2026",
    "432 hz healing frequency",
    "528 hz dna repair music",
    "solfeggio frequencies all 9",
    "ancient civilization music",
    "sufi meditation music",
    "celtic meditation music",
    "tibetan singing bowls",
    "binaural beats deep sleep",
    "study music lo-fi ambient",
    "emotional healing piano",
    "chakra cleansing music",
    "indian raga meditation",
    "japanese zen music",
    "persian ambient music",
    "world music ambient relaxing",
    "stress relief music 2026",
    "anxiety relief music",
    "baby sleep music",
    "focus music for coding",
]


def _search_trending(youtube, query, max_results=5):
    """Search for trending videos in a niche."""
    try:
        resp = youtube.search().list(
            part="snippet", q=query, type="video",
            maxResults=max_results, order="viewCount",
            publishedAfter=(datetime.utcnow().replace(day=1)).strftime("%Y-%m-%dT00:00:00Z"),
        ).execute()

        video_ids = [item["id"]["videoId"] for item in resp.get("items", [])]
        if not video_ids:
            return []

        # Get full stats
        vids = youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(video_ids)
        ).execute()

        results = []
        for v in vids.get("items", []):
            stats = v["statistics"]
            results.append({
                "title": v["snippet"]["title"],
                "channel": v["snippet"]["channelTitle"],
                "video_id": v["id"],
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "duration": v["contentDetails"]["duration"],
                "published": v["snippet"]["publishedAt"][:10],
                "tags": v["snippet"].get("tags", [])[:10],
            })
        return results
    except Exception as e:
        print(f"  Error searching '{query}': {e}")
        return []


def _get_competitor_recent(youtube, channel_id, max_results=5):
    """Get recent videos from a competitor channel."""
    try:
        resp = youtube.search().list(
            part="snippet", channelId=channel_id, type="video",
            maxResults=max_results, order="date",
        ).execute()

        video_ids = [item["id"]["videoId"] for item in resp.get("items", [])]
        if not video_ids:
            return []

        vids = youtube.videos().list(
            part="snippet,statistics", id=",".join(video_ids)
        ).execute()

        results = []
        for v in vids.get("items", []):
            stats = v["statistics"]
            results.append({
                "title": v["snippet"]["title"],
                "channel": v["snippet"]["channelTitle"],
                "views": int(stats.get("viewCount", 0)),
                "published": v["snippet"]["publishedAt"][:10],
            })
        return results
    except Exception as e:
        print(f"  Error fetching competitor {channel_id}: {e}")
        return []


def scan_trends():
    """Run full trend scan and generate recommendations."""
    youtube = auth.youtube_service()

    print("Scanning YouTube trends...\n")

    # 1. Search trending videos in each niche
    trending_data = {}
    for query in NICHE_QUERIES:
        print(f"  Searching: {query}")
        trending_data[query] = _search_trending(youtube, query)

    # 2. Monitor competitors
    competitor_data = {}
    for ch_id in COMPETITOR_CHANNELS:
        recent = _get_competitor_recent(youtube, ch_id)
        if recent:
            ch_name = recent[0]["channel"]
            competitor_data[ch_name] = recent
            print(f"  Competitor: {ch_name} ({len(recent)} recent)")

    # 3. Get our own videos for comparison
    channel_id = config.channel_id()
    ch = youtube.channels().list(part="contentDetails,statistics", id=channel_id).execute()
    our_stats = ch["items"][0]["statistics"]

    # 4. Claude AI analysis
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    prompt = f"""You are a YouTube growth strategist for Sonat Mundi, a meditation/ambient music channel.

OUR CHANNEL STATS:
- Subscribers: {our_stats.get('subscriberCount', '?')}
- Total views: {our_stats.get('viewCount', '?')}
- Videos: {our_stats.get('videoCount', '?')}

CONTENT PILLARS:
1. Sounds of World — ancient civilizations, Silk Road, ethnic music
2. Sounds of Frequencies — Solfeggio, 432Hz, 528Hz, binaural
3. Sounds of Concepts — study, sleep, meditation, focus
4. Sounds of Moods — emotional instrumental journeys
5. Sounds of Sleep — 8-hour deep sleep music

TRENDING VIDEOS BY NICHE (this month):
{json.dumps(trending_data, indent=2)}

COMPETITOR RECENT UPLOADS:
{json.dumps(competitor_data, indent=2)}

TASK: Analyze trends and provide:

1. "trend_summary": 3-5 key observations about what's trending now
2. "opportunities": top 10 video ideas ranked by potential, each with:
   - "title": SEO-optimized title (ready to use)
   - "series": which content pillar it belongs to
   - "format": "long-form" or "8-hour" or "shorts-series"
   - "why": why this will perform well (data-backed reasoning)
   - "target_keywords": 5-7 search terms to target
   - "estimated_potential": "very high", "high", "medium"
   - "competitor_gap": what competitors are missing that we can exploit
3. "avoid": topics/formats that are oversaturated
4. "timing_advice": best upload schedule based on trends

Return ONLY valid JSON object."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        analysis = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        analysis = json.loads(text[start:end])

    # Save full report
    report = {
        "date": datetime.utcnow().isoformat(),
        "trending_data": trending_data,
        "competitor_data": competitor_data,
        "our_stats": our_stats,
        "analysis": analysis,
    }

    report_path = os.path.join(REPORTS_DIR, f"trend_scan_{datetime.utcnow():%Y%m%d}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved: {report_path}")

    # Print summary
    print("\n=== TREND OZETI ===")
    for obs in analysis.get("trend_summary", []):
        print(f"  • {obs}")

    print("\n=== TOP FIRSATLAR ===")
    for i, opp in enumerate(analysis.get("opportunities", [])[:10], 1):
        print(f"  {i}. [{opp.get('estimated_potential', '?')}] {opp['title'][:60]}")
        print(f"     Seri: {opp.get('series', '?')} | Format: {opp.get('format', '?')}")

    return report


if __name__ == "__main__":
    scan_trends()
