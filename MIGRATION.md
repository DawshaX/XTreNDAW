# مانيِفست النقل — ناخد من المستودع القديم إيه، وما ناخدش إيه

> الهدف: **بناء جديد على نضافة**، والمستودعات القديمة تفضل زي ما هي (مصدر قطع غيار، مش أساس).
> المستودعان: `DawshaX/daousha` (767.8 MB) · `DawshaX/dawshax.github.io` (7 KB)

## ✅ ناخده (قطع صغيرة، مجرّبة، ومش محتاجة إعادة اختراع)

| منين | إيه | ليه ناخده |
|---|---|---|
| `nova/tts.py` | فكرة **التوقيت كلمة-بكلمة** من edge-tts | دي أصعب حاجة في المزامنة، وحلّها موجود |
| `nova/scenes.py` + `nova/flux.py` | توليد خلفيات برمجيًا (بلا مفتاح) + جلب Pexels | يضمن إن الإنتاج **مايقفش** لو مفيش مفاتيح |
| `nova/captions.py` | منطق الكابتشنز الكينيتيك | شغال، نعيد كتابته أنضف |
| `nova/publish/youtube.py` | بروتوكول **resumable upload** + ضبط الغلاف | الجزء الصح في الكود القديم |
| `nova/publish/instagram.py` + `facebook.py` | نموذج الـcontainer/publish الخاص بـMeta | مطلوب حرفيًا من الـAPI |
| `content/fact_bank.json` (10 KB) | بنك حقائق جاهز | وقود أولي للمصنع |
| `assets/brand/*` + `assets/fonts/Tajawal-*.ttf` | اللوجو/القناع/الخط العربي | لو قررنا نستخدم الهوية (قرارك) |
| `docs/setup-keys.md` | شرح استخراج المفاتيح | توفير وقت عليك |
| `.github/workflows/keepalive.yml` | فكرة الـkeepalive | **ضروري** — الجدولة بتتعطل بصمت بعد 60 يوم |
| `dashboard/status.html` | فكرة لوحة المتابعة | نبنيها أنضف |

## ❌ ما ناخدوش (ومع السبب المقيس)

| إيه | ليه لأ |
|---|---|
| `content/topics_archive_part1..4.json` (78.5 MB) | أرشيف ضخم داخل git — سبب رئيسي في الـ768 MB |
| `docs/episode*/…mp4` و`*.wav` و`*.png` | ميديا جوه git. فيديوهات 65 MB كانت هترفض من إنستجرام (حدّه 100 MB و≤90 ثانية) |
| `server/` (TypeScript + drizzle + vite) | طبقة كاملة مش مستخدمة من المحرك — وزن بلا فايدة |
| `client/` (React components) | نفس السبب — نبني غرفة تحكم أخف لو احتجنا |
| الـdefaults المكتوبة جوه `settings.py` | `FACEBOOK_PAGE_ID` و`TELEGRAM_CHAT_ID` مكتوبين في كود **عام** = تسريب |
| `NOVA_DAILY_CAP=24` / `NOVA_PLATFORM_GAP_H=1` | مستحيل على يوتيوب: الرفع 1600 وحدة من 10,000/يوم → ≈6/يوم |
| `nova.yml` بحلقة الـself-dispatch (`sleep 1500`) | بيحرق runner بالراحة؛ cron عادي + keepalive أنضف |
| مسار اللغة الإنجليزية في `run_cycle.py` | **بايظ**: `groups`/`groups_en` معرّفين جوه `if lang == "ar":` وبيتستخدموا برّاها → `NameError` |

## 🔒 قواعد المشروع الجديد (من أول commit)
1. مفيش سر في الكود — GitHub Secrets فقط.
2. مفيش ميديا في git — Artifacts/Releases.
3. كل وحدة ليها اختبار ينفذ الكود الحقيقي.
4. مواصفات الفيديو ثابتة: 1080×1920 · 30fps · H.264+AAC · faststart · ≤90 ثانية · ≤40 MB.
5. أي سقف (يومي/ساعي) بيتكتب ومصدره مكتوب جنبه.
