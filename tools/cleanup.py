# -*- coding: utf-8 -*-
"""حذف نسخة مكررة: يوتيوب + تيليجرام."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

YT_ID = os.environ.get("CLEAN_YT", "")
TG_ID = os.environ.get("CLEAN_TG", "")

if YT_ID:
    from xtrendaw.publish import youtube
    ok = youtube.delete(YT_ID)
    print("YT delete:", ok)

if TG_ID:
    import requests
    r = requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/deleteMessage",
        json={"chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
              "message_id": int(TG_ID)}, timeout=30)
    print("TG delete:", r.status_code, r.text[:120])
