import sys
titles = [
    "Ancient Soul Journey Vol.1 \u2726 Sufi Ambient & Persian Lounge & 528 Hz Solfeggio | United Colours of Sound",
    "Ancient Soul Journey Vol.1 \u2726 Sufi Ambient & Persian Lounge & 528Hz Solfeggio | United Colours of Sound",
    "Ancient Soul Journey Vol.1 \u2726 Sufi Ambient, Persian Lounge & 528Hz Solfeggio | United Colours of Sound",
    "Ancient Soul Journey Vol.1 \u2726 Sufi Ambient, Persian Lounge, 528Hz Solfeggio | United Colours of Sound",
]
for t in titles:
    sys.stdout.buffer.write(f"{len(t):3d}  {t}\n".encode("utf-8"))
