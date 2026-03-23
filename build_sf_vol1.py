#!/usr/bin/env python3
"""
Build Sacred_Frequencies_Vol1.mp4
  - 15 static JPEG covers  +  15 MP3 audio tracks
  - 1920×1080, CRF 28, libx264 / aac 192k
  - 2-second video crossfade (xfade=fade) between each image pair
  - 3-second audio crossfade (acrossfade d=3) between each audio pair
  - Chapter markers embedded in the MP4 container
"""

import subprocess
import os
import sys

# Force UTF-8 output on Windows terminals with non-Unicode codepages
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE   = r"D:\Yedekler\UCS\Sounds of Frequencies Vol.1 Sacred Frequencies"
COVERS = os.path.join(BASE, "covers")
OUTPUT = os.path.join(BASE, "Sacred_Frequencies_Vol1.mp4")
META   = os.path.join(BASE, "sf_chapters.txt")

NAMES = [
    "1. Foundation \u2014 174 Hz",
    "2. Cellular Repair \u2014 285 Hz",
    "3. Liberation \u2014 396 Hz",
    "4. Transformation \u2014 417 Hz",
    "5. The Love Frequency \u2014 528 Hz",
    "6. Connection \u2014 639 Hz",
    "7. Expression \u2014 741 Hz",
    "8. Return \u2014 852 Hz",
    "9. Divine \u2014 963 Hz",
    "10. Earth Resonance \u2014 432 Hz",
    "11. Binaural Delta \u2014 2 Hz",
    "12. Binaural Theta \u2014 6 Hz",
    "13. Binaural Alpha \u2014 10 Hz",
    "14. Binaural Gamma \u2014 40 Hz",
    "15. The Complete Spectrum \u2014 All Frequencies",
]

TITLES = [n.split(". ", 1)[1] for n in NAMES]

# Track durations in seconds (verified against user-provided chapter timestamps)
DURATIONS = [312, 358, 354, 479, 343, 329, 306, 361, 479, 423, 398, 294, 354, 335, 479]

# Chapter start timestamps as provided by user (converted to seconds)
CHAPTER_STARTS = [
      0,   # Foundation — 174 Hz       00:00
    312,   # Cellular Repair — 285 Hz  05:12
    670,   # Liberation — 396 Hz       11:10
   1024,   # Transformation — 417 Hz   17:04
   1503,   # The Love Frequency        25:03
   1846,   # Connection                30:46
   2175,   # Expression                36:15
   2481,   # Return                    41:21
   2842,   # Divine                    47:22
   3321,   # Earth Resonance           55:21
   3744,   # Binaural Delta          1:02:24
   4142,   # Binaural Theta          1:09:02
   4436,   # Binaural Alpha          1:13:56
   4790,   # Binaural Gamma          1:19:50
   5125,   # The Complete Spectrum   1:25:25
]

VF = 2    # video crossfade seconds
AF = 3    # audio crossfade seconds
N  = len(NAMES)

video_total = sum(DURATIONS) - (N - 1) * VF   # 5576 s
audio_total = sum(DURATIONS) - (N - 1) * AF   # 5562 s

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
# Duration = exact track duration; static image loop provides enough frames.
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

# --- Scale / pad each image to 1920×1080, 25 fps ---
for i in range(N):
    fc.append(
        f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25[v{i}]"
    )

# --- Video xfade chain ---
# offset[i] = CHAPTER_STARTS[i+1] - (i+1)*VF
# This places the crossfade exactly at the end of each image's display time.
for i in range(N - 1):
    offset = CHAPTER_STARTS[i + 1] - (i + 1) * VF
    ina    = "[v0]"        if i == 0     else f"[vx{i - 1}]"
    inb    = f"[v{i + 1}]"
    out    = "[vfinal]"    if i == N - 2 else f"[vx{i}]"
    fc.append(
        f"{ina}{inb}xfade=transition=fade:duration={VF}:offset={offset}{out}"
    )

# --- Audio acrossfade chain ---
for i in range(N - 1):
    ina  = f"[{N}:a]"         if i == 0     else f"[ax{i - 1}]"
    inb  = f"[{N + i + 1}:a]"
    out  = "[ax_pre]"          if i == N - 2 else f"[ax{i}]"
    fc.append(
        f"{ina}{inb}acrossfade=d={AF}:c1=tri:c2=tri{out}"
    )

# Pad audio tail to match video total (video is 14 s longer due to VF vs AF)
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
    "-b:a", "192k",
    "-movflags", "+faststart",
    OUTPUT,
]

# ── 5. Run ────────────────────────────────────────────────────────────────────
print(f"\nOutput      : {OUTPUT}")
print(f"Video total : {video_total // 60}m {video_total % 60}s")
print(f"Audio total : {audio_total // 60}m {audio_total % 60}s  (padded to video length)")
print(f"Inputs      : {N} images + {N} audio + 1 metadata = {2*N+1} total\n")
print("Starting FFmpeg ...\n")

result = subprocess.run(cmd)
if result.returncode != 0:
    print("\nFFmpeg failed!", file=sys.stderr)
    sys.exit(1)

print(f"\nDone: {OUTPUT}")
