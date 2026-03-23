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

# ── Config ────────────────────────────────────────────────────────────────────
CREDENTIALS_FILE = r"D:\Yedekler\UCS\credentials.json"
TOKEN_FILE       = r"D:\Yedekler\UCS\token.json"
VIDEO_FILE       = r"D:\Yedekler\UCS\playlist_vol1.mp4"
SCOPES           = ["https://www.googleapis.com/auth/youtube.upload"]

VIDEO_TITLE = (
    "Ancient Soul Journey Vol.1 \u2726 Sufi Ambient, Persian Lounge, 528Hz Solfeggio"
    " | United Colours of Sound"
)

VIDEO_DESCRIPTION = """Welcome to United Colours of Sound — where ancient wisdom meets modern frequencies.

✦ TRACKLIST:
00:00 - Sufi Ambient I
07:59 - Sufi Ambient II
15:58 - Sufi Ambient III
19:50 - Sufi Ambient IV
23:42 - 528 Hz Solfeggio I
25:51 - 528 Hz Solfeggio II
28:17 - Persian Lounge I
31:20 - Persian Lounge II

🎵 Perfect for: Meditation | Sleep | Study | Healing | Yoga

🌐 unitedcoloursofsound.com

#sufimusic #528hz #persianlounge #ambientmusic #meditationmusic #healingfrequency #spiritualmusic #worldmusic"""

VIDEO_TAGS = [
    "sufi ambient", "528hz", "persian lounge", "meditation music",
    "healing frequency", "spiritual music", "world music", "ambient music",
]

CATEGORY_ID  = "10"   # Music
PRIVACY      = "public"

# Retry config
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
            print("Refreshing access token …")
            creds.refresh(Request())
        else:
            print("Opening browser for Google OAuth2 …")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"Token saved -> {TOKEN_FILE}")

    return build("youtube", "v3", credentials=creds)


# ── Upload with resumable upload + retry ─────────────────────────────────────
def upload(youtube):
    file_size = os.path.getsize(VIDEO_FILE)
    print(f"\nFile : {VIDEO_FILE}")
    print(f"Size : {file_size / 1024**2:.1f} MB")

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
        chunksize=8 * 1024 * 1024,   # 8 MB chunks
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
                done_mb = file_size * status.progress() / 1024**2
                rate    = done_mb / elapsed if elapsed > 0 else 0  # MB/s
                eta     = ((1 - status.progress()) * elapsed / status.progress()
                           if status.progress() > 0 else 0)
                print(f"  {pct:3d}%  |  {done_mb:.0f}/{file_size/1024**2:.0f} MB"
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

    elapsed = time.time() - start_time
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
