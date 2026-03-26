"""
Sonat Mundi — Instagram Auto Publisher (GitHub Actions uyumlu)

Kullanim:
  # Lokal calistirma
  export INSTAGRAM_USERNAME=sonat.mundi
  export INSTAGRAM_PASSWORD=xxx
  python -m growth.instagram_publisher --day 1
  python -m growth.instagram_publisher --day all
  python -m growth.instagram_publisher --day 1 --posts-only
  python -m growth.instagram_publisher --day 1 --reels-only
  python -m growth.instagram_publisher --day 1 --dry-run

  # GitHub Actions icin env vars:
  PUBLISH_DAY=1  PUBLISH_MODE=both  DRY_RUN=false
"""

import os
import sys
import time
import json
import random
import logging
import argparse
import urllib.request
from pathlib import Path
from datetime import datetime

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("instagram_publisher")

# ── PATHS ──
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
POSTS_DIR = Path(os.environ.get("INSTAGRAM_POSTS_DIR", str(SCRIPT_DIR / "instagram" / "posts")))
SESSION_FILE = Path(os.environ.get("INSTAGRAM_SESSION_FILE", str(REPO_ROOT / "ig_session.json")))
MEDIA_DIR = Path(os.environ.get("INSTAGRAM_MEDIA_DIR", str(REPO_ROOT / "media")))
COVERS_DIR = Path(os.environ.get("INSTAGRAM_COVERS_DIR", str(MEDIA_DIR / "covers")))
SHORTS_DIR = Path(os.environ.get("INSTAGRAM_SHORTS_DIR", str(MEDIA_DIR / "shorts")))

# ── SAFETY SETTINGS ──
MIN_DELAY = int(os.environ.get("INSTAGRAM_MIN_DELAY", "180"))
MAX_DELAY = int(os.environ.get("INSTAGRAM_MAX_DELAY", "300"))
DAILY_LIMIT = int(os.environ.get("INSTAGRAM_DAILY_LIMIT", "5"))
COMMENT_DELAY = int(os.environ.get("INSTAGRAM_COMMENT_DELAY", "30"))

# ── YouTube thumbnail URLs for fallback cover downloads ──
YOUTUBE_THUMBNAIL_MAP = {
    "world_album_cover_3000x3000.jpg": "https://i.ytimg.com/vi/PLACEHOLDER_WORLD/maxresdefault.jpg",
    "study_album_cover_3000x3000.jpg": "https://i.ytimg.com/vi/PLACEHOLDER_STUDY/maxresdefault.jpg",
    "moods_album_cover_3000x3000.jpg": "https://i.ytimg.com/vi/PLACEHOLDER_MOODS/maxresdefault.jpg",
    "frequencies_album_cover_3000x3000.jpg": "https://i.ytimg.com/vi/PLACEHOLDER_FREQ/maxresdefault.jpg",
    "asj_vol1_album_cover_3000x3000.jpg": "https://i.ytimg.com/vi/PLACEHOLDER_ASJ/maxresdefault.jpg",
    "civilizations_album_cover_3000x3000.jpg": "https://i.ytimg.com/vi/PLACEHOLDER_CIV/maxresdefault.jpg",
}

