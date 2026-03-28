#!/usr/bin/env python3
"""Auto-translate YouTube video titles and descriptions to 15+ languages.
Uses deep-translator (free Google Translate) + YouTube Data API localizations."""

import os
import sys
import pickle
import time
import re

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from deep_translator import GoogleTranslator

SCOPES = ["https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
CHANNEL_ID = "UCVFOpInPEdxJQF_FmnoKSMQ"

# Target languages — high-value for music channels
# deep-translator code -> YouTube BCP-47 locale
TARGET_LANGUAGES = {
    "tr": "tr",        # Turkish
    "es": "es",        # Spanish
    "pt": "pt-BR",     # Portuguese (Brazil)
    "de": "de",        # German
    "fr": "fr",        # French
    "it": "it",        # Italian
    "ja": "ja",        # Japanese
    "ko": "ko",        # Korean
    "zh-CN": "zh-Hans", # Chinese Simplified
    "hi": "hi",        # Hindi
    "ar": "ar",        # Arabic
    "ru": "ru",        # Russian
    "id": "id",        # Indonesian
    "th": "th",        # Thai
    "vi": "vi",        # Vietnamese
    "pl": "pl",        # Polish
    "nl": "nl",        # Dutch
}


def get_creds():
    """Get YouTube API credentials from env (GitHub Actions) or local file."""
    import base64

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


def translate_text(text, target_lang, retries=3):
    """Translate text with retry logic."""
    if not text or not text.strip():
        return text
    for attempt in range(retries):
        try:
            result = GoogleTranslator(source="en", target=target_lang).translate(text)
            return result or text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 + attempt)
            else:
                print(f"      Translation failed ({target_lang}): {e}")
                return text


def clean_title_for_translation(title):
    """Extract the meaningful part of the title for translation.
    Keep brand name, Hz values, and special terms untranslated."""
    # Remove "| Sonat Mundi" suffix and similar
    title = re.sub(r'\s*\|\s*Sonat Mundi.*$', '', title)
    # Remove hashtags
    title = re.sub(r'#\w+', '', title)
    # Remove special Unicode symbols
    title = re.sub(r'[^\w\s\-\u2014\u2013.,!?:;()\'"/@&+\u00b7]', '', title)
    return title.strip()


def clean_desc_for_translation(desc):
    """Clean description for translation — keep links and brand intact."""
    lines = desc.split('\n')
    translatable = []
    preserved = []
    for line in lines:
        stripped = line.strip()
        # Don't translate URLs, copyright lines, brand lines, empty lines
        if (stripped.startswith('http') or
            stripped.startswith('\u00a9') or
            'Sonat Mundi' in stripped or
            'Omnia Resonant' in stripped or
            'sonatmundi.com' in stripped or
            stripped.startswith('#') or
            not stripped):
            preserved.append(('keep', line))
        else:
            preserved.append(('translate', line))
            translatable.append(line)
    return preserved, '\n'.join(translatable)


def build_translated_desc(preserved_structure, translated_text, original_desc):
    """Rebuild description with translated parts and preserved parts."""
    translated_lines = translated_text.split('\n') if translated_text else []
    t_idx = 0
    result = []
    for action, line in preserved_structure:
        if action == 'keep':
            result.append(line)
        else:
            if t_idx < len(translated_lines):
                result.append(translated_lines[t_idx])
                t_idx += 1
            else:
                result.append(line)
    return '\n'.join(result)


def get_all_videos(youtube):
    """Get all video IDs and their current data."""
    uploads_pl = CHANNEL_ID.replace("UC", "UU", 1)
    video_ids = []
    next_page = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_pl,
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for item in resp["items"]:
            video_ids.append(item["contentDetails"]["videoId"])
        next_page = resp.get("nextPageToken")
        if not next_page:
            break
    return video_ids


def get_video_details(youtube, video_ids):
    """Get full video details including existing localizations."""
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = youtube.videos().list(
            part="snippet,localizations",
            id=",".join(batch),
        ).execute()
        videos.extend(resp["items"])
    return videos


