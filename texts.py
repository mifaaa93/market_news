"""Тексты интерфейса. Новости в них не входят — только оболочка бота."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "tagline": "Ежедневная аналитика рынков",
        "today_head": "Сегодняшние главные новости:",
        "updated": "Обновлено: {stamp} ({tz})",
        "disclaimer": "Не является инвестиционной рекомендацией.",
        "source": "Источник",
        "topic": "Тема",
        "loading": "Собираю свежие заголовки из BBC Business, CNBC, MarketWatch, OilPrice и CoinDesk. Через несколько секунд здесь будут новости дня.",
        "empty": "Ленты источников сейчас не ответили. Меню на месте: откройте дайджест чуть позже — бот подтянет материалы сам.",
        "no_summary": "В ленте не было отдельного абзаца. Ниже источник и соседние материалы по теме. Цифры бот не додумывает.",
        "open_later": "Текст выше сохранён из ленты издания. Ссылка на страницу источника открывается после того, как вы посмотрите несколько материалов здесь.",
        "links_ready": "Страницу источника можно открыть кнопкой ниже. Это сайт издания.",
        "full_note": "Это текст публикации {source}. Оценки и цифры — из исходного материала, бот их не добавляет.",
        "related": "Рядом по теме",
        "no_article": "Этого материала уже нет в ленте. Откройте свежий дайджест.",
        "empty_cat": "В теме «{cat}» пока нет свежих материалов. Выберите другую тему или общий дайджест.",
        "unknown": "Я веду по рынку через кнопки под сообщением. Начните с дайджеста или откройте /help.",
        "digest_title": "Дайджест дня",
        "analytics_title": "Аналитика",
        "latest_title": "Последние новости",
        "cats_title": "Темы",
        "settings_title": "Настройки",
        "sources_title": "Источники",
        "week_title": "Недельная подборка",
        "plus_title": "Market News Plus",
        "plots": "Главные сюжеты",
        "spread": "Как распределились материалы",
        "brief": "Короткий разбор",
        "by_topic": "По темам",
        "analytics_blurb": "В свежей подборке чаще встречается тема «{cat}» — материалов: {n}. Начать можно с «{title}» ({source}). Здесь только уже вышедшие новости: бот не прогнозирует цены и не советует, что покупать или продавать.",
        "cats_intro": "Темы за последние дни. Каждый материал открывается внутри бота.",
        "latest_intro": "Свежие публикации по времени выхода.",
        "digest_intro": "Главное за день. Откройте любой пункт — текст останется в боте.",
        "week_intro": "Двенадцать материалов за семь дней, по разным темам.",
        "sources_locked": "Издания, из которых собран дайджест. Ссылки на их сайты открываются после нескольких прочитанных материалов внутри бота.",
        "sources_open": "Издания, из которых собран дайджест. Кнопки ниже ведут на их сайты.",
        "sources_line": "В этом выпуске: {names}.",
        "only_one": "В этой подборке пока одна новость",
        "mail_footer": "Ежедневная рассылка Market News. Час и язык меняются в /settings.",
        "settings_lang": "Язык интерфейса: {lang}",
        "settings_push_on": "Рассылка включена, в {hour}:00 ({tz})",
        "settings_push_off": "Рассылка выключена",
        "plus_active": "Plus активен до {until}",
        "plus_off": "Plus не подключён. Дайджест, аналитика и рассылка бесплатные.",
        "plus_pitch": "Plus добавляет недельную подборку и более подробную раскладку по темам. Обычный дайджест от этого не зависит и остаётся бесплатным. {days} дней — {stars} Stars, оплата внутри Telegram.",
        "plus_thanks": "Plus подключён до {until}. Недельная подборка лежит в настройках.",
        "plus_invoice_title": "Market News Plus",
        "plus_invoice_desc": "30 дней: недельная подборка и подробная раскладка по темам. Ежедневный дайджест остаётся бесплатным.",
        "pay_failed": "Окно оплаты не открылось. Новости по-прежнему доступны через меню.",
        "story_empty": "Новость дня появится, когда лента ответит. Откройте дайджест через минуту.",
        "opening": "Открываю полный текст…",
        "full_missing": "Полный текст на сайте издания не открылся. Ниже то, что было в ленте.",
        "error": "Не вышло открыть этот экран. Нажмите /start.",
        "cat_stocks": "Акции",
        "cat_oil": "Нефть и газ",
        "cat_macro": "Макро",
        "cat_crypto": "Крипта",
        "cat_markets": "Рынки",
        "btn_digest": "📅 Полный дайджест",
        "btn_analytics": "📊 Аналитика",
        "btn_latest": "📰 Последние",
        "btn_cats": "🗂 Категории",
        "btn_story": "⭐ Новость дня",
        "btn_settings": "⚙️ Настройки",
        "btn_help": "ℹ️ Помощь",
        "btn_full": "Читать полностью",
        "btn_next": "Следующая",
        "btn_menu": "В меню",
        "btn_back": "Назад",
        "btn_source": "Открыть источник",
        "btn_push_on": "Включить рассылку",
        "btn_push_off": "Выключить рассылку",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "Продлить Plus",
        "btn_week": "🗓 Недельная подборка",
        "btn_pay": "Оплатить {stars} Stars",
        "btn_sources": "📚 Источники",
        "src_bbc": "Деловые новости и компании со всего мира.",
        "src_cnbc": "Рынки, экономика, отчётность и энергия.",
        "src_mw": "Новости рынков и компаний.",
        "src_oil": "Нефть, газ и энергетика.",
        "src_coin": "Криптовалютные рынки.",
        "help": """<b>Помощь</b>

