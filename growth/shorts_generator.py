"""
Shorts Generator — Analyze channel videos and recommend/generate Shorts content.

Uses Claude AI to analyze video performance and suggest optimal Shorts:
- Best timestamp segments for each video
- SEO-optimized titles with #Shorts
- Engagement-focused descriptions
- Trending tag suggestions

Note: Actual video rendering requires FFmpeg (done locally, not in CI).
This module generates the metadata and cut-list for Shorts.
"""

import json
import os
from datetime import datetime

import anthropic

from . import auth, config

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _get_all_videos(youtube):
    """Fetch all long-form videos from the channel."""
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


def _is_short(video):
    """Check if a video is already a Short (vertical, <60s)."""
    dur = video["contentDetails"]["duration"]
    # Shorts are typically PT30S to PT59S
    if "H" in dur or "M" in dur:
        return False
    return True


def generate_shorts_plan():
    """Analyze all long-form videos and generate a Shorts content plan."""
    youtube = auth.youtube_service()
    videos = _get_all_videos(youtube)

    # Separate long-form from Shorts
    long_form = [v for v in videos if not _is_short(v)]
    existing_shorts = [v for v in videos if _is_short(v)]

    print(f"Long-form videos: {len(long_form)}")
    print(f"Existing Shorts: {len(existing_shorts)}")

    # Build context for Claude
    video_summaries = []
    for v in long_form:
        stats = v["statistics"]
        video_summaries.append({
            "title": v["snippet"]["title"],
            "video_id": v["id"],
            "duration": v["contentDetails"]["duration"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "tags": v["snippet"].get("tags", [])[:15],
        })

    existing_titles = [s["snippet"]["title"] for s in existing_shorts]

    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    prompt = f"""You are a YouTube Shorts strategy expert for Sonat Mundi, a meditation/ambient music channel.

CHANNEL VIDEOS (long-form):
{json.dumps(video_summaries, indent=2)}

EXISTING SHORTS (already created — DO NOT duplicate):
{json.dumps(existing_titles, indent=2)}

TASK: Generate a Shorts content plan. For each long-form video, suggest 2-3 NEW Shorts that haven't been made yet.

For each Short, provide:
1. "source_video_id": the parent video ID
2. "start_time": suggested start timestamp (MM:SS format)
3. "duration": 45-55 seconds
4. "title": SEO-optimized, engaging, must include #Shorts
5. "description": 2-3 lines + call to action to watch full video
6. "tags": 7-10 relevant tags
7. "hook": the first 3 seconds — what text/visual hook would grab attention
8. "priority": "high", "medium", or "low" based on parent video performance

Focus on:
- Trending topics (frequencies, sleep, ancient civilizations)
- Emotional hooks ("This sound is 12,000 years old", "Can't sleep?")
- Numbers and specific claims ("528 Hz repairs DNA")
- Questions ("Have you ever heard music from ancient Persia?")

Return ONLY valid JSON array. No markdown, no explanation."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        plan = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        text = response.content[0].text
        start = text.find("[")
        end = text.rfind("]") + 1
        plan = json.loads(text[start:end])

    # Save plan
    report = {
        "date": datetime.utcnow().isoformat(),
        "long_form_count": len(long_form),
        "existing_shorts_count": len(existing_shorts),
        "new_shorts_suggested": len(plan),
        "shorts_plan": plan,
    }

    report_path = os.path.join(REPORTS_DIR, f"shorts_plan_{datetime.utcnow():%Y%m%d}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nGenerated {len(plan)} Shorts suggestions")
    print(f"Report saved: {report_path}")

    # Print summary
    for i, s in enumerate(plan, 1):
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s.get("priority", ""), "")
        print(f"  {i}. {priority_icon} {s['title'][:60]}")

    return report


if __name__ == "__main__":
    generate_shorts_plan()
