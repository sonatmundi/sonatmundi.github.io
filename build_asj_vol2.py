#!/usr/bin/env python3
"""
Build Ancient_Soul_Journey_Vol2.mp4
  - 15 static JPEG covers  +  15 MP3 audio tracks
  - 1920×1080, CRF 28, libx264 / aac 256k
  - 2-second video crossfade (xfade=fade) between each image pair
  - 3-second audio crossfade (acrossfade d=3 c1=tri c2=tri) between each audio pair
  - Chapter markers embedded in the MP4 container
"""

import subprocess
import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE   = r"D:\Yedekler\UCS\Sounds\Ancient Soul Journey Vol.2 Echoes of Ancient Civilizations"
COVERS = os.path.join(BASE, "covers")
OUTPUT = os.path.join(BASE, "Ancient_Soul_Journey_Vol2.mp4")
META   = os.path.join(BASE, "asj_vol2_chapters.txt")

NAMES = [
    "1. Gobekli Tepe \u2014 First Temple",
    "2. Sumerian Dream \u2014 Mesopotamia",
    "3. Silk Road Dusk \u2014 Central Asia",
    "4. Zoroastrian Fire \u2014 Persia",
    "5. Scythian Wind \u2014 Eurasian Steppes",
    "6. Lydian Gold \u2014 Ancient Anatolia",
    "7. Urartu \u2014 Mountain Kingdom",
    "8. Phoenician Sea \u2014 Mediterranean",
    "9. Druid Circle \u2014 Celtic Lands",
    "10. Norse Void \u2014 Scandinavia",
    "11. Vedic Dawn \u2014 Ancient India",
    "12. Shamanic Journey \u2014 Siberia",
    "13. Hellenistic Dusk \u2014 Ancient Greece",
    "14. Egyptian Temple \u2014 Nile Valley",
    "15. The Eternal Return \u2014 All Civilizations",
]

TITLES = [n.split(". ", 1)[1] for n in NAMES]

# Track durations in seconds (measured from MP3 files)
DURATIONS = [309, 253, 277, 259, 319, 286, 304, 292, 251, 227, 423, 259, 292, 315, 270]

# Chapter start timestamps as provided (converted to seconds)
CHAPTER_STARTS = [
       0,   # Gobekli Tepe — First Temple        00:00
     309,   # Sumerian Dream — Mesopotamia       05:09
     562,   # Silk Road Dusk — Central Asia      09:22
     839,   # Zoroastrian Fire — Persia          13:59
    1098,   # Scythian Wind — Eurasian Steppes   18:18
    1417,   # Lydian Gold — Ancient Anatolia     23:37
    1703,   # Urartu — Mountain Kingdom          28:23
    2007,   # Phoenician Sea — Mediterranean     33:27
    2299,   # Druid Circle — Celtic Lands        38:19
    2550,   # Norse Void — Scandinavia           42:30
    2777,   # Vedic Dawn — Ancient India         46:17
    3200,   # Shamanic Journey — Siberia         53:20
    3459,   # Hellenistic Dusk — Ancient Greece  57:39
    3751,   # Egyptian Temple — Nile Valley    1:02:31
    4066,   # The Eternal Return              1:07:46
]

VF = 2    # video crossfade seconds
AF = 3    # audio crossfade seconds
N  = len(NAMES)

video_total = sum(DURATIONS) - (N - 1) * VF   # 4308 s
audio_total = sum(DURATIONS) - (N - 1) * AF   # 4294 s

# ── 1. Write FFmpeg chapters metadata file ────────────────────────────────────
with open(META, "w", encoding="utf-8") as f:
    f.write(";FFMETADATA1\n\n")
    for i in range(N):
        start_ms = CHAPTER_STARTS[i] * 1000
        end_ms   = (CHAPTER_STARTS[i + 1] * 1000) if i < N - 1 else (video_total * 1000)
        f.write(
            f"[CHAPTER]\n"
            f"TIMEBASE=1/1000\n"
            f"START={start_ms}\n"
            f"END={end_ms}\n"
            f"title={TITLES[i]}\n\n"
        )
print(f"Chapters metadata written: {META}")

# ── 2. Build FFmpeg inputs ────────────────────────────────────────────────────
cmd = ["ffmpeg", "-y"]

# Image inputs: indices 0 … N-1
for i in range(N):
    cmd += [
        "-loop", "1",
        "-t", str(DURATIONS[i]),
        "-i", os.path.join(COVERS, f"{NAMES[i]}.jpeg"),
    ]

# Audio inputs: indices N … 2N-1
for i in range(N):
    cmd += ["-i", os.path.join(BASE, f"{NAMES[i]}.mp3")]

# Metadata input: index 2N (= 30)
cmd += ["-i", META]

# ── 3. Build filter_complex ───────────────────────────────────────────────────
fc = []

# Scale / pad each image to 1920×1080, 25 fps
for i in range(N):
    fc.append(
        f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25[v{i}]"
    )

# Video xfade chain
# offset[i] = CHAPTER_STARTS[i+1] - (i+1)*VF
for i in range(N - 1):
    offset = CHAPTER_STARTS[i + 1] - (i + 1) * VF
    ina    = "[v0]"       if i == 0     else f"[vx{i - 1}]"
    inb    = f"[v{i + 1}]"
    out    = "[vfinal]"   if i == N - 2 else f"[vx{i}]"
    fc.append(
        f"{ina}{inb}xfade=transition=fade:duration={VF}:offset={offset}{out}"
    )

# Audio acrossfade chain
for i in range(N - 1):
    ina  = f"[{N}:a]"          if i == 0     else f"[ax{i - 1}]"
    inb  = f"[{N + i + 1}:a]"
    out  = "[ax_pre]"           if i == N - 2 else f"[ax{i}]"
    fc.append(
        f"{ina}{inb}acrossfade=d={AF}:c1=tri:c2=tri{out}"
    )

# Pad audio tail to match video total
fc.append(f"[ax_pre]apad=whole_dur={video_total}[afinal]")

fc_str = "; ".join(fc)

# ── 4. Assemble final command ─────────────────────────────────────────────────
meta_idx = 2 * N   # = 30

cmd += [
    "-filter_complex", fc_str,
    "-map", "[vfinal]",
    "-map", "[afinal]",
    "-map_metadata", str(meta_idx),
    "-map_chapters",  str(meta_idx),
    "-c:v", "libx264",
    "-crf", "28",
    "-preset", "slow",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "256k",
    "-movflags", "+faststart",
    OUTPUT,
]

# ── 5. Run ────────────────────────────────────────────────────────────────────
print(f"\nOutput      : {OUTPUT}")
print(f"Video total : {video_total // 60}m {video_total % 60}s  ({video_total}s)")
print(f"Audio total : {audio_total // 60}m {audio_total % 60}s  ({audio_total}s)  (padded to video length)")
print(f"Inputs      : {N} images + {N} audio + 1 metadata = {2*N+1} total")
print(f"Chapters    : {N}")
print()
print("Starting FFmpeg ...\n")

result = subprocess.run(cmd)
if result.returncode != 0:
    print("\nFFmpeg failed!", file=sys.stderr)
    sys.exit(1)

print(f"\nDone: {OUTPUT}")
