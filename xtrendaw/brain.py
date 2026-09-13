"""المخ — توليد مواضيع جديدة لما المخزون يقرّب يخلص (ما ينفدش أبدًا).

طبقتان:
1) LLM مجاني (Groq) لو فيه مفتاح → مواضيع لا نهائية ثنائية اللغة.
2) احتياطي قوالب جاهزة (بلا مفتاح) عشان المصنع ما يقفش أبدًا.
النتيجة دايمًا موضوع جديد ببصمة ما اتكررتش (state بيمنع التكرار).
"""
from __future__ import annotations

import json

import requests

from . import content, settings

# احتياطي بلا مفتاح — مواضيع إضافية جاهزة
FALLBACK_POOL: list[dict] = [
    {
        "angle": "الموز مش فاكهة",
        "title_ar": "الموز مش فاكهة… وشجرة الموز مش شجرة!",
        "title_en": "Bananas aren't fruit, and banana trees aren't trees!",
        "hook_ar": "تحذير: كل اللي تعرفه عن الموز غلط من أوله لآخره!",
        "hook_en": "Warning: everything you know about bananas is wrong, top to bottom!",
        "facts_ar": [
            "الموز بيصنف علميًا من التوت، مش الفواكه.",
            "شجرة الموز مش شجرة أصلًا — دي أكبر عشبة معمرة في العالم.",
            "يعني إنت بتاكل توتة ضخمة من عشبة عملاقة. استمتع!",
        ],
        "facts_en": [
            "Botanically, bananas are classified as berries, not fruits.",
            "A banana tree isn't a tree at all — it's the world's largest herb.",
            "So you're eating a giant berry from a massive herb. Enjoy!",
        ],
        "tags": "حقائق,نبات,طعام,XTreNDAW",
    },
    {
        "angle": "المريخ أزرق",
        "title_ar": "غروب الشمس على المريخ أزرق… مش أحمر!",
        "title_en": "Sunsets on Mars are blue, not red!",
        "hook_ar": "تحذير: لو سافرت المريخ، الغروب هيلخبط كل حساباتك!",
        "hook_en": "Warning: on Mars, the sunset will break all your expectations!",
        "facts_ar": [
            "الغبار الدقيق في جو المريخ بيشتت الضوء الأحمر ويسيب الأزرق.",
            "فعند الغروب بتشوف هالة زرقا حوالين الشمس.",
            "يعني الكوكب الأحمر بيغروب بالأزرق… المفارقة حلوة!",
        ],
        "facts_en": [
            "Fine dust in Mars' air scatters red light and lets blue through.",
            "So at sunset you see a blue halo around the sun.",
            "So the red planet sets in blue… what a twist!",
        ],
        "tags": "حقائق,فضاء,مريخ,XTreNDAW",
    },
    {
        "angle": "القلب بيض ضوء",
        "title_ar": "قلبك بيض ضوء كفاية يشغل مصباح… بجد!",
        "title_en": "Your heart powers a small light bulb, seriously!",
        "hook_ar": "تحذير: جوه صدرك مولد كهرباء شغال من أول يوم!",
        "hook_en": "Warning: inside your chest there's a power plant running since day one!",
        "facts_ar": [
            "القلب بيضخ طاقة يومية تكفي نظريًا لإضاءة لمبة صغيرة.",
            "بيدق حوالي 100 ألف مرة في اليوم من غير ما ياخد إجازة.",
            "يعني عندك موتور شغال 24 ساعة ومش بيشتكي… اتعلم منه!",
        ],
        "facts_en": [
            "The heart's daily output could theoretically light a small bulb.",
            "It beats about 100,000 times a day without ever taking a break.",
            "So you own a 24/7 engine that never complains… learn from it!",
        ],
        "tags": "حقائق,جسم,صحة,XTreNDAW",
    },
]


def _llm_topic() -> dict | None:
    if not settings.has_llm():
        return None
    prompt = (
        "اعمل موضوع فيديو حقائق قصير بالعربي والإنجليزي. رجّع JSON فقط بهذه المفاتيح: "
        "angle, title_ar, title_en, hook_ar, hook_en, facts_ar(3), facts_en(3), tags. "
        "النبرة: تحذير لعب في الـhook، نكتة في الحقيقة التالتة، ختام مريح."
    )
    try:
        r = requests.post(
            f"{settings.LLM['base']}/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM['key']}"},
            json={"model": settings.LLM["model"],
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.9},
            timeout=60,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        text = text[text.find("{"): text.rfind("}") + 1]
        t = json.loads(text)
        if t.get("hook_ar") and t.get("facts_ar"):
            t.setdefault("id", f"auto")
            return t
    except Exception:
        return None
    return None


def generate(topics: list[dict]) -> dict | None:
    """موضوع جديد مش مكرر بالبصمة، وإلا None."""
    seen = {content.fingerprint(t) for t in topics}

    t = _llm_topic()
    if t and content.fingerprint(t) not in seen:
        return t

    for cand in FALLBACK_POOL:
        if content.fingerprint(cand) not in seen:
            return dict(cand)
    return None
