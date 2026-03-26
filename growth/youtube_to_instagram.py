#!/usr/bin/env python3
"""
Sonat Mundi — YouTube-to-Instagram Automation System

Automatically generates unique Instagram content (Reels, Posts, Carousels)
from YouTube channel videos and publishes via instagrapi.

Usage:
  python -m growth.youtube_to_instagram --mode auto
  python -m growth.youtube_to_instagram --mode reels --video-id zP49iY99TuI
  python -m growth.youtube_to_instagram --mode posts
  python -m growth.youtube_to_instagram --mode playlists
  python -m growth.youtube_to_instagram --mode generate-only
  python -m growth.youtube_to_instagram --mode auto --dry-run

Environment variables:
  INSTAGRAM_USERNAME  — Instagram login
  INSTAGRAM_PASSWORD  — Instagram password
"""

import os
import sys
import json
import time
import random
import hashlib
import logging
import argparse
import subprocess
import tempfile
import pickle
import glob as globmod
import textwrap
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("yt2ig")

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORK_DIR = REPO_ROOT / "media" / "ig_generated"
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Local paths for credentials / media
SOUNDS_BASE = Path(r"D:\Yedekler\UCS\Sounds")
IG_BASE = Path(r"D:\Yedekler\UCS\instagram")
SESSION_FILE = Path(os.environ.get(
    "INSTAGRAM_SESSION_FILE",
    str(IG_BASE / "ig_session.json"),
))
HISTORY_FILE = Path(os.environ.get(
    "PUBLISH_HISTORY_FILE",
    str(IG_BASE / "publish_history.json"),
))
LOGO_PATH = REPO_ROOT / "sonat_mundi-logo_transparent.png"

# YouTube token paths
YT_TOKEN_PATH = SOUNDS_BASE / "Sounds of Concepts Vol.1 Study Music" / "yt_token.pickle"
YT_ANALYSIS_TOKEN = SOUNDS_BASE / "yt_token_analysis.pickle"
YT_CLIENT_SECRET_DIR = SOUNDS_BASE / "Sounds of Concepts Vol.1 Study Music"

# ── Safety ───────────────────────────────────────────────────────────────────
MIN_POST_DELAY = 180   # seconds between posts
MAX_POSTS_PER_RUN = 4
REEL_MIN_DURATION = 30
REEL_MAX_DURATION = 50

# ── Channel Data ─────────────────────────────────────────────────────────────
CHANNEL_ID = "UCVFOpInPEdxJQF_FmnoKSMQ"

VIDEOS = {
    "zP49iY99TuI": {
        "title": "Sufi Ambient Music — Ancient Soul Journey Vol.1",
        "duration_s": 2040,
        "series": "Ancient Soul Journey",
        "vol": 1,
    },
    "woc8YjxwHjg": {
        "title": "Deep Focus Study Music — Sounds of Concepts Vol.1",
        "duration_s": 4080,
        "series": "Sounds of Concepts",
        "vol": 1,
    },
    "FqfQRXqjpZY": {
        "title": "Silk Road World Music — Sounds of World Vol.1",
        "duration_s": 3300,
        "series": "Sounds of World",
        "vol": 1,
    },
    "sJ8GxI0s6yU": {
        "title": "Emotional Healing Music — Sounds of Moods Vol.1",
        "duration_s": 4320,
        "series": "Sounds of Moods",
        "vol": 1,
    },
    "0SfvkXgnLhM": {
        "title": "528 Hz Solfeggio Frequencies — Sacred Frequencies Vol.1",
        "duration_s": 5520,
        "series": "Sacred Frequencies",
        "vol": 1,
    },
    "7u3AMLTKr_U": {
        "title": "Ancient Civilizations Music — Ancient Soul Journey Vol.2",
        "duration_s": 4260,
        "series": "Ancient Soul Journey",
        "vol": 2,
    },
    "3N4e-BVWv_k": {
        "title": "8 Hour Sleep Music — Velvet Silence",
        "duration_s": 28800,
        "series": "Velvet Silence",
        "vol": 1,
    },
}

PLAYLISTS = {
    "PLFwHyBcRUIvWB-zuYabHpeA1I5SanQfEt": {
        "title": "Deep Sleep Collection",
        "videos": ["3N4e-BVWv_k"],
    },
    "PLFwHyBcRUIvVYjQahdDJ1zvPaNd1ZC_OT": {
        "title": "Sacred Frequencies",
        "videos": ["0SfvkXgnLhM"],
    },
    "PLFwHyBcRUIvUaegQrL-bSgB1IwjV4990v": {
        "title": "Ancient World Music",
        "videos": ["zP49iY99TuI", "7u3AMLTKr_U", "FqfQRXqjpZY"],
    },
    "PLFwHyBcRUIvX9wvqnl3b5d1qexRG3s9Zg": {
        "title": "Study & Focus Music",
        "videos": ["woc8YjxwHjg"],
    },
    "PLFwHyBcRUIvXGtW_B_sYFEAOz91CCBoKS": {
        "title": "Meditation & Healing",
        "videos": ["sJ8GxI0s6yU", "0SfvkXgnLhM"],
    },
}

# Map video IDs to local directories (for faster access than downloading)
VIDEO_LOCAL_DIRS = {
    "zP49iY99TuI": SOUNDS_BASE / "Ancient Soul Journey Vol.1",
    "woc8YjxwHjg": SOUNDS_BASE / "Sounds of Concepts Vol.1 Study Music",
    "FqfQRXqjpZY": SOUNDS_BASE / "Sounds of World Vol. 1 Ancient Silk Road Authentic",
    "sJ8GxI0s6yU": SOUNDS_BASE / "Sounds of Moods Vol. 1 The Human Spectrum",
    "0SfvkXgnLhM": SOUNDS_BASE / "Sounds of Frequencies Vol.1 Sacred Frequencies",
    "7u3AMLTKr_U": SOUNDS_BASE / "Ancient Soul Journey Vol.2 Echoes of Ancient Civilizations",
    "3N4e-BVWv_k": SOUNDS_BASE / "Sounds of Sleep Vol.1 Deep Sleep",
}

# ── Brand Colors ─────────────────────────────────────────────────────────────
COLOR_BG = (8, 8, 12)           # #08080c
COLOR_GOLD = (212, 178, 85)     # #d4b255
COLOR_WHITE = (240, 236, 228)   # #f0ece4
COLOR_DIM = (120, 115, 105)     # subtle text

# ════════════════════════════════════════════════════════════════════════════
#  CONTENT POOLS
# ════════════════════════════════════════════════════════════════════════════