Market News присылает деловые новости и короткую сводку по рынку.

<b>Команды</b>
/start — главные новости сейчас
/digest — дайджест дня
/today — то же, что дайджест
/analytics — раскладка по темам
/settings — язык и рассылка
/help — эта справка

<b>Как читать</b>
Откройте дайджест, затем новость. «Читать полностью» показывает текст внутри бота. Ссылка на сайт издания появляется после нескольких материалов: сначала виден сам сюжет.

<b>Рассылка</b>
Один раз в день, в час из настроек. Там же её можно выключить.

<b>Откуда новости</b>
BBC Business, CNBC, MarketWatch, OilPrice, CoinDesk.

Это не инвестиционная рекомендация и не прогноз цен.""",
    },
    "en": {
        "tagline": "Daily market analytics",
        "today_head": "Today's top stories:",
        "updated": "Updated: {stamp} ({tz})",
        "disclaimer": "Not investment advice.",
        "source": "Source",
        "topic": "Topic",
        "loading": "Collecting fresh headlines from BBC Business, CNBC, MarketWatch, OilPrice and CoinDesk. Today's stories will show up here in a few seconds.",
        "empty": "The source feeds did not answer. The menu still works: open the digest in a minute and the bot will load the stories.",
        "no_summary": "The feed had no standalone paragraph. The source and nearby stories are below. The bot does not invent figures.",
        "open_later": "The text above is saved from the publisher's feed. The link to the original page opens after you have read several stories here.",
        "links_ready": "The source page can be opened with the button below. It is the publisher's site.",
        "full_note": "This is the text from {source}. Figures and judgements come from the original piece; the bot does not add any.",
        "related": "Nearby on this topic",
        "no_article": "This story is no longer in the feed. Open a fresh digest.",
        "empty_cat": "Nothing fresh in “{cat}” yet. Pick another topic or the main digest.",
        "unknown": "Use the buttons under the message. Start with the digest, or open /help.",
        "digest_title": "Daily digest",
        "analytics_title": "Analytics",
        "latest_title": "Latest news",
        "cats_title": "Topics",
        "settings_title": "Settings",
        "sources_title": "Sources",
        "week_title": "Weekly briefing",
        "plus_title": "Market News Plus",
        "plots": "Main stories",
        "spread": "How the stories are split",
        "brief": "Short read",
        "by_topic": "By topic",
        "analytics_blurb": "In the latest batch, “{cat}” shows up most often — {n} stories. A sensible place to start is “{title}” ({source}). This is only news that is already out: the bot does not forecast prices or tell you what to buy or sell.",
        "cats_intro": "Topics from the last few days. Every story opens inside the bot.",
        "latest_intro": "The newest stories, in the order they were published.",
        "digest_intro": "The main stories of the day. Open any item and the text stays in the bot.",
        "week_intro": "Twelve stories from the last seven days, across topics.",
        "sources_locked": "Publishers behind the digest. Links to their sites open after you have read several stories inside the bot.",
        "sources_open": "Publishers behind the digest. The buttons below go to their sites.",
        "sources_line": "In this edition: {names}.",
        "only_one": "This list has only one story so far",
        "mail_footer": "Daily Market News delivery. Change the hour or the language in /settings.",
        "settings_lang": "Interface language: {lang}",
        "settings_push_on": "Delivery is on, at {hour}:00 ({tz})",
        "settings_push_off": "Delivery is off",
        "plus_active": "Plus is active until {until}",
        "plus_off": "Plus is not active. The digest, the analytics and the daily delivery are free.",
        "plus_pitch": "Plus adds a weekly briefing and a longer topic breakdown. The regular digest stays free either way. {days} days — {stars} Stars, paid inside Telegram.",
        "plus_thanks": "Plus is active until {until}. The weekly briefing is in settings.",
        "plus_invoice_title": "Market News Plus",
        "plus_invoice_desc": "30 days: a weekly briefing and a longer topic breakdown. The daily digest stays free.",
        "pay_failed": "The payment window did not open. The news is still available from the menu.",
        "story_empty": "The story of the day will appear once the feed answers. Open the digest in a minute.",
        "opening": "Opening the full text…",
        "full_missing": "The full text did not open on the publisher site. Below is what the feed had.",
        "error": "This screen did not open. Tap /start.",
        "cat_stocks": "Stocks",
        "cat_oil": "Oil and gas",
        "cat_macro": "Macro",
        "cat_crypto": "Crypto",
        "cat_markets": "Markets",
        "btn_digest": "📅 Full digest",
        "btn_analytics": "📊 Analytics",
        "btn_latest": "📰 Latest",
        "btn_cats": "🗂 Categories",
        "btn_story": "⭐ Story of the day",
        "btn_settings": "⚙️ Settings",
        "btn_help": "ℹ️ Help",
        "btn_full": "Read in full",
        "btn_next": "Next",
        "btn_menu": "Menu",
        "btn_back": "Back",
        "btn_source": "Open source",
        "btn_push_on": "Turn delivery on",
        "btn_push_off": "Turn delivery off",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "Renew Plus",
        "btn_week": "🗓 Weekly briefing",
        "btn_pay": "Pay {stars} Stars",
        "btn_sources": "📚 Sources",
        "src_bbc": "Business news and companies from around the world.",
        "src_cnbc": "Markets, the economy, earnings and energy.",
        "src_mw": "Market and company news.",
        "src_oil": "Oil, gas and energy.",
        "src_coin": "Cryptocurrency markets.",
        "help": """<b>Help</b>

