"""Тексты интерфейса. Новости в них не входят — только оболочка бота."""

from __future__ import annotations

PRESTIGE_SOURCES = (
    "Reuters",
    "CNBC",
    "BBC",
    "The Guardian",
    "Yahoo",
    "Seeking Alpha",
    "Livemint",
)


def format_publishers(names: list[str] | None = None, *, limit: int = 12) -> str:
    items = [name.strip() for name in (names or []) if name and name.strip()]
    if len(items) < 3:
        items = list(PRESTIGE_SOURCES)
    return ", ".join(items[:limit])


STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "tagline": "Ежедневная аналитика рынков",
        "today_head": "Сегодняшние главные новости:",
        "updated": "Обновлено: {stamp} ({tz})",
        "disclaimer": "Не является инвестиционной рекомендацией.",
        "source": "Источник",
        "topic": "Тема",
        "loading": "Собираю свежие заголовки по рынкам. Через несколько секунд здесь будут новости дня.",
        "empty": "Свежих материалов пока нет. Откройте дайджест чуть позже или включите источники в «Моя лента».",
        "no_summary": "В ленте не было отдельного абзаца. Ниже источник и соседние материалы по теме. Цифры бот не додумывает.",
        "open_later": "Текст выше сохранён из ленты издания.",
        "links_ready": "",
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
        "plus_title": "Подписка Market News",
        "plots": "Главные сюжеты",
        "spread": "Как распределились материалы",
        "brief": "Короткий разбор",
        "by_topic": "По темам",
        "analytics_blurb": "В свежей подборке чаще встречается тема «{cat}» — материалов: {n}. Начать можно с «{title}» ({source}). Здесь только уже вышедшие новости: бот не прогнозирует цены и не советует, что покупать или продавать.",
        "cats_intro": "Темы за последние дни. Каждый материал открывается внутри бота.",
        "latest_intro": "Свежие публикации по времени выхода.",
        "digest_intro": "Главные деловые заголовки ведущих изданий.",
        "week_intro": "Двенадцать материалов за семь дней, по разным темам.",
        "sources_locked": "Издания, из которых собран дайджест.",
        "sources_open": "Издания, из которых собран дайджест.",
        "sources_intro": "Сначала издания текущего топа: {sources}. Переходов на внешние сайты здесь нет.",
        "sources_line": "В этом выпуске: {names}.",
        "only_one": "В этой подборке пока одна новость",
        "mail_footer": "Ежедневная рассылка Market News. Час и язык меняются в /settings.",
        "settings_lang": "Язык интерфейса: {lang}",
        "settings_push_on": "Рассылка включена, в {hour}:00 ({tz})",
        "settings_push_off": "Рассылка выключена",
        "plus_active": "Plus активен до {until}",
        "plus_off": "Подписка не подключена. Дайджест, аналитика и полный текст остаются бесплатными.",
        "plus_pitch": "Лента рынка в одном окне. Базовый тариф — 0 Stars: до 5 источников и дневной дайджест. Plus — {plus_stars} Stars на 30 дней: до {plus_limit} источников, сообщение по новой статье с минимальной задержкой. Pro — {pro_stars} Stars: до {pro_limit} источников, уведомления мгновенно.",
        "plus_thanks": "{plan} подключён до {until}. Дневной дайджест остаётся доступен.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 дней: больше источников и уведомления по новым статьям.",
        "plans_title": "Тарифы Market News",
        "plans_text": "Для вашего языка сейчас {catalog} источников.\n\nБазовый — 0 Stars: до 5 включённых источников, дневной дайджест.\n\nPlus — 200 Stars / 30 дней: до 100 источников, сообщение по новой статье с минимальной задержкой.\n\nPro — 500 Stars / 30 дней: до 500 источников, уведомления мгновенно.",
        "feed_title": "Моя лента",
        "feed_intro": "Сначала издания из текущего топа (★), затем остальные по числу новостей. Включено {enabled} из {limit}.",
        "feed_page": "Страница {page} из {pages}",
        "feed_locked": "нужен {plan}",
        "admin_title": "Админка подписок",
        "admin_intro": "Закрытый раздел.\nВыдача: ID тариф срок_дней — например: 123456789 pro 30.\nОтзыв или статус: просто ID.",
        "admin_grant": "✅ Выдать подписку",
        "admin_revoke": "🚫 Забрать подписку",
        "admin_status": "🔎 Проверить статус",
        "admin_prompt_grant": "Отправьте: ID тариф срок_дней\nПример: 123456789 plus 30",
        "admin_prompt_user": "Отправьте Telegram ID пользователя.",
        "admin_bad_input": "Не удалось разобрать данные. Попробуйте ещё раз.",
        "admin_not_found": "Пользователь с таким ID ещё не запускал бота.",
        "admin_granted": "Готово: {plan} выдан пользователю {user_id} до {until}.",
        "admin_revoked": "Подписка пользователя {user_id} отозвана.",
        "admin_status_result": "Пользователь {user_id}: {status}.",
        "admin_confirm": "✅ Подтвердить отзыв",
        "admin_cancel": "❌ Отмена",
        "admin_confirm_question": "Отозвать {status} у пользователя {user_id}? Звёзды не возвращаются автоматически.",
        "admin_user_granted": "Вам подключён {plan} до {until}.",
        "admin_user_revoked": "Ваша подписка отозвана администратором. Бесплатный дайджест остаётся доступен.",
        "admin_confirm_wait": "Для отзыва нажмите кнопку подтверждения. Для отмены нажмите «Отмена» или /admin.",
        "admin_expired": "Подтверждение устарело. Откройте /admin заново.",
        "subscription_status": "Статус: {status}",
        "pay_failed": "Окно оплаты не открылось. Новости по-прежнему доступны через меню.",
        "story_empty": "Новость дня появится, когда лента ответит. Откройте дайджест через минуту.",
        "opening": "Открываю полный текст…",
        "full_missing": "Полный текст на сайте издания не открылся. Ниже то, что было в ленте.",
        "error": "Не вышло открыть этот экран. Нажмите /start.",
        "cat_stocks": "📈 Акции",
        "cat_oil": "🛢 Нефть и газ",
        "cat_macro": "🏦 Макро",
        "cat_crypto": "🪙 Крипта",
        "cat_markets": "🌐 Рынки",
        "btn_digest": "📅 Полный дайджест новостей",
        "btn_how_it_works": "💡 Как работает продукт",
        "btn_analytics": "📊 Аналитика рынков",
        "btn_latest": "📰 Последние новости",
        "btn_cats": "🗂 Категории",
        "btn_story": "🔥 Новость дня",
        "btn_settings": "⚙️ Настройки",
        "btn_help": "ℹ️ Помощь",
        "btn_full": "📖 Читать полностью",
        "btn_next": "➡️ Следующая",
        "btn_menu": "🏠 В меню",
        "btn_back": "↩️ Назад",
        "btn_collapse": "🔼 Свернуть",
        "btn_push_on": "🔔 Включить рассылку",
        "btn_push_off": "🔕 Выключить рассылку",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "⭐ Продлить Plus",
        "btn_week": "🗓 Недельная подборка",
        "btn_pay": "⭐ Оплатить {stars} Stars",
        "btn_sources": "📚 Источники",
        "btn_subscription": "⭐ Подписка",
        "btn_my_feed": "📰 Моя лента",
        "btn_prev_page": "‹",
        "btn_next_page": "›",
        "btn_feed_off": "✖️ Отключить все",
        "btn_feed_top": "★ Только топ",
        "btn_read": "📖 Читать",
        "btn_pay_plus": "⭐ Plus · 200 Stars",
        "btn_pay_pro": "💎 Pro · 500 Stars",
        "btn_plan_plus": "Plus",
        "btn_plan_pro": "Pro",
        "btn_plan_base": "нет подписки",
        "admin_grant": "✅ Выдать подписку",
        "admin_revoke": "🚫 Забрать подписку",
        "admin_status": "🔎 Проверить статус",
        "how_it_works": """<b>Как работает Market News</b>

Market News собирает деловые новости с {sources} и переводит их на язык интерфейса.

<b>Что доступно бесплатно</b>
• Главные новости и дневной дайджест.
• Аналитика и разбивка по темам: акции, нефть, макро и крипта.
• Текст материалов внутри бота.
• Выбор языка интерфейса и времени ежедневной рассылки.

<b>Подписка Plus</b>
200 Stars на 30 дней.
• До 100 источников в ленте.
• Уведомление по новой статье с минимальной задержкой.

<b>Подписка Pro</b>
500 Stars на 30 дней.
• До 500 источников.
• Уведомления по новым статьям мгновенно.

<b>Моя лента</b>
Сначала издания из текущего топа, отмеченные ★. Затем остальные по числу новостей.

Оплата не закрывает бесплатные новости. Это не инвестиционная рекомендация и не прогноз цены.""",
        "src_default": "Источник деловых новостей.",
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
Откройте дайджест, затем новость. «Читать полностью» показывает текст внутри бота.

