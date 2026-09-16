"""إيچنت التحليل — المصنع بيتعلم من جمهوره.

كل أسبوع: يجيب إحصائيات أحدث الفيديوهات (RSS عام + YouTube Data API بتوكن
الرفع لو مسموح) ويكتب state/stats_report.json — والمخطط بيقدّم الأنواع
اللي الجمهور بيحبها. فشل الشبكة/الصلاحيات = تقرير فاضي بأمان، بلا كراش.
"""
from __future__ import annotations

import json
import re
import time

import requests

from . import settings

CHANNEL = "UC2PCynDtd_wtPrgoAuqH6yw"
REPORT = settings.ROOT / "state" / "stats_report.json"
WEEK = 7 * 24 * 3600

# من عنوان الحلقة → نوعها
KIND_PATTERNS = [
    ("الرقية", "ruqyah"), ("التحصين", "tahseen"), ("جزء عمّ", "juz"),
    ("الأسماء الحسنى", "asma"), ("السيرة", "seerah"), ("حصن المسلم", "hisn"),
    ("النووية", "nawawi"), ("قصص الأنبياء", "qissa"), ("التدبُّر", "tafsir"),
    ("سُورَةُ", "quran"), ("حديث", "hadith"), ("دعاء", "dua"),
    ("أذكار", "adhkar"), ("الكون", "kawn"), ("الآخرة", "akhira"),
    ("الأخلاق", "akhlaq"), ("معلومة", "info"),
]


def _rss_ids() -> list[tuple[str, str]]:
    r = requests.get(
        f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}",
        timeout=30)
    ids = re.findall(r"<yt:videoId>(.*?)</yt:videoId>", r.text)
    titles = re.findall(r"<title>(.*?)</title>", r.text)[1:]
    return list(zip(ids, titles))[:30]


def _kind_of(title: str) -> str:
    for pat, kind in KIND_PATTERNS:
        if pat in title:
            return kind
    return "info"


def _stats(ids: list[str]) -> dict:
    """محاولة YouTube Data API — لو التوكن ما يسمحش نرجع فاضي."""
    try:
        from .publish import youtube as _yt
        tok = _yt._token()
        if not tok:
            return {}
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "statistics", "id": ",".join(ids[:50])},
            headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        if not r.ok:
            return {}
        out = {}
        for it in r.json().get("items", []):
            out[it["id"]] = int(
                it.get("statistics", {}).get("viewCount", 0))
        return out
    except Exception:
        return {}


def run() -> dict:
    """تقرير أسبوعي — يعيد ملخصه."""
    rep = {"ts": time.time(), "videos": [], "best_kind": None,
           "by_kind": {}}
    try:
        pairs = _rss_ids()
    except Exception:
        pairs = []
    if not pairs:
        return rep
    stats = _stats([i for i, _ in pairs])
    by_kind: dict[str, int] = {}
    for vid, title in pairs:
        k = _kind_of(title)
        v = stats.get(vid, 0)
        rep["videos"].append({"id": vid, "kind": k, "views": v,
                              "title": title[:60]})
        by_kind[k] = by_kind.get(k, 0) + v
    rep["by_kind"] = by_kind
    if any(by_kind.values()):
        rep["best_kind"] = max(by_kind, key=by_kind.get)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    return rep


def due() -> bool:
    """التقرير مستحق لو عمره أسبوع+ أو مش موجود."""
    if not REPORT.exists():
        return True
    try:
        ts = json.loads(REPORT.read_text(encoding="utf-8")).get("ts", 0)
    except Exception:
        return True
    return time.time() - ts > WEEK


if __name__ == "__main__":
    print(run())
