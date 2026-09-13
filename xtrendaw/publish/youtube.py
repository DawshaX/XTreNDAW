"""يوتيوب — OAuth refresh token + رفع Resumable.

تحذير معروف: لو مشروع Google معملش Compliance Audit، الفيديو بيطلع Private.
فالمحوّل بيرجع الرابط أيًا كان، والحالة بتتبين من يوتيوب نفسه.
"""
import requests
from .. import settings

def _token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": settings.YOUTUBE["client_id"],
        "client_secret": settings.YOUTUBE["client_secret"],
        "refresh_token": settings.YOUTUBE["refresh_token"],
        "grant_type": "refresh_token"}, timeout=30)
    return r.json().get("access_token") if r.ok else None

def publish(video_path, title, caption, tags):
    if not settings.has_youtube():
        return None, "no_credentials"
    tok = _token()
    if not tok:
        return None, "refresh_failed"
    meta = {"snippet": {"title": title[:100], "description": caption[:4900],
                        "tags": tags[:15], "categoryId": "27"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                 "X-Upload-Content-Type": "video/mp4",
                 "X-Upload-Content-Length": str(video_path.stat().st_size)},
        json=meta, timeout=60)
    if init.status_code != 200:
        return None, f"init_{init.status_code}"
    up = requests.put(init.headers["Location"],
                      headers={"Content-Length": str(video_path.stat().st_size)},
                      data=open(video_path, "rb"), timeout=900)
    if up.status_code not in (200, 201):
        return None, f"upload_{up.status_code}"
    return f"https://www.youtube.com/watch?v={up.json().get('id','')}", None
