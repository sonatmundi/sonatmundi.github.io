#!/usr/bin/env python3
"""
SEO Updater — Fetches current video metadata, generates AI-optimized versions,
and updates videos on YouTube.

Usage:
    python -m growth.seo_updater --dry-run    # show changes without applying
    python -m growth.seo_updater --apply       # apply changes to YouTube
"""

import argparse
import json
import os
import sys
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from growth import config, auth

CHANNEL_ID = config.channel_id()
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")

BRAND_CONTEXT = """\
Channel: Sonat Mundi — United Colours of Sound
Tagline: Omnia Resonant (All things resonate)

Content pillars:
  1. Sounds of World — authentic world music from 195 nations
  2. Sounds of Moods — instrumental journeys through human emotions
  3. Sounds of Concepts — study, sleep, meditation, focus music
  4. Sounds of Frequencies — 432 Hz, 528 Hz, Solfeggio, Binaural healing

About section (MUST appear at the end of every description):
---
About Sonat Mundi:
We create immersive soundscapes inspired by world music traditions, human emotions, healing frequencies and the poetry of everyday life.

🌍 SOUNDS OF WORLD — 195 nations, every tradition
🎭 SOUNDS OF MOODS — The full emotional spectrum
🎯 SOUNDS OF CONCEPTS — Study, sleep, meditation, movement
✨ SOUNDS OF FREQUENCIES — 432 Hz, 528 Hz, Solfeggio, Binaural

🌐 sonatmundi.com
📧 info@sonatmundi.com

© Sonat Mundi — United Colours of Sound
Omnia Resonant — All things resonate.
---

Rules:
- Title max 100 characters
- Title format: keep the existing decorative symbols (✦ ❖ ❆ etc.)
- Title MUST end with "| Sonat Mundi"
- Tags total max 500 characters, include long-tail keywords
- Description first 2 lines are CRITICAL (shown in YouTube search results)
- Description MUST keep the existing tracklist with timestamps EXACTLY as-is
- Only modify: first 2 lines, keyword density, add missing instrument/mood keywords
- Add CTA like "Subscribe for weekly healing music" before the About section
- ALL content must be YouTube monetization-compliant
"""


def fetch_all_videos(youtube):
    """Fetch full metadata for all channel videos."""
    ch = youtube.channels().list(part="contentDetails", id=CHANNEL_ID).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    pl_resp = youtube.playlistItems().list(
        part="contentDetails", playlistId=uploads_id, maxResults=50
    ).execute()
    video_ids = [item["contentDetails"]["videoId"] for item in pl_resp["items"]]

    resp = youtube.videos().list(
        part="snippet,statistics", id=",".join(video_ids)
    ).execute()

    return resp.get("items", [])


def generate_optimized_metadata(videos):
    """Use Claude to generate optimized metadata for all videos."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())

    video_data = []
    for v in videos:
        s = v["snippet"]
        st = v.get("statistics", {})
        video_data.append({
            "id": v["id"],
            "title": s["title"],
            "description": s["description"],
            "tags": s.get("tags", []),
            "categoryId": s.get("categoryId", "10"),
            "views": int(st.get("viewCount", 0)),
            "defaultLanguage": s.get("defaultLanguage", "en"),
        })

    prompt = f"""{BRAND_CONTEXT}

I need you to optimize the SEO metadata for these YouTube videos.
For EACH video, generate improved title, tags, and description.

CRITICAL RULES:
1. Keep existing tracklist timestamps EXACTLY as they are — do not modify any timestamp or track name
2. Only improve: title keywords, first 2 lines of description, tags, and add CTA before about section
3. Title must stay under 100 characters and end with "| Sonat Mundi"
4. Tags: add high-volume search keywords that are missing. Total under 500 chars.
5. Description: make first 2 lines extremely searchable and compelling
6. Keep the existing about section at the end

Return a JSON array:
[{{
  "id": "video_id",
  "original_title": "...",
  "new_title": "optimized title",
  "new_tags": ["tag1", "tag2", ...],
  "new_description": "full optimized description (keep tracklist intact)"
}}]

