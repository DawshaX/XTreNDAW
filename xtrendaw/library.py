# -*- coding: utf-8 -*-
"""مكتبة الوسائط الموحدة — مصادر مجانية تُستدعى في أي وقت.

إضافة فوق ما هو قائم (ويكيميديا في scenes.py تفضل دائمًا المصدر الأول).
المصادر هنا تعمل كبديل تلقائي وتتوسع بلا نهاية:
  1) Wikimedia Commons  — صور حقيقية (بلا مفتاح)
  2) Internet Archive   — صور وأفلام تاريخية/طبيعة (بلا مفتاح)
  3) NASA Image Library — فضاء وعلوم، ملكية عامة (بلا مفتاح)
  4) Pixabay (اختياري)  — فيديو/صور بجودة عالية بمفتاح مجاني PIXABAY_KEY

كل النتائج تُخزَّن في ذاكرة state/media_cache.json عشان التنويع
(المصنع ما يرجعش نفس الصورة لسلسلة واحدة).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from . import settings

CACHE = settings.STATE / "media_cache.json"
UA = {"User-Agent": "XDAW-NOVA-factory/1.0 (free knowledge shorts; "
                   "dawshaxlol@gmail.com) requests"}


def _cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(c: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


def _used(query: str) -> set:
    return set(_cache().get(query, []))


def _mark_used(query: str, url: str) -> None:
    c = _cache()
    lst = c.get(query, [])
    if url not in lst:
        lst.append(url)
        c[query] = lst[-40:]
        _save_cache(c)


# ---------------------------------------------------------------- مصادر الصور
def wikimedia_image(query: str) -> str | None:
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "generator": "search",
                    "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 12,
                    "prop": "imageinfo", "iiprop": "url|size|mime",
                    "iiurlwidth": 1280, "format": "json"},
            headers=UA, timeout=20)
        pages = (r.json().get("query") or {}).get("pages") or {}
        cands = []
        for p in pages.values():
            ii = (p.get("imageinfo") or [{}])[0]
            if ii.get("mime") == "image/jpeg" and ii.get("width", 0) >= 900:
                u = ii.get("thumburl") or ii.get("url")
                if u and u not in _used(query):
                    cands.append((ii.get("width", 0) * ii.get("height", 0), u))
        if cands:
            return max(cands)[1]
    except Exception:
        pass
    return None


def archive_image(query: str) -> str | None:
    try:
        r = requests.get(
            "https://archive.org/advancedsearch.php",
            params={"q": f'({query}) AND mediatype:image',
                    "fl[]": "identifier", "rows": 8, "page": 1,
                    "output": "json"}, headers=UA, timeout=20)
        docs = r.json()["response"]["docs"]
        for d in docs:
            ident = d["identifier"]
            f = requests.get(f"https://archive.org/metadata/{ident}",
                             headers=UA, timeout=20).json()
            for fl in f.get("files", []):
                nm = fl.get("name", "")
                if nm.lower().endswith((".jpg", ".jpeg")):
                    url = f"https://archive.org/download/{ident}/{nm}"
                    if url not in _used(query):
                        return url
    except Exception:
        pass
    return None


def nasa_image(query: str) -> str | None:
    try:
        r = requests.get("https://images-api.nasa.gov/search",
                         params={"q": query, "media_type": "image"},
                         headers=UA, timeout=20).json()
        for item in r.get("collection", {}).get("items", []):
            links = item.get("links") or []
            for l in links:
                u = l.get("href", "")
                if u.endswith((".jpg", ".jpeg")) and u not in _used(query):
                    return u
    except Exception:
        pass
    return None


def pixabay_media(query: str, video: bool = False) -> str | None:
    key = settings.get("PIXABAY_KEY", "")
    if not key:
        return None
    try:
        ep = "videos" if video else ""
        r = requests.get(f"https://pixabay.com/api/{ep}/",
                         params={"key": key, "q": query, "per_page": 12,
                                 "safesearch": "true"}, headers=UA,
                         timeout=20).json()
        hits = r.get("hits", [])
        for h in hits:
            if video:
                u = (h.get("videos") or {}).get("medium", {}).get("url") \
                    or (h.get("videos") or {}).get("small", {}).get("url")
            else:
                u = h.get("largeImageURL")
            if u and u not in _used(query):
                return u
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- واجهات عامة
def openverse_image(query: str) -> str | None:
    """Openverse — ملايين الصور الحرة (CC) بلا مفتاح؛ مصدر إضافي مجاني."""
    try:
        r = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "page_size": 12, "mature": "false",
                    "license_type": "all-cc"},
            headers=UA, timeout=20)
        if not r.ok:
            return None
        used = _used(query)
        for it in r.json().get("results") or []:
            u = it.get("url") or ""
            w = it.get("width") or 0
            if not u or u in used or u.lower().endswith(".svg"):
                continue
            if w and w < 900:
                continue
            return u
    except Exception:
        return None
    return None


IMAGE_SOURCES = (wikimedia_image, archive_image, nasa_image, openverse_image)


def find_image(query: str) -> str | None:
    """أول صورة متاحة من المصادر بالترتيب — مع منع التكرار."""
    for src in IMAGE_SOURCES:
        url = src(query)
        if url:
            _mark_used(query, url)
            return url
    return None


def find_video(query: str) -> str | None:
    """فيديو مجاني (أرشيف/Pixabay) — يُستدعى وقت الحاجة للمشاهد المتحركة."""
    for src in (lambda q: pixabay_media(q, video=True),):
        url = src(query)
        if url:
            _mark_used(query, url)
            return url
    try:
        r = requests.get(
            "https://archive.org/advancedsearch.php",
            params={"q": f"({query}) AND mediatype:movies",
                    "fl[]": "identifier", "rows": 6, "page": 1,
                    "output": "json"}, headers=UA, timeout=20)
        for d in r.json()["response"]["docs"]:
            ident = d["identifier"]
            f = requests.get(f"https://archive.org/metadata/{ident}",
                             headers=UA, timeout=20).json()
            for fl in f.get("files", []):
                nm = fl.get("name", "")
                if nm.lower().endswith((".mp4", ".ogv")):
                    url = f"https://archive.org/download/{ident}/{nm}"
                    if url not in _used(query):
                        _mark_used(query, url)
                        return url
    except Exception:
        pass
    return None


def download(url: str, out: Path, timeout: int = 120) -> Path | None:
    try:
        r = requests.get(url, headers=UA, timeout=timeout, stream=True)
        if not r.ok or not r.content:
            return None
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        return out
    except Exception:
        return None
