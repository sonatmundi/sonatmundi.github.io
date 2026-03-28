"""
Sonat Mundi — Instagram Auto Publisher
Güvenli, yavaş, session-kayıtlı Instagram yükleme scripti.

Kullanım:
  python upload_instagram.py              → Tüm planı göster
  python upload_instagram.py --day 1      → Sadece Gün 1 paylaş
  python upload_instagram.py --day all    → Tüm günleri sırayla paylaş (arayla)
  python upload_instagram.py --reels-only → Sadece Reel'leri paylaş
  python upload_instagram.py --posts-only → Sadece Post'ları paylaş
"""

import os
import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime

# ── AYARLAR ──
INSTAGRAM_USERNAME = "sonat.mundi"
SESSION_FILE = Path(r"D:\Yedekler\UCS\instagram\ig_session.json")
BASE_DIR = Path(r"D:\Yedekler\UCS\instagram\posts")
SHORTS_DIR = Path(r"D:\Yedekler\UCS\Sounds\Shorts")
COVERS_DIR = Path(r"D:\Yedekler\UCS\album_covers_3000")

# Güvenlik ayarları
MIN_DELAY = 180   # Post arası minimum bekleme (saniye) = 3 dakika
MAX_DELAY = 300   # Post arası maximum bekleme (saniye) = 5 dakika
DAILY_LIMIT = 5   # Günlük max paylaşım
COMMENT_DELAY = 30 # Post sonrası hashtag yorumu için bekleme

# ── 9 GÜNLÜK PLAN ──
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
        "post": None,  # Gün 9 sadece Reel
        "reel": {
            "video": "short_velvet_silence.mp4",
            "caption_file": "post_09/reel_caption.txt",
        },
    },
]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")


def safe_delay(label=""):
    delay = random.randint(MIN_DELAY, MAX_DELAY)
    log(f"Guvenlik beklemesi: {delay} saniye... {label}")
    for remaining in range(delay, 0, -30):
        time.sleep(min(30, remaining))
        if remaining > 30:
            print(f"    ... {remaining}s kaldi")
    log("Devam ediliyor.")


def load_caption(caption_file):
    """Caption dosyasını oku, reel dosyalarından sadece caption kısmını al."""
    path = BASE_DIR / caption_file
    text = path.read_text(encoding="utf-8").strip()

    # Reel caption dosyalarında ilk bölüm meta bilgi, --- sonrası caption
    if "---" in text:
        parts = text.split("---", 1)
        text = parts[1].strip()

    # Hashtag satırlarını caption'dan ayır (ilk yorum olarak atılacak)
    lines = text.split("\n")
    caption_lines = []
    hashtag_line = ""
    for line in lines:
        if line.strip().startswith("#") and len(line.strip()) > 20:
            hashtag_line = line.strip()
        else:
            # YouTube URL satırlarını kaldır (Instagram'da tıklanamaz)
            if line.strip().startswith("http"):
                continue
            # "REEL FILE:" ve "SOURCE:" satırlarını kaldır
            if line.strip().startswith("REEL FILE:") or line.strip().startswith("SOURCE:"):
                continue
            caption_lines.append(line)

    caption = "\n".join(caption_lines).strip()
    return caption, hashtag_line


def load_hashtags(hashtags_file):
    path = BASE_DIR / hashtags_file
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def login(password):
    """Instagram'a giriş yap, session kaydet."""
    from instagrapi import Client

    cl = Client()

    # Cihaz ayarları (gerçek cihaz gibi görünsün)
    cl.set_locale("en_US")
    cl.set_timezone_offset(3 * 3600)  # UTC+3 Turkey

    # Kayıtlı session varsa kullan
    if SESSION_FILE.exists():
        log("Kayitli session bulundu, yukleniyor...")
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(INSTAGRAM_USERNAME, password)
            cl.get_timeline_feed()  # Session geçerli mi test et
            log("Session gecerli, giris basarili!")
            return cl
        except Exception as e:
            log(f"Session gecersiz, yeniden giris yapiliyor... ({e})")

    # Yeni giriş
    log("Instagram'a giris yapiliyor...")
    cl.login(INSTAGRAM_USERNAME, password)
    cl.dump_settings(SESSION_FILE)
    log("Giris basarili! Session kaydedildi.")
    return cl


def upload_photo(cl, image_path, caption, hashtags):
    """Tekli fotoğraf paylaş + hashtag yorumu."""
    log(f"Foto yukleniyor: {image_path.name}")
    media = cl.photo_upload(str(image_path), caption)
    log(f"Foto paylasild! Media ID: {media.pk}")

    if hashtags:
        time.sleep(COMMENT_DELAY)
        cl.media_comment(media.pk, hashtags)
        log("Hashtag yorumu eklendi.")

    return media


def upload_carousel(cl, image_paths, caption, hashtags):
    """Carousel (birden fazla görsel) paylaş + hashtag yorumu."""
    paths = [str(p) for p in image_paths]
    log(f"Carousel yukleniyor: {len(paths)} gorsel")
    media = cl.album_upload(paths, caption)
    log(f"Carousel paylasild! Media ID: {media.pk}")

    if hashtags:
        time.sleep(COMMENT_DELAY)
        cl.media_comment(media.pk, hashtags)
        log("Hashtag yorumu eklendi.")

    return media


