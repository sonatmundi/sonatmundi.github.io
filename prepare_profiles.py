"""Prepare profile images for all platforms."""
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import os

OUT = "D:/Yedekler/UCS/profile_images"
os.makedirs(OUT, exist_ok=True)

# ── 1. SUNO — Personal photo (square, 800x800) ─────────────────────────────
print("=== SUNO — Kişisel Profil ===")
img = Image.open("D:/Yedekler/UCS/profil resmim.jpg").convert("RGB")

# Upscale and make square
size = max(img.size)
square = Image.new("RGB", (size, size), (20, 20, 30))
x = (size - img.width) // 2
y = (size - img.height) // 2
square.paste(img, (x, y))
suno = square.resize((800, 800), Image.LANCZOS)
suno.save(f"{OUT}/suno_profile_800x800.jpg", "JPEG", quality=95)
print(f"  Saved: suno_profile_800x800.jpg (800x800)")

# ── 2. SONAT MUNDI LOGO — Square versions for platforms ─────────────────────
print("\n=== SONAT MUNDI LOGO — Platform Profilleri ===")
logo = Image.open("D:/Yedekler/UCS/Sounds/Sounds of Sleep Vol.1 Deep Sleep/sonat_mundi-logo_png.png").convert("RGBA")

# The logo is 2048x1152 (16:9). We need to make it square.
# Center crop to square, focusing on the logo center
w, h = logo.size
crop_size = min(w, h)
left = (w - crop_size) // 2
top = (h - crop_size) // 2
logo_square = logo.crop((left, top, left + crop_size, top + crop_size))

# YouTube Channel Profile (800x800)
yt = logo_square.resize((800, 800), Image.LANCZOS).convert("RGB")
yt.save(f"{OUT}/youtube_profile_800x800.jpg", "JPEG", quality=95)
print(f"  Saved: youtube_profile_800x800.jpg (800x800)")

# Spotify / Apple Music / DistroKid (3000x3000 — highest quality)
sp = logo_square.resize((3000, 3000), Image.LANCZOS).convert("RGB")
sp.save(f"{OUT}/spotify_profile_3000x3000.jpg", "JPEG", quality=95)
print(f"  Saved: spotify_profile_3000x3000.jpg (3000x3000)")

# Bandcamp (800x800)
bc = logo_square.resize((800, 800), Image.LANCZOS).convert("RGB")
bc.save(f"{OUT}/bandcamp_profile_800x800.jpg", "JPEG", quality=95)
print(f"  Saved: bandcamp_profile_800x800.jpg (800x800)")

# Gumroad (square 500x500)
gm = logo_square.resize((500, 500), Image.LANCZOS).convert("RGB")
gm.save(f"{OUT}/gumroad_profile_500x500.jpg", "JPEG", quality=95)
print(f"  Saved: gumroad_profile_500x500.jpg (500x500)")

# PNG version (transparent background preserved)
logo_sq_png = logo_square.resize((1024, 1024), Image.LANCZOS)
logo_sq_png.save(f"{OUT}/sonat_mundi_square_1024x1024.png", "PNG")
print(f"  Saved: sonat_mundi_square_1024x1024.png (1024x1024, transparent)")

# ── 3. BANNER images ────────────────────────────────────────────────────────
print("\n=== BANNER Görselleri ===")

# YouTube Banner (2560x1440)
banner = Image.open("D:/Yedekler/UCS/Sounds/Sounds of Sleep Vol.1 Deep Sleep/sonat_mundi-logo_png.png").convert("RGB")
# Scale to fit 2560 wide
scale = 2560 / banner.width
new_h = int(banner.height * scale)
banner_scaled = banner.resize((2560, new_h), Image.LANCZOS)

# Place on 2560x1440 dark canvas, centered
yt_banner = Image.new("RGB", (2560, 1440), (8, 8, 15))
y_offset = (1440 - new_h) // 2
yt_banner.paste(banner_scaled, (0, y_offset))
yt_banner.save(f"{OUT}/youtube_banner_2560x1440.jpg", "JPEG", quality=95)
print(f"  Saved: youtube_banner_2560x1440.jpg (2560x1440)")

# Spotify Header (2660x1140)
sp_banner = Image.new("RGB", (2660, 1140), (8, 8, 15))
scale2 = 2660 / banner.width
new_h2 = int(banner.height * scale2)
banner_scaled2 = banner.resize((2660, new_h2), Image.LANCZOS)
y_offset2 = (1140 - new_h2) // 2
sp_banner.paste(banner_scaled2, (0, y_offset2))
sp_banner.save(f"{OUT}/spotify_banner_2660x1140.jpg", "JPEG", quality=95)
print(f"  Saved: spotify_banner_2660x1140.jpg (2660x1140)")

print(f"\nTüm görseller hazır: {OUT}/")