# ── 9 GUNLUK PLAN ──
PLAN = [
    {
        "day": 1,
        "post": {
            "type": "carousel",
            "images": [
                "post_01/slide_1_logo.png",
                "post_01/slide_2_ucos.png",
                "post_01/slide_3_motto.png",
                "post_01/slide_4_stats.png",
                "post_01/slide_5_stream.png",
            ],
            "caption_file": "post_01/caption.txt",
            "hashtags_file": "post_01/hashtags.txt",
        },
        "reel": {
            "video": "short_528hz.mp4",
            "caption_file": "post_01/reel_caption.txt",
        },
    },
    {
        "day": 2,
        "post": {
            "type": "photo",
            "image": "world_album_cover_3000x3000.jpg",
            "image_dir": "covers",
            "caption_file": "post_02/caption.txt",
            "hashtags_file": "post_02/hashtags.txt",
        },
        "reel": {
            "video": "short_varanasi.mp4",
            "caption_file": "post_02/reel_caption.txt",
        },
    },
    {
        "day": 3,
        "post": {
            "type": "photo",
            "image": "study_album_cover_3000x3000.jpg",
            "image_dir": "covers",
            "caption_file": "post_03/caption.txt",
            "hashtags_file": "post_03/hashtags.txt",
        },
        "reel": {
            "video": "short_cafe_study.mp4",
            "caption_file": "post_03/reel_caption.txt",
        },
    },
    {
        "day": 4,
        "post": {
            "type": "carousel",
            "images": [
                "post_04/slide_1_intro.png",
                "post_04/slide_2_world.png",
                "post_04/slide_3_moods.png",
                "post_04/slide_4_concepts.png",
                "post_04/slide_5_frequencies.png",
                "post_04/slide_6_sleep.png",
            ],
            "caption_file": "post_04/caption.txt",
            "hashtags_file": "post_04/hashtags.txt",
        },
        "reel": {
            "video": "short_persian.mp4",
            "caption_file": "post_04/reel_caption.txt",
        },
    },
    {
        "day": 5,
        "post": {
            "type": "photo",
            "image": "moods_album_cover_3000x3000.jpg",
            "image_dir": "covers",
            "caption_file": "post_05/caption.txt",
            "hashtags_file": "post_05/hashtags.txt",
        },
        "reel": {
            "video": "short_nostalgia.mp4",
            "caption_file": "post_05/reel_caption.txt",
        },
    },
    {
        "day": 6,
        "post": {
            "type": "photo",
            "image": "frequencies_album_cover_3000x3000.jpg",
            "image_dir": "covers",
            "caption_file": "post_06/caption.txt",
            "hashtags_file": "post_06/hashtags.txt",
        },
        "reel": {
            "video": "short_432hz.mp4",
            "caption_file": "post_06/reel_caption.txt",
        },
    },
    {
        "day": 7,
        "post": {
            "type": "photo",
            "image": "asj_vol1_album_cover_3000x3000.jpg",
            "image_dir": "covers",
            "caption_file": "post_07/caption.txt",
            "hashtags_file": "post_07/hashtags.txt",
        },
        "reel": {
            "video": "short_gobekli_tepe.mp4",
            "caption_file": "post_07/reel_caption.txt",
        },
    },
    {
        "day": 8,
        "post": {
            "type": "photo",
            "image": "civilizations_album_cover_3000x3000.jpg",
            "image_dir": "covers",
            "caption_file": "post_08/caption.txt",
            "hashtags_file": "post_08/hashtags.txt",
        },
        "reel": {
            "video": "short_deep_sleep.mp4",
            "caption_file": "post_08/reel_caption.txt",
        },
    },
    {
        "day": 9,
        "post": None,
        "reel": {
            "video": "short_velvet_silence.mp4",
            "caption_file": "post_09/reel_caption.txt",
        },
    },
]


def safe_delay(label=""):
    """Rate-limiting delay between uploads."""
    delay = random.randint(MIN_DELAY, MAX_DELAY)
    logger.info(f"Guvenlik beklemesi: {delay}s {label}")
    for remaining in range(delay, 0, -30):
        time.sleep(min(30, remaining))
        if remaining > 30:
            logger.debug(f"  ... {remaining}s kaldi")
    logger.info("Devam ediliyor.")


def load_caption(caption_file):
    """Caption dosyasini oku."""
    path = POSTS_DIR / caption_file
    if not path.exists():
        logger.error(f"Caption dosyasi bulunamadi: {path}")
        return "", ""

    text = path.read_text(encoding="utf-8").strip()

    # Reel caption dosyalarinda --- sonrasi caption
    if "---" in text:
        parts = text.split("---", 1)
        text = parts[1].strip()

    lines = text.split("\n")
    caption_lines = []
    hashtag_line = ""
    for line in lines:
        if line.strip().startswith("#") and len(line.strip()) > 20:
            hashtag_line = line.strip()
        else:
            if line.strip().startswith("http"):
                continue
            if line.strip().startswith("REEL FILE:") or line.strip().startswith("SOURCE:"):
                continue
            caption_lines.append(line)

    caption = "\n".join(caption_lines).strip()
    return caption, hashtag_line