def upload_reel(cl, video_path, caption, hashtags):
    """Reel (video) paylaş + hashtag yorumu."""
    log(f"Reel yukleniyor: {video_path.name}")
    media = cl.clip_upload(str(video_path), caption)
    log(f"Reel paylasild! Media ID: {media.pk}")

    if hashtags:
        time.sleep(COMMENT_DELAY)
        cl.media_comment(media.pk, hashtags)
        log("Hashtag yorumu eklendi.")

    return media


def process_day(cl, day_plan, posts_only=False, reels_only=False):
    """Bir günün post + reel planını uygula."""
    day = day_plan["day"]
    print(f"\n{'='*50}")
    print(f"  GUN {day}")
    print(f"{'='*50}")
    count = 0

    # POST
    if day_plan["post"] and not reels_only:
        post = day_plan["post"]
        caption, inline_hashtags = load_caption(post["caption_file"])
        hashtags = load_hashtags(post.get("hashtags_file", "")) or inline_hashtags

        if post["type"] == "carousel":
            images = [BASE_DIR / img for img in post["images"]]
            # Dosya kontrolü
            missing = [p for p in images if not p.exists()]
            if missing:
                log(f"HATA: Eksik dosyalar: {missing}")
                return count
            upload_carousel(cl, images, caption, hashtags)
        elif post["type"] == "photo":
            if post.get("image_dir") == "covers":
                img_path = COVERS_DIR / post["image"]
            else:
                img_path = BASE_DIR / post["image"]
            if not img_path.exists():
                log(f"HATA: Dosya bulunamadi: {img_path}")
                return count
            upload_photo(cl, img_path, caption, hashtags)

        count += 1

        if day_plan["reel"] and not posts_only:
            safe_delay("(Post → Reel arasi)")

    # REEL
    if day_plan["reel"] and not posts_only:
        reel = day_plan["reel"]
        caption, inline_hashtags = load_caption(reel["caption_file"])

        video_path = SHORTS_DIR / reel["video"]
        if not video_path.exists():
            log(f"HATA: Video bulunamadi: {video_path}")
            return count

        upload_reel(cl, video_path, caption, inline_hashtags)
        count += 1

    return count


def show_plan():
    """Tüm planı göster."""
    print("\n" + "=" * 60)
    print("  SONAT MUNDI — 9 GUNLUK INSTAGRAM LANSMAN PLANI")
    print("=" * 60)
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
        print(f"  Gun {day}: POST={post_desc}  |  REEL={reel_desc}")
    print("=" * 60)
    print(f"\nKullanim:")
    print(f"  python upload_instagram.py --day 1       → Gun 1 paylas")
    print(f"  python upload_instagram.py --day all     → Tum gunler (arayla)")
    print(f"  python upload_instagram.py --posts-only  → Sadece post'lar")
    print(f"  python upload_instagram.py --reels-only  → Sadece reel'ler")
    print()


def main():
    args = sys.argv[1:]

    if not args:
        show_plan()
        return

    # Argümanları parse et
    target_day = None
    posts_only = "--posts-only" in args
    reels_only = "--reels-only" in args

    for i, a in enumerate(args):
        if a == "--day" and i + 1 < len(args):
            target_day = args[i + 1]

    if target_day is None and not posts_only and not reels_only:
        show_plan()
        return

    # Şifre iste
    import getpass
    password = getpass.getpass(f"Instagram sifresi (@{INSTAGRAM_USERNAME}): ")

    # Giriş yap
    cl = login(password)

    # Hangi günler?
    if target_day == "all":
        days_to_process = PLAN
    elif target_day:
        day_num = int(target_day)
        days_to_process = [d for d in PLAN if d["day"] == day_num]
        if not days_to_process:
            print(f"HATA: Gun {day_num} bulunamadi!")
            return
    else:
        days_to_process = PLAN

    total_uploaded = 0

    for i, day_plan in enumerate(days_to_process):
        count = process_day(cl, day_plan, posts_only, reels_only)
        total_uploaded += count

        # Günlük limit kontrolü
        if total_uploaded >= DAILY_LIMIT:
            log(f"Gunluk limit ({DAILY_LIMIT}) doldu! Yarin devam edin.")
            log(f"Komut: python upload_instagram.py --day {day_plan['day'] + 1}")
            break

        # Sonraki güne geçmeden önce uzun bekleme
        if i < len(days_to_process) - 1:
            wait = random.randint(600, 900)  # 10-15 dakika
            log(f"Sonraki gune gecmeden once {wait // 60} dakika bekleniyor...")
            time.sleep(wait)

    print(f"\n{'='*50}")
    print(f"  TAMAMLANDI! Toplam {total_uploaded} icerik paylasild.")
    print(f"{'='*50}\n")

    # Session güncelle
    cl.dump_settings(SESSION_FILE)
    log("Session kaydedildi.")


if __name__ == "__main__":
    main()
