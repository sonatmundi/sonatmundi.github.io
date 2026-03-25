"""
Title Optimizer — SEO-focused title generation and optimization.

Analyzes current video titles against trending search terms,
competitor titles, and YouTube SEO best practices.
Generates optimized title alternatives using Claude AI.
"""

import json
import os
from datetime import datetime

import anthropic

from . import auth, config

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _get_all_videos(youtube):
    """Fetch all videos with full metadata."""
    channel_id = config.channel_id()
    ch = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    uploads_pl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids = []
    next_page = None
    while True:
        pl = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_pl, maxResults=50, pageToken=next_page
        ).execute()
        for item in pl["items"]:
            video_ids.append(item["contentDetails"]["videoId"])
        next_page = pl.get("nextPageToken")
        if not next_page:
            break

    all_videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        vids = youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(batch)
        ).execute()
        all_videos.extend(vids["items"])
    return all_videos


def _search_competitors(youtube, query, max_results=10):
    """Search YouTube for competitor videos in our niche."""
    try:
        resp = youtube.search().list(
            part="snippet", q=query, type="video", maxResults=max_results,
            order="viewCount", videoCategoryId="10",
        ).execute()
        return [
            {
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "video_id": item["id"]["videoId"],
            }
            for item in resp.get("items", [])
        ]
    except Exception as e:
        print(f"  Search error for '{query}': {e}")
        return []


def optimize_titles(apply_changes=False):
    """Analyze and optimize all video titles."""
    youtube = auth.youtube_service()
    videos = _get_all_videos(youtube)

    print(f"Analyzing {len(videos)} videos...")

    # Search for competitor titles in key niches
    search_queries = [
        "sleep music 8 hours",
        "528 hz healing frequency",
        "meditation music ancient",
        "study music focus",
        "world music ambient",
        "solfeggio frequencies complete",
        "emotional healing instrumental",
    ]

    competitor_data = {}
    for query in search_queries:
        results = _search_competitors(youtube, query)
        competitor_data[query] = results
        print(f"  Found {len(results)} competitors for '{query}'")

    # Build video info for Claude
    video_info = []
    for v in videos:
        stats = v["statistics"]
        video_info.append({
            "video_id": v["id"],
            "current_title": v["snippet"]["title"],
            "description_first_line": v["snippet"].get("description", "")[:150],
            "tags": v["snippet"].get("tags", [])[:10],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "duration": v["contentDetails"]["duration"],
        })

    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    prompt = f"""You are a YouTube SEO expert specializing in meditation, ambient, and healing music channels.

CHANNEL: Sonat Mundi — United Colours of Sound
BRAND SUFFIX: Always end titles with "| Sonat Mundi"

CURRENT VIDEOS:
{json.dumps(video_info, indent=2)}

COMPETITOR TITLES (top performing in our niches):
{json.dumps(competitor_data, indent=2)}

TASK: For each video, analyze the current title and provide:

1. "video_id": the video ID
2. "current_title": existing title
3. "seo_score": 1-10 rating of current title
4. "issues": list of SEO problems (missing keywords, too long, poor structure)
5. "optimized_title": the best SEO-optimized alternative (max 100 chars)
6. "alternative_titles": 2 more options
7. "missing_tags": tags that should be added
8. "optimized_description_first_line": the most important line for search
9. "priority": "critical", "high", "medium", "low"

YOUTUBE TITLE SEO RULES:
- Primary keyword first (e.g., "8 Hour Sleep Music" not "Velvet Silence 8 Hour...")
- Include numbers, durations, and specific terms (Hz values, instrument names)
- Use power words: "Deep", "Ultimate", "Pure", "Sacred", "Ancient"
- Emotional triggers: "Relief", "Healing", "Transform", "Unlock"
- Keep under 70 chars for full visibility on mobile
- Use ✦ ❖ ❆ separators (already doing this — good)
- Brand always last: "| Sonat Mundi"

Return ONLY valid JSON array."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        results = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        text = response.content[0].text
        start = text.find("[")
        end = text.rfind("]") + 1
        results = json.loads(text[start:end])

    # Apply changes if requested
    if apply_changes:
        for item in results:
            if item.get("priority") in ("critical", "high") and item.get("optimized_title"):
                vid_id = item["video_id"]
                new_title = item["optimized_title"]
                try:
                    # Get current snippet
                    vid = youtube.videos().list(part="snippet", id=vid_id).execute()
                    if vid["items"]:
                        snippet = vid["items"][0]["snippet"]
                        snippet["title"] = new_title
                        # Add missing tags
                        existing_tags = snippet.get("tags", [])
                        for tag in item.get("missing_tags", []):
                            if tag not in existing_tags:
                                existing_tags.append(tag)
                        snippet["tags"] = existing_tags[:500]  # YouTube limit

                        youtube.videos().update(
                            part="snippet",
                            body={"id": vid_id, "snippet": snippet}
                        ).execute()
                        print(f"  ✓ Updated: {new_title[:60]}")
                except Exception as e:
                    print(f"  ✗ Error updating {vid_id}: {e}")

    # Save report
    report = {
        "date": datetime.utcnow().isoformat(),
        "videos_analyzed": len(videos),
        "changes_applied": apply_changes,
        "optimizations": results,
    }

    report_path = os.path.join(REPORTS_DIR, f"title_optimization_{datetime.utcnow():%Y%m%d}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved: {report_path}")

    # Summary
    for item in results:
        priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            item.get("priority", ""), ""
        )
        score = item.get("seo_score", "?")
        print(f"  {priority_icon} [{score}/10] {item['current_title'][:50]}")
        if item.get("optimized_title") != item.get("current_title"):
            print(f"         → {item['optimized_title'][:50]}")

    return report


if __name__ == "__main__":
    import sys
    apply = "--apply" in sys.argv
    optimize_titles(apply_changes=apply)
