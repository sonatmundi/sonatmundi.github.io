# SONAT MUNDI -- COMPLETE BANDCAMP STORE SETUP GUIDE
**Prepared 2026-03-27**

---

## QUICK-START CHECKLIST

- [ ] Create account at bandcamp.com/signup_common
- [ ] Set URL to sonatmundi.bandcamp.com
- [ ] Upload profile image and banner
- [ ] Paste artist bio
- [ ] Connect Stripe payment account
- [ ] Prepare audio files (convert MP3 to FLAC if needed)
- [ ] Upload Album 1: Ancient Soul Journey Vol.1 (8 tracks, test run)
- [ ] Set pricing: $7, individual tracks $1, "let fans pay more" ON
- [ ] Paste album description and tags
- [ ] Publish and verify everything looks correct
- [ ] Upload remaining 5 albums with descriptions, tags, and pricing
- [ ] Enable full discography purchase at $39
- [ ] Add Bandcamp link to YouTube descriptions, Instagram bio, sonatmundi.com
- [ ] Announce store launch on YouTube community post and Instagram
- [ ] Prepare promotion for May 1 Bandcamp Friday

---

## 1. ACCOUNT CREATION & SETUP

1. Go to **https://bandcamp.com/signup_common**
2. Email: **unitedcoloursofsound@gmail.com**
3. Choose **"Artist / Band"** account type
4. URL: **sonatmundi.bandcamp.com**
5. Artist name: `Sonat Mundi`
6. Location: Istanbul, Turkey

### Profile Links:
- Website: https://sonatmundi.com
- YouTube: https://www.youtube.com/@sonatmundi
- Instagram: https://www.instagram.com/sonat.mundi

### Payment: Connect Stripe account

---

## 2. AUDIO FILE PREPARATION

Bandcamp requires lossless uploads (WAV/FLAC/AIFF). Source files are MP3.

**Batch conversion (FFmpeg):**
```bash
for f in *.mp3; do ffmpeg -i "$f" "${f%.mp3}.flac"; done
```

---

## 3. ARTIST BIO (Copy-Paste)

```
Sonat Mundi is a global music project dedicated to exploring the universal language of sound. Drawing from ancient traditions, sacred frequencies, and the emotional depth of human experience, we craft immersive sonic journeys that transcend borders and time.

From the resonant tones of Solfeggio frequencies to the rich musical heritage of the Silk Road, from contemplative Sufi traditions to modern deep focus compositions -- every release is a gateway to a deeper listening experience.

Omnia Resonant -- Everything Resonates.

Released under the United Colours of Sound label.
```

---

## 4. ALBUM DESCRIPTIONS

### Sounds of Frequencies Vol.1
```
A comprehensive collection of sacred frequencies and healing tones, meticulously tuned to the ancient Solfeggio scale and beyond. 15 immersive tracks spanning the full spectrum -- from 174 Hz Foundation Tone to 963 Hz Crown Frequency, including 432 Hz Universal Resonance and 528 Hz Transformation Frequency. Designed for deep meditation, sound therapy, yoga, and mindful listening.
```

### Sounds of World Vol.1
```
A musical caravan across the legendary Silk Road -- from the bazaars of Istanbul to the oasis cities of Central Asia, from Persian gardens to the vast steppes of Mongolia. 15 tracks of evocative string arrangements, haunting wind instruments, and atmospheric soundscapes that transport you across continents and centuries.
```

### Ancient Soul Journey Vol.2
```
From the temples of Egypt to the mountains of Tibet, from Mesopotamian plains to Mesoamerican pyramids. A 15-track odyssey through time, drawing from tonal palettes and instruments of humanity's oldest civilizations, reimagined through contemporary ambient and world fusion production.
```

### Sounds of Concepts Vol.1
```
Engineered for concentration. 12 tracks of deep focus music -- minimal, non-intrusive, and rhythmically calibrated to support sustained attention. Gentle ambient textures, slow-evolving harmonic progressions, and soft rhythmic pulses. Perfect for studying, coding, writing, reading, or any task demanding full cognitive engagement.
```

### Sounds of Moods Vol.1
```
Joy. Melancholy. Wonder. Serenity. The full emotional spectrum translated into sound. 15 tracks where each composition captures a distinct emotional state with nuance, depth, and authenticity. Blends ambient, neo-classical, and cinematic elements.
```

### Ancient Soul Journey Vol.1
```
Where Sufi mysticism meets modern ambient production. 8 intimate tracks drawing from whirling dervish ceremonies, contemplative ney flute, and hypnotic bendir rhythms -- reimagined through contemporary ambient and lounge production. Persian melodic scales intertwine with warm synthesizer pads.
```

---

## 5. TAGS

| Album | Tags |
|-------|------|
| Frequencies Vol.1 | healing frequencies, solfeggio frequencies, 432 Hz, 528 Hz, sound healing, meditation music, ambient, sacred tones, relaxation, sound therapy |
| World Vol.1 | world music, silk road, middle eastern, central asian, ethnic ambient, traditional, global sounds, Istanbul, cinematic world, folk fusion |
| ASJ Vol.2 | ancient music, world fusion, ambient, meditation, spiritual, cinematic, ancient civilizations, ethereal, tribal ambient, new age |
| Concepts Vol.1 | study music, deep focus, ambient, concentration, lo-fi ambient, productivity, focus music, background music, calm, instrumental |
| Moods Vol.1 | ambient, emotional, cinematic, neo-classical, mood music, atmospheric, melancholy, contemplative, instrumental, soundscape |
| ASJ Vol.1 | sufi music, persian, ambient, lounge, middle eastern, meditation, mystical, ney flute, spiritual, world music |

---

## 6. PRICING

| Album | Tracks | Album Price | Track Price |
|-------|--------|-------------|-------------|
| Frequencies Vol.1 | 15 | $9 | $1 |
| World Vol.1 | 15 | $9 | $1 |
| ASJ Vol.2 | 15 | $9 | $1 |
| Concepts Vol.1 | 12 | $9 | $1 |
| Moods Vol.1 | 15 | $9 | $1 |
| ASJ Vol.1 | 8 | $7 | $1 |
| **Full Discography** | 80+ | **$39** | - |

**"Let fans pay more" = ALWAYS ON** (40% of buyers pay extra)

---

## 7. BANDCAMP PRO vs FREE

**Start FREE.** Upgrade to Pro ($10/mo) when you have 100+ followers or want custom domain.

---

## 8. BANDCAMP FRIDAYS 2026

| Date | Status |
|------|--------|
| **May 1, 2026** | **NEXT -- Store must be ready!** |
| August 7, 2026 | Upcoming |
| September 4, 2026 | Upcoming |
| October 2, 2026 | Upcoming |
| November 6, 2026 | Upcoming |
| December 4, 2026 | Upcoming |

On Bandcamp Fridays, Bandcamp waives its 15% revenue share -- you keep 100%.

---

## 9. UPLOAD ORDER

1. Ancient Soul Journey Vol.1 (8 tracks -- test run)
2. Sounds of Frequencies Vol.1
3. Sounds of World Vol.1
4. Ancient Soul Journey Vol.2
5. Sounds of Concepts Vol.1
6. Sounds of Moods Vol.1
