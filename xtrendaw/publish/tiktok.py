# -*- coding: utf-8 -*-
"""تيك توك — Content Posting API (Direct Post برفع مباشر، بلا دومينات)."""
import json
import time
from pathlib import Path

import requests

from .. import settings

API = "https://open.tiktokapis.com/v2"


def _tok() -> str:
    return settings.TIKTOK.get("access_token") or ""


def refresh_token() -> bool:
    rt = settings.TIKTOK.get("refresh_token")
    if not rt or not settings.TIKTOK.get("client_key"):
        return False
    try:
        r = requests.post(f"{API}/oauth/token/", data={
            "client_key": settings.TIKTOK["client_key"],
            "client_secret": settings.TIKTOK["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": rt}, timeout=30)
        d = r.json().get("data") or {}
        if d.get("access_token"):
            from .. import state
            state.set_tiktok_tokens(d["access_token"],
                                    d.get("refresh_token", rt))
            return True
    except Exception:
        pass
    return False


def exchange_code(code: str, redirect_uri: str):
    r = requests.post(f"{API}/oauth/token/", data={
        "client_key": settings.TIKTOK["client_key"],
        "client_secret": settings.TIKTOK["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri}, timeout=30)
    d = r.json()
    data = d.get("data") or {}
    if data.get("access_token"):
        from .. import state
        state.set_tiktok_tokens(data["access_token"], data.get("refresh_token", ""))
        return True, data.get("open_id", "")
    return False, str(d)[:140]


def _ensure_fresh() -> None:
    import time as _t
    from .. import state
    f = state.TIKTOK_TOKEN_FILE
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return
    if _t.time() > float(d.get("expires_at", 0)):
        refresh_token()


def publish(video, title, caption, tags):
    if not settings.has_tiktok():
        return None, "no_credentials"
    _ensure_fresh()
    path = Path(video)
    size = path.stat().st_size
    text = (title + "\n\n" + caption)[:2200]
    try:
        r = requests.post(f"{API}/post/publish/video/init/",
                          headers={"Authorization": f"Bearer {_tok()}",
                                   "Content-Type": "application/json; charset=UTF-8"},
                          json={"post_info": {"title": text,
                                              "privacy_level": settings.TIKTOK_PRIVACY,
                                              "disable_comment": False,
                                              "disable_duet": False,
                                              "disable_stitch": False},
                                "source_info": {"source": "FILE_UPLOAD",
                                                "video_size": size,
                                                "chunk_size": size,
                                                "total_chunk_count": 1}},
                          timeout=60)
        d = r.json().get("data") or {}
        up, pid = d.get("upload_url"), d.get("publish_id")
        if not up:
            return None, f"tt_init:{r.text[:140]}"
        u = requests.put(up, data=path.read_bytes(),
                         headers={"Content-Type": "video/mp4",
                                  "Content-Length": str(size)}, timeout=600)
        if u.status_code not in (200, 201, 204):
            return None, f"tt_upload:{u.status_code}"
        for _ in range(40):
            st = requests.get(f"{API}/post/publish/status/",
                              params={"publish_id": pid},
                              headers={"Authorization": f"Bearer {_tok()}"},
                              timeout=30).json()
            status = (st.get("data") or {}).get("status")
            if status == "PUBLISH_COMPLETE":
                return f"https://www.tiktok.com (publish {pid})", None
            if status in ("FAILED", "REVIEW_FAILED"):
                return None, f"tt_{status}:{str(st)[:100]}"
            time.sleep(5)
        return f"tt_pending:{pid}", None
    except Exception as e:
        return None, f"tt_exception:{str(e)[:80]}"