Market News sends business stories and a short market brief.

<b>Commands</b>
/start — the top stories right now
/digest — today's digest
/today — the same as the digest
/analytics — a breakdown by topic
/settings — language and delivery
/help — this note

<b>How to read</b>
Open the digest, then a story. “Read in full” stays inside the bot. A link to the publisher appears after several stories, so the piece itself comes first.

<b>Delivery</b>
Once a day, at the hour you pick in settings. You can turn it off there.

<b>Where the news comes from</b>
BBC Business, CNBC, MarketWatch, OilPrice, CoinDesk.

This is not investment advice and not a price forecast.""",
    },
    "ar": {
        "tagline": "تحليل يومي للأسواق",
        "today_head": "أبرز أخبار اليوم:",
        "updated": "آخر تحديث: {stamp} ({tz})",
        "disclaimer": "ليس نصيحة استثمارية.",
        "source": "المصدر",
        "topic": "الموضوع",
        "loading": "أجمع العناوين الجديدة من BBC Business وCNBC وMarketWatch وOilPrice وCoinDesk. ستظهر أخبار اليوم هنا خلال ثوانٍ.",
        "empty": "لم تستجب مصادر الأخبار الآن. القائمة تعمل: افتح الموجز بعد دقيقة وسيحمّل البوت المواد.",
        "no_summary": "لم تأتِ في الخلاصة فقرة مستقلة. في الأسفل المصدر ومواد قريبة من الموضوع. البوت لا يخترع أرقامًا.",
        "open_later": "النص أعلاه محفوظ من خلاصة الناشر. رابط الصفحة الأصلية يفتح بعد قراءة عدة مواد هنا.",
        "links_ready": "يمكن فتح صفحة المصدر بالزر في الأسفل. هذا موقع الناشر.",
        "full_note": "هذا نص من {source}. الأرقام والأحكام من المادة الأصلية، والبوت لا يضيف شيئًا.",
        "related": "مواد قريبة في الموضوع",
        "no_article": "هذه المادة لم تعد في الخلاصة. افتح موجزًا جديدًا.",
        "empty_cat": "لا مواد جديدة في «{cat}» بعد. اختر موضوعًا آخر أو الموجز العام.",
        "unknown": "استخدم الأزرار تحت الرسالة. ابدأ بالموجز أو افتح /help.",
        "digest_title": "موجز اليوم",
        "analytics_title": "التحليل",
        "latest_title": "آخر الأخبار",
        "cats_title": "المواضيع",
        "settings_title": "الإعدادات",
        "sources_title": "المصادر",
        "week_title": "موجز الأسبوع",
        "plus_title": "Market News Plus",
        "plots": "أبرز الموضوعات",
        "spread": "كيف توزعت المواد",
        "brief": "قراءة قصيرة",
        "by_topic": "حسب الموضوع",
        "analytics_blurb": "في الدفعة الأخيرة يظهر موضوع «{cat}» أكثر من غيره — {n} مواد. يمكن البدء بـ«{title}» ({source}). هنا أخبار نُشرت فقط: البوت لا يتوقع الأسعار ولا يقول ماذا تشتري أو تبيع.",
        "cats_intro": "مواضيع الأيام الأخيرة. كل مادة تُفتح داخل البوت.",
        "latest_intro": "أحدث المواد حسب وقت النشر.",
        "digest_intro": "أهم ما في اليوم. افتح أي بند ويبقى النص داخل البوت.",
        "week_intro": "اثنتا عشرة مادة من آخر سبعة أيام، من مواضيع مختلفة.",
        "sources_locked": "الناشرون وراء الموجز. روابط مواقعهم تُفتح بعد قراءة عدة مواد داخل البوت.",
        "sources_open": "الناشرون وراء الموجز. الأزرار في الأسفل تؤدي إلى مواقعهم.",
        "sources_line": "في هذا العدد: {names}.",
        "only_one": "في هذه القائمة خبر واحد حتى الآن",
        "mail_footer": "رسالة Market News اليومية. غيّر الساعة أو اللغة في /settings.",
        "settings_lang": "لغة الواجهة: {lang}",
        "settings_push_on": "الإرسال مفعّل، الساعة {hour}:00 ({tz})",
        "settings_push_off": "الإرسال متوقف",
        "plus_active": "Plus فعّال حتى {until}",
        "plus_off": "Plus غير مفعّل. الموجز والتحليل والرسالة اليومية مجانية.",
        "plus_pitch": "يضيف Plus موجزًا أسبوعيًا وتفصيلًا أطول حسب المواضيع. الموجز العادي يبقى مجانيًا. {days} يومًا — {stars} Stars، والدفع داخل تيليغرام.",
        "plus_thanks": "Plus مفعّل حتى {until}. الموجز الأسبوعي في الإعدادات.",
        "plus_invoice_title": "Market News Plus",
        "plus_invoice_desc": "30 يومًا: موجز أسبوعي وتفصيل أطول حسب المواضيع. الموجز اليومي يبقى مجانيًا.",
        "pay_failed": "لم تُفتح نافذة الدفع. الأخبار ما زالت متاحة من القائمة.",
        "story_empty": "خبر اليوم يظهر عندما ترد الخلاصة. افتح الموجز بعد دقيقة.",
        "opening": "أفتح النص الكامل…",
        "full_missing": "لم يفتح النص الكامل على موقع الناشر. في الأسفل ما جاء في الخلاصة.",
        "error": "لم تُفتح هذه الشاشة. اضغط /start.",
        "cat_stocks": "الأسهم",
        "cat_oil": "النفط والغاز",
        "cat_macro": "الاقتصاد الكلي",
        "cat_crypto": "العملات الرقمية",
        "cat_markets": "الأسواق",
        "btn_digest": "📅 الموجز الكامل",
        "btn_analytics": "📊 التحليل",
        "btn_latest": "📰 الأحدث",
        "btn_cats": "🗂 التصنيفات",
        "btn_story": "⭐ خبر اليوم",
        "btn_settings": "⚙️ الإعدادات",
        "btn_help": "ℹ️ مساعدة",
        "btn_full": "اقرأ كاملًا",
        "btn_next": "التالية",
        "btn_menu": "القائمة",
        "btn_back": "رجوع",
        "btn_source": "فتح المصدر",
        "btn_push_on": "تشغيل الإرسال",
        "btn_push_off": "إيقاف الإرسال",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "تجديد Plus",
        "btn_week": "🗓 موجز الأسبوع",
        "btn_pay": "ادفع {stars} Stars",
        "btn_sources": "📚 المصادر",
        "src_bbc": "أخبار الأعمال والشركات من حول العالم.",
        "src_cnbc": "الأسواق والاقتصاد والنتائج والطاقة.",
        "src_mw": "أخبار الأسواق والشركات.",
        "src_oil": "النفط والغاز والطاقة.",
        "src_coin": "أسواق العملات الرقمية.",
        "help": """<b>مساعدة</b>

