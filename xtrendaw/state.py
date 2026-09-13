"""الذاكرة الخفيفة — إيه اللي اتنتج، وبصمات ضد التكرار.

مش قاعدة بيانات؛ ملف JSON صغير في state/ (مهمل من git إلا .gitkeep).
الهدف الوحيد دلوقتي: ما ننتجش نفس الحلقة مرتين، ونعرف نختار "التالي".
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import content, settings

STATE_FILE = settings.STATE / "produced.json"


def _read() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"episodes": {}, "fingerprints": []}


def _write(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def is_produced(topic_id: str) -> bool:
    return topic_id in _read()["episodes"]


def fingerprint_seen(topic: dict) -> bool:
    fp = content.fingerprint(topic)
    return fp in _read()["fingerprints"]


def mark_produced(topic: dict, video: str, duration: float) -> None:
    data = _read()
    fp = content.fingerprint(topic)
    data["episodes"][topic["id"]] = {
        "title": topic.get("title_ar", topic["angle"]),
        "fingerprint": fp,
        "video": video,
        "duration": round(duration, 2),
        "at": time.strftime("%Y-%m-%d %H:%M"),
    }
    if fp not in data["fingerprints"]:
        data["fingerprints"].append(fp)
    _write(data)


def produced_ids() -> list[str]:
    return list(_read()["episodes"].keys())


def next_topic(topics: list[dict]) -> dict | None:
    """أول موضوع لسه ما اتنتجش ومش مكرر بالبصمة."""
    seen_fps = set(_read()["fingerprints"])
    for t in topics:
        if is_produced(t["id"]):
            continue
        if content.fingerprint(t) in seen_fps:
            continue
        return t
    return None