def load_hashtags(hashtags_file):
    """Hashtag dosyasini oku."""
    if not hashtags_file:
        return ""
    path = POSTS_DIR / hashtags_file
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def try_download_cover(image_name, dest_path):
    """YouTube thumbnail'den album cover indirmeyi dene (fallback)."""
    url = YOUTUBE_THUMBNAIL_MAP.get(image_name)
    if not url or "PLACEHOLDER" in url:
        logger.warning(f"YouTube thumbnail URL tanimlanmamis: {image_name}")
        return False

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cover indiriliyor: {url}")
        urllib.request.urlretrieve(url, str(dest_path))
        logger.info(f"Cover indirildi: {dest_path}")
        return True
    except Exception as e:
        logger.warning(f"Cover indirilemedi: {e}")
        return False


def resolve_image_path(post_info):
    """Resolve image path: local first, then try download."""
    if post_info.get("image_dir") == "covers":
        img_path = COVERS_DIR / post_info["image"]
    else:
        img_path = POSTS_DIR / post_info["image"]

    if img_path.exists():
        return img_path

    # Fallback: try to download from YouTube
    if post_info.get("image_dir") == "covers":
        if try_download_cover(post_info["image"], img_path):
            return img_path

    return None


def resolve_carousel_images(image_list):
    """Resolve carousel image paths."""
    resolved = []
    for img_rel in image_list:
        # Carousel images: check POSTS_DIR then MEDIA_DIR
        img_path = POSTS_DIR / img_rel
        if not img_path.exists():
            img_path = MEDIA_DIR / img_rel
        if not img_path.exists():
            logger.error(f"Carousel gorseli bulunamadi: {img_rel}")
            return None
        resolved.append(img_path)
    return resolved


def login_instagram():
    """Instagram'a giris yap, session kaydet/yukle."""
    from instagrapi import Client

    username = os.environ.get("INSTAGRAM_USERNAME", "sonat.mundi")
    password = os.environ.get("INSTAGRAM_PASSWORD")

    if not password:
        logger.error("INSTAGRAM_PASSWORD ortam degiskeni tanimli degil!")
        sys.exit(1)

    cl = Client()
    cl.set_locale("en_US")
    cl.set_timezone_offset(3 * 3600)  # UTC+3 Turkey

    # Kayitli session varsa yukle
    if SESSION_FILE.exists():
        logger.info(f"Kayitli session yukleniyor: {SESSION_FILE}")
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(username, password)
            cl.get_timeline_feed()
            logger.info("Session gecerli, giris basarili!")
            return cl
        except Exception as e:
            logger.warning(f"Session gecersiz, yeniden giris: {e}")

    # Yeni giris
    logger.info(f"Instagram'a giris yapiliyor (@{username})...")
    cl.login(username, password)

    # Session kaydet
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    cl.dump_settings(SESSION_FILE)
    logger.info(f"Giris basarili! Session kaydedildi: {SESSION_FILE}")
    return cl


def upload_photo(cl, image_path, caption, hashtags):
    """Tekli fotograf paylas + hashtag yorumu."""
    logger.info(f"Foto yukleniyor: {image_path.name}")
    media = cl.photo_upload(str(image_path), caption)
    logger.info(f"Foto paylasild! Media ID: {media.pk}")

    if hashtags:
        time.sleep(COMMENT_DELAY)
        cl.media_comment(media.pk, hashtags)
        logger.info("Hashtag yorumu eklendi.")
    return media


def upload_carousel(cl, image_paths, caption, hashtags):
    """Carousel paylas + hashtag yorumu."""
    paths = [str(p) for p in image_paths]
    logger.info(f"Carousel yukleniyor: {len(paths)} gorsel")
    media = cl.album_upload(paths, caption)
    logger.info(f"Carousel paylasild! Media ID: {media.pk}")

    if hashtags:
        time.sleep(COMMENT_DELAY)
        cl.media_comment(media.pk, hashtags)
        logger.info("Hashtag yorumu eklendi.")
    return media


