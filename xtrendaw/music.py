"""موسيقى خلفية مولّدة 100% (بلا حقوق) — نبض 2099 تحت السرد.

سينثويف بسيط: باد كورد + باص نابض (sidechain) + هات خفيف.
الحجم منخفض عشان ما يغطيش على الصوت.
"""
from __future__ import annotations

import numpy as np
from pathlib import Path

SR = 44100


def _sine(freq: float, dur: float, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, dur, int(dur * sr), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def make_music(duration: float, out_path: Path, bpm: int = 100,
               volume: float = 0.22) -> Path:
    n = int(duration * SR)
    beat = 60.0 / bpm

    # باد كورد (Am → F → C → G) يتبدل كل مازورة
    chords = [
        [220.0, 261.6, 329.6],   # Am
        [174.6, 220.0, 261.6],   # F
        [196.0, 246.9, 293.7],   # G
        [164.8, 207.7, 246.9],   # E
    ]
    pad = np.zeros(n, dtype=np.float32)
    bar = beat * 4
    nbars = int(duration / bar) + 1
    for b in range(nbars):
        start = int(b * bar * SR)
        length = int(bar * SR)
        if start >= n:
            break
        freqs = chords[b % len(chords)]
        seg = np.zeros(length, dtype=np.float32)
        for f in freqs:
            seg += _sine(f, bar).astype(np.float32)
        # هجوم وتحرير ناعمين
        env = np.ones(length, dtype=np.float32)
        atk = int(0.05 * SR)
        env[:atk] *= np.linspace(0, 1, atk)
        seg *= env
        end = min(n, start + length)
        pad[start:end] += seg[: end - start]

    # باص نابض (sidechain pumping)
    bass = np.zeros(n, dtype=np.float32)
    nbeats = int(duration / beat) + 1
    for i in range(nbeats):
        s = int(i * beat * SR)
        L = int(beat * SR)
        if s >= n:
            break
        pulse = _sine(55.0, beat).astype(np.float32)
        decay = np.exp(-np.linspace(0, 5, L))
        seg = pulse * decay
        e = min(n, s + L)
        bass[s:e] += seg[: e - s]

    # هات خفيف (ضوضاء مفلترة) على الأنصاف
    hat = np.zeros(n, dtype=np.float32)
    half = beat / 2
    nh = int(duration / half) + 1
    for i in range(nh):
        s = int(i * half * SR)
        L = int(0.03 * SR)
        if s + L >= n:
            break
        noise = np.random.default_rng(i).uniform(-1, 1, L).astype(np.float32)
        noise *= np.exp(-np.linspace(0, 12, L))
        hat[s:s + L] += noise * 0.3

    mix = pad * 0.5 + bass * 0.9 + hat * 0.25
    peak = np.max(np.abs(mix)) or 1.0
    mix = (mix / peak) * volume

    # تحويل لـWAV 16bit ستيريو
    pcm = (mix * 32767).astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import wave

    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    return out_path
