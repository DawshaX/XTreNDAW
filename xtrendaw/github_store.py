"""تخزين النواتج على GitHub Releases — الفيديوهات والأغلفة تبقى هناك 100%.

ليه Releases مش git:
- الميديا ممنوعة تدخل git (قاعدة المستودع) عشان ما يتخنش.
- Releases بتدي روابط **عامة** ثابتة (مطلوبة لإنستجرام بعدين) من غير ما
  تاريخ git يتخن.

بيتعمل idempotent: لو نفس الاسم موجود بيتحدث بدل ما يكرر.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from . import settings

TAG = "episodes"
API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"


def _repo() -> str:
    return settings.get("GITHUB_REPOSITORY") or "DawshaX/XTreNDAW"


def _token() -> str:
    tok = settings.get("GITHUB_TOKEN") or settings.get("GH_TOKEN")
    if tok:
        return tok
    # محليًا: من ~/.git-credentials (مش بيتحفظ في الشغل)
    cred = Path.home() / ".git-credentials"
    if cred.exists():
        for line in cred.read_text().splitlines():
            if "x-access-token:" in line and "@github.com" in line:
                return line.split("x-access-token:", 1)[1].split("@", 1)[0]
    return ""


def _headers(tok: str) -> dict:
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
    }


def ensure_release(tok: str) -> int:
    """يرجع id.release باسم TAG — بينشئه لو مش موجود."""
    r = requests.get(f"{API}/repos/{_repo()}/releases/tags/{TAG}",
                     headers=_headers(tok), timeout=30)
    if r.status_code == 200:
        return r.json()["id"]
    r = requests.post(f"{API}/repos/{_repo()}/releases", headers=_headers(tok),
                      json={"tag_name": TAG, "name": "XTreNDAW — الحلقات",
                            "body": "فيديوهات وأغلفة الحلقات (روابط عامة).",
                            "make_latest": "true"}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def _delete_same_name(tok: str, release_id: int, name: str) -> None:
    r = requests.get(f"{API}/repos/{_repo()}/releases/{release_id}/assets",
                     headers=_headers(tok), timeout=30)
    if not r.ok:
        return
    for a in r.json():
        if a["name"] == name:
            requests.delete(f"{API}/repos/{_repo()}/releases/assets/{a['id']}",
                            headers=_headers(tok), timeout=30)


def upload_file(tok: str, release_id: int, path: Path) -> str:
    """يرفع ملف ويرجع رابطه العام."""
    _delete_same_name(tok, release_id, path.name)
    ctype = {
        ".mp4": "video/mp4", ".png": "image/png", ".jpg": "image/jpeg",
    }.get(path.suffix, "application/octet-stream")
    with open(path, "rb") as f:
        r = requests.post(
            f"{UPLOADS}/repos/{_repo()}/releases/{release_id}/assets",
            params={"name": path.name},
            headers={**_headers(tok), "Content-Type": ctype,
                     "Content-Length": str(path.stat().st_size)},
            data=f, timeout=900,
        )
    r.raise_for_status()
    return r.json().get(
        "browser_download_url",
        f"https://github.com/{_repo()}/releases/download/{TAG}/{path.name}",
    )


def upload_episode(video: Path, cover: Path | None = None) -> dict:
    """يرفع الفيديو (+الغلاف) ويرجع {video: url, cover: url}."""
    tok = _token()
    if not tok:
        raise RuntimeError("مفيش توكن GitHub — ما أقدرش أرفع النواتج")
    release_id = ensure_release(tok)
    urls = {"video": upload_file(tok, release_id, video)}
    if cover and Path(cover).exists():
        urls["cover"] = upload_file(tok, release_id, Path(cover))
    return urls


def available() -> bool:
    return bool(_token())
