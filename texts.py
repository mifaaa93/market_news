"""Тексты интерфейса. Новости в них не входят — только оболочка бота."""

from __future__ import annotations

MAJOR_SOURCES = (
    "Reuters, BBC, CNBC, The Guardian, Bloomberg, Yahoo Finance, Business Insider"
)
_PUBLISHER_TAIL = {
    "ru": " и тысячи других",
    "en": " and thousands of others",
    "ar": " وآلاف غيرها",
}


def format_publishers(names: list[str] | None = None, *, lang: str = "ru", limit: int = 12) -> str:
    return MAJOR_SOURCES + _PUBLISHER_TAIL.get(lang, _PUBLISHER_TAIL["en"])


STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "tagline": "Ежедневная аналитика рынков",
        "today_head": "Сегодняшние главные новости:",
        "updated": "Обновлено: {stamp} ({tz})",
        "disclaimer": "",
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
        "sources_intro": "{sources}. В ленте сначала издания текущего топа (★). Переходов на внешние сайты здесь нет.",
        "sources_line": "В этом выпуске: {names}.",
        "only_one": "В этой подборке пока одна новость",
        "mail_footer": "Ежедневная рассылка Market News. Час и язык меняются в /settings.",
        "settings_lang": "Язык интерфейса: {lang}",
        "settings_push_on": "Рассылка включена, в {hour}:00 ({tz})",
        "settings_push_off": "Рассылка выключена",
        "plus_active": "Plus активен до {until}",
        "plus_off": "Подписка не подключена. Дайджест, аналитика и полный текст остаются бесплатными.",
        "plus_pitch": """Одна премиальная лента рынка вместо десятков вкладок.

Базовый — 0 Stars. До 5 источников, дневной дайджест, аналитика и полный текст новостей внутри бота — чтобы спокойно держать руку на пульсе.

Plus — {plus_stars} Stars на 30 дней. До {plus_limit} источников и мгновенные персональные уведомления о новых публикациях. Получайте важные новости раньше большинства — сразу после того, как они появляются в вашей ленте.

Pro — {pro_stars} Stars на 30 дней. До {pro_limit} источников и максимальный охват для постоянного мониторинга нескольких рынков. Один центр управления новостями — чтобы быть впереди информационного потока и не узнавать о важном последним.""",
        "plus_thanks": "{plan} подключён до {until}. Дневной дайджест остаётся доступен.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 дней: больше источников и уведомления по новым статьям.",
        "plans_title": "Тарифы Market News",
        "plans_text": """Новости не ждут. И вам не нужно.

Соберите свою ленту рынка и получайте мгновенные уведомления о новых публикациях — чтобы узнавать о важном раньше большинства.

Для вашего языка сейчас {catalog} источников.

Базовый — 0 Stars
Для ежедневного обзора главного: до 5 включённых источников, дневной дайджест, аналитика и полный текст внутри бота.

Plus — 200 Stars / 30 дней
До 100 выбранных источников. Каждая новая статья — отдельное уведомление прямо в Telegram. Следите за рынком в течение дня, не дожидаясь вечернего дайджеста.

Pro — 500 Stars / 30 дней
До 500 источников и максимальный охват для постоянного мониторинга нескольких рынков. Больше сигналов из вашей персональной ленты — меньше шансов пропустить важный материал.

Вы выбираете источники. Бот следит за публикациями. Вы узнаёте первыми в своей ленте.""",
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
        "admin_stats": "📊 Статистика",
        "admin_stats_text": "<b>Статистика</b>\nНовостей: {articles}\nСегодня: {today}\nПо темам:\n{categories}\nПользователей: {users}\nВключено источников у пользователей: {picks}\nИсточников в каталоге: {catalog}",
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
        "btn_feed_find": "🔍 Найти источник",
        "btn_feed_all": "✓ Выбрать все источники",
        "btn_source_on": "✓ Включить источник",
        "btn_source_off": "✖️ Отключить источник",
        "source_search_prompt": "Пришлите название издания или ссылку. Ищем только среди источников, которые уже есть в боте.",
        "source_not_found": "Такого источника в боте нет. Можно включить только издания, которые уже появляются в ленте.",
        "source_enabled": "Источник включён: {name}.",
        "source_already": "Этот источник уже в вашей ленте: {name}.",
        "source_many": "Нашлось несколько изданий. Выберите нужное.",
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
• До 5 выбранных источников и дневной дайджест главного.
• Аналитика и разбивка по темам: акции, нефть, макро и крипта.
• Заголовок, саммари и полный текст материалов внутри бота.
• Выбор языка интерфейса и времени ежедневной рассылки.
Это подходит, если вам достаточно один раз в день быстро понять, что произошло на рынке.