def upload_reel(cl, video_path, caption, hashtags):
    """Reel paylas + hashtag yorumu."""
    logger.info(f"Reel yukleniyor: {video_path.name}")
    media = cl.clip_upload(str(video_path), caption)
    logger.info(f"Reel paylasild! Media ID: {media.pk}")

    if hashtags:
        time.sleep(COMMENT_DELAY)
        cl.media_comment(media.pk, hashtags)
        logger.info("Hashtag yorumu eklendi.")
    return media


def process_day(cl, day_plan, posts_only=False, reels_only=False, dry_run=False):
    """Bir gunun post + reel planini uygula."""
    day = day_plan["day"]
    logger.info(f"{'='*50}")
    logger.info(f"  GUN {day}")
    logger.info(f"{'='*50}")
    count = 0
    results = []

    # POST
    if day_plan["post"] and not reels_only:
        post = day_plan["post"]
        caption, inline_hashtags = load_caption(post["caption_file"])
        hashtags = load_hashtags(post.get("hashtags_file", "")) or inline_hashtags

        if post["type"] == "carousel":
            images = resolve_carousel_images(post["images"])
            if images is None:
                logger.error(f"Gun {day}: Carousel gorselleri eksik, atlaniyor.")
                results.append(f"Gun {day} POST: ATLANDI (eksik gorseller)")
            elif dry_run:
                logger.info(f"[DRY-RUN] Carousel yuklenecek: {len(images)} gorsel")
                logger.info(f"[DRY-RUN] Caption: {caption[:100]}...")
                results.append(f"Gun {day} POST: DRY-RUN carousel ({len(images)} gorsel)")
                count += 1
            else:
                upload_carousel(cl, images, caption, hashtags)
                results.append(f"Gun {day} POST: Carousel paylasild ({len(images)} gorsel)")
                count += 1

        elif post["type"] == "photo":
            img_path = resolve_image_path(post)
            if img_path is None:
                logger.error(f"Gun {day}: Gorsel bulunamadi, atlaniyor.")
                results.append(f"Gun {day} POST: ATLANDI (gorsel bulunamadi)")
            elif dry_run:
                logger.info(f"[DRY-RUN] Foto yuklenecek: {img_path.name}")
                logger.info(f"[DRY-RUN] Caption: {caption[:100]}...")
                results.append(f"Gun {day} POST: DRY-RUN foto ({img_path.name})")
                count += 1
            else:
                upload_photo(cl, img_path, caption, hashtags)
                results.append(f"Gun {day} POST: Foto paylasild ({img_path.name})")
                count += 1

        if day_plan["reel"] and not posts_only and not dry_run:
            safe_delay("(Post -> Reel arasi)")

    # REEL
    if day_plan["reel"] and not posts_only:
        reel = day_plan["reel"]
        caption, inline_hashtags = load_caption(reel["caption_file"])

        video_path = SHORTS_DIR / reel["video"]
        if not video_path.exists():
            logger.warning(f"Gun {day}: Video bulunamadi: {video_path} — Reel atlaniyor.")
            results.append(f"Gun {day} REEL: ATLANDI (video bulunamadi: {reel['video']})")
        elif dry_run:
            logger.info(f"[DRY-RUN] Reel yuklenecek: {video_path.name}")
            logger.info(f"[DRY-RUN] Caption: {caption[:100]}...")
            results.append(f"Gun {day} REEL: DRY-RUN ({video_path.name})")
            count += 1
        else:
            upload_reel(cl, video_path, caption, inline_hashtags)
            results.append(f"Gun {day} REEL: Paylasild ({video_path.name})")
            count += 1

    return count, results


def show_plan():
    """Tum plani goster."""
    logger.info("=" * 60)
    logger.info("  SONAT MUNDI — 9 GUNLUK INSTAGRAM LANSMAN PLANI")
    logger.info("=" * 60)
    for dp in PLAN:
        day = dp["day"]
        post_desc = "—"
        reel_desc = "—"
        if dp["post"]:
            if dp["post"]["type"] == "carousel":
                n = len(dp["post"]["images"])
                post_desc = f"Carousel ({n} slide)"
            else:
                post_desc = dp["post"]["image"]
        if dp["reel"]:
            reel_desc = dp["reel"]["video"]
        logger.info(f"  Gun {day}: POST={post_desc}  |  REEL={reel_desc}")
    logger.info("=" * 60)