REEL_HOOKS = [
    "Close your eyes and let this sound carry you away...",
    "This frequency has been used for centuries to heal the soul.",
    "Warning: You might fall asleep within 30 seconds.",
    "Ancient civilizations knew the power of this sound.",
    "Your nervous system will thank you for pressing play.",
    "Put your headphones on. Trust us on this one.",
    "This is what 4000 years of musical tradition sounds like.",
    "The Silk Road carried more than silk — it carried this sound.",
    "Scientists call this the 'love frequency' — 528 Hz.",
    "One minute of this can shift your entire mood.",
    "Stop scrolling. Your soul needs this right now.",
    "This sound has traveled through time to reach you.",
    "If music could heal, it would sound exactly like this.",
    "The monks played this at dawn for a reason.",
    "Let the ancient strings dissolve your stress.",
    "This is the sound of deep, dreamless sleep.",
    "Sufi masters meditated to frequencies like these.",
    "Your brain on this music: instant calm.",
    "This is what the universe sounds like at rest.",
    "The healing power of sound is not a myth. Listen.",
    "Every culture on Earth has a version of this healing sound.",
    "Play this tonight. Wake up different tomorrow.",
    "There is a reason this video has been played non-stop.",
    "Some sounds do not just enter your ears — they enter your soul.",
    "The Ney flute has been healing hearts for 800 years.",
    "Frequencies this pure do not come around often.",
    "Ancient Anatolian soundscapes for the modern mind.",
    "This music was composed with intention. Feel the difference.",
    "What if one sound could rewrite your entire evening?",
    "The desert winds carry melodies like these.",
    "Your focus is about to hit a new level.",
    "Study music that actually works — neuroscience agrees.",
    "Solfeggio frequencies: the code to inner harmony.",
    "The sound of civilizations lost to time.",
    "This is not background music. This is transformation.",
    "Sometimes the oldest medicine is the most powerful.",
    "Healers across the world use this exact frequency.",
    "Press play and let go of everything else.",
    "Your bedtime ritual is about to change forever.",
    "When words fail, these frequencies speak.",
    "Sound therapy is not alternative — it is ancient.",
    "The bazaars of the Silk Road echoed with these tones.",
    "Eight hours of velvet silence. You deserve this.",
    "This frequency resonates at the heart of DNA repair.",
    "Ancient wisdom, modern peace. All in one sound.",
    "The sound of a thousand years of Sufi tradition.",
    "Let the Duduk carry your worries into the night sky.",
    "Sleep is not a luxury — it is a necessity. Listen.",
    "World music that transcends borders and time.",
    "This is the sound they do not want you to know about.",
    "Imagine if you could hear the pyramids sing.",
    "From Istanbul to Samarkand — the sound of the ancient world.",
    "432 Hz: the frequency of the cosmos itself.",
    "Your study session just got a sacred upgrade.",
]

QUOTE_POOL = [
    ("Music is the universal language of mankind.", "Henry Wadsworth Longfellow"),
    ("Where words fail, music speaks.", "Hans Christian Andersen"),
    ("Music gives a soul to the universe, wings to the mind.", "Plato"),
    ("One good thing about music: when it hits you, you feel no pain.", "Bob Marley"),
    ("Music is the moonlight in the gloomy night of life.", "Jean Paul"),
    ("Without music, life would be a mistake.", "Friedrich Nietzsche"),
    ("Music is the strongest form of magic.", "Marilyn Manson"),
    ("The earth has music for those who listen.", "William Shakespeare"),
    ("Music is the shorthand of emotion.", "Leo Tolstoy"),
    ("Silence is the sleep that nourishes wisdom.", "Francis Bacon"),
    ("Sound is the vocabulary of nature.", "Pierre Schaeffer"),
    ("Rhythm is the soul of life. The whole universe revolves in rhythm.", "Babatunde Olatunji"),
    ("Music acts like a magic key, to which the most tightly closed heart opens.", "Maria von Trapp"),
    ("To produce music is also in a sense to produce children.", "Friedrich Nietzsche"),
    ("If I were not a physicist, I would probably be a musician.", "Albert Einstein"),
    ("Life is like a beautiful melody, only the lyrics are messed up.", "Hans Christian Andersen"),
    ("Music is feeling. You cannot intellectualize it.", "Eric Dolphy"),
    ("After silence, that which comes nearest to expressing the inexpressible is music.", "Aldous Huxley"),
    ("Every sound has a frequency. Every frequency has a purpose.", "Sonat Mundi"),
    ("Ancient sounds for modern souls.", "Sonat Mundi"),
    ("Let the frequency find you.", "Sonat Mundi"),
    ("Sound is the bridge between the visible and the invisible.", "Sonat Mundi"),
    ("Healing does not always come from words. Sometimes, it comes from waves.", "Sonat Mundi"),
    ("The universe is not silent. You just need to tune in.", "Sonat Mundi"),
    ("Sleep is sacred. Sound is the key.", "Sonat Mundi"),
    ("From the Silk Road to your soul — music connects everything.", "Sonat Mundi"),
    ("The oldest instrument is the human voice. The second oldest is rhythm.", "Sonat Mundi"),
    ("One frequency can change the chemistry of your mind.", "Sonat Mundi"),
    ("Music is the archaeology of emotion.", "Sonat Mundi"),
    ("Every culture that ever existed had one thing in common: music.", "Sonat Mundi"),
]

FREQUENCY_FACTS = [
    {
        "freq": "432 Hz",
        "title": "The Cosmic Frequency",
        "body": "432 Hz is often called the frequency of the universe. It is mathematically "
                "consistent with the patterns of nature. Many ancient instruments were tuned to "
                "432 Hz, and listeners report feeling more relaxed and centered compared to 440 Hz.",
        "color_accent": (160, 130, 220),
    },
    {
        "freq": "528 Hz",
        "title": "The Love Frequency",
        "body": "528 Hz is known as the 'Miracle Tone' or 'Love Frequency'. Research suggests it "
                "may help repair DNA and reduce stress hormones. It is one of the six original "
                "Solfeggio frequencies used in sacred Gregorian chants.",
        "color_accent": (85, 212, 150),
    },
    {
        "freq": "396 Hz",
        "title": "Liberation from Fear",
        "body": "396 Hz is the Solfeggio frequency associated with liberating guilt and fear. "
                "It helps turn grief into joy and is believed to cleanse feelings of guilt, "
                "which is one of the fundamental obstacles to self-realization.",
        "color_accent": (212, 85, 100),
    },
    {
        "freq": "639 Hz",
        "title": "Connecting Relationships",
        "body": "639 Hz is used for balancing emotions and elevating mood. It promotes "
                "communication, understanding, and harmony in interpersonal relationships. "
                "This frequency can be used to encourage the cell to communicate with its environment.",
        "color_accent": (85, 170, 212),
    },
    {
        "freq": "741 Hz",
        "title": "Awakening Intuition",
        "body": "741 Hz is associated with solving problems and awakening intuition. It cleanses "
                "the cell of toxins and electromagnetic radiation. This frequency is said to lead "
                "to a purer, more stable, and healthier life.",
        "color_accent": (212, 170, 85),
    },
    {
        "freq": "852 Hz",
        "title": "Return to Spiritual Order",
        "body": "852 Hz is linked to returning to spiritual order. It awakens inner strength "
                "and raises awareness. This frequency is associated with the third eye chakra "
                "and can help heighten intuition and spiritual awareness.",
        "color_accent": (170, 85, 212),
    },
    {
        "freq": "174 Hz",
        "title": "Natural Anesthetic",
        "body": "174 Hz is the lowest of the Solfeggio frequencies. It tends to reduce pain "
                "physically and energetically. It gives organs a sense of security, safety, "
                "and love, encouraging them to do their best.",
        "color_accent": (100, 180, 100),
    },
    {
        "freq": "285 Hz",
        "title": "Cellular Healing",
        "body": "285 Hz influences energy fields, sending a message to restructure damaged "
                "organs. It is said to leave your body feeling rejuvenated and energized. "
                "It helps in healing wounds, cuts, and burns.",
        "color_accent": (180, 120, 80),
    },
    {
        "freq": "963 Hz",
        "title": "Crown Chakra Activation",
        "body": "963 Hz is known as the frequency of the Gods. It awakens the crown chakra "
                "and raises positive energy. Associated with pineal gland activation, it is "
                "believed to help reconnect with your highest self and universal consciousness.",
        "color_accent": (220, 200, 255),
    },
]

