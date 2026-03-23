#!/usr/bin/env python3
"""
Create Sounds of World Vol.1 – Ancient Silk Road compilation video.
15 tracks · each with its own cover image · 2 s video xfade · 3 s audio acrossfade
"""

import subprocess
import os

BASE   = r"D:\Yedekler\UCS\Sounds of World Vol. 1 Ancient Silk Road Authentic"
COVERS = os.path.join(BASE, "covers")
OUTPUT = os.path.join(BASE, "Sounds_of_World_Vol1.mp4")
META   = os.path.join(BASE, "vol1.ffmeta")

# ── Track list (audio_file, cover_image, duration_seconds) ─────────────────
TRACKS = [
    ("1. Anatolian Dawn.mp3",
     "1. Anatolian Dawn.jpeg",                       251.999979),
    ("2. Samarkand Caravanserai (Uzbekistan).mp3",
     "2. Samarkand Caravanserai (Uzbekistan).jpeg",  132.559979),
    ("3. Hafiz\u2019s Secret (Persia).mp3",
     "3. Hafiz\u2019s Secret (Persia).jpeg",         188.879979),
    ("4. The Spirit of Tengri (Mongolia).mp3",
     "4. The Spirit of Tengri (Mongolia).jpeg",      288.679979),
    ("5. Duduk\u2019s Lament (Armenia_Caucasus).mp3",
     "5. Duduk\u2019s Lament (Armenia-Caucasus).jpeg", 157.759979),
    ("6. Andalusian Twilight (Spain_Moorish).mp3",
     "6. Andalusian Twilight (Spain-Moorish).jpeg",  206.999979),
    ("7. Kyoto Moon (Japan).mp3",
     "7. Kyoto Moon (Japan).jpeg",                   126.519979),
    ("8. Himalayan Silence (Tibet).mp3",
     "8. Himalayan Silence (Tibet).jpeg",            184.079979),
    ("9. Varanasi Morning (India).mp3",
     "9. Varanasi Morning (India).jpeg",             479.399979),
    ("10. Tuareg Fire (Sahara).mp3",
     "10. Tuareg Fire (Sahara).jpeg",                231.319979),
    ("11. Byzantine Echoes (Greece).mp3",
     "11. Byzantine Echoes (Greece).jpeg",           211.199979),
    ("12. Balkan Soul (Balkans).mp3",
     "12. Balkan Soul (Balkans).jpeg",               157.679979),
    ("13. Mesopotamian Wind (Iraq_Sumer).mp3",
     "13. Mesopotamian Wind (Iraq-Sumer).jpeg",      247.439979),
    ("14. The Weaver\u2019s Song (China).mp3",
     "14. The Weaver\u2019s Song (China).jpeg",      209.519979),
    ("15. Global Silk Road (Finale).mp3",
     "15. Global Silk Road (Finale).jpeg",           276.159979),
]

NAMES = [
    "Anatolian Dawn", "Samarkand Caravanserai", "Hafiz's Secret",
    "The Spirit of Tengri", "Duduk's Lament", "Andalusian Twilight",
    "Kyoto Moon", "Himalayan Silence", "Varanasi Morning",
    "Tuareg Fire", "Byzantine Echoes", "Balkan Soul",
    "Mesopotamian Wind", "The Weaver's Song", "Global Silk Road",
]

N        = len(TRACKS)
V_XFADE  = 2          # seconds — image crossfade
A_XFADE  = 3          # seconds — audio acrossfade
durations = [t[2] for t in TRACKS]

# Image input durations are trimmed by (A_XFADE - V_XFADE) = 1 s so that
# the video and audio streams end at exactly the same time.
img_durs = [d - (A_XFADE - V_XFADE) for d in durations[:-1]] + [durations[-1]]

# Chapter start times (seconds into the output)
chap_starts = [0.0]
for i in range(1, N):
    chap_starts.append(chap_starts[-1] + durations[i - 1] - A_XFADE)
total_s = chap_starts[-1] + durations[-1]


# ── Write FFmetadata (chapters) ─────────────────────────────────────────────
def write_ffmeta():
    lines = [";FFMETADATA1\n", "title=Sounds of World Vol.1 Ancient Silk Road\n\n"]
    for i in range(N):
        start_ms = int(chap_starts[i] * 1000)
        end_ms   = (int(chap_starts[i + 1] * 1000) - 1) if i < N - 1 else int(total_s * 1000)
        lines += [
            "[CHAPTER]\n",
            "TIMEBASE=1/1000\n",
            f"START={start_ms}\n",
            f"END={end_ms}\n",
            f"title={NAMES[i]}\n",
            "\n",
        ]
    with open(META, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    print(f"Chapter metadata -> {META}")


# ── Build FFmpeg command ─────────────────────────────────────────────────────
def make_cmd():
    cmd = ["ffmpeg", "-y"]

    # Image inputs (looped stills, each trimmed to its adjusted duration)
    for i, (_, img, _) in enumerate(TRACKS):
        cmd += ["-loop", "1", "-t", f"{img_durs[i]:.3f}", "-i", os.path.join(COVERS, img)]

    # Audio inputs
    for audio, _, _ in TRACKS:
        cmd += ["-i", os.path.join(BASE, audio)]

    # FFmetadata input
    cmd += ["-i", META]

    # ── Video filter: scale each image then chain xfade transitions ──────────
    SCALE = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25"
    )
    vf = [f"[{i}:v]{SCALE}[v{i}]" for i in range(N)]

    # xfade offsets are cumulative across the chain
    offset = img_durs[0] - V_XFADE
    prev = "v0"
    for i in range(1, N):
        out = "vout" if i == N - 1 else f"xf{i}"
        vf.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={V_XFADE}:offset={offset:.3f}[{out}]"
        )
        prev = out
        if i < N - 1:
            offset += img_durs[i] - V_XFADE

    # ── Audio filter: chain acrossfade transitions ───────────────────────────
    af = []
    prev_a = f"{N}:a"          # first audio input index = N (images are 0..N-1)
    for i in range(1, N):
        out_a = "aout" if i == N - 1 else f"af{i}"
        af.append(f"[{prev_a}][{N + i}:a]acrossfade=d={A_XFADE}[{out_a}]")
        prev_a = out_a

    filter_complex = ";".join(vf + af)

    meta_idx = N + N   # index of the ffmeta input (after images and audios)

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-map_metadata", str(meta_idx),
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        OUTPUT,
    ]
    return cmd


# ── Print chapter summary ────────────────────────────────────────────────────
def print_chapters():
    print("\nChapter markers:")
    for i, (name, t) in enumerate(zip(NAMES, chap_starts)):
        m, s = divmod(int(t), 60)
        h, m = divmod(m, 60)
        print(f"  {i+1:2d}. {h:02d}:{m:02d}:{s:02d}  {name}")
    m, s = divmod(int(total_s), 60)
    h, m = divmod(m, 60)
    print(f"  Total duration: {h:02d}:{m:02d}:{s:02d}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    write_ffmeta()
    print_chapters()

    cmd = make_cmd()
    print(f"\nOutput -> {OUTPUT}")
    print("Starting FFmpeg (this will take a while)...\n")

    subprocess.run(cmd, check=True)

    print(f"\nDone! -> {OUTPUT}")
