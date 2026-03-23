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
VIDEO_FILE       = r"D:\Yedekler\UCS\Sounds of Frequencies Vol.1 Sacred Frequencies\Sacred_Frequencies_Vol1.mp4"
SCOPES           = ["https://www.googleapis.com/auth/youtube.upload"]

VIDEO_TITLE = (
    "Sounds of Frequencies Vol.1 \u2756 Sacred Frequencies \u2756 "
    "Solfeggio & Binaural Healing Tones | Sonat Mundi"
)

VIDEO_DESCRIPTION = """Sonat Mundi \u2014 United Colours of Sound
Omnia Resonant

Sacred Frequencies \u2014 The Complete Healing Spectrum.

15 pure solfeggio and binaural frequency compositions, each tuned to a specific healing purpose. From the deep grounding of 174 Hz to the divine consciousness of 963 Hz \u2014 this is sound as medicine, as ancient as the universe itself.

Use headphones for the full healing experience, especially for binaural tracks.

\u2756 TRACKLIST:

00:00 - Foundation \u2014 174 Hz
The lowest solfeggio frequency. Root Chakra grounding. Pure sine tone foundation with cave water resonance. Reduces pain, relieves stress, brings deep sense of safety and security.

05:12 - Cellular Repair \u2014 285 Hz
Tissue regeneration frequency. Sacral Chakra support. Soft forest stream ambience. Influences energy fields, heals damaged tissue, supports cellular regeneration at quantum level.

11:10 - Liberation \u2014 396 Hz
Root and Sacral Chakra liberator. Gentle distant thunder. Releases fear, guilt and grief. Turns grief into joy, liberates from subconscious negative beliefs.

17:04 - Transformation \u2014 417 Hz
Sacral Chakra activator. Soft ocean waves. Facilitates change, clears traumatic experiences, cleanses negative energy from cells and environment.

25:03 - The Love Frequency \u2014 528 Hz
Heart Chakra miracle tone. Birdsong at dawn. The most studied healing frequency \u2014 DNA repair, increased energy, clarity of mind, deep inner peace, awakened creativity.

30:46 - Connection \u2014 639 Hz
Heart Chakra harmonizer. Gentle rain on leaves. Enhances communication, understanding, tolerance and love. Reconnects broken relationships, harmonizes family and community energy.

36:15 - Expression \u2014 741 Hz
Throat Chakra awakener. Wind through pine forest. Awakens intuition and creative expression. Cleanses cells from toxins, electromagnetic radiation and viral infections.

41:21 - Return \u2014 852 Hz
Third Eye Chakra activator. Distant temple bells. Returns the soul to spiritual order. Awakens intuition, raises cellular energy, opens communication with higher self.

47:22 - Divine \u2014 963 Hz
Crown Chakra and pineal gland activation. Cosmic silence with resonance. The frequency of divine consciousness \u2014 awakens perfect state, enables non-vibrational experiences, connects to universal oneness.

55:21 - Earth Resonance \u2014 432 Hz
Universal natural tuning, Schumann Resonance alignment. Mountain wind. Mathematical tuning of the universe \u2014 connects to nature, reduces anxiety, opens the heart, aligns with cosmic vibration.

1:02:24 - Binaural Delta \u2014 2 Hz
Deep sleep and healing brainwave state. Night forest ambience. Delta waves promote deepest sleep, cellular regeneration, immune system boost, unconscious healing. Use headphones.

1:09:02 - Binaural Theta \u2014 6 Hz
Deep meditation and creativity brainwave state. Gentle stream. Theta waves connect to subconscious mind, enhance intuition, creativity and emotional healing. Use headphones.

1:13:56 - Binaural Alpha \u2014 10 Hz
Relaxed awareness brainwave state. Soft breeze and birds. Alpha waves promote calm focus, stress relief, positive thinking and light meditation. Use headphones.

1:19:50 - Binaural Gamma \u2014 40 Hz
Peak consciousness and cognitive enhancement. Subtle cosmic hum. Gamma waves associated with heightened awareness, memory formation, peak mental performance and spiritual insight. Use headphones.

1:25:25 - The Complete Spectrum \u2014 All Frequencies
All 9 solfeggio frequencies layered in harmonic unity. Full nature tapestry. The complete healing journey \u2014 174, 285, 396, 417, 528, 639, 741, 852, 963 Hz unified in one transcendent composition.

\u2756 Healing Properties by Frequency:
174 Hz \u2014 Pain relief, stress reduction, grounding
285 Hz \u2014 Cellular regeneration, tissue healing
396 Hz \u2014 Fear and guilt release, liberation
417 Hz \u2014 Trauma clearing, transformation
528 Hz \u2014 DNA repair, love, inner peace
639 Hz \u2014 Relationship harmony, communication
741 Hz \u2014 Detoxification, creative expression
852 Hz \u2014 Spiritual awakening, intuition
963 Hz \u2014 Divine consciousness, unity
432 Hz \u2014 Natural alignment, heart opening
Binaural Delta \u2014 Deep sleep, immune healing
Binaural Theta \u2014 Meditation, creativity
Binaural Alpha \u2014 Calm focus, stress relief
Binaural Gamma \u2014 Peak consciousness, clarity

\u2756 Recommended Use:
Use headphones for binaural tracks (tracks 11-14)
Find a comfortable position \u2014 sitting or lying down
Set intention before listening
Allow the frequencies to work naturally
Drink water after each session

\u2756 About Sonat Mundi:
We create immersive soundscapes inspired by world music traditions, human emotions, healing frequencies and the poetry of everyday life.

\U0001f30d SOUNDS OF WORLD \u2014 195 nations, every tradition
\U0001f3ad SOUNDS OF MOODS \u2014 The full emotional spectrum
\U0001f3af SOUNDS OF CONCEPTS \u2014 Study, sleep, meditation, movement
\u2728 SOUNDS OF FREQUENCIES \u2014 432 Hz, 528 Hz, Solfeggio, Binaural

\U0001f310 sonatmundi.com
\U0001f4e7 info@sonatmundi.com

\u00a9 Sonat Mundi \u2014 United Colours of Sound
Omnia Resonant \u2014 All things resonate."""

VIDEO_TAGS = [
    "solfeggio frequencies", "healing frequencies", "528 hz", "432 hz",
    "174 hz", "285 hz", "396 hz", "417 hz", "639 hz", "741 hz", "852 hz", "963 hz",
    "binaural beats", "delta waves", "theta waves", "alpha waves", "gamma waves",
    "chakra healing", "DNA repair", "meditation music", "sleep music", "healing music",
    "sacred frequencies", "sonat mundi", "omnia resonant", "sounds of frequencies",
    "pure tones", "crystal clear audio",
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
                done_gb = file_size * status.progress() / 1024**3
                rate    = done_gb / elapsed * 1024 if elapsed > 0 else 0  # MB/s
                eta     = ((1 - status.progress()) * elapsed / status.progress()
                           if status.progress() > 0 else 0)
                print(f"  {pct:3d}%  |  {done_gb:.2f}/{file_size/1024**3:.2f} GB"
                      f"  |  {rate:.1f} MB/s  |  ETA {int(eta//60)}m{int(eta%60):02d}s")
                retry_count = 0  # reset on success

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
