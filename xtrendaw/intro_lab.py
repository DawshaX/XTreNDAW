"""مختبر الافتتاحيات — أول ثانيتين هما أقوى لحظة في الفيديو.

بدل صورة ثابتة متكررة: 7 هياكل حركية مختلفة تمامًا (وارب، كشاف ضوء،
انفجار حلقي، كالييدوسكوب، صعود، مدار، جليتش 2099) — وكل هيكل متغيّر
بلا حدود من بذرة الحلقة (اتجاه، سرعة، مدة، كثافة نجوم، لون توهّج، زاوية).
الناتج: مليارات افتتاحيات مختلفة، كلها بهوية البراند الأحمر XDAW NOVA.
"""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import settings, scenes
from .tts import ffmpeg

W, H = settings.VIDEO["width"], settings.VIDEO["height"]
FPS = 30


def _h(seed: str, salt: str) -> int:
    return int(hashlib.sha256((seed + "|" + salt).encode()).hexdigest()[:16], 16)


# ---------- أصول مرسومة إجرائيًا (تتبذر من DNA) ----------

def _stars(path: Path, seed: str, rgb: str, density: int) -> Path:
    if path.exists():
        return path
    rnd = random.Random(seed)
    r, g, b = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
    img = Image.new("RGB", (W * 2, H * 2), (4, 5, 12))
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(4):
        bx, by = rnd.randint(0, W * 2), rnd.randint(0, H * 2)
        br = rnd.randint(500, 950)
        peak = rnd.randint(26, 44)
        ys, xs = np.mgrid[-128:128, -128:128]
        rad = np.clip(np.sqrt(xs * xs + ys * ys) / 128.0, 0, 1)
        al = np.clip((1 - rad) ** 2.2, 0, 1) * peak
        blob = np.zeros((256, 256, 4), np.uint8)
        blob[:, :, 0], blob[:, :, 1], blob[:, :, 2] = r, g, b
        blob[:, :, 3] = al.astype(np.uint8)
        bi = Image.fromarray(blob).resize((br * 2, br * 2), Image.LANCZOS)
        img.paste(bi, (bx - br, by - br), bi)
    for _ in range(density):
        x, y = rnd.randint(0, W * 2 - 1), rnd.randint(0, H * 2 - 1)
        sz = rnd.choice([1, 2, 2, 3, 4])
        d.ellipse([x, y, x + sz, y + sz],
                  fill=(235, 240, 255, rnd.randint(120, 255)))
    img.save(path)
    return path


def _glow_logo(path: Path, size: int) -> Path:
    if path.exists():
        return path
    pad = size // 2
    img = Image.new("RGBA", (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    cx = cy = size // 2 + pad
    for rr, a in [(int(size * 0.95), 12), (int(size * 0.72), 20),
                  (int(size * 0.52), 34), (int(size * 0.34), 55)]:
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 42, 42, a))
    lg = scenes.load_logo(size)
    img.paste(lg, (pad, pad), lg)
    img.save(path)
    return path


def _ring(path: Path, rgb: str, thick: int = 10) -> Path:
    if path.exists():
        return path
    s = 1000
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
    d.ellipse([20, 20, s - 20, s - 20], outline=(r, g, b, 235), width=thick)
    img.save(path)
    return path


def _arcs(path: Path, rgb: str) -> Path:
    if path.exists():
        return path
    s = 1000
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
    for a0 in (10, 130, 250):
        d.arc([30, 30, s - 30, s - 30], a0, a0 + 80,
              fill=(r, g, b, 240), width=16)
    img.save(path)
    return path


def _beam(path: Path) -> Path:
    if path.exists():
        return path
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(150):
        a = int(110 * np.sin(np.pi * i / 150))
        d.line([(W // 2 - 120 + i, -200), (W // 2 - 420 + i, H + 200)],
               fill=(255, 244, 230, a), width=3)
    img.save(path)
    return path


def _speedlines(path: Path, rgb: str) -> Path:
    if path.exists():
        return path
    rnd = random.Random(rgb + "sl")
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(46):
        x = rnd.randint(0, W)
        y = rnd.randint(-100, H)
        ln = rnd.randint(120, 420)
        a = rnd.randint(90, 190)
        d.line([(x, y), (x, y + ln)], fill=(255, 255, 255, a),
               width=rnd.choice([2, 3, 4]))
    img.save(path)
    return path


def _grid2099(path: Path) -> Path:
    if path.exists():
        return path
    img = Image.new("RGB", (W * 2, H * 2), (8, 2, 6))
    d = ImageDraw.Draw(img, "RGBA")
    hy = int(H * 1.05)
    for i in range(1, 26):
        y = hy + int((H * 0.95) * (i / 25) ** 2.1)
        d.line([(0, y), (W * 2, y)], fill=(255, 30, 48, 190),
               width=3 + i // 4)
    for x in range(-10, 11):
        d.line([(W + x * 60, hy), (W + x * 620, H * 2)],
               fill=(255, 30, 48, 150), width=3)
    d.ellipse([W - 420, hy - 420, W + 420, hy + 60], fill=(255, 60, 40, 90))
    rnd = random.Random("2099")
    for _ in range(240):
        x, y = rnd.randint(0, W * 2 - 1), rnd.randint(0, hy - 100)
        d.ellipse([x, y, x + 2, y + 2],
                  fill=(255, 220, 220, rnd.randint(120, 255)))
    img.save(path)
    return path


def _scan(path: Path) -> Path:
    if path.exists():
        return path
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 8):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 26), width=2)
    img.save(path)
    return path


