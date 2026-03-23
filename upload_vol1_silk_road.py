#!/usr/bin/env python3
"""
Upload Sounds of World Vol.1 – Ancient Silk Road to YouTube.
"""

import os
import sys
import time
import http.client
import httplib2

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ── Config ─────────────────────────────────────────────────────────────────
CREDENTIALS_FILE = r"D:\Yedekler\UCS\credentials.json"
TOKEN_FILE       = r"D:\Yedekler\UCS\token.json"
VIDEO_FILE       = r"D:\Yedekler\UCS\Sounds of World Vol. 1 Ancient Silk Road Authentic\Sounds_of_World_Vol1.mp4"
SCOPES           = ["https://www.googleapis.com/auth/youtube.upload"]

VIDEO_TITLE = (
    "Sounds of World Vol.1 \u2746 Ancient Silk Road \u2746 "
    "15 Tracks of Authentic World Music | Sonat Mundi"
)

VIDEO_DESCRIPTION = """\
Sonat Mundi \u2014 United Colours of Sound
Omnia Resonant

A sonic journey through the Ancient Silk Road \u2014 15 authentic world music compositions, each rooted in the living traditions of its homeland. From the mystical plains of Anatolia to the sacred temples of Tibet, from the Flamenco courts of Andalusia to the vast Mongolian steppe \u2014 this is music that remembers.

\u2746 TRACKLIST:
00:00 - Anatolian Dawn \u2014 Ney flute, Sufi Makam scales, microtonal woodwind textures, sunrise atmosphere
04:00 - Samarkand Caravanserai \u2014 Tanbur and Dutar melodies, Doyra percussion, Central Asian folk scales
08:00 - Hafiz\u2019s Secret \u2014 Santur hammered dulcimer with fast tremolos, Dastgah scales, soft Tombak rhythm
12:00 - The Spirit of Tengri \u2014 Kh\u00f6\u00f6mei throat singing drones, Morin Khuur horsehead fiddle, vast steppe atmosphere
16:00 - Duduk\u2019s Lament \u2014 Double-reed Duduk woodwind, traditional drone accompaniment, Armenian folk melody
20:00 - Andalusian Twilight \u2014 Flamenco guitar fingerpicking, Moorish Oud fusion, Cajon drum, Phrygian dominant scales
24:00 - Kyoto Moon \u2014 Koto 13-string zither plucking, Shakuhachi flute with traditional vibrato, Pentatonic scales
28:00 - Himalayan Silence \u2014 Tibetan Singing Bowls, long sustain, Dungchen long horn drones, spiritual temple atmosphere
32:00 - Varanasi Morning \u2014 Sitar improvisation, Tabla drums, Tanpura drone, authentic Indian Raga scales
36:00 - Tuareg Fire \u2014 Tishoumaren desert blues guitar, hypnotic Tinariwen rhythms, tribal hand claps
40:00 - Byzantine Echoes \u2014 Ancient Lyre plucking, Byzantine chant textures, stone cathedral acoustics, Phrygian mode
44:00 - Balkan Soul \u2014 Kaval flute, odd-meter 7/8 Balkan rhythms, Accordion swells, traditional folk soul
48:00 - Mesopotamian Wind \u2014 Qanun zither with delicate ornamentation, Bendir frame drum, Tigris river atmosphere
52:00 - The Weaver\u2019s Song \u2014 Pipa lute plucking, Guzheng glissandos, ancient Chinese silk-making folk rhythm
56:00 - Global Silk Road \u2014 Oud, Sitar and Ney fusion, world instruments meeting in harmony, epic cultural finale

\u2746 Instruments featured:
Ney \u00b7 Oud \u00b7 Sitar \u00b7 Koto \u00b7 Shakuhachi \u00b7 Santur \u00b7 Tanbur \u00b7 Dutar \u00b7 Doyra \u00b7 Morin Khuur \u00b7 Duduk \u00b7 Flamenco Guitar \u00b7 Cajon \u00b7 Tibetan Singing Bowls \u00b7 Dungchen \u00b7 Tabla \u00b7 Tanpura \u00b7 Qanun \u00b7 Bendir \u00b7 Pipa \u00b7 Guzheng \u00b7 Kaval \u00b7 Accordion \u00b7 Lyre

\u2746 Cultures & Traditions:
Anatolia \u00b7 Uzbekistan \u00b7 Persia \u00b7 Mongolia \u00b7 Armenia \u00b7 Andalusia \u00b7 Japan \u00b7 Tibet \u00b7 India \u00b7 Sahara \u00b7 Byzantine Greece \u00b7 Balkans \u00b7 Mesopotamia \u00b7 China \u00b7 Global Fusion

\u2746 About Sonat Mundi:
We create immersive soundscapes inspired by world music traditions, human emotions, healing frequencies and the poetry of everyday life.

\U0001f30d SOUNDS OF WORLD \u2014 195 nations, every tradition
\U0001f3ad SOUNDS OF EMOTIONS \u2014 Joy, melancholy, wonder, serenity
\U0001f3af SOUNDS OF CONCEPTS \u2014 Study, sleep, meditation, movement
\u2728 SOUNDS OF FREQUENCIES \u2014 432 Hz, 528 Hz, Solfeggio, Binaural

\U0001f310 sonatmundi.com
\U0001f4e7 info@sonatmundi.com

\u00a9 Sonat Mundi \u2014 United Colours of Sound
Omnia Resonant \u2014 All things resonate.\
"""

