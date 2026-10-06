# Kabuzio bot: our own background music for the Reels on Facebook, TikTok, Pinterest and Telegram
# (their APIs can't add music; Instagram gets a trending song instead). Generated note by note here, so it is 100 %
# ours: no rights, no blocked videos. Calm "quiet luxury" mood: soft pad + piano arpeggio + low bass, ~72 bpm.
#   make(out_wav, seconds, seed)   same seed = same track; reel.py uses the product id, so each Reel sounds different
import math, os, random, struct, subprocess, wave

RATE = 22050
# chord progressions as semitones over the key (major 7ths / minor 9ths: warm, never cheesy)
PROGS = [
    [(0, 4, 7, 11), (9, 12, 16, 19), (5, 9, 12, 16), (7, 11, 14, 17)],     # Imaj7  vi7  IVmaj7  V7
    [(0, 3, 7, 10), (8, 12, 15, 19), (3, 7, 10, 14), (10, 14, 17, 21)],    # i7  VImaj7  IIImaj7  VII
    [(0, 4, 7, 11), (5, 9, 12, 16), (2, 5, 9, 12), (7, 11, 14, 17)],       # Imaj7  IVmaj7  ii7  V7
    [(0, 3, 7, 14), (5, 8, 12, 15), (10, 14, 17, 21), (8, 12, 15, 19)],    # i(add9)  iv7  VII  VImaj7
]
ARPS = [(0, 1, 2, 3, 2, 1, 0, 2), (0, 2, 1, 3, 0, 2, 1, 3), (0, 1, 2, 3, 3, 2, 1, 2)]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def make(out, seconds=16, seed=0):
    rnd = random.Random(str(seed))
    key = rnd.choice([57, 58, 60, 62, 63])  # A, Bb, C, D, Eb
    prog, arp = rnd.choice(PROGS), rnd.choice(ARPS)
    bpm = rnd.choice([66, 70, 74])
    beat = 60.0 / bpm
    bar = 4 * beat
    n = int(seconds * RATE)
    buf = [0.0] * n

    def add(f, start, dur, amp, harm, decay, attack=0.006):
        a, b = int(start * RATE), min(n, int((start + dur) * RATE))
        w = [2 * math.pi * f * (k + 1) / RATE for k in range(len(harm))]
        for i in range(a, b):
            t = (i - a) / RATE
            env = min(1.0, t / attack) * math.exp(-t * decay) * min(1.0, (b - i) / (0.05 * RATE))
            s = 0.0
            for k, h in enumerate(harm):
                s += h * math.sin(w[k] * (i - a))
            buf[i] += amp * env * s

    t, c = 0.0, 0
    while t < seconds:
        ch = prog[c % len(prog)]
        for note in ch:  # pad: slow swell, very soft
            add(hz(key - 12 + note), t, bar + 0.4, 0.05, (1, 0.25), 0.35, attack=0.9)
        add(hz(key - 24 + ch[0]), t, bar, 0.16, (1, 0.3), 0.6, attack=0.02)  # bass
        for k, idx in enumerate(arp):  # piano: eighth notes over the chord, an octave up
            vel = 0.11 if k % 2 == 0 else 0.075
            add(hz(key + ch[idx]), t + k * beat / 2, beat * 2.5, vel, (1, 0.45, 0.2, 0.08), 2.4)
        if c % 2 == 1:  # a high answering note every other bar
            add(hz(key + 12 + ch[rnd.choice((1, 2, 3))]), t + 2.5 * beat, beat * 3, 0.05, (1, 0.3), 1.2)
        t += bar
        c += 1
    peak = max(1e-9, max(abs(x) for x in buf))
    raw = os.path.splitext(out)[0] + "-raw.wav"
    with wave.open(raw, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(32000 * 0.9 * x / peak)) for x in buf))
    # room reverb + stereo width + fades, at 44.1 kHz
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
                        "aresample=44100,aecho=0.8:0.6:90|170|260:0.35|0.25|0.15,lowpass=f=7000,"
                        "pan=stereo|c0=c0|c1=c0,aecho=0.9:0.9:12:0.4,"
                        f"afade=t=in:d=0.4,afade=t=out:st={max(0, seconds - 1.8)}:d=1.8,loudnorm=I=-18:TP=-2",
                        "-ar", "44100", out], capture_output=True, text=True)
    os.remove(raw)
    if r.returncode:
        raise SystemExit("ffmpeg música: " + r.stderr[-400:])
    return out


def with_music(video, out, seed):
    """Copy of the Reel with our music under it (the video stream is copied, not re-encoded)."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout.strip() or 16)
    wav = make(os.path.splitext(out)[0] + ".wav", math.ceil(dur), seed)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-t", f"{dur:.2f}", "-movflags", "+faststart", out],
                       capture_output=True, text=True)
    os.remove(wav)
    if r.returncode:
        raise SystemExit("ffmpeg música: " + r.stderr[-400:])
    return out


if __name__ == "__main__":
    import sys
    print(make(sys.argv[1] if len(sys.argv) > 1 else "/tmp/musica.wav", 16, sys.argv[2] if len(sys.argv) > 2 else 0))
