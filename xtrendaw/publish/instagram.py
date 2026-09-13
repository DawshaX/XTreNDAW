"""إنستجرام Reels — حساب Business + video_url عام + container/publish.

بيستخدم رابط Releases العام (مطلوب: ≤90s وH.264+AAC — مواصفاتنا بتضمنها).
"""
import time
import requests
from .. import settings

def publish(video_url, title, caption, tags):
    if not settings.has_instagram():
        return None, "no_credentials"
    tok = settings.INSTAGRAM["token"]
    uid = settings.INSTAGRAM["user_id"]
    c = requests.post(f"https://graph.facebook.com/v19.0/{uid}/media",
                      data={"media_type": "REELS", "video_url": video_url,
                            "caption": f"{title}\n{caption}"[:2200],
                            "share_to_feed": "true", "access_token": tok}, timeout=120)
    if not c.ok:
        return None, f"ig_container_{c.status_code}:{c.text[:120]}"
    cid = c.json()["id"]
    for _ in range(30):
        st = requests.get(f"https://graph.facebook.com/v19.0/{cid}",
                          params={"fields": "status_code", "access_token": tok}, timeout=30)
        code = st.json().get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            return None, "ig_processing_error"
        time.sleep(4)
    p = requests.post(f"https://graph.facebook.com/v19.0/{uid}/media_publish",
                      data={"creation_id": cid, "access_token": tok}, timeout=120)
    if not p.ok:
        return None, f"ig_publish_{p.status_code}:{p.text[:120]}"
    return f"https://www.instagram.com/p/{p.json().get('id','')}", None