VIDEO_TAGS = [
    "silk road music", "world music", "ancient music", "ambient world music",
    "ney flute", "oud music", "sitar music", "koto music", "tibetan bowls",
    "flamenco guitar", "armenian duduk", "mongolian throat singing", "indian raga",
    "persian music", "japanese music", "anatolian music", "uzbek music",
    "balkan music", "byzantine music", "mesopotamian music",
    "chinese traditional music", "tuareg music",
    "sonat mundi", "omnia resonant", "sounds of world",
]

CATEGORY_ID = "10"    # Music
PRIVACY     = "public"

# Retry config
MAX_RETRIES          = 10
RETRIABLE_STATUS     = {500, 502, 503, 504}
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError,
    http.client.NotConnected, http.client.IncompleteRead,
    http.client.ImproperConnectionState, http.client.CannotSendRequest,
    http.client.CannotSendHeader, http.client.ResponseNotReady,
    http.client.BadStatusLine,
)


# ── Auth ───────────────────────────────────────────────────────────────────
def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing access token …")
            creds.refresh(Request())
        else:
            print("Opening browser for Google OAuth2 …")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"Token saved -> {TOKEN_FILE}")

    return build("youtube", "v3", credentials=creds)


# ── Upload with resumable upload + retry ──────────────────────────────────
def upload(youtube):
    file_size = os.path.getsize(VIDEO_FILE)
    print(f"\nFile : {VIDEO_FILE}")
    print(f"Size : {file_size / 1024**3:.2f} GB")

    body = {
        "snippet": {
            "title":       VIDEO_TITLE,
            "description": VIDEO_DESCRIPTION,
            "tags":        VIDEO_TAGS,
            "categoryId":  CATEGORY_ID,
        },
        "status": {
            "privacyStatus":           PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        VIDEO_FILE,
        mimetype="video/mp4",
        chunksize=8 * 1024 * 1024,
        resumable=True,
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    print("\nStarting upload …\n")
    response    = None
    retry_count = 0
    start_time  = time.time()

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct     = int(status.progress() * 100)
                elapsed = time.time() - start_time
                done_gb = file_size * status.progress() / 1024**3
                rate    = done_gb / elapsed * 1024 if elapsed > 0 else 0
                eta     = ((1 - status.progress()) * elapsed / status.progress()
                           if status.progress() > 0 else 0)
                print(f"  {pct:3d}%  |  {done_gb:.2f}/{file_size/1024**3:.2f} GB"
                      f"  |  {rate:.1f} MB/s  |  ETA {int(eta//60)}m{int(eta%60):02d}s")
                retry_count = 0

        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS:
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    sys.exit(f"Too many retries ({MAX_RETRIES}). Aborting.")
                wait = 2 ** retry_count
                print(f"HTTP {e.resp.status} — retry {retry_count}/{MAX_RETRIES} in {wait}s …")
                time.sleep(wait)
            else:
                raise

        except RETRIABLE_EXCEPTIONS as e:
            retry_count += 1
            if retry_count > MAX_RETRIES:
                sys.exit(f"Too many retries ({MAX_RETRIES}). Aborting.")
            wait = 2 ** retry_count
            print(f"Network error: {e}\nRetry {retry_count}/{MAX_RETRIES} in {wait}s …")
            time.sleep(wait)

    elapsed  = time.time() - start_time
    video_id = response.get("id", "unknown")
    print(f"\nUpload complete in {int(elapsed//60)}m{int(elapsed%60):02d}s")
    print(f"  Video ID : {video_id}")
    print(f"  URL      : https://www.youtube.com/watch?v={video_id}")
    return video_id


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(CREDENTIALS_FILE):
        sys.exit(f"ERROR: credentials.json not found at {CREDENTIALS_FILE}")
    if not os.path.exists(VIDEO_FILE):
        sys.exit(f"ERROR: video file not found at {VIDEO_FILE}")

    youtube = authenticate()
    upload(youtube)