Videos:
{json.dumps(video_data, indent=2, ensure_ascii=False)}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return []


def show_diff(original, optimized):
    """Display changes in a readable format."""
    print(f"\n{'='*70}")
    print(f"  VIDEO: {original['snippet']['title'][:60]}")
    print(f"  ID: {original['id']}")
    print(f"{'='*70}")

    opt = None
    for o in optimized:
        if o["id"] == original["id"]:
            opt = o
            break

    if not opt:
        print("  (no changes)")
        return

    # Title diff
    old_title = original["snippet"]["title"]
    new_title = opt["new_title"]
    if old_title != new_title:
        print(f"\n  TITLE:")
        print(f"    OLD: {old_title}")
        print(f"    NEW: {new_title}")
        print(f"    LEN: {len(old_title)} -> {len(new_title)}")
    else:
        print(f"\n  TITLE: (unchanged)")

    # Tags diff
    old_tags = set(original["snippet"].get("tags", []))
    new_tags = set(opt.get("new_tags", []))
    added = new_tags - old_tags
    removed = old_tags - new_tags
    if added or removed:
        print(f"\n  TAGS:")
        if added:
            print(f"    ADDED: {', '.join(sorted(added))}")
        if removed:
            print(f"    REMOVED: {', '.join(sorted(removed))}")
        total_len = sum(len(t) for t in opt["new_tags"])
        print(f"    TOTAL LENGTH: {total_len}/500 chars")

    # Description first 2 lines
    old_desc_lines = original["snippet"]["description"].split("\n")[:2]
    new_desc_lines = opt.get("new_description", "").split("\n")[:2]
    print(f"\n  DESCRIPTION (first 2 lines):")
    print(f"    OLD: {' | '.join(old_desc_lines)}")
    print(f"    NEW: {' | '.join(new_desc_lines)}")


def apply_updates(youtube, videos, optimized):
    """Apply optimized metadata to YouTube videos."""
    success = 0
    for video in videos:
        opt = None
        for o in optimized:
            if o["id"] == video["id"]:
                opt = o
                break
        if not opt:
            continue

        snippet = video["snippet"].copy()
        snippet["title"] = opt["new_title"]
        snippet["tags"] = opt["new_tags"]
        snippet["description"] = opt["new_description"]
        # categoryId is required for update
        snippet["categoryId"] = snippet.get("categoryId", "10")

        try:
            youtube.videos().update(
                part="snippet",
                body={
                    "id": video["id"],
                    "snippet": snippet,
                },
            ).execute()
            print(f"  ✓ Updated: {opt['new_title'][:60]}")
            success += 1
        except Exception as e:
            print(f"  ✗ Failed: {video['id']} — {e}")

    return success


def main():
    parser = argparse.ArgumentParser(description="Sonat Mundi SEO Updater")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes to YouTube")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Specify --dry-run or --apply")
        return

    youtube = auth.youtube_service()

    print("Fetching video metadata...")
    videos = fetch_all_videos(youtube)
    print(f"Found {len(videos)} videos.\n")

    print("Generating AI-optimized metadata...")
    optimized = generate_optimized_metadata(videos)

    # Save optimization plan
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    plan_path = os.path.join(REPORTS_DIR, f"seo_update_plan_{ts}.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(optimized, f, indent=2, ensure_ascii=False)
    print(f"Plan saved: {plan_path}")

    # Show diffs
    for video in videos:
        show_diff(video, optimized)

    if args.dry_run:
        print(f"\n{'='*70}")
        print("  DRY RUN — No changes applied.")
        print("  Run with --apply to update YouTube.")
        print(f"{'='*70}")
        return

    if args.apply:
        print(f"\n{'='*70}")
        print("  APPLYING CHANGES TO YOUTUBE...")
        print(f"{'='*70}\n")
        count = apply_updates(youtube, videos, optimized)
        print(f"\n  ✓ {count}/{len(videos)} videos updated successfully.")


if __name__ == "__main__":
    main()
