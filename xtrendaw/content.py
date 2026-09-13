"""بنك المحتوى: مواضيع ثنائية اللغة + نبرة (تحذير/فكاهة/راحة).

القالب: hook (تحذير يخطف) + 3 حقائق (التالتة فيها لمسة جنون/نكتة) + outro (راحة/دعاء).
كل موضوع ليه نص عربي (للصوت) وإنجليزي (للقراءة على الشاشة).
التوليد اللامحدود بـLLM مجاني بيضاف كطبقة اختيارية فوق ده.
"""
from __future__ import annotations

import hashlib
import json
import re

from . import settings

TOPICS_PATH = settings.ROOT / "content" / "topics.json"

SEED_TOPICS: list[dict] = [
    {
        "id": "ep1",
        "angle": "جسمك مصنوع من نجوم",
        "title_ar": "جسمك فيه نجوم حقيقية… والدليل هيصدمك!",
        "title_en": "Your body is literally made of stars!",
        "hook_ar": "تحذير رسمي: بعد الحلقة دي مش هتبص لإيدك زي قبل كده أبدًا!",
        "hook_en": "Official warning: after this, you'll never look at your hand the same way again!",
        "facts_ar": [
            "كل ذرة كربون في جسمك اتصنعت جوه قلب نجم ضخم.",
            "الحديد اللي في دمك ما اتكونش غير في آخر لحظات انفجار نجمي.",
            "يعني إنت مش بس في الكون… إنت حرفيًا مصنوع منه. قفلت؟",
        ],
        "facts_en": [
            "Every carbon atom in your body was forged inside a giant star.",
            "The iron in your blood only formed in a star's final explosive moments.",
            "So you're not just in the universe… you're literally made of it. Mic drop.",
        ],
        "outro_ar": "انتو خير ونور من الله. تابع XTreNDAW — الجاية أجنّ!",
        "outro_en": "You are goodness and light. Follow XTreNDAW — the next one is wilder!",
        "tags": "حقائق,علوم,فضاء,XTreNDAW",
    },
    {
        "id": "ep2",
        "angle": "المادة المضادة",
        "title_ar": "أغلى من الماس بمليون مرة… مادة تكلف تريليونات!",
        "title_en": "A million times pricier than diamond!",
        "hook_ar": "تحذير: لو لمست المادة دي… قول على نفسك ومحتويات الكون السلام!",
        "hook_en": "Warning: touch this stuff and say goodbye to yourself and, well, the universe!",
        "facts_ar": [
            "جرام واحد من المادة المضادة يتجاوز 60 تريليون دولار.",
            "كل اللي صنعته البشرية منها ما يملأش ملعقة شاي.",
            "يعني أغلى حاجة في الكون… ومحدش قادر يلمسها. المفارقة قاتلة!",
        ],
        "facts_en": [
            "A single gram of antimatter costs over 60 trillion dollars.",
            "Everything humanity ever made of it wouldn't fill a teaspoon.",
            "So it's the priciest thing in the universe… and nobody can touch it. The irony kills!",
        ],
        "outro_ar": "انتو خير ونور من الله. تابع XTreNDAW — الجاية أجنّ!",
        "outro_en": "You are goodness and light. Follow XTreNDAW — the next one is wilder!",
        "tags": "حقائق,علوم,فيزياء,XTreNDAW",
    },
    {
        "id": "ep3",
        "angle": "سر النوم",
        "title_ar": "مخك بيغسل نفسه وإنت نايم… الحقيقة مرعبة!",
        "title_en": "Your brain washes itself while you sleep!",
        "hook_ar": "تحذير أخير: مخك بيغسل نفسه وإنت نايم… ومتقدرش توقفه!",
        "hook_en": "Final warning: your brain washes itself while you sleep… and you can't stop it!",
        "facts_ar": [
            "أثناء النوم مخك بيقلص حجمه عشان السائل النخاعي يغسله.",
            "الغسيل ده بيشيل البروتينات السامة المسببة للزهايمر.",
            "يعني النوم مش كسل… النوم صيانة مجانية من المصنع!",
        ],
        "facts_en": [
            "While you sleep, your brain shrinks so spinal fluid can wash it.",
            "That wash flushes out the toxic proteins linked to Alzheimer's.",
            "So sleep isn't laziness… it's free factory maintenance!",
        ],
        "outro_ar": "انتو خير ونور من الله. تابع XTreNDAW — الجاية أجنّ!",
        "outro_en": "You are goodness and light. Follow XTreNDAW — the next one is wilder!",
        "tags": "حقائق,علوم,مخ,XTreNDAW",
    },
    {
        "id": "ep4",
        "angle": "ذكاء الأخطبوط",
        "title_ar": "الأخطبوط عنده 3 قلوب و9 أدمغة… مش هزار!",
        "title_en": "An octopus has 3 hearts and 9 brains!",
        "hook_ar": "تحذير: بعد الحلقة دي هتحس إن الأخطبوط أذكى منك… معلش!",
        "hook_en": "Warning: after this, you'll feel the octopus is smarter than you… sorry!",
        "facts_ar": [
            "الأخطبوط عنده 3 قلوب، واتنين منهم بيضخوا للخياشيم بس.",
            "ثلثي خلاياه العصبية في دراعاته — يعني دراعه بيفكر لوحده.",
            "يعني لو قطعوا دراع، الدراع بيكمل شغل كأنه مخ صغير. مرعب ولطيف!",
        ],
        "facts_en": [
            "An octopus has 3 hearts, and two only pump to the gills.",
            "Two-thirds of its neurons are in its arms — each arm thinks on its own.",
            "So a severed arm keeps working like a tiny brain. Creepy and cute!",
        ],
        "tags": "حقائق,بحر,ذكاء,XTreNDAW",
    },
    {
        "id": "ep5",
        "angle": "الثقوب السوداء",
        "title_ar": "الثقب الأسود بيمسح الزمن… والدليل هيخليك تدوخ!",
        "title_en": "A black hole literally bends time!",
        "hook_ar": "تحذير أخير: لو قربت من ثقب أسود، ساعتك هتمشي أبطأ من صحابك!",
        "hook_en": "Final warning: near a black hole, your clock ticks slower than your friends'!",
        "facts_ar": [
            "الجاذبية هناك قوية لدرجة إن الزمن نفسه بيتمدد.",
            "ساعة قرب ثقب أسود ممكن تساوي سنين على الأرض.",
            "يعني السفر للمستقبل ممكن نظريًا… بس من غير تذكرة رجوع!",
        ],
        "facts_en": [
            "Gravity there is so strong that time itself stretches.",
            "One hour near a black hole can equal years on Earth.",
            "So traveling to the future is theoretically possible… just no return ticket!",
        ],
        "tags": "حقائق,فضاء,فيزياء,XTreNDAW",
    },
    {
        "id": "ep6",
        "angle": "العسل لا يفسد",
        "title_ar": "لقى عسل في مقبرة فرعونية… ولسه يتاكل!",
        "title_en": "Honey found in a pharaoh's tomb… still edible!",
        "hook_ar": "تحذير: الأكل الوحيد اللي بيعيش آلاف السنين من غير ثلاجة… خمن!",
        "hook_en": "Warning: the only food that lasts thousands of years without a fridge… guess!",
        "facts_ar": [
            "العسل مفيهوش مية وحمضيته قليلة، فالبكتيريا مش بتقدر تعيش فيه.",
            "علماء لقوا عسل في مقابر مصرية عمره 3000 سنة ولسه صالح.",
            "يعنى الفراعنة خزنوا أكلهم أحسن مننا واحنا عندنا ثلاجات!",
        ],
        "facts_en": [
            "Honey has almost no water and low acidity, so bacteria can't survive in it.",
            "Scientists found 3,000-year-old honey in Egyptian tombs, still edible.",
            "So the pharaohs stored food better than us — with fridges!",
        ],
        "tags": "حقائق,تاريخ,طعام,XTreNDAW",
    },
    {
        "id": "ep7",
        "angle": "سرعة الضوء",
        "title_ar": "لو ركبت شعاع ضوء… هتشوف الكون بشكل مجنون!",
        "title_en": "Ride a light beam and the universe goes wild!",
        "hook_ar": "تحذير: مفيش حاجة في الكون بتكسر حاجز الضوء… ولا حتى أفكارك!",
        "hook_en": "Warning: nothing in the universe breaks the light barrier… not even your thoughts!",
        "facts_ar": [
            "الضوء بيمشي 300 ألف كيلومتر في الثانية الواحدة.",
            "يعني ضوء الشمس اللي بيوصلك دلوقتي طلع منها من 8 دقايق.",
            "يعني إنت مش بتشف الشمس دلوقتي… إنت بتشف الماضي!",
        ],
        "facts_en": [
            "Light travels 300,000 kilometers every single second.",
            "So the sunlight reaching you now left the sun 8 minutes ago.",
            "So you're not seeing the sun now… you're seeing the past!",
        ],
        "tags": "حقائق,فضاء,ضوء,XTreNDAW",
    },
]