def update_video_localizations(youtube, video, localizations):
    """Push localizations to a video."""
    body = {
        "id": video["id"],
        "snippet": {
            "title": video["snippet"]["title"],
            "description": video["snippet"]["description"],
            "categoryId": video["snippet"].get("categoryId", "10"),
            "defaultLanguage": "en",
        },
        "localizations": localizations,
    }
    # Include existing tags if present
    if "tags" in video["snippet"]:
        body["snippet"]["tags"] = video["snippet"]["tags"]

    youtube.videos().update(
        part="snippet,localizations",
        body=body,
    ).execute()


def main():
    print("=" * 60)
    print("SONAT MUNDI \u2014 Auto-Translation System")
    print(f"Translating to {len(TARGET_LANGUAGES)} languages")
    print("=" * 60)

    creds = get_creds()
    youtube = build("youtube", "v3", credentials=creds)

    # Get all videos
    print("\nFetching all videos...")
    video_ids = get_all_videos(youtube)
    print(f"  Found {len(video_ids)} videos")

    videos = get_video_details(youtube, video_ids)
    print(f"  Got details for {len(videos)} videos")

    translated_count = 0
    skipped_count = 0
    error_count = 0

    for idx, video in enumerate(videos, 1):
        vid_id = video["id"]
        title = video["snippet"]["title"]
        desc = video["snippet"].get("description", "")

        # Check if already has localizations for all target languages
        existing_locs = video.get("localizations", {})
        yt_targets = set(TARGET_LANGUAGES.values())
        existing_set = set(existing_locs.keys())
        missing = yt_targets - existing_set

        if not missing:
            print(f"\n[{idx}/{len(videos)}] SKIP (all {len(TARGET_LANGUAGES)} langs exist): {title[:50]}")
            skipped_count += 1
            continue

        print(f"\n[{idx}/{len(videos)}] Translating: {title[:50]}")
        print(f"  Missing {len(missing)} languages: {', '.join(sorted(missing)[:5])}...")

        # Prepare text for translation
        clean_title = clean_title_for_translation(title)
        preserved_structure, translatable_desc = clean_desc_for_translation(desc)

        localizations = dict(existing_locs)  # Keep existing translations

        for dt_lang, yt_locale in TARGET_LANGUAGES.items():
            if yt_locale in existing_locs:
                continue  # Already translated

            # Translate title
            translated_title = translate_text(clean_title, dt_lang)
            if translated_title:
                translated_title = translated_title[:100]  # YouTube limit

            # Translate description
            translated_desc_text = translate_text(translatable_desc, dt_lang) if translatable_desc else ""
            full_desc = build_translated_desc(preserved_structure, translated_desc_text, desc)
            if full_desc:
                full_desc = full_desc[:5000]  # YouTube limit

            localizations[yt_locale] = {
                "title": translated_title or title,
                "description": full_desc or desc,
            }

            print(f"    {yt_locale}: {translated_title[:40]}..." if translated_title else f"    {yt_locale}: (kept original)")
            time.sleep(0.5)  # Rate limit for free Google Translate

        # Push to YouTube
        try:
            update_video_localizations(youtube, video, localizations)
            print(f"  \u2713 Pushed {len(localizations)} localizations to YouTube")
            translated_count += 1
        except HttpError as e:
            if "quotaExceeded" in str(e):
                print(f"\n  QUOTA EXCEEDED \u2014 stopping. {len(videos) - idx} videos remaining.")
                break
            print(f"  \u2717 YouTube API error: {e}")
            error_count += 1
        except Exception as e:
            print(f"  \u2717 Error: {e}")
            error_count += 1

        time.sleep(1)  # Pace between videos

    # Summary
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {translated_count} translated, {skipped_count} skipped, {error_count} errors")
    print(f"Languages: {', '.join(sorted(TARGET_LANGUAGES.values()))}")


if __name__ == "__main__":
    main()
