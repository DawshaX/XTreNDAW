"""قناة مشاركة المشاهدين — أي حد حر يطلب حلقة.

المشاهد يفتح Issue على الريپو عليها ليبل "مشاهد" → المصنع يقرأ الطلبات،
ينتج الأكثر إلحاحًا بالأولوية القصوى، ويرد على صاحب الطلب ويقفله بلينك الحلقة.
"""
from __future__ import annotations

import re

import requests as _rq

from . import github_store

API = "https://api.github.com"
LABEL = "مشاهد"


def _repo() -> str:
    return github_store._repo()


def pending() -> list[dict]:
    """الطلبات المفتوحة مرتّبة بالأقدم (الأقدم = استنى أكتر)."""
    tok = github_store._token()
    if not tok:
        return []
    try:
        r = _rq.get(f"{API}/repos/{_repo()}/issues",
                    params={"state": "open", "labels": LABEL, "per_page": 20},
                    headers=github_store._headers(tok), timeout=30)
        if not r.ok:
            return []
        return [{"issue": i["number"], "title": i["title"], "body": i.get("body") or ""}
                for i in r.json()]
    except Exception:
        return []


def topic_from(req: dict) -> dict:
    """طلب مشاهد → موضوع بنفس روح نوفا (بلا اختلاق وقائع)."""
    want = re.sub(r"\s+", " ", req["title"]).strip()[:60]
    return {
        "angle": f"طلب:{req['issue']}",
        "title_ar": f"إنتو طلبتوها: «{want}»… ونوفا لبّت النداء!",
        "title_en": f"You asked for '{want}'… NOVA answered!",
        "hook_ar": f"تحذير: دي مش حلقة عادية — دي طلب من مشاهد حر، ونوفا بتسمع!",
        "hook_en": "Warning: not a normal episode — a free viewer asked, NOVA listens!",
        "facts_ar": [
            f"الطلب جه مباشرة من قناة المشاركة: «{want}».",
            "نوفا بتقرأ كل الطلبات وبتختار الأكتر مطلبًا — صوتك مسموع بجد.",
            "وإنت كمان حر… باب الطلبات مفتحت تحت أي فيديو وعلى الصفحة.",
        ],
        "facts_en": [
            f"The request came straight from our participation channel: '{want}'.",
            "NOVA reads every request and picks the most wanted — your voice matters.",
            "You're free too… the request door is open under every video.",
        ],
        "tags": "طلب_مشاهد,نوفا_تسمع,XTreNDAW",
        "_issue": req["issue"],
    }


def answer_and_close(issue: int, video_url: str) -> None:
    """رد ودود على صاحب الطلب + قفل الـIssue باللينك."""
    tok = github_store._token()
    if not tok:
        return
    try:
        _rq.post(f"{API}/repos/{_repo()}/issues/{issue}/comments",
                 json={"body": f"🎬 طلبك اتنفذ! الحلقة نزلت: {video_url}\n"
                               "— نوفا 🖤 إنت حر، اطلب تاني في أي وقت."},
                 headers=github_store._headers(tok), timeout=30)
        _rq.patch(f"{API}/repos/{_repo()}/issues/{issue}",
                  json={"state": "closed"},
                  headers=github_store._headers(tok), timeout=30)
    except Exception:
        pass