def send_notification_email(results, success=True):
    """GitHub Actions tamamlandiginda email bildirimi gonder."""
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        logger.info("Email ayarlari tanimli degil, bildirim atlanıyor.")
        return

    import smtplib
    from email.mime.text import MIMEText

    status = "BASARILI" if success else "HATALI"
    body = f"Instagram Publisher Sonucu: {status}\n\n"
    body += f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    body += "Detaylar:\n"
    for r in results:
        body += f"  - {r}\n"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Sonat Mundi Instagram: {status}"
    msg["From"] = gmail_address
    msg["To"] = gmail_address

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        logger.info("Email bildirimi gonderildi.")
    except Exception as e:
        logger.warning(f"Email gonderilemedi: {e}")


def parse_args():
    """Argumanlari parse et (CLI + env var destegi)."""
    parser = argparse.ArgumentParser(description="Sonat Mundi Instagram Publisher")
    parser.add_argument("--day", type=str, default=os.environ.get("PUBLISH_DAY"),
                        help="Gun numarasi (1-9) veya 'all'")
    parser.add_argument("--posts-only", action="store_true",
                        default=os.environ.get("PUBLISH_MODE") == "posts-only",
                        help="Sadece post paylas")
    parser.add_argument("--reels-only", action="store_true",
                        default=os.environ.get("PUBLISH_MODE") == "reels-only",
                        help="Sadece reel paylas")
    parser.add_argument("--dry-run", action="store_true",
                        default=os.environ.get("DRY_RUN", "false").lower() == "true",
                        help="Gercek yukleme yapma, sadece ne yapilacagini goster")
    parser.add_argument("--show-plan", action="store_true",
                        help="Tum plani goster ve cik")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.show_plan or args.day is None:
        show_plan()
        return

    logger.info(f"Instagram Publisher baslatiliyor...")
    logger.info(f"  Day: {args.day}")
    logger.info(f"  Mode: {'posts-only' if args.posts_only else 'reels-only' if args.reels_only else 'both'}")
    logger.info(f"  Dry-run: {args.dry_run}")
    logger.info(f"  Posts dir: {POSTS_DIR}")
    logger.info(f"  Media dir: {MEDIA_DIR}")
    logger.info(f"  Session: {SESSION_FILE}")

    # Instagram'a giris (dry-run'da gerekmez)
    cl = None
    if not args.dry_run:
        cl = login_instagram()

    # Hangi gunler?
    if args.day == "all":
        days_to_process = PLAN
    else:
        try:
            day_num = int(args.day)
        except ValueError:
            logger.error(f"Gecersiz gun: {args.day}")
            sys.exit(1)
        days_to_process = [d for d in PLAN if d["day"] == day_num]
        if not days_to_process:
            logger.error(f"Gun {day_num} bulunamadi!")
            sys.exit(1)

    total_uploaded = 0
    all_results = []

    for i, day_plan in enumerate(days_to_process):
        count, results = process_day(cl, day_plan, args.posts_only, args.reels_only, args.dry_run)
        total_uploaded += count
        all_results.extend(results)

        # Gunluk limit kontrolu
        if total_uploaded >= DAILY_LIMIT:
            logger.warning(f"Gunluk limit ({DAILY_LIMIT}) doldu!")
            break

        # Sonraki gune gecmeden once uzun bekleme
        if i < len(days_to_process) - 1 and not args.dry_run:
            wait = random.randint(600, 900)
            logger.info(f"Sonraki gune gecmeden once {wait // 60} dakika bekleniyor...")
            time.sleep(wait)

    # Ozet
    logger.info("=" * 50)
    logger.info(f"TAMAMLANDI! Toplam {total_uploaded} icerik islendi.")
    for r in all_results:
        logger.info(f"  {r}")
    logger.info("=" * 50)

    # Session kaydet
    if cl and not args.dry_run:
        cl.dump_settings(SESSION_FILE)
        logger.info("Session kaydedildi.")

    # Email bildirim
    send_notification_email(all_results, success=True)

    # GitHub Actions output
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"total_uploaded={total_uploaded}\n")
            f.write(f"summary={'|'.join(all_results)}\n")


if __name__ == "__main__":
    main()
