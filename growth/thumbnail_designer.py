"""
Thumbnail Designer — Generate thumbnail design briefs and audit existing thumbnails.

Uses Claude AI to:
1. Analyze existing thumbnails for CTR optimization
2. Generate design briefs for new videos
3. Suggest improvements based on competitor analysis
4. Create a consistent brand visual language

Note: Actual image generation requires Pillow (done locally).
This module generates the design specifications and audit reports.
"""

import json
import os
from datetime import datetime

import anthropic

from . import auth, config

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _get_all_videos(youtube):
    """Fetch all videos with thumbnails."""
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


def _search_top_thumbnails(youtube, query, max_results=5):
    """Get top performing video thumbnails in a niche."""
    try:
        resp = youtube.search().list(
            part="snippet", q=query, type="video",
            maxResults=max_results, order="viewCount",
        ).execute()
        results = []
        for item in resp.get("items", []):
            thumbs = item["snippet"].get("thumbnails", {})
            high = thumbs.get("high", thumbs.get("medium", thumbs.get("default", {})))
            results.append({
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "thumbnail_url": high.get("url", ""),
            })
        return results
    except Exception:
        return []


def audit_and_design():
    """Audit existing thumbnails and generate design briefs for all videos."""
    youtube = auth.youtube_service()
    videos = _get_all_videos(youtube)

    print(f"Analyzing {len(videos)} video thumbnails...\n")

    # Get competitor thumbnails for reference
    competitor_thumbs = {}
    reference_queries = [
        "8 hour sleep music",
        "528 hz healing",
        "ancient meditation music",
        "study music ambient",
    ]
    for query in reference_queries:
        competitor_thumbs[query] = _search_top_thumbnails(youtube, query)

    # Build video info
    video_info = []
    for v in videos:
        stats = v["statistics"]
        thumbs = v["snippet"].get("thumbnails", {})
        high = thumbs.get("high", thumbs.get("medium", thumbs.get("default", {})))

        # Check if custom thumbnail exists
        has_custom = high.get("width", 0) >= 1280  # Custom thumbs are usually HD

        video_info.append({
            "video_id": v["id"],
            "title": v["snippet"]["title"],
            "duration": v["contentDetails"]["duration"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "thumbnail_url": high.get("url", ""),
            "has_custom_thumbnail": has_custom,
            "tags": v["snippet"].get("tags", [])[:5],
        })

    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    prompt = f"""You are a YouTube thumbnail design expert for Sonat Mundi, a meditation/ambient music channel.

BRAND IDENTITY:
- Colors: Deep blue, teal, gold accents, dark backgrounds
- Logo: Sonat Mundi with rainbow sound wave circle
- Style: Atmospheric, cosmic, peaceful, premium feel
- Font style: Clean, modern (Segoe UI family)

OUR VIDEOS:
{json.dumps(video_info, indent=2)}

TOP PERFORMING COMPETITOR THUMBNAILS:
{json.dumps(competitor_thumbs, indent=2)}

TASK: For each video, generate a thumbnail design brief:

1. "video_id": video ID
2. "title": video title
3. "has_custom": whether it already has a custom thumbnail
4. "current_score": 1-10 rating (estimate based on title/content match)
5. "priority": "critical" (no custom), "high", "medium", "low"
6. "design_brief":
   - "background": description of background image/mood
   - "color_palette": 3-4 hex colors
   - "text_elements": list of text overlays with position and size
   - "badge": any badge (e.g., "8 HOURS", "528 Hz", duration)
   - "badge_color": hex color for badge
   - "logo_position": where to place Sonat Mundi logo
   - "mood": the emotional feel (dark, mystical, peaceful, energetic)
   - "key_visual": the main visual element
7. "ctr_tips": 2-3 tips to maximize click-through rate
8. "avoid": what NOT to do for this type of content

THUMBNAIL BEST PRACTICES:
- Dark backgrounds for sleep/meditation (viewers browse at night)
- Large, readable text (visible on mobile)
- Maximum 5-7 words of text
- Strong contrast between text and background
- Avoid clutter — one clear focal point
- YouTube timestamp is bottom-right — keep that area clear
- Brand logo bottom-left (established pattern)
- Gold badge top-left for duration/frequency

Return ONLY valid JSON array."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        designs = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        text = response.content[0].text
        start = text.find("[")
        end = text.rfind("]") + 1
        designs = json.loads(text[start:end])

    # Save report
    report = {
        "date": datetime.utcnow().isoformat(),
        "videos_analyzed": len(videos),
        "designs": designs,
    }

    report_path = os.path.join(REPORTS_DIR, f"thumbnail_designs_{datetime.utcnow():%Y%m%d}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report saved: {report_path}")

    # Summary
    critical = sum(1 for d in designs if d.get("priority") == "critical")
    high = sum(1 for d in designs if d.get("priority") == "high")
    print(f"\n  Critical (no custom thumb): {critical}")
    print(f"  High priority: {high}")

    for d in designs:
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            d.get("priority", ""), ""
        )
        score = d.get("current_score", "?")
        print(f"  {icon} [{score}/10] {d['title'][:50]}")

    return report


if __name__ == "__main__":
    audit_and_design()
