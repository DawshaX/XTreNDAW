"""فيسبوك Reels — page token + file_url (الرابط العام من Releases)."""
import requests
from .. import settings

def publish(video_url, title, caption, tags):
    if not settings.has_facebook():
        return None, "no_credentials"
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{settings.FACEBOOK['page_id']}/videos",
        data={"file_url": video_url,
              "description": f"{title}\n{caption}"},
        params={"access_token": settings.FACEBOOK["token"]}, timeout=120)
    if not r.ok:
        return None, f"fb_{r.status_code}:{r.text[:120]}"
    d = r.json()
    vid = d.get("id") or d.get("video_id")
    return f"https://www.facebook.com/{settings.FACEBOOK['page_id']}/videos/{vid}", None