<b>Подписка Plus</b>
200 Stars на 30 дней. Для тех, кому важно узнавать о новых публикациях в течение дня.
• До 100 источников в одной персональной ленте.
• Отдельное сообщение по каждой новой статье выбранного источника, как только материал сохранён ботом.
• Не нужно ждать дайджест или вручную проверять десятки сайтов.

<b>Подписка Pro</b>
500 Stars на 30 дней. Для постоянного мониторинга нескольких рынков и максимального охвата.
• До 500 источников в одной ленте.
• Отдельные сообщения по новым материалам, чтобы важные публикации не терялись среди сайтов и каналов.
• Удобно собрать широкий круг изданий в одном окне и читать новости внутри Telegram.

<b>Моя лента</b>
Сначала издания из текущего топа, отмеченные ★. Затем остальные по числу новостей. Можно найти издание по названию или ссылке, если оно уже есть в боте.

Оплата не закрывает бесплатные новости.""",
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

""",
    },
    "en": {
        "tagline": "Daily market analytics",
        "today_head": "Today's top stories:",
        "updated": "Updated: {stamp} ({tz})",
        "disclaimer": "",
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
        "sources_intro": "{sources}. Headline publishers come first in the feed (★). There are no external-site buttons here.",
        "sources_line": "In this edition: {names}.",
        "only_one": "This list has only one story so far",
        "mail_footer": "Daily Market News delivery. Change the hour or the language in /settings.",
        "settings_lang": "Interface language: {lang}",
        "settings_push_on": "Delivery is on, at {hour}:00 ({tz})",
        "settings_push_off": "Delivery is off",
        "plus_active": "Plus is active until {until}",
        "plus_off": "No subscription is active. The digest, analytics and full text stay free.",
        "plus_pitch": """One premium market feed instead of dozens of tabs.

Basic — 0 Stars. Up to 5 sources, a daily digest, analytics and full story text inside the bot — a calm way to stay on top of the essentials.

Plus — {plus_stars} Stars for 30 days. Up to {plus_limit} sources and instant personal alerts about new publications. See important stories before most people do — as soon as they appear in your selected feed.

Pro — {pro_stars} Stars for 30 days. Up to {pro_limit} sources and maximum coverage for continuous monitoring across markets. One command center for the news flow — stay ahead instead of hearing about important events last.""",
        "plus_thanks": "{plan} is active until {until}. The daily digest remains available.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 days: more sources and alerts for new stories.",
        "plans_title": "Market News plans",
        "plans_text": """Markets don't wait. Neither should you.

Build your own market feed and get instant alerts for new stories — so you hear about what matters before most people do.

There are {catalog} sources for your language now.

Basic — 0 Stars
For a daily overview: up to 5 selected sources, a daily digest, analytics and full story text inside the bot.

Plus — 200 Stars / 30 days
Up to 100 selected sources. Every new story gets its own alert in Telegram. Track markets through the day without waiting for the evening digest.

Pro — 500 Stars / 30 days
Up to 500 sources and maximum coverage for continuous monitoring across markets. More signals from your personal feed — fewer important stories missed.

You choose the sources. The bot tracks publications. Be first to know in your feed.""",
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
        "admin_stats": "📊 Stats",
        "admin_stats_text": "<b>Stats</b>\nStories: {articles}\nToday: {today}\nBy topic:\n{categories}\nUsers: {users}\nEnabled source picks: {picks}\nSources in catalog: {catalog}",
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
        "btn_feed_find": "🔍 Find a source",
        "btn_feed_all": "✓ Select all sources",
        "btn_source_on": "✓ Enable this source",
        "btn_source_off": "✖️ Disable this source",
        "source_search_prompt": "Send a publisher name or a link. We only search sources already in the bot.",
        "source_not_found": "This source is not in the bot. You can only enable publishers that already appear in the feed.",
        "source_enabled": "Source enabled: {name}.",
        "source_already": "This source is already in your feed: {name}.",
        "source_many": "Several publishers matched. Pick one.",
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
• Up to 5 selected sources and a daily digest of the essentials.
• Analytics by stocks, oil, macro and crypto.
• Headlines, summaries and full story text inside the bot.
• Interface language and daily delivery time settings.
This is enough if you want a quick, focused market overview once a day.

<b>Plus subscription</b>
200 Stars for 30 days. For people who need new publications during the day.
• Up to 100 sources in one personal feed.
• A separate message for every new story from a selected source as soon as the bot saves it.
• No waiting for the digest and no manual checking of dozens of websites.

<b>Pro subscription</b>
500 Stars for 30 days. For continuous monitoring across several markets.
• Up to 500 sources in one feed.
• Separate messages for new stories, so important publications do not get lost across sites and channels.
• Build broad coverage in one place and read the stories inside Telegram.

<b>My feed</b>
Headline publishers come first, marked ★. The rest follow by story count. You can find a publisher by name or link if it is already in the bot.

Payment does not lock free news.""",
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

""",
    },
    "ar": {
        "tagline": "تحليل يومي للأسواق",
        "today_head": "أبرز أخبار اليوم:",
        "updated": "آخر تحديث: {stamp} ({tz})",
        "disclaimer": "",
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
        "sources_intro": "{sources}. في الموجز يظهر ناشرو العناوين أولًا (★). لا توجد أزرار لمواقع خارجية هنا.",
        "sources_line": "في هذا العدد: {names}.",
        "only_one": "في هذه القائمة خبر واحد حتى الآن",
        "mail_footer": "رسالة Market News اليومية. غيّر الساعة أو اللغة في /settings.",
        "settings_lang": "لغة الواجهة: {lang}",
        "settings_push_on": "الإرسال مفعّل، الساعة {hour}:00 ({tz})",
        "settings_push_off": "الإرسال متوقف",
        "plus_active": "Plus فعّال حتى {until}",
        "plus_off": "لا يوجد اشتراك فعّال. الموجز والتحليل والنص الكامل مجانية.",
        "plus_pitch": """نافذة واحدة مميزة لأخبار السوق بدلًا من عشرات علامات التبويب.

الأساسي — 0 Stars. حتى 5 مصادر، وموجز يومي، وتحليل، والنص الكامل داخل البوت — طريقة هادئة لمعرفة أهم ما حدث.

Plus — {plus_stars} Stars لمدة 30 يومًا. حتى {plus_limit} مصدرًا وتنبيهات شخصية فورية بالأخبار الجديدة. اطّلع على الأخبار المهمة قبل معظم الناس — فور ظهورها في موجزك المختار.

Pro — {pro_stars} Stars لمدة 30 يومًا. حتى {pro_limit} مصدرًا مع أوسع تغطية لمتابعة عدة أسواق باستمرار. مركز واحد لإدارة تدفق الأخبار — لتبقى في المقدمة ولا تعرف الخبر المهم أخيرًا.""",
        "plus_thanks": "اشتراك {plan} فعّال حتى {until}. يبقى الموجز اليومي متاحًا.",
        "plus_invoice_title": "Market News {plan}",
        "plus_invoice_desc": "30 يومًا: مصادر أكثر وتنبيهات بالأخبار الجديدة.",
        "plans_title": "خطط Market News",
        "plans_text": """الأسواق لا تنتظر. فلماذا تنتظر أنت؟

أنشئ موجزك الخاص واحصل على تنبيهات فورية بالأخبار الجديدة — لتعرف ما يهم قبل معظم الناس.

يوجد الآن {catalog} مصدرًا بلغتك.

الأساسي — 0 Stars
للمراجعة اليومية: حتى 5 مصادر مختارة، وموجز يومي، وتحليل، والنص الكامل داخل البوت.

Plus — 200 Stars / 30 يومًا
حتى 100 مصدر تختاره بنفسك. تنبيه منفصل في Telegram لكل خبر جديد. تابع السوق طوال اليوم دون انتظار الموجز المسائي.

Pro — 500 Stars / 30 يومًا
حتى 500 مصدر وأوسع تغطية لمتابعة عدة أسواق باستمرار. إشارات أكثر من موجزك الشخصي، واحتمال أقل لتفويت خبر مهم.

أنت تختار المصادر. البوت يتابع الأخبار. كن أول من يعرف في موجزك.""",
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
        "admin_stats": "📊 إحصاءات",
        "admin_stats_text": "<b>إحصاءات</b>\nالأخبار: {articles}\nاليوم: {today}\nحسب الموضوع:\n{categories}\nالمستخدمون: {users}\nالمصادر المفعّلة لدى المستخدمين: {picks}\nالمصادر في الكتالوج: {catalog}",
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
        "btn_feed_find": "🔍 ابحث عن مصدر",
        "btn_feed_all": "✓ تفعيل كل المصادر",
        "btn_source_on": "✓ تفعيل هذا المصدر",
        "btn_source_off": "✖️ إيقاف هذا المصدر",
        "source_search_prompt": "أرسل اسم الناشر أو رابطًا. نبحث فقط بين المصادر الموجودة في البوت.",
        "source_not_found": "هذا المصدر غير موجود في البوت. يمكن تفعيل الناشرين الذين يظهرون في الموجز فقط.",
        "source_enabled": "تم تفعيل المصدر: {name}.",
        "source_already": "هذا المصدر في موجزك بالفعل: {name}.",
        "source_many": "عُثر على عدة ناشرين. اختر واحدًا.",
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
• حتى 5 مصادر مختارة وموجز يومي لأهم الأخبار.
• تحليل حسب الأسهم والنفط والاقتصاد الكلي والعملات الرقمية.
• العناوين والملخصات والنص الكامل داخل البوت.
• اختيار اللغة ووقت الإرسال اليومي.
هذا مناسب لمن يريد فهم أهم ما حدث في السوق مرة واحدة يوميًا.

<b>اشتراك Plus</b>
200 Stars لمدة 30 يومًا. لمن يحتاج إلى معرفة الأخبار الجديدة خلال اليوم.
• حتى 100 مصدر في موجز شخصي واحد.
• رسالة منفصلة لكل خبر جديد من مصدر مختار فور حفظه في البوت.
• لا حاجة لانتظار الموجز أو مراجعة عشرات المواقع يدويًا.

<b>اشتراك Pro</b>
500 Stars لمدة 30 يومًا. للمراقبة المستمرة لعدة أسواق.
• حتى 500 مصدر في موجز واحد.
• رسائل منفصلة بالأخبار الجديدة حتى لا تضيع المواد المهمة بين المواقع والقنوات.
• اجمع تغطية واسعة في مكان واحد واقرأ الأخبار داخل Telegram.

<b>موجزي</b>
ناشرو العناوين أولًا بعلامة ★، ثم الباقي بعدد الأخبار. يمكن البحث بالاسم أو الرابط إذا كان المصدر موجودًا في البوت.

الدفع لا يغلق الأخبار المجانية.""",
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

""",
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
    "Market News собирает деловые новости с Reuters, BBC, CNBC, The Guardian, "
    "Bloomberg, Yahoo Finance и тысяч других изданий. Дайджест раз в день, читать можно в боте."
)
ABOUT_EN = (
    "Market News collects business news from Reuters, BBC, CNBC, The Guardian, "
    "Bloomberg, Yahoo Finance and thousands of others. A digest arrives once a day "
    "and can be read inside the bot."
)
SHORT_RU = "Ежедневный дайджест рынков: новости и короткая сводка внутри бота."
SHORT_EN = "A daily market digest: stories and a short brief inside the bot."
ABOUT_AR = (
    "يجمع Market News أخبار الأعمال من Reuters وBBC وCNBC وThe Guardian "
    "وBloomberg وYahoo Finance وآلاف غيرها. يصل الموجز مرة في اليوم ويمكن قراءته داخل البوت."
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
