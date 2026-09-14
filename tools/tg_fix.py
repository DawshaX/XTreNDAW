# -*- coding: utf-8 -*-
"""تصحيح رسالة قناة تيليجرام: edit أو delete."""
import os
import sys

import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
ACTION = os.environ.get("TG_ACTION", "edit")
MSG_ID = int(os.environ.get("TG_MESSAGE_ID", "0"))
TEXT = os.environ.get("TG_TEXT", "")

API = f"https://api.telegram.org/bot{TOKEN}"

if ACTION == "delete":
    r = requests.post(f"{API}/deleteMessage",
                      json={"chat_id": CHAT, "message_id": MSG_ID}, timeout=30)
else:
    r = requests.post(f"{API}/editMessageCaption",
                      json={"chat_id": CHAT, "message_id": MSG_ID,
                            "caption": TEXT}, timeout=30)
print(ACTION, r.status_code, r.text[:200])
sys.exit(0 if r.ok else 1)