DID_YOU_KNOW_FACTS = [
    "The Ney flute, central to Sufi music, has been played for over 4,500 years — making it one of the oldest instruments still in use.",
    "The Silk Road was not just a trade route — it was a musical highway. Instruments like the Oud traveled from Arabia to China along its paths.",
    "In ancient Egypt, music was believed to have the power to heal illness. Temples had dedicated rooms for 'sound therapy'.",
    "The Duduk, an Armenian woodwind, produces sounds so mournful that UNESCO declared it an Intangible Cultural Heritage.",
    "Tibetan singing bowls produce frequencies that can entrain brain waves into meditative states within minutes.",
    "The ancient Greeks believed that music was governed by the same mathematical laws that governed the universe — the 'Music of the Spheres'.",
    "Aboriginal Australians have been playing the Didgeridoo for over 40,000 years — the oldest wind instrument in continuous use.",
    "The Sitar has 18-21 strings, but only 6-7 are actually played. The rest vibrate sympathetically, creating its signature resonance.",
    "In Japan, Shakuhachi flute monks practiced 'blowing zen' — a form of meditation through sound rather than silence.",
    "The Hang Drum was invented in Switzerland in 2000 — one of the newest instruments based on one of the oldest concepts: steel pan tuning.",
    "Ancient Mesopotamian cuneiform tablets contain the oldest known musical notation — a hymn from 3,400 years ago.",
    "The Throat Singing tradition of Tuva (Mongolia) allows one person to produce two distinct notes simultaneously.",
    "In Indian classical music, specific Ragas are prescribed for specific times of day, seasons, and even medical conditions.",
    "The word 'music' comes from the Greek 'mousike' — the art of the Muses, who were goddesses of inspiration.",
    "Pythagoras discovered that musical intervals could be expressed as mathematical ratios — the foundation of all music theory.",
    "The Gamelan orchestras of Indonesia tune their instruments to two scales that exist nowhere else in the world.",
    "Native American flutes are tuned to the pentatonic scale — the same five-note scale found in cultures across every continent.",
    "The Kora, a 21-string West African harp, has been called 'the instrument that sounds like a full orchestra'.",
    "In ancient China, music was one of the six arts every educated person was expected to master.",
    "The concept of 'sound healing' is not New Age — it dates back over 40,000 years to Aboriginal Australian songlines.",
]

# ── Hashtag Sets (rotated to avoid repetition) ──────────────────────────────
HASHTAG_SETS = {
    "ambient": [
        "#ambientmusic #ambient #meditation #relaxingmusic #healingmusic #deeprelaxation",
        "#ambientmusic #chillmusic #backgroundmusic #calmmusic #peacefulmusic #mindfulness",
        "#ambientmusic #atmosphericmusic #dronemusic #floatingmusic #etherealmusic #tranquil",
    ],
    "study": [
        "#studymusic #focusmusic #deepfocus #productivitymusic #lofi #concentrationmusic",
        "#studymusic #studywithme #focusflow #brainmusic #workmusic #deepwork",
        "#studymusic #studytips #musicforstudy #coffeeandmusic #focusmode #studyvibes",
    ],
    "sleep": [
        "#sleepmusic #deepsleep #insomnia #relaxingsleep #bedtimemusic #8hoursleep",
        "#sleepmusic #sleepwell #nightmusic #dreamsounds #sleepasmr #restfulsleep",
        "#sleepmusic #sleephygiene #sleepaid #calmnight #peacefulsleep #goodnight",
    ],
    "healing": [
        "#healingmusic #soundhealing #soundtherapy #emotionalhealing #innerpeace #selfcare",
        "#healingmusic #musictherapy #healingfrequencies #mentalhealthmusic #wellnessmusic",
        "#healingmusic #mindfulness #holistichealing #energyhealing #soulmusic #therapy",
    ],
    "frequency": [
        "#528hz #solfeggiofrequencies #healingfrequencies #sacredfrequencies #frequencyhealing",
        "#432hz #solfeggiofrequencies #frequencymusic #soundhealing #vibrationalhealing",
        "#solfeggiofrequencies #chakrahealing #meditationmusic #frequencyhealing #dnarepair",
    ],
    "world": [
        "#worldmusic #silkroad #ancientmusic #ethnicmusic #traditionalmusic #culturalmusic",
        "#worldmusic #globalmusic #folkmusic #rootsmusic #ancientworld #musichistory",
        "#worldmusic #sufimusic #middleeasternmusic #turkishmusic #orientalmusic #oud",
    ],
    "general": [
        "#sonatmundi #musiclovers #newmusic #youtube #musicislife #goodvibes",
        "#sonatmundi #musicdiscovery #undergroundmusic #indiemusic #explorepage #reels",
        "#sonatmundi #musicproducer #originalmusic #musiccommunity #instagramreels #viral",
    ],
}

# ════════════════════════════════════════════════════════════════════════════
#  PUBLISH HISTORY
# ════════════════════════════════════════════════════════════════════════════

def load_history() -> dict:
    """Load or initialize publish history."""
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("Corrupt history file, starting fresh")
    return {
        "reels": [],        # [{video_id, start_s, end_s, ts, ig_id}]
        "posts": [],        # [{type, key, ts, ig_id}]
        "carousels": [],    # [{playlist_id, ts, ig_id}]
        "last_run": None,
        "daily_counts": {},  # {"2026-03-26": 3}
    }


