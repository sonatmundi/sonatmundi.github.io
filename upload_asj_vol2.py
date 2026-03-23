#!/usr/bin/env python3
"""
Upload Ancient Soul Journey Vol.2 to YouTube.
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

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ────────────────────────────────────────────────────────────────────
CREDENTIALS_FILE = r"D:\Yedekler\UCS\credentials.json"
TOKEN_FILE       = r"D:\Yedekler\UCS\token.json"
VIDEO_FILE       = r"D:\Yedekler\UCS\Sounds\Ancient Soul Journey Vol.2 Echoes of Ancient Civilizations\Ancient_Soul_Journey_Vol2.mp4"
SCOPES           = ["https://www.googleapis.com/auth/youtube.upload"]

VIDEO_TITLE = (
    "Ancient Soul Journey Vol.2 \u2756 Echoes of Ancient Civilizations "
    "\u2756 Meditative World Music | Sonat Mundi"
)

VIDEO_DESCRIPTION = """\
A sonic journey through humanity\u2019s oldest civilizations \u2014 15 meditative instrumental compositions inspired by ancient instruments and sacred traditions.

From the first temple at G\u00f6bekli Tepe to the eternal return of all civilizations \u2014 close your eyes and travel through time.

\u2756 TRACKLIST:
00:00 - G\u00f6bekli Tepe \u2014 First Temple | Bone flute, stone resonance
05:09 - Sumerian Dream \u2014 Mesopotamia | Ancient lyre, sacred scales
09:22 - Silk Road Dusk \u2014 Central Asia | Dutar, Tanbur, modal drone
13:59 - Zoroastrian Fire \u2014 Persia | Santur, Ney, sacred fire
18:18 - Scythian Wind \u2014 Eurasian Steppes | Morin Khuur, steppe drone
23:37 - Lydian Gold \u2014 Ancient Anatolia | Ancient lyre, Lydian mode
28:23 - Urartu \u2014 Mountain Kingdom | Duduk, highland meditation
33:27 - Phoenician Sea \u2014 Mediterranean | Ancient lyre, sea drone
38:19 - Druid Circle \u2014 Celtic Lands | Celtic harp, forest meditation
42:30 - Norse Void \u2014 Scandinavia | Nyckelharpa, Hardanger fiddle
46:17 - Vedic Dawn \u2014 Ancient India | Tanpura, Sitar, Raga
53:20 - Shamanic Journey \u2014 Siberia | Throat singing, shaman drum
57:39 - Hellenistic Dusk \u2014 Ancient Greece | Ancient aulos, Greek modes
1:02:31 - Egyptian Temple \u2014 Nile Valley | Ancient oud, temple drone
1:07:46 - The Eternal Return \u2014 All Civilizations | All instruments unified

\u2756 Perfect for: Meditation \u00b7 Deep Sleep \u00b7 Study \u00b7 Yoga \u00b7 Healing \u00b7 Ancient History

\U0001f310 sonatmundi.com | \U0001f4e7 info@sonatmundi.com
\u00a9 Sonat Mundi \u2014 United Colours of Sound | Omnia Resonant"""

VIDEO_TAGS = [
    "ancient world music", "meditation music", "ambient world music",
    "ancient civilizations music", "mesopotamia music", "persian music",
    "celtic music", "nordic music", "vedic music", "ancient egypt music",
    "silk road music", "meditative instrumental", "sonat mundi",
    "omnia resonant", "ancient soul journey", "healing music",
    "sleep music", "study music", "world music", "ethnic music",
]

CATEGORY_ID  = "10"   # Music
PRIVACY      = "public"

MAX_RETRIES          = 10
RETRIABLE_STATUS     = {500, 502, 503, 504}
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError,
                        http.client.NotConnected,
                        http.client.IncompleteRead,
                        http.client.ImproperConnectionState,
                        http.client.CannotSendRequest,
                        http.client.CannotSendHeader,
                        http.client.ResponseNotReady,
                        http.client.BadStatusLine)

# ── Auth ──────────────────────────────────────────────────────────────────────
def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing access token ...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed ({e}). Re-authorizing ...")
                creds = None
        if not creds or not creds.valid:
            print("Opening browser for Google OAuth2 ...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"Token saved -> {TOKEN_FILE}")

    return build("youtube", "v3", credentials=creds)


# ── Upload ────────────────────────────────────────────────────────────────────
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
            "privacyStatus":          PRIVACY,
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

    print("\nStarting upload ...\n")
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
                print(f"HTTP {e.resp.status} — retry {retry_count}/{MAX_RETRIES} in {wait}s ...")
                time.sleep(wait)
            else:
                raise

        except RETRIABLE_EXCEPTIONS as e:
            retry_count += 1
            if retry_count > MAX_RETRIES:
                sys.exit(f"Too many retries ({MAX_RETRIES}). Aborting.")
            wait = 2 ** retry_count
            print(f"Network error: {e}\nRetry {retry_count}/{MAX_RETRIES} in {wait}s ...")
            time.sleep(wait)

    elapsed  = time.time() - start_time
    video_id = response.get("id", "unknown")
    print(f"\nUpload complete in {int(elapsed//60)}m{int(elapsed%60):02d}s")
    print(f"  Video ID : {video_id}")
    print(f"  URL      : https://www.youtube.com/watch?v={video_id}")
    return video_id


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(CREDENTIALS_FILE):
        sys.exit(f"ERROR: credentials.json not found at {CREDENTIALS_FILE}")
    if not os.path.exists(VIDEO_FILE):
        sys.exit(f"ERROR: video file not found at {VIDEO_FILE}")

    youtube = authenticate()
    upload(youtube)
