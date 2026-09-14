"""إنستجرام Reels — Instagram API (تسجيل دخول إنستجرام، بلا صفحة فيسبوك).

الحساب: @xdaw_nova — MEDIA_CREATOR.
الرابط العام من Releases هو مصدر الفيديو (≤90s، H.264+AAC — مواصفاتنا بتضمنها).
"""
import time

import requests

from .. import settings

API = "https://graph.instagram.com/v21.0"


def _tok() -> str:
    return settings.INSTAGRAM["token"] or ""


def _uid() -> str:
    return settings.INSTAGRAM["user_id"] or ""


def refresh_token() -> bool:
    """تجديد التوكن الطويل (صالح 60 يوم) — بيتنادى من الدورة والبوت."""
    tok = _tok()
    if not tok:
        return False
    try:
        r = requests.get(f"{API}/refresh_access_token",
                         params={"grant_type": "ig_refresh_token",
                                 "access_token": tok}, timeout=30)
        if r.ok and r.json().get("access_token"):
            from .. import state
            state.set_ig_token(r.json()["access_token"])
            return True
    except Exception:
        pass
    return False


def publish(video_url, title, caption, tags):
    if not settings.has_instagram():
        return None, "no_credentials"
    tok, uid = _tok(), _uid()
    text = f"{title}\n\n{caption}"[:2100]
    try:
        c = requests.post(f"{API}/{uid}/media",
                          data={"media_type": "REELS", "video_url": video_url,
                                "caption": text, "share_to_feed": "true",
                                "access_token": tok}, timeout=120)
        if not c.ok:
            return None, f"ig_container_{c.status_code}:{c.text[:120]}"
        cid = c.json()["id"]

        for _ in range(40):
            st = requests.get(f"{API}/{cid}",
                              params={"fields": "status_code",
                                      "access_token": tok}, timeout=30).json()
            code = st.get("status_code")
            if code == "FINISHED":
                break
            if code == "ERROR":
                return None, "ig_processing_error"
            time.sleep(5)
        else:
            return None, "ig_timeout"

        p = requests.post(f"{API}/{uid}/media_publish",
                          data={"creation_id": cid, "access_token": tok},
                          timeout=120)
        if not p.ok:
            return None, f"ig_publish_{p.status_code}:{p.text[:120]}"
        mid = p.json().get("id", "")
        try:
            per = requests.get(f"{API}/{mid}",
                               params={"fields": "permalink",
                                       "access_token": tok},
                               timeout=30).json().get("permalink")
        except Exception:
            per = None
        return per or f"https://www.instagram.com/reel/{mid}/", None
    except Exception as e:
        return None, f"ig_exception:{str(e)[:80]}"