<b>Рассылка</b>
Один раз в день, в час из настроек. Там же её можно выключить.

<b>Откуда новости</b>
{sources}. Полный список — в «Моя лента».

Это не инвестиционная рекомендация и не прогноз цен.""",
    },
    "en": {
        "tagline": "Daily market analytics",
        "today_head": "Today's top stories:",
        "updated": "Updated: {stamp} ({tz})",
        "disclaimer": "Not investment advice.",
        "source": "Source",
        "topic": "Topic",
        "loading": "Collecting fresh market headlines. Today's stories will show up here in a few seconds.",
        "empty": "No fresh stories yet. Open the digest in a minute or enable sources in My feed.",
        "no_summary": "The feed had no standalone paragraph. The source and nearby stories are below. The bot does not invent figures.",
        "open_later": "The text above is saved from the publisher's feed.",
        "links_ready": "",
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
        "plus_title": "Market News Subscription",
        "plots": "Main stories",
        "spread": "How the stories are split",
        "brief": "Short read",
        "by_topic": "By topic",
        "analytics_blurb": "In the latest batch, “{cat}” shows up most often — {n} stories. A sensible place to start is “{title}” ({source}). This is only news that is already out: the bot does not forecast prices or tell you what to buy or sell.",
        "cats_intro": "Topics from the last few days. Every story opens inside the bot.",
        "latest_intro": "The newest stories, in the order they were published.",
        "digest_intro": "The current top business headlines from leading publishers.",
        "week_intro": "Twelve stories from the last seven days, across topics.",
        "sources_locked": "Publishers behind the digest.",
        "sources_open": "Publishers behind the digest.",
        "sources_intro": "Headline publishers first: {sources}. There are no external-site buttons here.",
        "sources_line": "In this edition: {names}.",
        "only_one": "This list has only one story so far",
        "mail_footer": "Daily Market News delivery. Change the hour or the language in /settings.",
        "settings_lang": "Interface language: {lang}",
        "settings_push_on": "Delivery is on, at {hour}:00 ({tz})",
        "settings_push_off": "Delivery is off",
        "plus_active": "Plus is active until {until}",
        "plus_off": "No subscription is active. The digest, analytics and full text stay free.",
        "plus_pitch": "One market feed in one place. Basic: 0 Stars, up to 5 sources and a daily digest. Plus: {plus_stars} Stars for 30 days, up to {plus_limit} sources, a new-story alert with minimal delay. Pro: {pro_stars} Stars, up to {pro_limit} sources, instant alerts.",
        "plus_thanks": "{plan} is active until {until}. The daily digest remains available.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 days: more sources and alerts for new stories.",
        "plans_title": "Market News plans",
        "plans_text": "There are {catalog} sources for your language now.\n\nBasic — 0 Stars: up to 5 sources, daily digest.\n\nPlus — 200 Stars / 30 days: up to 100 sources, a new-story alert with minimal delay.\n\nPro — 500 Stars / 30 days: up to 500 sources, instant alerts.",
        "feed_title": "My feed",
        "feed_intro": "Headline publishers first (★), then the rest by story count. {enabled} of {limit} enabled.",
        "feed_page": "Page {page} of {pages}",
        "feed_locked": "needs {plan}",
        "admin_title": "Subscription admin",
        "admin_intro": "Private section.\nGrant: ID plan days — for example: 123456789 pro 30.\nRevoke or status: send only the ID.",
        "admin_grant": "✅ Grant subscription",
        "admin_revoke": "🚫 Revoke subscription",
        "admin_status": "🔎 Check status",
        "admin_prompt_grant": "Send: ID plan days\nExample: 123456789 plus 30",
        "admin_prompt_user": "Send the user's Telegram ID.",
        "admin_bad_input": "Could not parse the data. Try again.",
        "admin_not_found": "This user has not started the bot yet.",
        "admin_granted": "Done: {plan} granted to {user_id} until {until}.",
        "admin_revoked": "Subscription for {user_id} was revoked.",
        "admin_status_result": "User {user_id}: {status}.",
        "admin_confirm": "✅ Confirm revocation",
        "admin_cancel": "❌ Cancel",
        "admin_confirm_question": "Revoke {status} for user {user_id}? Stars are not automatically refunded.",
        "admin_user_granted": "Your {plan} subscription is active until {until}.",
        "admin_user_revoked": "Your subscription has been revoked by an admin. The free digest is still available.",
        "admin_confirm_wait": "Use the confirmation button to revoke. To cancel, tap Cancel or /admin.",
        "admin_expired": "Confirmation expired. Open /admin again.",
        "subscription_status": "Status: {status}",
        "pay_failed": "The payment window did not open. The news is still available from the menu.",
        "story_empty": "The story of the day will appear once the feed answers. Open the digest in a minute.",
        "opening": "Opening the full text…",
        "full_missing": "The full text did not open on the publisher site. Below is what the feed had.",
        "error": "This screen did not open. Tap /start.",
        "cat_stocks": "📈 Stocks",
        "cat_oil": "🛢 Oil and gas",
        "cat_macro": "🏦 Macro",
        "cat_crypto": "🪙 Crypto",
        "cat_markets": "🌐 Markets",
        "btn_digest": "📅 Full news digest",
        "btn_how_it_works": "💡 How the product works",
        "btn_analytics": "📊 Market analytics",
        "btn_latest": "📰 Latest news",
        "btn_cats": "🗂 Categories",
        "btn_story": "🔥 Story of the day",
        "btn_settings": "⚙️ Settings",
        "btn_help": "ℹ️ Help",
        "btn_full": "📖 Read in full",
        "btn_next": "➡️ Next",
        "btn_menu": "🏠 Menu",
        "btn_back": "↩️ Back",
        "btn_collapse": "🔼 Collapse",
        "btn_push_on": "🔔 Turn delivery on",
        "btn_push_off": "🔕 Turn delivery off",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "⭐ Renew Plus",
        "btn_week": "🗓 Weekly briefing",
        "btn_pay": "⭐ Pay {stars} Stars",
        "btn_sources": "📚 Sources",
        "btn_subscription": "⭐ Subscription",
        "btn_my_feed": "📰 My feed",
        "btn_prev_page": "‹",
        "btn_next_page": "›",
        "btn_feed_off": "✖️ Disable all",
        "btn_feed_top": "★ Top only",
        "btn_read": "📖 Read",
        "btn_pay_plus": "⭐ Plus · 200 Stars",
        "btn_pay_pro": "💎 Pro · 500 Stars",
        "btn_plan_plus": "Plus",
        "btn_plan_pro": "Pro",
        "btn_plan_base": "no subscription",
        "admin_grant": "✅ Grant subscription",
        "admin_revoke": "🚫 Revoke subscription",
        "admin_status": "🔎 Check status",
        "how_it_works": """<b>How Market News works</b>

