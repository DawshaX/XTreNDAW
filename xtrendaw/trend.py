"""رادار التريند اللحظي — عيون المصنع على الكون.

مصادر مجانية بلا مفاتيح (متحقق منها من السيرفر):
  1) Google Trends RSS (مصر/السعودية/عالمي) — عناوين + حجم بحث تقريبي.
  2) YouTube Suggest — اقتراحات البحث الحيّة (اللي الناس بتدوّره فعلًا).
  3) HackerNews — إشارة التك/عالمي.

بيحفظ state/trends.json بين الدورات عشان يقيس "سرعة الصعود":
موضوع يقفز في الرتب دورة ورا دورة = ترند سخن → أولوية إنتاج.
وفلتر قيم NOVA: فضايح/أذى مش داخلين المصنع مهما كانوا سخنين.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import settings

GEOS = ["EG", "SA", "US"]
YT_SEEDS = ["مبار", "حلقة", "اغنية", "فيلم", "تحدي", "خبر", "ترند", "ai"]
BLOCKLIST = ["فضيحة", "فضايح", "قمار", "مخدرات", "انتقام", "تعذيب", "مذبحة"]

STATE = settings.ROOT / "state" / "trends.json"


def _get(url: str, timeout: int = 12):
    return requests.get(url, timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})


def _traffic_num(s: str) -> int:
    m = re.search(r"([\d.]+)\s*([KMB]?)", s or "")
    if not m:
        return 0
    v = float(m.group(1))
    return int(v * {"K": 1e3, "M": 1e6, "B": 1e9, "": 1}[m.group(2)])


def google_trends(geo: str) -> list[dict]:
    """عناوين تريند جوجل + حجم البحث التقريبي."""
    out = []
    try:
        r = _get(f"https://trends.google.com/trending/rss?geo={geo}")
        if not r.ok:
            return out
        root = ET.fromstring(r.content)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            pub = item.findtext("pubDate") or ""
            traffic = ""
            for el in item.iter():
                if el.tag.endswith("approx_traffic"):
                    traffic = el.text or ""
            if title:
                out.append({"title": title, "traffic": _traffic_num(traffic),
                            "traffic_raw": traffic, "source": f"google:{geo}",
                            "published": pub})
    except Exception:
        pass
    return out


def youtube_suggest() -> list[dict]:
    """اقتراحات بحث يوتيوب الحيّة بالعربي."""
    out = []
    import urllib.parse
    for seed in YT_SEEDS:
        try:
            u = ("https://suggestqueries.google.com/complete/search?client=youtube"
                 f"&ds=yt&hl=ar&q={urllib.parse.quote(seed)}")
            r = _get(u)
            if not r.ok:
                continue
            m = re.findall(r'\["([^"]+)",\d', r.text)
            for s in m[:4]:
                out.append({"title": s, "traffic": 0, "traffic_raw": "",
                            "source": "youtube:suggest", "published": ""})
        except Exception:
            continue
    return out


def hackernews() -> list[dict]:
    try:
        ids = _get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:8]
        out = []
        for i in ids:
            it = _get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json").json()
            out.append({"title": it.get("title", ""), "traffic": it.get("score", 0),
                        "traffic_raw": str(it.get("score", 0)), "source": "hn",
                        "published": ""})
        return out
    except Exception:
        return []


def _norm(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip().lower()
    return re.sub(r"[أإآ]", "ا", t)


def _blocked(t: str) -> bool:
    tl = _norm(t)
    return any(b in tl for b in BLOCKLIST)


def scan() -> list[dict]:
    """مسح كل المصادر → قائمة موحّدة مرتّبة بالنقاط."""
    raw: list[dict] = []
    for geo in GEOS:
        raw += google_trends(geo)
    raw += youtube_suggest()
    raw += hackernews()

    # دمج المكرر + عدّ المصادر المتقاطعة
    merged: dict[str, dict] = {}
    for r_ in raw:
        if _blocked(r_["title"]):
            continue
        key = _norm(r_["title"])[:60]
        if key not in merged:
            merged[key] = {**r_, "sources": 1}
        else:
            merged[key]["sources"] += 1
            merged[key]["traffic"] = max(merged[key]["traffic"], r_["traffic"])

    now = datetime.now(timezone.utc)
    prev = {}
    if STATE.exists():
        try:
            prev = {p["key"]: p for p in
                    json.loads(STATE.read_text(encoding="utf-8"))}
        except Exception:
            prev = {}

    scored = []
    for key, t in merged.items():
        score = 0.0
        score += min(60, t["traffic"] / 200)          # حجم البحث
        if t["source"].startswith("youtube"):
            score += 4
        score += 25 * (t["sources"] - 1)               # تقاطع مصادر = إشارة حقيقية
        if t["published"]:
            try:
                dt = datetime.strptime(t["published"], "%a, %d %b %Y %H:%M:%S %Z")
                age_h = (now - dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                score += max(0, 20 - age_h)            # الأحدث يسخن أكتر
            except Exception:
                pass
        scored.append({**t, "key": key, "score": round(score, 1)})

    scored.sort(key=lambda x: -x["score"])
    top = scored[:25]
    for i, t in enumerate(top):
        t["rank"] = i + 1
        old = prev.get(t["key"])
        t["velocity"] = (old["rank"] - t["rank"]) if old and "rank" in old else 0
        if t["velocity"] > 0:
            t["score"] = round(t["score"] + 8 * t["velocity"], 1)

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(top, ensure_ascii=False, indent=1), encoding="utf-8")
    top.sort(key=lambda x: -x["score"])
    return top


def main() -> None:
    top = scan()
    print(f"📡 رادار NOVA — {datetime.now():%H:%M} · {len(top)} إشارة")
    for t in top[:12]:
        up = f" ↑{t['velocity']}" if t.get("velocity") else ""
        tr = f" · {t['traffic_raw']}" if t["traffic_raw"] else ""
        print(f" {t['rank']:>2}. [{t['score']:>5.1f}]{up} {t['title'][:58]} "
              f"({t['source']}{tr})")


if __name__ == "__main__":
    main()