LABELS_AR = ["الحقيقة الأولى:", "الحقيقة الثانية:", "والحقيقة الثالثة:"]
LABELS_EN = ["Fact one:", "Fact two:", "And fact three:"]


def fingerprint(topic: dict) -> str:
    raw = "|".join([
        re.sub(r"\s+", " ", (topic.get("title_ar") or topic["angle"])).strip(),
        *[re.sub(r"\s+", " ", f).strip() for f in (topic.get("facts_ar") or [])],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def compose_script(topic: dict, lang: str = "ar") -> list[dict]:
    """موضوع → مقاطع مرتبة hook/fact1..3/outro بلغة محددة."""
    labels = LABELS_EN if lang == "en" else LABELS_AR
    hook = topic.get(f"hook_{lang}") or topic.get("hook_ar", "")
    facts = topic.get(f"facts_{lang}") or topic.get("facts_ar") or []
    outro = settings.BRAND["outro_en" if lang == "en" else "outro_ar"]

    segs = [{"seg": "hook", "text": hook.strip()}]
    for i, fact in enumerate(facts[:3]):
        label = labels[i] if i < len(labels) else f"Fact {i + 1}:" if lang == "en" else f"الحقيقة {i + 1}:"
        segs.append({"seg": f"fact{i + 1}", "text": f"{label} {fact.strip()}"})
    segs.append({"seg": "outro", "text": outro.strip()})
    return segs


def english_lines(topic: dict) -> list[str]:
    """سطر إنجليزي موازٍ لكل مقطع (نفس ترتيب compose_script) — للقراءة."""
    segs = compose_script(topic, "en")
    return [s["text"] for s in segs]


def make_caption(topic: dict) -> str:
    tags = " ".join(f"#{t.strip()}" for t in topic.get("tags", "").split(",") if t.strip())
    return f"{topic['title_ar']}\n{topic.get('title_en','')}\n{tags}"


def scene_queries(topic: dict) -> list[str]:
    return [t.strip() for t in topic.get("tags", "").split(",") if t.strip()][:4]


def load_topics() -> list[dict]:
    """المواضيع من content/topics.json — بتتزرع بالـSEED أول مرة."""
    if TOPICS_PATH.exists():
        try:
            return json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    save_topics(SEED_TOPICS)
    return [dict(t) for t in SEED_TOPICS]


def save_topics(topics: list[dict]) -> None:
    TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOPICS_PATH.write_text(
        json.dumps(topics, ensure_ascii=False, indent=1), encoding="utf-8"
    )
