"""
Playlist Manager — Automatically create, update, and sync YouTube playlists.

Categorizes all channel videos and ensures playlists stay current.
Runs weekly or on-demand via GitHub Actions.
"""

import json
import os
import sys
from datetime import datetime

from . import auth, config

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Playlist definitions — keywords used to categorize videos
PLAYLIST_DEFS = [
    {
        "title": "🌙 Deep Sleep Collection — 8 Hour Sleep Music & Insomnia Relief",
        "description": (
            "Fall asleep faster with hours of pure sleep music. Piano, cello, music box "
            "& binaural undertones designed for deep, restorative sleep.\n\n"
            "© Sonat Mundi — United Colours of Sound\nOmnia Resonant — All things resonate."
        ),
        "keywords": ["sleep", "insomnia", "velvet", "lullaby", "bedtime", "dream"],
    },
    {
        "title": "🔮 Sacred Frequencies — Solfeggio, 432Hz, 528Hz & Binaural Beats",
        "description": (
            "Healing frequencies for body, mind and soul. Solfeggio tones, binaural beats "
            "and sacred frequencies for meditation, chakra balancing and deep healing.\n\n"
            "© Sonat Mundi — United Colours of Sound\nOmnia Resonant — All things resonate."
        ),
        "keywords": ["hz", "frequenc", "solfeggio", "binaural", "tone"],
    },
    {
        "title": "🌍 Ancient World Music — Silk Road, Civilizations & Sacred Sounds",
        "description": (
            "Journey through ancient civilizations with authentic world instruments. "
            "From Göbekli Tepe to the Silk Road, from Persia to Japan.\n\n"
            "© Sonat Mundi — United Colours of Sound\nOmnia Resonant — All things resonate."
        ),
        "keywords": ["silk road", "world", "ancient", "civiliz", "sufi", "celtic", "persian",
                     "egyptian", "viking", "norse", "indian", "japanese", "tibetan"],
    },
    {
        "title": "📚 Study & Focus Music — Deep Concentration & Productivity",
        "description": (
            "Boost your focus with carefully crafted study music. Piano, jazz, ambient "
            "soundscapes designed for deep work and concentration.\n\n"
            "© Sonat Mundi — United Colours of Sound\nOmnia Resonant — All things resonate."
        ),
        "keywords": ["study", "focus", "concentrat", "productivity", "work", "cafe", "library"],
    },
    {
        "title": "🧘 Meditation & Healing — Emotional Recovery & Inner Peace",
        "description": (
            "Music for meditation, emotional healing and inner peace. Pure instrumental "
            "tracks with piano, cello and strings.\n\n"
            "© Sonat Mundi — United Colours of Sound\nOmnia Resonant — All things resonate."
        ),
        "keywords": ["meditation", "healing", "emotional", "relaxation", "peace",
                     "mindful", "chakra", "zen"],
    },
    {
        "title": "🎭 Sounds of Moods — The Human Spectrum",
        "description": (
            "A musical journey through the full spectrum of human emotion. "
            "From euphoria to stillness, nostalgia to courage.\n\n"
            "© Sonat Mundi — United Colours of Sound\nOmnia Resonant — All things resonate."
        ),
        "keywords": ["mood", "emotion", "euphoria", "nostalgia", "stillness", "courage",
                     "grief", "wonder", "human spectrum"],
    },
]


def _get_all_videos(youtube):
    """Fetch all videos from the channel."""
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

    # Get full details
    all_videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        vids = youtube.videos().list(part="snippet,contentDetails", id=",".join(batch)).execute()
        all_videos.extend(vids["items"])

    return all_videos


def _get_existing_playlists(youtube):
    """Fetch all playlists from the channel."""
    channel_id = config.channel_id()
    playlists = []
    next_page = None
    while True:
        resp = youtube.playlists().list(
            part="snippet", channelId=channel_id, maxResults=50, pageToken=next_page
        ).execute()
        playlists.extend(resp.get("items", []))
        next_page = resp.get("nextPageToken")
        if not next_page:
            break
    return playlists


def _get_playlist_video_ids(youtube, playlist_id):
    """Get all video IDs currently in a playlist."""
    ids = []
    next_page = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=next_page
        ).execute()
        for item in resp["items"]:
            ids.append(item["contentDetails"]["videoId"])
        next_page = resp.get("nextPageToken")
        if not next_page:
            break
    return ids


def _categorize_video(video, playlist_def):
    """Check if a video belongs to a playlist based on keywords."""
    title = video["snippet"]["title"].lower()
    desc = video["snippet"].get("description", "").lower()
    tags = [t.lower() for t in video["snippet"].get("tags", [])]

    # Skip Shorts (under 90 seconds)
    duration = video["contentDetails"]["duration"]
    if "H" not in duration and "M" not in duration:
        return False  # likely very short

    text = f"{title} {desc} {' '.join(tags)}"
    return any(kw in text for kw in playlist_def["keywords"])


def sync_playlists():
    """Main function: sync all playlists with current channel videos."""
    youtube = auth.youtube_service()
    videos = _get_all_videos(youtube)
    existing = _get_existing_playlists(youtube)

    print(f"Found {len(videos)} videos, {len(existing)} existing playlists")

    report = {"date": datetime.utcnow().isoformat(), "actions": []}

    for pl_def in PLAYLIST_DEFS:
        # Find existing playlist by title match
        existing_pl = None
        for ep in existing:
            if ep["snippet"]["title"] == pl_def["title"]:
                existing_pl = ep
                break

        # Create if not exists
        if not existing_pl:
            print(f"Creating playlist: {pl_def['title']}")
            resp = youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {"title": pl_def["title"], "description": pl_def["description"]},
                    "status": {"privacyStatus": "public"},
                },
            ).execute()
            pl_id = resp["id"]
            current_vids = []
            report["actions"].append({"type": "create", "playlist": pl_def["title"], "id": pl_id})
        else:
            pl_id = existing_pl["id"]
            current_vids = _get_playlist_video_ids(youtube, pl_id)
            print(f"Updating playlist: {pl_def['title']} ({len(current_vids)} videos)")

        # Find videos that should be in this playlist
        target_vids = [v["id"] for v in videos if _categorize_video(v, pl_def)]

        # Add missing videos
        added = 0
        for vid in target_vids:
            if vid not in current_vids:
                try:
                    youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": pl_id,
                                "resourceId": {"kind": "youtube#video", "videoId": vid},
                            }
                        },
                    ).execute()
                    added += 1
                    print(f"  + Added {vid}")
                except Exception as e:
                    print(f"  ! Error adding {vid}: {e}")

        if added:
            report["actions"].append({
                "type": "update", "playlist": pl_def["title"], "added": added
            })

    # Save report
    report_path = os.path.join(REPORTS_DIR, f"playlist_sync_{datetime.utcnow():%Y%m%d}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")
    return report


if __name__ == "__main__":
    sync_playlists()
