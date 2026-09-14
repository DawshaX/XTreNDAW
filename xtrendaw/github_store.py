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
import re
import shutil
import tempfile
import time
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


VAULT_TAG = "vault"


def _ensure_tag(tok: str, tag: str, name: str, body: str = "",
                latest: bool = False) -> int:
    r = requests.get(f"{API}/repos/{_repo()}/releases/tags/{tag}",
                     headers=_headers(tok), timeout=30)
    if r.status_code == 200:
        return r.json()["id"]
    r = requests.post(f"{API}/repos/{_repo()}/releases", headers=_headers(tok),
                      json={"tag_name": tag, "name": name, "body": body,
                            "make_latest": "true" if latest else "false"},
                      timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def ensure_release(tok: str) -> int:
    """release القناة العامة (الحلقات المنشورة)."""
    return _ensure_tag(tok, TAG, "XTreNDAW — الحلقات",
                       "فيديوهات وأغلفة الحلقات (روابط عامة).", latest=True)


def _vault_id(tok: str) -> int:
    """release المخزن: حلقات جاهزة تستنى موعد نشرها."""
    return _ensure_tag(tok, VAULT_TAG, "NOVA Vault — مخزون جاهز للنشر",
                       "مخزون داخلي؛ بيتفرج منه على القناة في مواعيد الذروة.")


def _delete_same_name(tok: str, release_id: int, name: str) -> None:
    for page in range(1, 8):
        r = requests.get(f"{API}/repos/{_repo()}/releases/{release_id}/assets",
                         params={"per_page": 100, "page": page},
                         headers=_headers(tok), timeout=30)
        if not r.ok or not r.json():
            return
        for a in r.json():
            if a["name"] == name:
                requests.delete(
                    f"{API}/repos/{_repo()}/releases/assets/{a['id']}",
                    headers=_headers(tok), timeout=30)


def upload_file(tok: str, release_id: int, path: Path, name: str | None = None) -> str:
    """يرفع ملف ويرجع رابطه العام."""
    name = name or path.name
    _delete_same_name(tok, release_id, name)
    ctype = {
        ".mp4": "video/mp4", ".png": "image/png", ".jpg": "image/jpeg",
    }.get(path.suffix, "application/octet-stream")
    with open(path, "rb") as f:
        r = requests.post(
            f"{UPLOADS}/repos/{_repo()}/releases/{release_id}/assets",
            params={"name": name},
            headers={**_headers(tok), "Content-Type": ctype,
                     "Content-Length": str(path.stat().st_size)},
            data=f, timeout=900,
        )
    if r.status_code == 422:  # مكرر لسه موجود — امسح صراحة واعد
        import time as _t
        _delete_same_name(tok, release_id, name)
        _t.sleep(2)
        with open(path, "rb") as f2:
            r = requests.post(
                f"{UPLOADS}/repos/{_repo()}/releases/{release_id}/assets",
                params={"name": name},
                headers={**_headers(tok), "Content-Type": ctype,
                         "Content-Length": str(path.stat().st_size)},
                data=f2, timeout=900)
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


def upload_to_vault(video: Path, cover: Path | None, meta: dict) -> dict:
    """يخزّن حلقة جاهزة في الـvault باسم q<timestamp> — تستنى موعدها."""
    tok = _token()
    if not tok:
        raise RuntimeError("مفيش توكن GitHub — ما أقدرش أخزّن")
    vid = _vault_id(tok)
    ts = int(time.time())
    tmp = Path(tempfile.mkdtemp())
    urls: dict[str, str] = {}
    v = tmp / f"q{ts}.mp4"
    shutil.copy(video, v)
    urls["video"] = upload_file(tok, vid, v)
    if cover and Path(cover).exists():
        c = tmp / f"q{ts}.png"
        shutil.copy(cover, c)
        urls["cover"] = upload_file(tok, vid, c)
    m = tmp / f"q{ts}.json"
    m.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    upload_file(tok, vid, m)
    shutil.rmtree(tmp, ignore_errors=True)
    return urls


def _assets(tok: str, rel: int) -> list[dict]:
    r = requests.get(f"{API}/repos/{_repo()}/releases/{rel}/assets",
                     headers=_headers(tok), timeout=30)
    return r.json() if r.ok else []


def promote_next() -> dict | None:
    """يفرج أقدم حلقة من الـvault على القناة العامة ويرجع بياناتها."""
    tok = _token()
    if not tok:
        return None
    vrel = _vault_id(tok)
    erel = ensure_release(tok)
    vids = sorted((a for a in _assets(tok, vrel)
                   if re.match(r"q\d+\.mp4$", a["name"])),
                  key=lambda a: a["name"])
    if not vids:
        return None
    ts = vids[0]["name"][1:-4]
    all_v = _assets(tok, vrel)
    cover_a = next((a for a in all_v if a["name"] == f"q{ts}.png"), None)
    meta_a = next((a for a in all_v if a["name"] == f"q{ts}.json"), None)
    meta = {}
    tmp = Path(tempfile.mkdtemp())

    def _dl(asset: dict, dst: Path) -> None:
        r = requests.get(asset["browser_download_url"], timeout=600)
        r.raise_for_status()
        dst.write_bytes(r.content)

    local_video = tmp / "video.mp4"
    _dl(vids[0], local_video)
    local_cover: Path | None = None
    if cover_a:
        local_cover = tmp / "cover.png"
        _dl(cover_a, local_cover)
    if meta_a:
        try:
            meta = json.loads(requests.get(meta_a["browser_download_url"],
                                           timeout=60).text)
        except Exception:
            meta = {}

    # الرقم الجاي على القناة
    nums = [int(re.match(r"ep(\d+)\.mp4$", a["name"]).group(1))
            for a in _assets(tok, erel) if re.match(r"ep\d+\.mp4$", a["name"])]
    n = max(nums, default=0) + 1
    urls = {"video": upload_file(tok, erel, local_video, f"ep{n}.mp4")}
    if local_cover:
        urls["cover"] = upload_file(tok, erel, local_cover, f"ep{n}-cover.png")

    for a in (vids[0], cover_a, meta_a):
        if a:
            requests.delete(f"{API}/repos/{_repo()}/releases/assets/{a['id']}",
                            headers=_headers(tok), timeout=30)
    return {"id": f"ep{n}", "urls": urls, "meta": meta,
            "local_video": local_video, "tmp": tmp}