يرسل Market News أخبار الأعمال وملخصًا قصيرًا للسوق.

<b>الأوامر</b>
/start — أبرز الأخبار الآن
/digest — موجز اليوم
/today — نفس الموجز
/analytics — توزيع حسب المواضيع
/settings — اللغة والإرسال
/help — هذه الملاحظة

<b>كيف تقرأ</b>
افتح الموجز ثم الخبر. «اقرأ كاملًا» يبقى داخل البوت. رابط الناشر يظهر بعد عدة مواد، فيأتي النص نفسه أولًا.

<b>الإرسال</b>
مرة في اليوم، في الساعة التي تختارها من الإعدادات. ويمكن إيقافه هناك.

<b>من أين تأتي الأخبار</b>
BBC Business وCNBC وMarketWatch وOilPrice وCoinDesk.

هذا ليس نصيحة استثمارية ولا توقعًا للأسعار.""",
    },
}

TZ_LABELS = {
    "ru": {
        "Europe/Moscow": "Москва",
        "Asia/Dubai": "Дубай",
        "Europe/London": "Лондон",
        "UTC": "UTC",
    },
    "en": {
        "Europe/Moscow": "Moscow",
        "Asia/Dubai": "Dubai",
        "Europe/London": "London",
        "UTC": "UTC",
    },
    "ar": {
        "Europe/Moscow": "موسكو",
        "Asia/Dubai": "دبي",
        "Europe/London": "لندن",
        "UTC": "UTC",
    },
}

ABOUT_RU = (
    "Market News собирает деловые новости и раскладывает их по темам: "
    "акции, нефть, макро и крипта. Дайджест приходит раз в день, читать можно "
    "прямо в боте. Материалы берутся из BBC Business, CNBC, MarketWatch, "
    "OilPrice и CoinDesk. Это не инвестиционный совет и не прогноз цен."
)
ABOUT_EN = (
    "Market News collects business stories and sorts them by topic: "
    "stocks, oil, macro and crypto. A digest arrives once a day and can be "
    "read inside the bot. Stories come from BBC Business, CNBC, MarketWatch, "
    "OilPrice and CoinDesk. This is not investment advice and not a price forecast."
)
SHORT_RU = "Ежедневный дайджест рынков: новости и короткая сводка внутри бота."
SHORT_EN = "A daily market digest: stories and a short brief inside the bot."
ABOUT_AR = (
    "يجمع Market News أخبار الأعمال ويصنفها حسب الموضوع: "
    "الأسهم والنفط والاقتصاد الكلي والعملات الرقمية. يصل الموجز مرة في اليوم "
    "ويمكن قراءته داخل البوت. المواد من BBC Business وCNBC وMarketWatch "
    "وOilPrice وCoinDesk. هذا ليس نصيحة استثمارية ولا توقعًا للأسعار."
)
SHORT_AR = "موجز يومي للأسواق: أخبار وملخص قصير داخل البوت."

COMMANDS_RU = (
    ("start", "Главные новости"),
    ("digest", "Дайджест дня"),
    ("today", "Сегодняшние новости"),
    ("analytics", "Аналитика"),
    ("settings", "Настройки"),
    ("help", "Помощь"),
)
COMMANDS_EN = (
    ("start", "Top stories"),
    ("digest", "Daily digest"),
    ("today", "Today's news"),
    ("analytics", "Analytics"),
    ("settings", "Settings"),
    ("help", "Help"),
)
COMMANDS_UK = (
    ("start", "Головні новини"),
    ("digest", "Дайджест дня"),
    ("today", "Новини сьогодні"),
    ("analytics", "Аналітика"),
    ("settings", "Налаштування"),
    ("help", "Допомога"),
)
COMMANDS_AR = (
    ("start", "أهم الأخبار"),
    ("digest", "موجز اليوم"),
    ("today", "أخبار اليوم"),
    ("analytics", "التحليل"),
    ("settings", "الإعدادات"),
    ("help", "المساعدة"),
)
COMMANDS = {
    "ru": COMMANDS_RU,
    "en": COMMANDS_EN,
    "uk": COMMANDS_UK,
    "ar": COMMANDS_AR,
}


def t(lang: str, key: str) -> str:
    table = STRINGS.get(lang) or STRINGS["ru"]
    if key in table:
        return table[key]
    if key in STRINGS["ru"]:
        return STRINGS["ru"][key]
    raise KeyError(key)


def fill(template: str, **kwargs: object) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def tz_label(lang: str, zone: str) -> str:
    table = TZ_LABELS.get(lang) or TZ_LABELS["ru"]
    return table.get(zone, zone)


def lang_label(lang: str) -> str:
    return {"ru": "Русский", "en": "English", "ar": "العربية"}.get(lang, lang)


def cat_name(lang: str, category: str) -> str:
    key = f"cat_{category}"
    if key in STRINGS["ru"]:
        return t(lang, key)
    return t(lang, "cat_markets")