# ---------- الهياكل السبعة ----------

def arch_warp(fc, dur, dirn):
    if dirn > 0:
        z = f"min(2.6,1+1.6*pow(on/{fc},1.35))"
    else:
        z = f"max(1.0,2.6-1.6*pow(on/{fc},1.35))"
    return (
        f"[0:v]zoompan=z='{z}':d={fc}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={W}x{H}:fps={FPS},setsar=1[bg];"
        f"[1:v]scale=w='max(2,2*floor(820*(2.0-1.0*min(1,n/16))/2))':h=-2:eval=frame[lg];"
        f"[bg][lg]overlay=x=(W-w)/2:y=(H-h)/2-90,"
        f"fade=t=in:st=0:d=0.12:color=white,format=yuv420p[v]"
    )


def arch_sweep(fc, dur, dirn):
    x0, x1 = (-W, W) if dirn > 0 else (W, -W)
    return (
        f"[0:v]scale={W}:{H},eq=brightness=-0.18[bg];"
        f"[bg][2:v]overlay=x='{x0}+({x1 - x0})*t/{dur:.2f}':y=0[m1];"
        f"[1:v]scale=w='max(2,2*floor(760*(1.12-0.12*min(1,n/20))/2))':h=-2:eval=frame,"
        f"fade=t=in:st={dur * 0.42:.2f}:d=0.35:alpha=1[lg];"
        f"[m1][lg]overlay=x=(W-w)/2:y=(H-h)/2-80,format=yuv420p[v]"
    )


def arch_burst(fc, dur, dirn):
    return (
        f"[0:v]scale={W}:{H}[bg];"
        f"[2:v]scale=w='max(4,2*floor((140+1900*n/{fc})/2))':h=-2:eval=frame,"
        f"fade=t=out:st={dur - 0.5:.2f}:d=0.5:alpha=1[r1];"
        f"[3:v]scale=w='max(4,2*floor((60+1500*max(0,n-8)/{fc})/2))':h=-2:eval=frame,"
        f"fade=t=out:st={dur - 0.4:.2f}:d=0.4:alpha=1[r2];"
        f"[bg][r1]overlay=x=(W-w)/2:y=(H-h)/2[m1];"
        f"[m1][r2]overlay=x=(W-w)/2:y=(H-h)/2[m2];"
        f"[1:v]scale=w='max(2,2*floor(820*(0.25+0.9*min(1,n/13))/2))':h=-2:eval=frame[lg];"
        f"[m2][lg]overlay=x=(W-w)/2:y=(H-h)/2-80,format=yuv420p[v]"
    )


def arch_kaleido(fc, dur, dirn):
    rot = 0.35 * dirn
    return (
        f"[0:v]scale={W}:{H},split=4[a][b][c][e];"
        f"[b]hflip[hf];[c]vflip[vf];[e]hflip,vflip[hv];"
        f"[a][hf][vf][hv]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0,"
        f"rotate=angle='{rot}*t':fillcolor=black:ow={W}:oh={H}[bg];"
        f"[1:v]scale=w='max(2,2*floor(760*(1+0.06*sin(t*7))/2))':h=-2:eval=frame[lg];"
        f"[bg][lg]overlay=x=(W-w)/2:y=(H-h)/2-80,format=yuv420p[v]"
    )


def arch_rise(fc, dur, dirn):
    return (
        f"[0:v]scale={W}:{H}[bg];"
        f"[bg][3:v]overlay=y='mod(t*1500,{H + 400})-400'[m0];"
        f"[m0][2:v]overlay=x=(W-w)/2:"
        f"y='(H/2-80)+(1-min(1,t/0.6))*{int(H * 0.85)}+130'[m1];"
        f"[m1][1:v]overlay=x=(W-w)/2:"
        f"y='(H/2-80)+(1-min(1,t/0.6))*{int(H * 0.85)}',format=yuv420p[v]"
    )