def save_history(h: dict):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(h, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("History saved to %s", HISTORY_FILE)


def used_reel_segments(h: dict, video_id: str) -> list:
    """Return list of (start, end) already used for a given video."""
    return [
        (r["start_s"], r["end_s"])
        for r in h.get("reels", [])
        if r.get("video_id") == video_id
    ]


def used_post_keys(h: dict) -> set:
    return {p.get("key") for p in h.get("posts", [])}


def used_carousel_playlists(h: dict) -> set:
    return {c.get("playlist_id") for c in h.get("carousels", [])}


def today_post_count(h: dict) -> int:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return h.get("daily_counts", {}).get(today, 0)


def increment_daily_count(h: dict):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    counts = h.setdefault("daily_counts", {})
    counts[today] = counts.get(today, 0) + 1


# ════════════════════════════════════════════════════════════════════════════
#  INSTAGRAM CLIENT
# ════════════════════════════════════════════════════════════════════════════

_ig_client = None


def get_ig_client():
    """Return authenticated instagrapi Client (cached)."""
    global _ig_client
    if _ig_client is not None:
        return _ig_client

    from instagrapi import Client

    cl = Client()
    cl.delay_range = [2, 5]

    # Try loading session
    if SESSION_FILE.exists():
        try:
            cl.load_settings(str(SESSION_FILE))
            cl.login(
                os.environ["INSTAGRAM_USERNAME"],
                os.environ["INSTAGRAM_PASSWORD"],
            )
            cl.get_timeline_feed()  # verify session
            log.info("Instagram session loaded from %s", SESSION_FILE)
            _ig_client = cl
            return cl
        except Exception as e:
            log.warning("Session load failed (%s), doing fresh login", e)

    cl.login(
        os.environ["INSTAGRAM_USERNAME"],
        os.environ["INSTAGRAM_PASSWORD"],
    )
    cl.dump_settings(str(SESSION_FILE))
    log.info("Fresh Instagram login, session saved to %s", SESSION_FILE)
    _ig_client = cl
    return cl


# ════════════════════════════════════════════════════════════════════════════
#  YOUTUBE HELPERS
# ════════════════════════════════════════════════════════════════════════════

def get_youtube_service():
    """Return authenticated YouTube Data API service."""
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    # Try analysis token first (broader scope)
    for token_path in [YT_ANALYSIS_TOKEN, YT_TOKEN_PATH]:
        if token_path.exists():
            try:
                with open(token_path, "rb") as f:
                    creds = pickle.load(f)
                if creds and creds.valid:
                    break
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    break
            except Exception as e:
                log.warning("Token %s failed: %s", token_path, e)
                creds = None

    if not creds or not creds.valid:
        # Fall back to existing auth module
        sys.path.insert(0, str(SCRIPT_DIR))
        from auth import get_credentials
        creds = get_credentials()

    return build("youtube", "v3", credentials=creds)


def download_thumbnail(video_id: str, output_path: Path) -> Path:
    """Download YouTube thumbnail for a video."""
    import urllib.request
    url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
    try:
        urllib.request.urlretrieve(url, str(output_path))
        return output_path
    except Exception:
        url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        urllib.request.urlretrieve(url, str(output_path))
        return output_path


def find_local_video(video_id: str) -> Optional[Path]:
    """Find local video file for a given YouTube video ID."""
    local_dir = VIDEO_LOCAL_DIRS.get(video_id)
    if local_dir and local_dir.exists():
        for ext in ("*.mp4", "*.mkv", "*.webm"):
            files = list(local_dir.glob(ext))
            if files:
                # Pick the largest file (likely the full video)
                return max(files, key=lambda f: f.stat().st_size)
    return None


def download_video_segment(video_id: str, start_s: int, duration_s: int, output_path: Path) -> Path:
    """Download or extract a segment from a YouTube video using yt-dlp + ffmpeg."""
    local = find_local_video(video_id)

    if local:
        log.info("Using local file: %s", local)
        source = str(local)
    else:
        # Download with yt-dlp
        log.info("Downloading video %s via yt-dlp...", video_id)
        tmp_dl = output_path.parent / f"_dl_{video_id}.mp4"
        url = f"https://www.youtube.com/watch?v={video_id}"
        cmd = [
            "yt-dlp",
            "--download-sections", f"*{start_s}-{start_s + duration_s}",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "--merge-output-format", "mp4",
            "-o", str(tmp_dl),
            "--no-playlist",
            "--quiet",
            url,
        ]
        subprocess.run(cmd, check=True, timeout=300)
        source = str(tmp_dl)

    # Extract segment and convert to 9:16 vertical with Ken Burns effect
    _extract_vertical_reel(source, start_s, duration_s, output_path)

    # Cleanup temp download
    tmp_dl = output_path.parent / f"_dl_{video_id}.mp4"
    if tmp_dl.exists() and tmp_dl != Path(source):
        tmp_dl.unlink()

    return output_path


def _extract_vertical_reel(source: str, start_s: int, duration_s: int, output: Path):
    """
    Extract a segment and convert to 1080x1920 (9:16) vertical format.
    Uses a slow zoom (Ken Burns) effect and adds a watermark.
    """
    # Determine if source is local (need to seek) or already trimmed
    local_video = Path(source)
    is_local = local_video.stat().st_size > 100_000_000  # > 100MB = full video

    watermark_text = "SONAT MUNDI"

    # Build FFmpeg filter for vertical conversion with Ken Burns
    # Start zoomed in at 1.0x, slowly zoom to 1.05x (subtle)
    zoom_filter = (
        "zoompan=z='min(zoom+0.0001,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        ":d=1:s=1080x1080:fps=30"
    )

    # Pad to 9:16 (1080x1920) with dark bars
    pad_filter = "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#08080c"

    # Watermark at bottom
    watermark_filter = (
        f"drawtext=text='{watermark_text}':fontsize=28:fontcolor=white@0.4"
        ":x=(w-tw)/2:y=h-80:font=Arial"
    )

    vf = f"{zoom_filter},{pad_filter},{watermark_filter}"

    cmd = ["ffmpeg", "-y"]

    if is_local:
        cmd += ["-ss", str(start_s)]

    cmd += ["-i", source]

    if is_local:
        cmd += ["-t", str(duration_s)]

    cmd += [
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-shortest",
        "-movflags", "+faststart",
        str(output),
    ]

    log.info("FFmpeg command: %s", " ".join(cmd[:6]) + " ...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        log.error("FFmpeg stderr: %s", result.stderr[-500:] if result.stderr else "")
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
    log.info("Reel created: %s", output)


# ════════════════════════════════════════════════════════════════════════════
#  IMAGE GENERATION (Pillow)
# ════════════════════════════════════════════════════════════════════════════

def _get_font(size: int, bold: bool = False):
    """Get a font, falling back gracefully."""
    from PIL import ImageFont
    # Try common fonts
    candidates = []
    if bold:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _load_logo(size: int = 120) -> "Image":
    """Load and resize the Sonat Mundi logo."""
    from PIL import Image
    if LOGO_PATH.exists():
        logo = Image.open(str(LOGO_PATH)).convert("RGBA")
        logo.thumbnail((size, size), Image.LANCZOS)
        return logo
    return None


def _draw_branded_footer(draw, img_width: int, img_height: int):
    """Draw the 'SONAT MUNDI' footer bar."""
    font_sm = _get_font(22)
    text = "SONAT MUNDI  |  sonat.mundi"
    bbox = draw.textbbox((0, 0), text, font=font_sm)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((img_width - tw) / 2, img_height - 55),
        text, fill=COLOR_DIM, font=font_sm,
    )
    # Gold line
    draw.line(
        [(img_width * 0.2, img_height - 70), (img_width * 0.8, img_height - 70)],
        fill=COLOR_GOLD, width=1,
    )


def generate_track_spotlight(video_id: str, output_path: Path) -> Path:
    """Generate a track spotlight post (thumbnail + title + duration overlay)."""
    from PIL import Image, ImageDraw, ImageFilter

    info = VIDEOS[video_id]
    img = Image.new("RGB", (1080, 1080), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Download and embed thumbnail
    thumb_path = WORK_DIR / f"thumb_{video_id}.jpg"
    if not thumb_path.exists():
        download_thumbnail(video_id, thumb_path)

    thumb = Image.open(str(thumb_path)).convert("RGB")
    # Place thumbnail in center with border
    thumb = thumb.resize((900, 506), Image.LANCZOS)
    # Add subtle blur overlay at edges
    img.paste(thumb, (90, 140))

    # Gold border around thumbnail
    draw.rectangle([(88, 138), (992, 648)], outline=COLOR_GOLD, width=2)

    # Title
    font_title = _get_font(36, bold=True)
    title_lines = textwrap.wrap(info["title"], width=35)
    y = 680
    for line in title_lines:
        draw.text((90, y), line, fill=COLOR_WHITE, font=font_title)
        y += 48

    # Duration
    dur_min = info["duration_s"] // 60
    dur_text = f"{dur_min} min" if dur_min < 120 else f"{dur_min // 60}h {dur_min % 60}min"
    font_dur = _get_font(28)
    draw.text((90, y + 20), f"Duration: {dur_text}", fill=COLOR_GOLD, font=font_dur)

    # Series badge
    font_badge = _get_font(22)
    draw.text((90, y + 60), f"Series: {info['series']} Vol.{info['vol']}", fill=COLOR_DIM, font=font_badge)

    # Logo
    logo = _load_logo(80)
    if logo:
        img.paste(logo, (90, 30), logo)

    # Branded footer
    _draw_branded_footer(draw, 1080, 1080)

    img.save(str(output_path), quality=95)
    log.info("Track spotlight saved: %s", output_path)
    return output_path


def generate_frequency_card(fact_index: int, output_path: Path) -> Path:
    """Generate a frequency info card post."""
    from PIL import Image, ImageDraw

    fact = FREQUENCY_FACTS[fact_index % len(FREQUENCY_FACTS)]
    img = Image.new("RGB", (1080, 1080), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Accent circle in top-right
    accent = fact.get("color_accent", COLOR_GOLD)
    for i in range(80):
        alpha = max(0, 80 - i)
        c = tuple(min(255, int(v * alpha / 80)) for v in accent)
        draw.ellipse(
            [(900 - i, 40 - i), (1060 + i, 200 + i)],
            outline=c, width=1,
        )

    # Frequency number — big
    font_freq = _get_font(72, bold=True)
    draw.text((90, 120), fact["freq"], fill=accent, font=font_freq)

    # Title
    font_title = _get_font(40, bold=True)
    draw.text((90, 220), fact["title"], fill=COLOR_WHITE, font=font_title)

    # Gold divider
    draw.line([(90, 290), (400, 290)], fill=COLOR_GOLD, width=2)

    # Body text
    font_body = _get_font(26)
    lines = textwrap.wrap(fact["body"], width=45)
    y = 320
    for line in lines:
        draw.text((90, y), line, fill=COLOR_WHITE, font=font_body)
        y += 38

    # Bottom tag
    font_tag = _get_font(22)
    draw.text((90, y + 40), "Solfeggio Frequency Series", fill=COLOR_DIM, font=font_tag)

    # Logo
    logo = _load_logo(80)
    if logo:
        img.paste(logo, (90, 30), logo)

    _draw_branded_footer(draw, 1080, 1080)
    img.save(str(output_path), quality=95)
    log.info("Frequency card saved: %s", output_path)
    return output_path


def generate_quote_post(quote_index: int, output_path: Path) -> Path:
    """Generate a quote post with branded background."""
    from PIL import Image, ImageDraw

    quote_text, author = QUOTE_POOL[quote_index % len(QUOTE_POOL)]
    img = Image.new("RGB", (1080, 1080), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Decorative gold quotes
    font_deco = _get_font(120, bold=True)
    draw.text((70, 180), "\u201C", fill=COLOR_GOLD, font=font_deco)

    # Quote text
    font_quote = _get_font(38, bold=True)
    lines = textwrap.wrap(quote_text, width=30)
    y = 340
    for line in lines:
        draw.text((110, y), line, fill=COLOR_WHITE, font=font_quote)
        y += 55

    # Author
    font_author = _get_font(26)
    draw.text((110, y + 30), f"— {author}", fill=COLOR_GOLD, font=font_author)

    # Logo
    logo = _load_logo(80)
    if logo:
        img.paste(logo, (90, 30), logo)

    _draw_branded_footer(draw, 1080, 1080)
    img.save(str(output_path), quality=95)
    log.info("Quote post saved: %s", output_path)
    return output_path


def generate_did_you_know(fact_index: int, output_path: Path) -> Path:
    """Generate a 'Did You Know?' post."""
    from PIL import Image, ImageDraw

    fact = DID_YOU_KNOW_FACTS[fact_index % len(DID_YOU_KNOW_FACTS)]
    img = Image.new("RGB", (1080, 1080), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Header
    font_header = _get_font(48, bold=True)
    draw.text((90, 140), "Did You Know?", fill=COLOR_GOLD, font=font_header)

    # Gold divider
    draw.line([(90, 210), (500, 210)], fill=COLOR_GOLD, width=3)

    # Fact text
    font_fact = _get_font(32)
    lines = textwrap.wrap(fact, width=35)
    y = 260
    for line in lines:
        draw.text((90, y), line, fill=COLOR_WHITE, font=font_fact)
        y += 48

    # Music note decoration
    font_note = _get_font(200)
    draw.text((800, 700), "\u266B", fill=(30, 30, 35), font=font_note)

    # Logo
    logo = _load_logo(80)
    if logo:
        img.paste(logo, (90, 30), logo)

    _draw_branded_footer(draw, 1080, 1080)
    img.save(str(output_path), quality=95)
    log.info("Did You Know post saved: %s", output_path)
    return output_path


def generate_stats_post(output_path: Path) -> Path:
    """Generate a channel stats/milestone post."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (1080, 1080), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Header
    font_header = _get_font(42, bold=True)
    draw.text((90, 100), "Sonat Mundi", fill=COLOR_GOLD, font=font_header)
    draw.text((90, 155), "Channel Highlights", fill=COLOR_WHITE, font=_get_font(32))

    # Divider
    draw.line([(90, 210), (990, 210)], fill=COLOR_GOLD, width=2)

    # Stats boxes
    stats = [
        ("7", "Albums Released"),
        ("7+", "Hours of Music"),
        ("5", "Curated Playlists"),
        ("6", "Music Traditions"),
        ("9", "Solfeggio Frequencies"),
        ("1", "Brand, Infinite Sound"),
    ]

    font_num = _get_font(52, bold=True)
    font_label = _get_font(22)

    for i, (num, label) in enumerate(stats):
        row = i // 2
        col = i % 2
        x = 90 + col * 480
        y = 260 + row * 220

        # Gold number
        draw.text((x, y), num, fill=COLOR_GOLD, font=font_num)
        # White label
        draw.text((x, y + 70), label, fill=COLOR_WHITE, font=font_label)

    # Logo
    logo = _load_logo(80)
    if logo:
        img.paste(logo, (920, 30), logo)

    _draw_branded_footer(draw, 1080, 1080)
    img.save(str(output_path), quality=95)
    log.info("Stats post saved: %s", output_path)
    return output_path


def generate_playlist_carousel(playlist_id: str, output_dir: Path) -> list:
    """Generate carousel slides for a playlist."""
    from PIL import Image, ImageDraw

    output_dir.mkdir(parents=True, exist_ok=True)
    pl = PLAYLISTS[playlist_id]
    slides = []

    # Slide 1: Playlist title
    img = Image.new("RGB", (1080, 1080), COLOR_BG)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(48, bold=True)
    font_sub = _get_font(28)

    # Gold border
    draw.rectangle([(30, 30), (1050, 1050)], outline=COLOR_GOLD, width=2)

    title_lines = textwrap.wrap(pl["title"], width=20)
    y = 350
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((1080 - tw) / 2, y), line, fill=COLOR_GOLD, font=font_title)
        y += 65

    draw.text((1080 // 2 - 80, y + 30), "PLAYLIST", fill=COLOR_WHITE, font=font_sub)

    logo = _load_logo(100)
    if logo:
        img.paste(logo, (490, 150), logo)

    _draw_branded_footer(draw, 1080, 1080)
    slide_path = output_dir / "slide_01_title.jpg"
    img.save(str(slide_path), quality=95)
    slides.append(slide_path)

    # Slides 2-N: Individual tracks
    for idx, vid_id in enumerate(pl["videos"][:5], start=2):
        info = VIDEOS.get(vid_id, {})
        img = Image.new("RGB", (1080, 1080), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Thumbnail
        thumb_path = WORK_DIR / f"thumb_{vid_id}.jpg"
        if not thumb_path.exists():
            download_thumbnail(vid_id, thumb_path)

        try:
            thumb = Image.open(str(thumb_path)).convert("RGB")
            thumb = thumb.resize((900, 506), Image.LANCZOS)
            img.paste(thumb, (90, 120))
            draw.rectangle([(88, 118), (992, 628)], outline=COLOR_GOLD, width=2)
        except Exception as e:
            log.warning("Could not load thumbnail for %s: %s", vid_id, e)

        # Track info
        font_track = _get_font(32, bold=True)
        title_lines = textwrap.wrap(info.get("title", vid_id), width=35)
        y = 670
        for line in title_lines:
            draw.text((90, y), line, fill=COLOR_WHITE, font=font_track)
            y += 45

        dur_min = info.get("duration_s", 0) // 60
        font_dur = _get_font(24)
        draw.text((90, y + 15), f"Duration: {dur_min} min", fill=COLOR_GOLD, font=font_dur)

        _draw_branded_footer(draw, 1080, 1080)
        slide_path = output_dir / f"slide_{idx:02d}_track.jpg"
        img.save(str(slide_path), quality=95)
        slides.append(slide_path)

    # Last slide: CTA
    img = Image.new("RGB", (1080, 1080), COLOR_BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(30, 30), (1050, 1050)], outline=COLOR_GOLD, width=2)

    font_cta = _get_font(44, bold=True)
    font_sub2 = _get_font(28)

    cta_text = "Listen on YouTube"
    bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
    tw = bbox[2] - bbox[0]
    draw.text(((1080 - tw) / 2, 400), cta_text, fill=COLOR_GOLD, font=font_cta)

    sub_text = "Full playlist available now"
    bbox2 = draw.textbbox((0, 0), sub_text, font=font_sub2)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((1080 - tw2) / 2, 470), sub_text, fill=COLOR_WHITE, font=font_sub2)

    link_text = "youtube.com/@SonatMundi"
    bbox3 = draw.textbbox((0, 0), link_text, font=font_sub2)
    tw3 = bbox3[2] - bbox3[0]
    draw.text(((1080 - tw3) / 2, 540), link_text, fill=COLOR_DIM, font=font_sub2)

    logo = _load_logo(100)
    if logo:
        img.paste(logo, (490, 220), logo)

    _draw_branded_footer(draw, 1080, 1080)
    slide_path = output_dir / f"slide_{len(slides) + 1:02d}_cta.jpg"
    img.save(str(slide_path), quality=95)
    slides.append(slide_path)

    log.info("Carousel generated: %d slides for '%s'", len(slides), pl["title"])
    return slides


# ════════════════════════════════════════════════════════════════════════════
#  CAPTION GENERATION
# ════════════════════════════════════════════════════════════════════════════

def _pick_hashtags(categories: list, count_per_cat: int = 1) -> str:
    """Pick a unique hashtag combo from multiple categories."""
    tags = set()
    for cat in categories:
        sets = HASHTAG_SETS.get(cat, HASHTAG_SETS["general"])
        chosen = random.choice(sets)
        tags.update(chosen.split())
    # Always include brand tag
    tags.add("#sonatmundi")
    # Limit to 30 hashtags (Instagram max)
    tag_list = sorted(tags)[:30]
    random.shuffle(tag_list)
    return " ".join(tag_list)


def generate_reel_caption(video_id: str) -> str:
    """Generate a unique Reel caption."""
    info = VIDEOS[video_id]
    hook = random.choice(REEL_HOOKS)

    categories = ["general"]
    title_lower = info["title"].lower()
    if "sleep" in title_lower:
        categories.append("sleep")
    if "study" in title_lower or "focus" in title_lower:
        categories.append("study")
    if "healing" in title_lower or "mood" in title_lower:
        categories.append("healing")
    if "frequency" in title_lower or "528" in title_lower or "solfeggio" in title_lower:
        categories.append("frequency")
    if "silk" in title_lower or "world" in title_lower or "ancient" in title_lower or "sufi" in title_lower:
        categories.append("world")
    if "ambient" in title_lower:
        categories.append("ambient")

    hashtags = _pick_hashtags(categories)

    caption = (
        f"{hook}\n\n"
        f"From: {info['title']}\n\n"
        f"Full version on YouTube (link in bio)\n"
        f"youtube.com/@SonatMundi\n\n"
        f".\n.\n.\n"
        f"{hashtags}"
    )
    return caption


def generate_post_caption(post_type: str, context: dict) -> str:
    """Generate caption for image posts."""
    intros = {
        "track_spotlight": [
            "New from the archive. Which track speaks to your soul?",
            "Have you listened to this one yet? Pure sonic journey.",
            "This track has been resonating with listeners worldwide.",
            "Every sound in this track was crafted with intention.",
        ],
        "frequency_card": [
            "Sound science meets ancient wisdom.",
            "Frequencies are not just numbers — they are medicine.",
            "The more you understand frequencies, the more they can heal you.",
            "Your body already knows this frequency. Let it remember.",
        ],
        "quote": [
            "Words that resonate at the frequency of truth.",
            "Let this sink in for a moment.",
            "Some truths are universal. This is one of them.",
            "Pause. Read. Feel.",
        ],
        "did_you_know": [
            "Music history is full of surprises.",
            "The world of sound is deeper than you think.",
            "Here is something to expand your sonic horizons.",
            "Knowledge + music = wisdom.",
        ],
        "stats": [
            "Building something meaningful, one frequency at a time.",
            "Grateful for every listener on this journey.",
            "The Sonat Mundi universe keeps growing.",
        ],
    }

    categories = context.get("categories", ["general"])
    hashtags = _pick_hashtags(categories)

    intro = random.choice(intros.get(post_type, intros["quote"]))
    body = context.get("body", "")

    caption = f"{intro}\n\n{body}\n\n" if body else f"{intro}\n\n"
    caption += f"Follow @sonat.mundi for more\n\n.\n.\n.\n{hashtags}"
    return caption


def generate_carousel_caption(playlist_id: str) -> str:
    """Generate caption for a playlist carousel."""
    pl = PLAYLISTS[playlist_id]
    video_count = len(pl["videos"])

    hashtags = _pick_hashtags(["general", "ambient", "healing"])

    caption = (
        f"Swipe through our '{pl['title']}' playlist\n\n"
        f"{video_count} carefully curated tracks for your listening journey.\n\n"
        f"Full playlist available on YouTube — link in bio\n"
        f"youtube.com/@SonatMundi\n\n"
        f"Save this post for later\n\n"
        f".\n.\n.\n"
        f"{hashtags}"
    )
    return caption


# ════════════════════════════════════════════════════════════════════════════
#  PUBLISHING FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def publish_reel(video_id: str, history: dict, dry_run: bool = False) -> Optional[dict]:
    """Generate and publish a single Reel from a YouTube video."""
    info = VIDEOS[video_id]
    used = used_reel_segments(history, video_id)
    max_start = info["duration_s"] - REEL_MAX_DURATION - 60  # buffer at end

    if max_start <= 60:
        log.warning("Video %s too short for more Reels", video_id)
        return None

    # Find a segment that doesn't overlap with used ones
    for attempt in range(50):
        duration = random.randint(REEL_MIN_DURATION, REEL_MAX_DURATION)
        start = random.randint(60, max_start)  # skip first 60s (usually intro)
        end = start + duration

        # Check overlap with used segments (require at least 30s gap)
        overlap = any(
            not (end + 30 < us or start - 30 > ue)
            for us, ue in used
        )
        if not overlap:
            break
    else:
        log.warning("Could not find unused segment for %s after 50 attempts", video_id)
        return None

    log.info("Reel segment: %s [%d-%d] (%ds)", video_id, start, end, duration)

    # Generate unique filename
    uid = hashlib.md5(f"{video_id}_{start}_{end}".encode()).hexdigest()[:8]
    reel_path = WORK_DIR / f"reel_{video_id}_{uid}.mp4"

    if not reel_path.exists():
        download_video_segment(video_id, start, duration, reel_path)

    caption = generate_reel_caption(video_id)

    if dry_run:
        log.info("[DRY RUN] Would publish Reel: %s (%ds from %ds)", info["title"], duration, start)
        log.info("[DRY RUN] Caption preview:\n%s", caption[:200])
        return {"video_id": video_id, "start_s": start, "end_s": end, "dry_run": True}

    # Publish
    cl = get_ig_client()
    try:
        media = cl.clip_upload(
            str(reel_path),
            caption=caption,
        )
        ig_id = str(media.pk) if media else None
        log.info("Reel published! IG ID: %s", ig_id)

        record = {
            "video_id": video_id,
            "start_s": start,
            "end_s": end,
            "ts": datetime.utcnow().isoformat(),
            "ig_id": ig_id,
            "caption_hash": hashlib.md5(caption.encode()).hexdigest()[:8],
        }
        history.setdefault("reels", []).append(record)
        increment_daily_count(history)
        save_history(history)
        return record

    except Exception as e:
        log.error("Failed to publish Reel: %s", e)
        raise


def publish_post(history: dict, dry_run: bool = False, post_type: str = None) -> Optional[dict]:
    """Generate and publish a unique image post."""
    used_keys = used_post_keys(history)

    # Decide post type if not specified
    post_types_weighted = [
        ("track_spotlight", 3),
        ("frequency_card", 2),
        ("quote", 3),
        ("did_you_know", 2),
        ("stats", 1),
    ]

    if post_type:
        chosen_type = post_type
    else:
        # Pick type, preferring ones with less usage
        type_counts = {}
        for p in history.get("posts", []):
            t = p.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        weighted = []
        for t, w in post_types_weighted:
            usage_penalty = type_counts.get(t, 0)
            weighted.append((t, max(1, w * 3 - usage_penalty)))

        total = sum(w for _, w in weighted)
        r = random.random() * total
        cumulative = 0
        chosen_type = weighted[0][0]
        for t, w in weighted:
            cumulative += w
            if r <= cumulative:
                chosen_type = t
                break

    log.info("Generating post type: %s", chosen_type)

    uid = hashlib.md5(f"{chosen_type}_{datetime.utcnow().isoformat()}_{random.random()}".encode()).hexdigest()[:8]
    img_path = WORK_DIR / f"post_{chosen_type}_{uid}.jpg"
    caption = ""
    post_key = ""
    context = {}

    if chosen_type == "track_spotlight":
        # Pick a video not recently spotlighted
        spotlighted = {k for k in used_keys if k.startswith("spotlight_")}
        available = [vid for vid in VIDEOS if f"spotlight_{vid}" not in spotlighted]
        if not available:
            available = list(VIDEOS.keys())  # reset cycle
        vid_id = random.choice(available)
        generate_track_spotlight(vid_id, img_path)
        post_key = f"spotlight_{vid_id}"
        info = VIDEOS[vid_id]
        context = {
            "categories": ["general", "ambient"],
            "body": f"{info['title']}\nFull version on YouTube — link in bio",
        }
        caption = generate_post_caption("track_spotlight", context)

    elif chosen_type == "frequency_card":
        used_freq_indices = {int(k.split("_")[1]) for k in used_keys if k.startswith("freq_")}
        available = [i for i in range(len(FREQUENCY_FACTS)) if i not in used_freq_indices]
        if not available:
            available = list(range(len(FREQUENCY_FACTS)))
        idx = random.choice(available)
        generate_frequency_card(idx, img_path)
        post_key = f"freq_{idx}"
        fact = FREQUENCY_FACTS[idx]
        context = {
            "categories": ["frequency", "healing", "general"],
            "body": f"{fact['freq']} — {fact['title']}",
        }
        caption = generate_post_caption("frequency_card", context)

    elif chosen_type == "quote":
        used_quote_indices = {int(k.split("_")[1]) for k in used_keys if k.startswith("quote_")}
        available = [i for i in range(len(QUOTE_POOL)) if i not in used_quote_indices]
        if not available:
            available = list(range(len(QUOTE_POOL)))
        idx = random.choice(available)
        generate_quote_post(idx, img_path)
        post_key = f"quote_{idx}"
        text, author = QUOTE_POOL[idx]
        context = {
            "categories": ["general"],
            "body": f'"{text}" — {author}',
        }
        caption = generate_post_caption("quote", context)

    elif chosen_type == "did_you_know":
        used_dyk_indices = {int(k.split("_")[1]) for k in used_keys if k.startswith("dyk_")}
        available = [i for i in range(len(DID_YOU_KNOW_FACTS)) if i not in used_dyk_indices]
        if not available:
            available = list(range(len(DID_YOU_KNOW_FACTS)))
        idx = random.choice(available)
        generate_did_you_know(idx, img_path)
        post_key = f"dyk_{idx}"
        context = {
            "categories": ["world", "general"],
            "body": DID_YOU_KNOW_FACTS[idx],
        }
        caption = generate_post_caption("did_you_know", context)

    elif chosen_type == "stats":
        generate_stats_post(img_path)
        post_key = f"stats_{datetime.utcnow().strftime('%Y%m')}"
        context = {
            "categories": ["general"],
            "body": "7 albums. 5 playlists. One sonic universe.",
        }
        caption = generate_post_caption("stats", context)

    if dry_run:
        log.info("[DRY RUN] Would publish %s post: %s", chosen_type, img_path.name)
        log.info("[DRY RUN] Caption preview:\n%s", caption[:200])
        return {"type": chosen_type, "key": post_key, "dry_run": True}

    # Publish
    cl = get_ig_client()
    try:
        media = cl.photo_upload(
            str(img_path),
            caption=caption,
        )
        ig_id = str(media.pk) if media else None
        log.info("Post published! Type=%s IG ID=%s", chosen_type, ig_id)

        record = {
            "type": chosen_type,
            "key": post_key,
            "ts": datetime.utcnow().isoformat(),
            "ig_id": ig_id,
        }
        history.setdefault("posts", []).append(record)
        increment_daily_count(history)
        save_history(history)
        return record

    except Exception as e:
        log.error("Failed to publish post: %s", e)
        raise


def publish_carousel(playlist_id: str, history: dict, dry_run: bool = False) -> Optional[dict]:
    """Generate and publish a playlist carousel."""
    pl = PLAYLISTS.get(playlist_id)
    if not pl:
        log.error("Unknown playlist: %s", playlist_id)
        return None

    uid = hashlib.md5(f"{playlist_id}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]
    carousel_dir = WORK_DIR / f"carousel_{uid}"
    slides = generate_playlist_carousel(playlist_id, carousel_dir)

    if not slides:
        log.error("No slides generated for playlist %s", playlist_id)
        return None

    caption = generate_carousel_caption(playlist_id)

    if dry_run:
        log.info("[DRY RUN] Would publish carousel for '%s' (%d slides)", pl["title"], len(slides))
        log.info("[DRY RUN] Caption preview:\n%s", caption[:200])
        return {"playlist_id": playlist_id, "slides": len(slides), "dry_run": True}

    # Publish
    cl = get_ig_client()
    try:
        media = cl.album_upload(
            [str(s) for s in slides],
            caption=caption,
        )
        ig_id = str(media.pk) if media else None
        log.info("Carousel published! Playlist=%s IG ID=%s", pl["title"], ig_id)

        record = {
            "playlist_id": playlist_id,
            "ts": datetime.utcnow().isoformat(),
            "ig_id": ig_id,
            "slide_count": len(slides),
        }
        history.setdefault("carousels", []).append(record)
        increment_daily_count(history)
        save_history(history)
        return record

    except Exception as e:
        log.error("Failed to publish carousel: %s", e)
        raise


# ════════════════════════════════════════════════════════════════════════════
#  MODE HANDLERS
# ════════════════════════════════════════════════════════════════════════════

def mode_reels(args, history: dict):
    """Generate and post Reels."""
    if args.video_id:
        video_ids = [args.video_id]
    else:
        video_ids = list(VIDEOS.keys())
        random.shuffle(video_ids)

    posted = 0
    for vid_id in video_ids:
        if posted >= MAX_POSTS_PER_RUN:
            log.info("Max posts per run reached (%d)", MAX_POSTS_PER_RUN)
            break
        if today_post_count(history) >= DAILY_LIMIT:
            log.info("Daily limit reached")
            break

        result = publish_reel(vid_id, history, dry_run=args.dry_run)
        if result:
            posted += 1
            if posted < MAX_POSTS_PER_RUN and not args.dry_run:
                delay = MIN_POST_DELAY + random.randint(0, 120)
                log.info("Waiting %ds before next post...", delay)
                time.sleep(delay)

    log.info("Reels mode complete. Posted: %d", posted)


def mode_posts(args, history: dict):
    """Generate and post image posts."""
    posted = 0
    max_posts = min(MAX_POSTS_PER_RUN, 3)

    for _ in range(max_posts):
        if today_post_count(history) >= DAILY_LIMIT:
            log.info("Daily limit reached")
            break

        result = publish_post(history, dry_run=args.dry_run)
        if result:
            posted += 1
            if posted < max_posts and not args.dry_run:
                delay = MIN_POST_DELAY + random.randint(0, 120)
                log.info("Waiting %ds before next post...", delay)
                time.sleep(delay)

    log.info("Posts mode complete. Posted: %d", posted)


def mode_playlists(args, history: dict):
    """Generate and post playlist carousels."""
    used_pls = used_carousel_playlists(history)
    available = [pid for pid in PLAYLISTS if pid not in used_pls]

    if not available:
        log.info("All playlists have been posted. Resetting cycle.")
        available = list(PLAYLISTS.keys())

    random.shuffle(available)

    posted = 0
    for pl_id in available[:2]:  # Max 2 carousels per run
        if today_post_count(history) >= DAILY_LIMIT:
            break

        result = publish_carousel(pl_id, history, dry_run=args.dry_run)
        if result:
            posted += 1
            if not args.dry_run:
                delay = MIN_POST_DELAY + random.randint(0, 120)
                log.info("Waiting %ds before next post...", delay)
                time.sleep(delay)

    log.info("Playlists mode complete. Posted: %d", posted)


def mode_auto(args, history: dict):
    """Smart auto mode: 1 Reel + 1 Post per run."""
    posted = 0

    # 1. Post a Reel
    video_ids = list(VIDEOS.keys())
    random.shuffle(video_ids)
    for vid_id in video_ids:
        result = publish_reel(vid_id, history, dry_run=args.dry_run)
        if result:
            posted += 1
            break

    if not args.dry_run and posted > 0:
        delay = MIN_POST_DELAY + random.randint(0, 120)
        log.info("Waiting %ds before next post...", delay)
        time.sleep(delay)

    # 2. Post an image
    if today_post_count(history) < DAILY_LIMIT:
        result = publish_post(history, dry_run=args.dry_run)
        if result:
            posted += 1

    log.info("Auto mode complete. Posted: %d", posted)


def mode_generate_only(args, history: dict):
    """Generate content without publishing (for preview)."""
    log.info("=== GENERATE-ONLY MODE ===")

    # Generate one of each type
    vid_id = random.choice(list(VIDEOS.keys()))

    # Reel
    info = VIDEOS[vid_id]
    used = used_reel_segments(history, vid_id)
    max_start = info["duration_s"] - REEL_MAX_DURATION - 60
    if max_start > 60:
        duration = random.randint(REEL_MIN_DURATION, REEL_MAX_DURATION)
        start = random.randint(60, max_start)
        uid = hashlib.md5(f"{vid_id}_{start}".encode()).hexdigest()[:8]
        reel_path = WORK_DIR / f"preview_reel_{uid}.mp4"
        log.info("Generating preview Reel: %s [%d-%d]", vid_id, start, start + duration)
        try:
            download_video_segment(vid_id, start, duration, reel_path)
            log.info("Preview Reel: %s", reel_path)
        except Exception as e:
            log.error("Reel generation failed: %s", e)

    # Post types
    for post_type in ["track_spotlight", "frequency_card", "quote", "did_you_know", "stats"]:
        uid = hashlib.md5(f"preview_{post_type}_{random.random()}".encode()).hexdigest()[:8]
        img_path = WORK_DIR / f"preview_{post_type}_{uid}.jpg"

        if post_type == "track_spotlight":
            generate_track_spotlight(random.choice(list(VIDEOS.keys())), img_path)
        elif post_type == "frequency_card":
            generate_frequency_card(random.randint(0, len(FREQUENCY_FACTS) - 1), img_path)
        elif post_type == "quote":
            generate_quote_post(random.randint(0, len(QUOTE_POOL) - 1), img_path)
        elif post_type == "did_you_know":
            generate_did_you_know(random.randint(0, len(DID_YOU_KNOW_FACTS) - 1), img_path)
        elif post_type == "stats":
            generate_stats_post(img_path)

        log.info("Preview %s: %s", post_type, img_path)

    # Carousel
    pl_id = random.choice(list(PLAYLISTS.keys()))
    carousel_dir = WORK_DIR / f"preview_carousel_{pl_id[:8]}"
    slides = generate_playlist_carousel(pl_id, carousel_dir)
    log.info("Preview carousel: %d slides in %s", len(slides), carousel_dir)

    log.info("=== All previews generated in %s ===", WORK_DIR)


# ════════════════════════════════════════════════════════════════════════════
#  DAILY LIMIT CONSTANT
# ════════════════════════════════════════════════════════════════════════════
DAILY_LIMIT = 6


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Sonat Mundi — YouTube to Instagram Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["reels", "posts", "playlists", "auto", "generate-only"],
        default=os.environ.get("YT2IG_MODE", "auto"),
        help="Content generation mode (default: auto)",
    )
    parser.add_argument(
        "--video-id",
        default=None,
        help="Target a specific YouTube video ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "false").lower() == "true",
        help="Show what would be done without posting",
    )

    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Sonat Mundi — YouTube to Instagram")
    log.info("Mode: %s | Dry run: %s | Video: %s",
             args.mode, args.dry_run, args.video_id or "all")
    log.info("=" * 60)

    # Verify environment
    if not args.dry_run and args.mode != "generate-only":
        if not os.environ.get("INSTAGRAM_USERNAME") or not os.environ.get("INSTAGRAM_PASSWORD"):
            log.error("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set")
            sys.exit(1)

    history = load_history()

    try:
        if args.mode == "reels":
            mode_reels(args, history)
        elif args.mode == "posts":
            mode_posts(args, history)
        elif args.mode == "playlists":
            mode_playlists(args, history)
        elif args.mode == "auto":
            mode_auto(args, history)
        elif args.mode == "generate-only":
            mode_generate_only(args, history)
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception as e:
        log.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        history["last_run"] = datetime.utcnow().isoformat()
        save_history(history)

    log.info("Done.")


if __name__ == "__main__":
    main()
