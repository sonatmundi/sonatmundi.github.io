#!/usr/bin/env python3
"""Build Sounds of Moods Vol.1 video with FFmpeg."""
import subprocess
import os

BASE = r"D:\Yedekler\UCS\Sounds of Moods Vol. 1 The Human Spectrum"
COVERS = BASE + r"\covers"
OUTPUT = BASE + r"\Sounds_of_Moods_Vol1.mp4"
META = r"D:\Yedekler\UCS\ffchapters_moods_vol1.txt"

CHAPTER_NAMES = [
    "First Light", "Quiet Storm", "Floating", "Nostalgia", "Euphoria",
    "Solitude", "Longing", "Wonder", "Surrender", "Rage",
    "Tenderness", "Courage", "Grief", "Ecstasy", "Stillness",
]

# Chapter start times in seconds (user-defined, used for metadata)
CHAPTER_STARTS = [0, 309, 609, 896, 1099, 1317, 1631, 1987, 2301, 2650,
                  2842, 3098, 3404, 3735, 3992]
TOTAL_S = 4356  # last chapter start + last track duration (6:04)

N = len(CHAPTER_NAMES)
XFADE = 2      # seconds, video crossfade
ACFADE = 3     # seconds, audio crossfade

# ── Image loop durations (chapter gaps; last image gets +30s buffer) ─────────
img_dur = []
for i in range(N):
    if i < N - 1:
        img_dur.append(CHAPTER_STARTS[i + 1] - CHAPTER_STARTS[i])
    else:
        img_dur.append(TOTAL_S - CHAPTER_STARTS[-1] + 30)  # buffer + -shortest

# ── Write FFMETADATA ──────────────────────────────────────────────────────────
with open(META, "w", encoding="utf-8") as f:
    f.write(";FFMETADATA1\n\n")
    for i in range(N):
        s = CHAPTER_STARTS[i] * 1000
        e = (CHAPTER_STARTS[i + 1] if i < N - 1 else TOTAL_S) * 1000
        f.write("[CHAPTER]\n")
        f.write("TIMEBASE=1/1000\n")
        f.write(f"START={s}\n")
        f.write(f"END={e}\n")
        f.write(f"title={CHAPTER_NAMES[i]}\n\n")
print(f"FFMETADATA written -> {META}")

# ── Build inputs ──────────────────────────────────────────────────────────────
img_inputs = []
for i in range(N):
    path = os.path.join(COVERS, f"{i+1}. {CHAPTER_NAMES[i]}.jpeg")
    img_inputs += ["-loop", "1", "-t", str(img_dur[i]), "-i", path]

aud_inputs = []
for i in range(N):
    path = os.path.join(BASE, f"{i+1}. {CHAPTER_NAMES[i]}.mp3")
    aud_inputs += ["-i", path]

meta_idx = N * 2  # metadata is the (N*2)th input (0-indexed)

# ── Calculate xfade offsets ───────────────────────────────────────────────────
# offset[k] = cumulative img duration up to k - (k+1)*XFADE
# (each xfade compresses the timeline by XFADE seconds)
cumsum = 0
xfade_offsets = []
for i in range(N - 1):
    cumsum += img_dur[i]
    xfade_offsets.append(cumsum - (i + 1) * XFADE)

# ── Build filter_complex ──────────────────────────────────────────────────────
parts = []

# Scale each image to 1920x1080, letterbox, 25 fps
for i in range(N):
    parts.append(
        f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25[v{i}]"
    )

# xfade chain
prev_v = "v0"
for i in range(N - 1):
    out = f"vx{i}"
    parts.append(
        f"[{prev_v}][v{i+1}]xfade=transition=fade"
        f":duration={XFADE}:offset={xfade_offsets[i]}[{out}]"
    )
    prev_v = out
vfinal = prev_v  # e.g. vx13

# acrossfade chain (audio inputs start at index N)
prev_a = f"{N}:a"
for i in range(1, N):
    out_a = f"ax{i-1}"
    parts.append(
        f"[{prev_a}][{N+i}:a]acrossfade=d={ACFADE}[{out_a}]"
    )
    prev_a = out_a
afinal = prev_a  # e.g. ax13

filter_complex = ";\n".join(parts)

# ── Assemble FFmpeg command ───────────────────────────────────────────────────
cmd = (
    ["ffmpeg", "-y"]
    + img_inputs
    + aud_inputs
    + ["-i", META]
    + ["-filter_complex", filter_complex]
    + ["-map", f"[{vfinal}]"]
    + ["-map", f"[{afinal}]"]
    + ["-map_metadata", str(meta_idx)]
    + ["-c:v", "libx264", "-crf", "28", "-preset", "slow"]
    + ["-c:a", "aac", "-b:a", "192k"]
    + ["-movflags", "+faststart"]
    + ["-shortest"]
    + [OUTPUT]
)

print("\nStarting FFmpeg render — this will take a while for a ~72 min video...")
print(f"Output: {OUTPUT}\n")
result = subprocess.run(cmd)

if result.returncode == 0:
    size_gb = os.path.getsize(OUTPUT) / 1024**3
    print(f"\nDone! Output: {OUTPUT}  ({size_gb:.2f} GB)")
else:
    print(f"\nFFmpeg exited with code {result.returncode}")