def arch_orbit(fc, dur, dirn):
    return (
        f"[0:v]scale={W}:{H}[bg];"
        f"[2:v]scale=1300:1300,rotate=angle='{2.6 * dirn}*t':fillcolor=black@0.0[o1];"
        f"[bg][o1]overlay=x=(W-w)/2:y=(H-h)/2-80[m1];"
        f"[2:v]scale=900:900,rotate=angle='{-1.8 * dirn}*t':fillcolor=black@0.0[o2];"
        f"[m1][o2]overlay=x=(W-w)/2:y=(H-h)/2-80[m2];"
        f"[1:v]scale=w='max(2,2*floor(720*(1+0.05*sin(t*6))/2))':h=-2:eval=frame[lg];"
        f"[m2][lg]overlay=x=(W-w)/2:y=(H-h)/2-80,format=yuv420p[v]"
    )


def arch_glitch(fc, dur, dirn):
    return (
        f"[0:v]zoompan=z='min(1.5,1+0.5*on/{fc})':d={fc}:x='iw/2-(iw/zoom/2)'"
        f":y='ih*0.62-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1[bg];"
        f"[1:v]colorchannelmixer=rr=0:gr=0:br=0:rg=0:gg=1:bg=0:rb=0:gb=0:bb=0[grn];"
        f"[1:v]colorchannelmixer=rr=0:gr=0:br=0:rg=0:gg=0:bg=0:rb=0:gb=0:bb=1[blu];"
        f"[bg][grn]overlay=x='(W-w)/2-14':y=(H-h)/2-80:"
        f"enable='between(t,0.35,0.55)+between(t,1.15,1.3)'[m1];"
        f"[m1][blu]overlay=x='(W-w)/2+14':y=(H-h)/2-80:"
        f"enable='between(t,0.35,0.55)+between(t,1.15,1.3)'[m2];"
        f"[1:v]scale=w='max(2,2*floor(800*(1+0.22*lt(mod(t*2,1),0.10))/2))':h=-2:eval=frame[lg];"
        f"[m2][lg]overlay=x=(W-w)/2:y=(H-h)/2-80[m3];"
        f"[m3][3:v]overlay=0:0:enable='between(t,0.3,0.6)+between(t,1.1,1.4)',"
        f"format=yuv420p[v]"
    )


_ARCHS = [arch_warp, arch_sweep, arch_burst, arch_kaleido,
          arch_rise, arch_orbit, arch_glitch]

_FILES = {
    0: ["stars", "logo"],
    1: ["stars", "logo", "beam"],
    2: ["stars", "logo", "ring", "ring"],
    3: ["stars", "logo"],
    4: ["stars", "logo", "ghost", "lines"],
    5: ["stars", "logo", "arcs"],
    6: ["grid", "logo", "scan", "scan"],
}


# ---------- الدخول العام ----------

def render(dna: dict, out: Path) -> tuple[Path, float]:
    """ينتج افتتاحية ديناميكية حسب DNA الحلقة ويرجع (المسار، المدة)."""
    seed = dna["seed"]
    rgb = dna["rgb"].lstrip("#")
    h = _h(seed, "intro")
    arch = h % 7
    dirn = 1 if (h >> 3) & 1 else -1
    dur = [2.2, 2.4, 2.6][(h >> 6) % 3]
    fc = int(round(dur * FPS))
    out.parent.mkdir(parents=True, exist_ok=True)
    ov = out.parent / "ov"
    ov.mkdir(parents=True, exist_ok=True)

    assets = {
        "stars": _stars(ov / f"st-{seed[:8]}-{h % 97}.png",
                        seed + str(h % 97), rgb, 300 + (h >> 9) % 500),
        "logo": _glow_logo(ov / "glowlogo.png", 470),
        "ring": _ring(ov / f"ring-{rgb}.png", rgb),
        "arcs": _arcs(ov / f"arcs-{rgb}.png", rgb),
        "beam": _beam(ov / "beam.png"),
        "lines": _speedlines(ov / f"sl-{rgb}.png", rgb),
        "grid": _grid2099(ov / "grid2099.png"),
        "scan": _scan(ov / "scan.png"),
        "ghost": None,
    }
    gp = ov / "ghost.png"
    if not gp.exists():
        scenes.load_logo(560, alpha=110).save(gp)
    assets["ghost"] = gp

    graph = _ARCHS[arch](fc, dur, dirn)
    cmd = [ffmpeg(), "-y"]
    for key in _FILES[arch]:
        cmd += ["-loop", "1", "-t", f"{dur:.2f}", "-i", str(assets[key])]
    cmd += ["-filter_complex", graph, "-map", "[v]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-t", f"{dur:.2f}", str(out)]
    from .video import _run
    _run(cmd, "افتتاحية")
    return out, dur