Market News collects business news from {sources} and translates it into the interface language.

<b>Free features</b>
• Top stories and a daily digest.
• Analytics by stocks, oil, macro and crypto.
• Story text inside the bot.
• Interface language and daily delivery time settings.

<b>Plus subscription</b>
200 Stars for 30 days.
• Up to 100 sources in the feed.
• A new-story alert with minimal delay.

<b>Pro subscription</b>
500 Stars for 30 days.
• Up to 500 sources.
• Instant alerts for new stories.

<b>My feed</b>
Headline publishers come first, marked ★. The rest follow by story count.

Payment does not lock free news. This is not investment advice or a price forecast.""",
        "src_default": "A business news publisher.",
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
Open the digest, then a story. “Read in full” stays inside the bot.

<b>Delivery</b>
Once a day, at the hour you pick in settings. You can turn it off there.

<b>Where the news comes from</b>
{sources}. The full list is in My feed.

This is not investment advice and not a price forecast.""",
    },
    "ar": {
        "tagline": "تحليل يومي للأسواق",
        "today_head": "أبرز أخبار اليوم:",
        "updated": "آخر تحديث: {stamp} ({tz})",
        "disclaimer": "ليس نصيحة استثمارية.",
        "source": "المصدر",
        "topic": "الموضوع",
        "loading": "أجمع عناوين الأسواق الجديدة. ستظهر أخبار اليوم هنا خلال ثوانٍ.",
        "empty": "لا مواد جديدة بعد. افتح الموجز بعد دقيقة أو فعّل المصادر في «موجزي».",
        "no_summary": "لم تأتِ في الخلاصة فقرة مستقلة. في الأسفل المصدر ومواد قريبة من الموضوع. البوت لا يخترع أرقامًا.",
        "open_later": "النص أعلاه محفوظ من خلاصة الناشر.",
        "links_ready": "",
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
        "plus_title": "اشتراك Market News",
        "plots": "أبرز الموضوعات",
        "spread": "كيف توزعت المواد",
        "brief": "قراءة قصيرة",
        "by_topic": "حسب الموضوع",
        "analytics_blurb": "في الدفعة الأخيرة يظهر موضوع «{cat}» أكثر من غيره — {n} مواد. يمكن البدء بـ«{title}» ({source}). هنا أخبار نُشرت فقط: البوت لا يتوقع الأسعار ولا يقول ماذا تشتري أو تبيع.",
        "cats_intro": "مواضيع الأيام الأخيرة. كل مادة تُفتح داخل البوت.",
        "latest_intro": "أحدث المواد حسب وقت النشر.",
        "digest_intro": "أبرز عناوين الأعمال من الناشرين الرائدين.",
        "week_intro": "اثنتا عشرة مادة من آخر سبعة أيام، من مواضيع مختلفة.",
        "sources_locked": "الناشرون وراء الموجز.",
        "sources_open": "الناشرون وراء الموجز.",
        "sources_intro": "ناشرو العناوين أولًا: {sources}. لا توجد أزرار لمواقع خارجية هنا.",
        "sources_line": "في هذا العدد: {names}.",
        "only_one": "في هذه القائمة خبر واحد حتى الآن",
        "mail_footer": "رسالة Market News اليومية. غيّر الساعة أو اللغة في /settings.",
        "settings_lang": "لغة الواجهة: {lang}",
        "settings_push_on": "الإرسال مفعّل، الساعة {hour}:00 ({tz})",
        "settings_push_off": "الإرسال متوقف",
        "plus_active": "Plus فعّال حتى {until}",
        "plus_off": "لا يوجد اشتراك فعّال. الموجز والتحليل والنص الكامل مجانية.",
        "plus_pitch": "كل أخبار السوق في نافذة واحدة. الأساسي: 0 Stars، حتى 5 مصادر وموجز يومي. Plus: {plus_stars} Stars لمدة 30 يومًا، حتى {plus_limit} مصدرًا وتنبيه بخبر جديد بأقل تأخير. Pro: {pro_stars} Stars، حتى {pro_limit} مصدرًا وتنبيهات فورية.",
        "plus_thanks": "اشتراك {plan} فعّال حتى {until}. يبقى الموجز اليومي متاحًا.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 يومًا: مصادر أكثر وتنبيهات بالأخبار الجديدة.",
        "plans_title": "خطط Market News",
        "plans_text": "يوجد الآن {catalog} مصدرًا للغتك.\n\nالأساسي — 0 Stars: حتى 5 مصادر وموجز يومي.\n\nPlus — 200 Stars / 30 يومًا: حتى 100 مصدر وتنبيه بخبر جديد بأقل تأخير.\n\nPro — 500 Stars / 30 يومًا: حتى 500 مصدر وتنبيهات فورية.",
        "feed_title": "موجزِي",
        "feed_intro": "ناشرو العناوين أولًا (★)، ثم الباقي بعدد الأخبار. مفعّل {enabled} من {limit}.",
        "feed_page": "صفحة {page} من {pages}",
        "feed_locked": "يتطلب {plan}",
        "admin_title": "إدارة الاشتراكات",
        "admin_intro": "قسم خاص.\nالمنح: ID الخطة الأيام — مثال: 123456789 pro 30.\nالسحب أو الحالة: أرسل المعرف فقط.",
        "admin_grant": "✅ منح اشتراك",
        "admin_revoke": "🚫 سحب اشتراك",
        "admin_status": "🔎 فحص الحالة",
        "admin_prompt_grant": "أرسل: ID الخطة الأيام\nمثال: 123456789 plus 30",
        "admin_prompt_user": "أرسل معرف Telegram للمستخدم.",
        "admin_bad_input": "تعذر فهم البيانات. حاول مرة أخرى.",
        "admin_not_found": "هذا المستخدم لم يبدأ البوت بعد.",
        "admin_granted": "تم: مُنحت {plan} للمستخدم {user_id} حتى {until}.",
        "admin_revoked": "تم سحب اشتراك المستخدم {user_id}.",
        "admin_status_result": "المستخدم {user_id}: {status}.",
        "admin_confirm": "✅ تأكيد السحب",
        "admin_cancel": "❌ إلغاء",
        "admin_confirm_question": "سحب {status} من المستخدم {user_id}؟ لا تُسترد النجوم تلقائيًا.",
        "admin_user_granted": "اشتراكك {plan} فعّال حتى {until}.",
        "admin_user_revoked": "سحب المسؤول اشتراكك. يبقى الموجز المجاني متاحًا.",
        "admin_confirm_wait": "استخدم زر التأكيد للسحب، أو إلغاء /admin.",
        "admin_expired": "انتهت صلاحية التأكيد. افتح /admin مجددًا.",
        "subscription_status": "الحالة: {status}",
        "pay_failed": "لم تُفتح نافذة الدفع. الأخبار ما زالت متاحة من القائمة.",
        "story_empty": "خبر اليوم يظهر عندما ترد الخلاصة. افتح الموجز بعد دقيقة.",
        "opening": "أفتح النص الكامل…",
        "full_missing": "لم يفتح النص الكامل على موقع الناشر. في الأسفل ما جاء في الخلاصة.",
        "error": "لم تُفتح هذه الشاشة. اضغط /start.",
        "cat_stocks": "📈 الأسهم",
        "cat_oil": "🛢 النفط والغاز",
        "cat_macro": "🏦 الاقتصاد الكلي",
        "cat_crypto": "🪙 العملات الرقمية",
        "cat_markets": "🌐 الأسواق",
        "btn_digest": "📅 الموجز الكامل للأخبار",
        "btn_how_it_works": "💡 كيف يعمل المنتج",
        "btn_analytics": "📊 تحليل الأسواق",
        "btn_latest": "📰 آخر الأخبار",
        "btn_cats": "🗂 التصنيفات",
        "btn_story": "🔥 خبر اليوم",
        "btn_settings": "⚙️ الإعدادات",
        "btn_help": "ℹ️ مساعدة",
        "btn_full": "📖 اقرأ كاملًا",
        "btn_next": "➡️ التالية",
        "btn_menu": "🏠 القائمة",
        "btn_back": "↩️ رجوع",
        "btn_collapse": "🔼 طي",
        "btn_push_on": "🔔 تشغيل الإرسال",
        "btn_push_off": "🔕 إيقاف الإرسال",
        "btn_plus": "⭐ Market News Plus",
        "btn_plus_renew": "⭐ تجديد Plus",
        "btn_week": "🗓 موجز الأسبوع",
        "btn_pay": "⭐ ادفع {stars} Stars",
        "btn_sources": "📚 المصادر",
        "btn_subscription": "⭐ الاشتراك",
        "btn_my_feed": "📰 موجزي",
        "btn_prev_page": "‹",
        "btn_next_page": "›",
        "btn_feed_off": "✖️ إيقاف الكل",
        "btn_feed_top": "★ الأعلى فقط",
        "btn_read": "📖 قراءة",
        "btn_pay_plus": "⭐ Plus · 200 Stars",
        "btn_pay_pro": "💎 Pro · 500 Stars",
        "btn_plan_plus": "Plus",
        "btn_plan_pro": "Pro",
        "btn_plan_base": "لا اشتراك",
        "admin_grant": "✅ منح اشتراك",
        "admin_revoke": "🚫 سحب اشتراك",
        "admin_status": "🔎 فحص الحالة",
        "how_it_works": """<b>كيف يعمل Market News</b>

يجمع Market News أخبار الأعمال من {sources} ويترجمها إلى لغة الواجهة.

<b>المزايا المجانية</b>
• أهم الأخبار والموجز اليومي.
• تحليل حسب الأسهم والنفط والاقتصاد الكلي والعملات الرقمية.
• نص المواد داخل البوت.
• اختيار اللغة ووقت الإرسال اليومي.

<b>اشتراك Plus</b>
200 Stars لمدة 30 يومًا.
• حتى 100 مصدر في الموجز.
• تنبيه بخبر جديد بأقل تأخير.

<b>اشتراك Pro</b>
500 Stars لمدة 30 يومًا.
• حتى 500 مصدر.
• تنبيهات فورية بالأخبار الجديدة.

<b>موجزي</b>
ناشرو العناوين أولًا بعلامة ★، ثم الباقي بعدد الأخبار.

الدفع لا يغلق الأخبار المجانية. هذا ليس نصيحة استثمارية ولا توقعًا للسعر.""",
        "src_default": "ناشر أخبار أعمال.",
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
افتح الموجز ثم الخبر. «اقرأ كاملًا» يبقى داخل البوت.

<b>الإرسال</b>
مرة في اليوم، في الساعة التي تختارها من الإعدادات. ويمكن إيقافه هناك.

<b>من أين تأتي الأخبار</b>
{sources}. القائمة الكاملة في «موجزي».

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
    "Market News собирает деловые новости с Reuters, CNBC, BBC, The Guardian, "
    "Yahoo, Seeking Alpha и других изданий. Дайджест раз в день, читать можно в боте. "
    "Это не инвестиционный совет и не прогноз цен."
)
ABOUT_EN = (
    "Market News collects business news from Reuters, CNBC, BBC, The Guardian, "
    "Yahoo, Seeking Alpha and other publishers. A digest arrives once a day "
    "and can be read inside the bot. This is not investment advice and not a price forecast."
)
SHORT_RU = "Ежедневный дайджест рынков: новости и короткая сводка внутри бота."
SHORT_EN = "A daily market digest: stories and a short brief inside the bot."
ABOUT_AR = (
    "يجمع Market News أخبار الأعمال من Reuters وCNBC وBBC وThe Guardian "
    "وYahoo وSeeking Alpha وغيرها. يصل الموجز مرة في اليوم ويمكن قراءته داخل البوت. "
    "هذا ليس نصيحة استثمارية ولا توقعًا للأسعار."
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


def interface_lang(language_code: str | None) -> str:
    """Язык интерфейса при первом запуске: наш код или русский."""
    raw = (language_code or "").strip().lower().replace("_", "-")
    primary = raw.split("-", 1)[0]
    if primary in STRINGS:
        return primary
    return "ru"


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
